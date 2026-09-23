"""The Fold setup draft cannot alter active settings before Finish."""

import os
import threading
import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

import database as db
from vigil_ui.i18n import TranslationBridge
from vigil_ui.setup_model import SetupModel
from vigil_ui.setup_service import prepare
from vigil_ui import setup_service


def test_ollama_setup_prepares_speech_without_committing_draft(monkeypatch, tmp_path):
    QApplication.instance() or QApplication([])
    monkeypatch.setattr(db, "_DB_PATH", str(tmp_path / "vigil.db"))
    db.init()
    translator = TranslationBridge("en")
    wizard = SetupModel(translator, initial=True)
    wizard.setValue("language", "fr")
    wizard.setValue("llm_provider", "ollama_local")
    wizard.setValue("ollama_model", "qwen3.5:latest")
    import transcriber
    downloaded = []
    monkeypatch.setattr(transcriber, "model_path", lambda name, *, download=False:
                        downloaded.append((name, download)) or str(tmp_path / "speech"))
    assert db.get_setting("language", "") == ""
    values = prepare(dict(wizard._draft), threading.Event(), lambda _: None)
    assert values["ollama_model"] == "qwen3.5:latest"
    assert values["setup_complete"] == "1"
    assert downloaded == [("base", True)]
    assert db.get_setting("setup_complete", "") == ""
    wizard.cancel()
    assert translator.language == "en"


def test_existing_llama_assets_are_reused_without_download(monkeypatch, tmp_path):
    binary = tmp_path / "llama-server"
    binary.write_bytes(b"binary")
    binary.chmod(0o755)
    model = tmp_path / "model.gguf"
    model.write_bytes(b"model")
    values = {
        "llm_provider": "llama_cpp",
        "llama_server_bin": str(binary),
        "llama_model": str(model),
        "hotkey_dict": "Ctrl+Alt+W",
        "hotkey_assist": "Ctrl+Alt+R",
        "tts_mode": "overlay",
    }
    result = prepare(values, threading.Event(), lambda _: None)
    assert result["llama_model"] == str(model)
    assert result["llama_server_bin"] == str(binary)
    assert result["llama_server_managed"] == "false"
    assert result["setup_complete"] == "1"


def test_reconfigure_discards_missing_legacy_paths(monkeypatch, tmp_path):
    QApplication.instance() or QApplication([])
    monkeypatch.setattr(db, "_DB_PATH", str(tmp_path / "vigil.db"))
    db.init()
    db.save_settings({
        "llama_server_bin": str(tmp_path / "writher/llama/llama-server"),
        "llama_model": str(tmp_path / "writher/models/Qwen_Qwen3.5-9B-Q4_K_M.gguf"),
    })
    wizard = SetupModel(TranslationBridge("fr"), initial=False)
    assert wizard.value("use_existing_binary") == "false"
    assert wizard.value("use_existing_model") == "false"
    assert wizard.value("llama_server_bin") == ""
    assert wizard.value("llama_model") == ""
    assert wizard.value("llama_catalog_model") == "Qwen_Qwen3.5-9B-Q4_K_M.gguf"


def test_catalog_mode_ignores_stale_paths_and_reports_download_progress(monkeypatch, tmp_path):
    binary = tmp_path / "vigil/llama/llama-server"
    model = tmp_path / "vigil/models/model.gguf"
    seen = []

    def install_binary(backend, cancelled, progress=None):
        progress(50, 100)
        return binary

    def install_model(choice, cancelled, progress=None):
        assert choice == "Qwen_Qwen3.5-9B-Q4_K_M.gguf"
        progress(75, 100)
        return model

    monkeypatch.setattr(setup_service, "install_binary", install_binary)
    monkeypatch.setattr(setup_service, "install_model", install_model)
    result = prepare({
        "llm_provider": "llama_cpp",
        "llama_server_bin": "/old/writher/llama/llama-server",
        "llama_model": "/old/writher/models/model.gguf",
        "llama_catalog_model": "Qwen_Qwen3.5-9B-Q4_K_M.gguf",
        "use_existing_binary": "false", "use_existing_model": "false",
        "hotkey_dict": "Ctrl+Alt+W", "hotkey_assist": "Ctrl+Alt+R",
        "tts_mode": "overlay",
    }, threading.Event(), lambda stage: seen.append(stage),
        lambda stage, done, total: seen.append((stage, done, total)))
    assert result["llama_server_bin"] == str(binary)
    assert result["llama_model"] == str(model)
    assert "use_existing_binary" not in result
    assert seen == ["binary", ("binary", 50, 100), "model", ("model", 75, 100)]


