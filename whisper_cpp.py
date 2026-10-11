"""whisper.cpp backend: GGML weights, a managed server, and a transcriber.

Measured on an RX 7900 XT (Vulkan, large-v3, French): a resident model answers
in about 165 ms for a 5 s dictation, against roughly 1.45 s when a
whisper-cli process is spawned per request. One server is therefore kept warm
across dictations -- but not forever: the model weighs 3.1 GB of video memory,
and one that never releases it leaves the user closing the whole application
to get the memory back. It is released after a spell without dictation, see
``whisper_unload_timeout``.

The server is only ever bound to the loopback interface.
"""

import os
import socket
import subprocess
import tempfile
import threading
import time
import wave
from pathlib import Path

import numpy as np

from data_paths import DATA_DIR
from dictation import initial_prompt, recognition_language
from logger import log

WHISPER_DIR = DATA_DIR / "whisper"
SERVER_NAME = "whisper-server"
CLI_NAME = "whisper-cli"
MODEL_DIR = WHISPER_DIR
MODEL_REPO = "ggerganov/whisper.cpp"

# Multilingual GGML weights published by ggerganov/whisper.cpp. The matching
# "*.en.bin" files are English-only and deliberately not listed.
MODEL_FILES = {
    "tiny": "ggml-tiny.bin",
    "base": "ggml-base.bin",
    "small": "ggml-small.bin",
    "medium": "ggml-medium.bin",
    "large-v3": "ggml-large-v3.bin",
}

_START_TIMEOUT = 180.0
_REQUEST_TIMEOUT = 120.0


class ModelUnavailable(RuntimeError):
    pass


def server_path() -> Path:
    return WHISPER_DIR / SERVER_NAME


def is_installed() -> bool:
    binary = server_path()
    return binary.is_file() and binary.stat().st_size > 0 and os.access(binary, os.X_OK)


def model_path(model: str, *, download: bool = False) -> str:
    """Resolve the GGML weights, downloading only when explicitly asked."""
    name = MODEL_FILES.get(model)
    if name is None:
        raise ModelUnavailable("No whisper.cpp model for " + str(model))
    target = MODEL_DIR / name
    if target.is_file() and target.stat().st_size > 0:
        return str(target)
    if not download:
        raise ModelUnavailable("Speech model is not available locally")
    from huggingface_hub import hf_hub_download

    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    cached = Path(hf_hub_download(repo_id=MODEL_REPO, filename=name))
    if not cached.is_file() or not cached.stat().st_size:
        raise ModelUnavailable("Speech model download is empty")
    return str(cached)


def _free_port() -> int:
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        return probe.getsockname()[1]


def _server_env() -> dict:
    """The bundled shared libraries live next to the binary."""
    env = dict(os.environ)
    existing = env.get("LD_LIBRARY_PATH", "")
    env["LD_LIBRARY_PATH"] = str(WHISPER_DIR) + (os.pathsep + existing if existing else "")
    return env


def write_wav(audio: np.ndarray, path: Path) -> None:
    """The server accepts a multipart file, so the PCM buffer becomes a WAV."""
    clipped = np.clip(np.asarray(audio, dtype=np.float32), -1.0, 1.0)
    pcm = (clipped * 32767).astype("<i2")
    with wave.open(str(path), "wb") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(16000)
        handle.writeframes(pcm.tobytes())


# Seconds of silence before the resident model is released. Long enough to
# serve a burst of dictations without paying the spawn again, short enough that
# 3.1 GB are not held all day. 0 keeps the server loaded for good.
DEFAULT_UNLOAD_SEC = 600


