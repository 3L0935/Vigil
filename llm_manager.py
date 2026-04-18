import os
import subprocess
import threading
import time
import urllib.parse
from pathlib import Path

import httpx

import database as db
from logger import log


class LlamaServerManager:
    def __init__(self):
        self._process: subprocess.Popen | None = None
        self._timer: threading.Timer | None = None
        self._lock = threading.RLock()

    # ── DB-backed properties (read at call time) ──────────────────────────

    def _is_managed(self) -> bool:
        return db.get_setting("llama_server_managed", "true") == "true"

    def _bin_path(self) -> str:
        return db.get_setting("llama_server_bin", "")

    def _model_path(self) -> str:
        return db.get_setting("llama_model", "")

    def _timeout_sec(self) -> int:
        try:
            return int(db.get_setting("llama_unload_timeout", "120"))
        except ValueError:
            return 120

    def _gpu_layers(self) -> int:
        val = db.get_setting("llm_gpu_layers", "off")
        if val in ("off", "", "-1"):
            return -1
        try:
            return int(val)
        except ValueError:
            return -1

    def _server_url(self) -> str:
        # DB is the source of truth for the URL (set by settings_window / setup).
        # Hardcoded default matches config.LLAMA_SERVER_URL; avoids importing
        # config here (config.py imports pynput which fails in headless test envs).
        return db.get_setting("llama_server_url", "http://localhost:8080")

    # ── Public API ────────────────────────────────────────────────────────

    def ensure_running(self):
        """Start server if needed, then reset inactivity timer."""
        with self._lock:
            if self._is_managed():
                if self._process is None or self._process.poll() is not None:
                    self._spawn()
            else:
                self._wait_health(timeout=5)
            self._reset_timer()

    def shutdown(self):
        """Immediately stop the managed server process."""
        with self._lock:
            if self._timer is not None:
                self._timer.cancel()
                self._timer = None
            if self._process is not None:
                self._process.terminate()
                try:
                    self._process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    self._process.kill()
                self._process = None
                log.info("llama-server stopped.")

    # ── Internal ──────────────────────────────────────────────────────────

    def _spawn(self):
        bin_path = self._bin_path()
        model_path = self._model_path()
        if not bin_path or not model_path:
            raise RuntimeError(
                "llama_server_bin or llama_model not configured — configure llama_server_bin and llama_model in settings."
            )
        port = urllib.parse.urlparse(self._server_url()).port or 8080
        cmd = [bin_path, "--model", model_path,
               "--port", str(port), "--host", "127.0.0.1"]
        ngl = self._gpu_layers()
        if ngl >= 0:
            cmd += ["-ngl", str(ngl)]
        log.info("Spawning llama-server: %s", " ".join(cmd))

        # Ensure shared libs in the same dir as the binary are found at runtime
        bin_dir = str(Path(bin_path).parent)
        env = os.environ.copy()
        existing = env.get("LD_LIBRARY_PATH", "")
        if bin_dir not in existing.split(":"):
            env["LD_LIBRARY_PATH"] = f"{bin_dir}:{existing}" if existing else bin_dir

        self._process = subprocess.Popen(
            cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,  # own process group → clean SIGKILL of all children
            env=env,
        )
        try:
            self._wait_health(timeout=30)
        except RuntimeError:
            self._process.terminate()
            try:
                self._process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self._process.kill()
            self._process = None
            raise
        log.info("llama-server ready.")

    def _wait_health(self, timeout: int):
        health_url = self._server_url().rstrip("/") + "/health"
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            try:
                r = httpx.get(health_url, timeout=2)
                if r.status_code == 200:
                    return
            except Exception:
                pass
            time.sleep(0.5)
        raise RuntimeError(f"llama-server not ready after {timeout}s")

    def _reset_timer(self):
        if self._timer is not None:
            self._timer.cancel()
        timeout = self._timeout_sec()
        if timeout <= 0:
            return
        self._timer = threading.Timer(timeout, self._auto_shutdown)
        self._timer.daemon = True
        self._timer.start()

    def _auto_shutdown(self):
        with self._lock:
            if self._process is not None:
                log.info("llama-server auto-unloaded after inactivity.")
                self.shutdown()


# Module-level singleton
manager = LlamaServerManager()