def test_cancelled_llama_prepare_never_returns_setup_complete(tmp_path):
    binary = tmp_path / "llama-server"
    binary.write_bytes(b"binary")
    binary.chmod(0o755)
    model = tmp_path / "model.gguf"
    model.write_bytes(b"model")
    cancelled = threading.Event()
    cancelled.set()
    with pytest.raises(setup_service.SetupCancelled):
        prepare({
            "llm_provider": "llama_cpp", "llama_server_bin": str(binary),
            "llama_model": str(model), "hotkey_dict": "Ctrl+Alt+W",
            "hotkey_assist": "Ctrl+Alt+R", "tts_mode": "overlay",
        }, cancelled, lambda _: None)


def test_spoken_setup_requires_a_voice_for_active_language():
    with pytest.raises(ValueError, match="selected language"):
        prepare({
            "llm_provider": "ollama_local", "ollama_local_url": "http://localhost:11434",
            "ollama_model": "qwen3.5:latest", "local_only": "true",
            "hotkey_dict": "Ctrl+Alt+W", "hotkey_assist": "Ctrl+Alt+R",
            "tts_mode": "both", "language": "fr", "tts_voice_fr": "",
        }, threading.Event(), lambda _: None)


def test_speech_download_failure_prevents_setup_completion(monkeypatch):
    import transcriber
    def unavailable(name, *, download=False):
        raise transcriber.ModelUnavailable("Speech model is not available locally")
    monkeypatch.setattr(transcriber, "model_path", unavailable)
    stages = []
    with pytest.raises(transcriber.ModelUnavailable):
        prepare({
            "llm_provider": "ollama_local", "ollama_local_url": "http://localhost:11434",
            "ollama_model": "qwen3.5:latest", "local_only": "true",
            "hotkey_dict": "Ctrl+Alt+W", "hotkey_assist": "Ctrl+Alt+R",
            "whisper_model": "medium", "tts_mode": "overlay",
        }, threading.Event(), stages.append)
    assert stages == ["speech"]


def test_setup_error_keeps_the_failed_download_stage():
    QApplication.instance() or QApplication([])
    wizard = SetupModel(TranslationBridge("fr"), initial=True)
    wizard._set_progress("binary")
    wizard._receive_prepared({}, "HTTP Error 403")
    assert "llama-server" in wizard.status
    assert "échoué" in wizard.status


def test_finish_restores_previous_settings_when_activation_fails(monkeypatch, tmp_path):
    QApplication.instance() or QApplication([])
    monkeypatch.setattr(db, "_DB_PATH", str(tmp_path / "vigil.db"))
    db.init()
    db.save_settings({"language": "en", "setup_complete": "1"})
    wizard = SetupModel(TranslationBridge("en"), initial=False)
    wizard._page = 7
    wizard._ready = True
    wizard._prepared_values = {"language": "fr", "setup_complete": "1"}
    rolled_back = []
    wizard.set_activation_callbacks(lambda initial: False,
                                    lambda initial: rolled_back.append(initial))
    wizard.next()
    assert db.get_setting("language") == "en"
    assert rolled_back == [False]
    assert wizard.page == 7
    assert wizard.status