class Server:
    """One whisper-server process, started on first use and kept warm."""

    def __init__(self, model: str, *, gpu: bool = True, threads: int | None = None):
        self._model = model
        self._gpu = gpu
        self._threads = threads or max(4, (os.cpu_count() or 8) // 2)
        self._process = None
        self._port = 0
        self._lock = threading.Lock()
        self._timer: threading.Timer | None = None
        self._generation = 0

    @property
    def port(self) -> int:
        return self._port

    def _command(self, port: int) -> list[str]:
        command = [
            str(server_path()),
            "-m", model_path(self._model),
            "-l", recognition_language() or "auto",
            "-t", str(self._threads),
            "-nt",
            "--host", "127.0.0.1",
            "--port", str(port),
        ]
        if not self._gpu:
            command.append("-ng")
        return command

    def _probe(self, port: int, deadline: float) -> bool:
        import httpx

        while time.monotonic() < deadline:
            if self._process is not None and self._process.poll() is not None:
                return False
            try:
                with httpx.Client(timeout=2, trust_env=False) as client:
                    if client.get(f"http://127.0.0.1:{port}/").status_code < 500:
                        return True
            except Exception:
                time.sleep(0.25)
        return False

    def ensure_running(self) -> int:
        with self._lock:
            if self._process is not None and self._process.poll() is None and self._port:
                self._reset_timer()
                return self._port
            if not is_installed():
                raise ModelUnavailable("whisper-server is not installed")
            port = _free_port()
            log.info("Starting whisper-server (%s, gpu=%s)", self._model, self._gpu)
            self._process = subprocess.Popen(
                self._command(port), env=_server_env(), cwd=str(WHISPER_DIR),
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            )
            self._port = port
            if not self._probe(port, time.monotonic() + _START_TIMEOUT):
                self.close()
                raise ModelUnavailable("whisper-server did not become ready")
            self._reset_timer()
            return port

    def _timeout_sec(self) -> int:
        import database as db
        try:
            return int(db.get_setting("whisper_unload_timeout", str(DEFAULT_UNLOAD_SEC)))
        except ValueError:
            return DEFAULT_UNLOAD_SEC

    def _reset_timer(self) -> None:
        if self._timer is not None:
            self._timer.cancel()
        self._generation += 1
        generation = self._generation
        timeout = self._timeout_sec()
        if timeout <= 0:
            self._timer = None
            return
        self._timer = threading.Timer(timeout, lambda: self._auto_shutdown(generation))
        self._timer.daemon = True
        self._timer.start()

    def _auto_shutdown(self, generation: int) -> None:
        """Release the model, unless a dictation came in and re-armed the timer.

        The lock is deliberately released before closing: close() takes it, and
        it is a plain Lock, so acquiring it twice from this thread would
        deadlock the timer and the model would never be released.
        """
        with self._lock:
            if generation != self._generation:
                return
        log.info("whisper-server auto-unloaded after inactivity.")
        self.close()

    def close(self) -> None:
        with self._lock:
            process, self._process = self._process, None
            self._port = 0
        if process is None or process.poll() is not None:
            return
        try:
            process.terminate()
            process.wait(timeout=10)
        except Exception:
            try:
                process.kill()
            except Exception:
                pass


class WhisperCppTranscriber:
    """Same interface as ``transcriber.Transcriber``: numpy in, text out."""

    def __init__(self, model_name: str | None = None, *, gpu: bool | None = None):
        import config

        self._model = model_name or config.MODEL_SIZE
        model_path(self._model)  # fail early, before a dictation is attempted
        self._gpu = config.STT_GPU if gpu is None else bool(gpu)
        self._server = Server(self._model, gpu=self._gpu)

    @property
    def server(self) -> Server:
        return self._server

    def transcribe(self, audio_np: np.ndarray) -> str:
        import httpx

        port = self._server.ensure_running()
        handle = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
        spool = Path(handle.name)
        handle.close()
        try:
            write_wav(audio_np, spool)
            data = {"response_format": "text", "temperature": "0.0"}
            prompt = initial_prompt()
            if prompt:
                data["prompt"] = prompt
            with httpx.Client(timeout=_REQUEST_TIMEOUT, trust_env=False) as client:
                with open(spool, "rb") as stream:
                    response = client.post(
                        f"http://127.0.0.1:{port}/inference",
                        files={"file": (spool.name, stream, "audio/wav")},
                        data=data,
                    )
                response.raise_for_status()
                return response.text.strip()
        finally:
            spool.unlink(missing_ok=True)

    def close(self) -> None:
        self._server.close()
