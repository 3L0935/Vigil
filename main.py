import os
import sys
import signal
import queue
import threading
from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication

# Windows-only: fix DPI awareness before any window is created.
if sys.platform == "win32":
    import ctypes
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        try:
            ctypes.windll.user32.SetProcessDPIAware()
        except Exception:
            pass

_STOP = object()  # sentinel to shut down pipeline workers

from logger import log, log_content
from recorder import Recorder
from transcriber import Transcriber
import transcriber as speech
import privacy
import dictation
import recovery
import clipboard_bridge
from logger import configure_content_logging
import injector
from injector import inject
from hotkey import HotkeyListener
from tray_qt import TrayIcon
import assistant
import service as dbus_service
import tts
from llm_manager import manager as _llm_manager
import config
import database as db
import locales
import setup_utils
from vigil_ui.app import create_engine, dispose_engine
from vigil_ui.i18n import TranslationBridge
from vigil_ui.live_settings import LiveSettingsModel
from vigil_ui.overlay import OverlayModel
from vigil_ui.setup_model import SetupModel

_pipeline_queue   = queue.Queue()
_assistant_queue  = queue.Queue()

recorder    = Recorder()
transcriber = None
tray        = None
widget      = None
root        = None
settings_win = None
setup_win = None
setup_model = None
settings_model = None
hotkey_listener = None
_ui_actions = queue.Queue()
_pipeline_busy = threading.Event()
_model_loading = threading.Event()
_setup_applying = threading.Event()
_record_lock = threading.RLock()

# ── Load persisted settings into config at startup ────────────────────────

def _load_settings():
    """Read settings from DB and apply them to config module."""
    if not db.get_setting("whisper_language", ""):
        db.save_setting("whisper_language", db.get_setting("language", config.LANGUAGE))
    url = db.get_setting("llama_server_url", "")
    if url:
        config.LLAMA_SERVER_URL = url
    vault = db.get_setting("obsidian_vault_path", "")
    if vault:
        config.OBSIDIAN_VAULT_PATH = vault
    lang = db.get_setting("language", "")
    if lang:
        config.LANGUAGE = lang
    pos = db.get_setting("overlay_position", "")
    if pos:
        config.OVERLAY_POSITION = pos
    whisper = db.get_setting("whisper_model", "")
    if whisper:
        config.MODEL_SIZE = whisper
    screen = db.get_setting("overlay_screen", "")
    if screen:
        config.OVERLAY_SCREEN = screen
    config.TTS_ENGINE   = db.get_setting("tts_engine",   "off")
    config.TTS_MODE     = db.get_setting("tts_mode",     "overlay")
    config.TTS_VOICE_FR = db.get_setting("tts_voice_fr", "")
    config.TTS_VOICE_EN = db.get_setting("tts_voice_en", "")
    provider = db.get_setting("llm_provider", "llama_cpp")
    config.LLM_PROVIDER = provider
    ollama_local_url = db.get_setting("ollama_local_url", "")
    if ollama_local_url:
        config.OLLAMA_LOCAL_URL = ollama_local_url
    ollama_cloud_url = db.get_setting("ollama_cloud_url", "")
    if ollama_cloud_url:
        config.OLLAMA_CLOUD_URL = ollama_cloud_url
    ollama_model = db.get_setting("ollama_model", "")
    if ollama_model:
        config.OLLAMA_MODEL = ollama_model
    ollama_key = db.get_setting("ollama_api_key", "")
    config.OLLAMA_API_KEY = ollama_key
    hk_dict = db.get_setting("hotkey_dict", "")
    if hk_dict:
        config.HOTKEY = hk_dict
    hk_asst = db.get_setting("hotkey_assist", "")
    if hk_asst:
        config.ASSISTANT_HOTKEY = hk_asst
    asst_name = db.get_setting("assistant_name", "")
    if asst_name:
        config.ASSISTANT_NAME = asst_name
    timeout = db.get_setting("overlay_answer_timeout", "")
    if timeout:
        try:
            config.OVERLAY_ANSWER_TIMEOUT = int(timeout)
        except ValueError:
            pass

    configure_content_logging(privacy.enabled("log_content"))

def _ui(callback):
    _ui_actions.put(callback)


def _on_whisper_model_change(model_name: str, download: bool = False):
    global transcriber
    if _pipeline_busy.is_set() or recorder.recording or _model_loading.is_set():
        widget.show_message(locales.get("busy"), 3000)
        return False
    config.MODEL_SIZE = model_name
    db.save_setting("whisper_model", model_name)
    _model_loading.set()
    transcriber = None
    status = locales.get("speech_downloading" if download else "speech_loading")
    widget.show_status(status)
    if tray:
        tray.set_tooltip(status)

    def load():
        try:
            if download:
                speech.model_path(model_name, download=True)
            model = Transcriber(model_name)
            _ui(lambda: _finish_model_load(model, None))
        except Exception as exc:
            log.error("Speech model load failed: %s", type(exc).__name__)
            _ui(lambda: _finish_model_load(None, locales.get("speech_missing")))
    threading.Thread(target=load, daemon=True, name="vigil-model-load").start()
    return True


def _finish_model_load(model, error):
    global transcriber
    if _shutting_down:
        return
    transcriber = model
    _model_loading.clear()
    if settings_model:
        settings_model.finish_download()
    if error:
        widget.show_message(error, 8000)
    else:
        widget.show_message(locales.get("speech_ready"), 2500)
    if tray:
        tray.set_tooltip(error or _build_tray_tip())


def _toggle_recording(owner):
    """All hotkey/tray/D-Bus sources use the recorder's single owner state."""
    if _shutting_down or _setup_applying.is_set():
        return
    with _record_lock:
        if recorder.owner == owner:
            audio = recorder.stop(owner)
            if tray:
                tray.set_recording(False)
                tray.set_tooltip(_build_tray_tip())
            if audio is not None and len(audio):
                _pipeline_busy.set()
                widget.show_processing()
                (_pipeline_queue if owner == "dictation" else _assistant_queue).put(audio)
            else:
                widget.hide()
            return
        if recorder.recording or _pipeline_busy.is_set() or _model_loading.is_set():
            widget.show_message(locales.get("busy"), 3000)
            return
        if transcriber is None:
            widget.show_message(locales.get("speech_missing"), 6000)
            return
        tts.stop()
        if not recorder.start(owner):
            return
        widget.hide_answer()
        if owner == "dictation":
            widget.show_recording()
        else:
            widget.show_assistant()
        if tray:
            tray.set_recording(True)
        log.info("Recording started (%s)", owner)


def _recording_expired(owner):
    def update():
        # Another capture may have started while this notification was queued.
        if recorder.recording:
            return
        if tray:
            tray.set_recording(False)
            tray.set_tooltip(_build_tray_tip())
        widget.show_message(locales.get("recording_expired"), 5000)
    _ui(update)


# ── Pipeline workers ──────────────────────────────────────────────────────

def _hide_if_idle():
    if not recorder.recording and not _pipeline_busy.is_set() and not _model_loading.is_set():
        widget.hide()


def _display_dictation(outcome):
    if outcome == "pasted":
        widget.set_expression("happy")
        QTimer.singleShot(1200, _hide_if_idle)
    elif outcome in ("recovered", "failed"):
        widget.show_message(locales.get("paste_" + outcome), 7000)
    else:
        widget.hide()


def _dictation_worker():
    """Transcribe/paste off the UI thread; publish one final UI result."""
    while True:
        item = _pipeline_queue.get()
        if item is _STOP:
            break
        outcome = "empty"
        try:
            log.info("Transcribing (dictation)")
            text = transcriber.transcribe(item)
            if text:
                log_content("Transcribed: %r", text)
                outcome = inject(dictation.postprocess(text))
        except Exception as exc:
            log.error("Dictation pipeline error: %s", type(exc).__name__)
            outcome = "failed"
        finally:
            _ui(lambda result=outcome: _complete_pipeline(lambda: _display_dictation(result)))


def _complete_pipeline(display):
    try:
        if not _shutting_down:
            display()
    finally:
        _pipeline_busy.clear()


def _display_assistant(result, waiting, level):
    widget.set_context_state(level, waiting)
    if result == locales.get("not_understood") or result.startswith(locales.get("error", detail="")):
        widget.set_expression("sad")
        widget.show_message(result, 3000)
    else:
        widget.set_expression("happy")
        if config.TTS_MODE in ("overlay", "both", "off"):
            widget.show_answer(result)
        QTimer.singleShot(1500, _hide_if_idle)


def _assistant_worker():
    """Keep all Qt presentation on the GUI thread."""
    while True:
        item = _assistant_queue.get()
        if item is _STOP:
            break
        display = lambda: widget.hide()
        try:
            log.info("Transcribing (assistant)")
            text = transcriber.transcribe(item)
            if text:
                log_content("Assistant heard: %r", text)
                result = assistant.process(text)
                waiting, level = assistant.is_waiting(), assistant.context_level()
                log_content("Assistant result: %s", result)
                if tts.is_enabled() and (not waiting or assistant.was_last_synthesised()):
                    try:
                        tts.speak(result)
                    except Exception as exc:
                        log.error("TTS error: %s", type(exc).__name__)
                display = lambda r=result, w=waiting, l=level: _display_assistant(r, w, l)
        except privacy.PolicyError as exc:
            display = lambda error=str(exc): widget.show_message(error, 7000)
        except Exception as exc:
            log.error("Assistant pipeline error: %s", type(exc).__name__)
            display = lambda: widget.show_message(locales.get("assistant_error"), 3000)
        finally:
            _ui(lambda callback=display: _complete_pipeline(callback))


# ── Quit & Main ───────────────────────────────────────────────────────────

def _show_settings():
    if settings_win:
        _ui(lambda: settings_win.show())


def _hide_settings():
    if settings_win:
        _ui(lambda: settings_win.hide())


def _clear_assistant_context():
    assistant.reset_context()
    if widget:
        def _do():
            widget.set_context_state(0, False)
            widget.hide_answer()
            widget.hide()
        _ui(_do)


assistant.register_action("open_settings", _show_settings)
assistant.register_action("close_settings", _hide_settings)


_shutting_down = False


def _tray_toggle_dictation():
    _ui(lambda: _toggle_recording("dictation"))


def _tray_toggle_assistant():
    _ui(lambda: _toggle_recording("assistant"))


def _build_tray_tip() -> str:
    mode = locales.get("mode_local" if privacy.local_only() else "mode_network")
    shortcuts = locales.get(
        "tray_shortcuts_status",
        dict_shortcut=config.HOTKEY,
        assist_shortcut=config.ASSISTANT_HOTKEY,
    )
    return f"Vigil — {mode} — {shortcuts}"


def _restart_hotkeys():
    global hotkey_listener
    if os.environ.get("VIGIL_SKIP_HOTKEYS") == "1":
        return True
    if hotkey_listener is None:
        hotkey_listener = HotkeyListener(
            on_press_cb=_tray_toggle_dictation,
            on_release_cb=_tray_toggle_dictation,
            on_assist_press_cb=_tray_toggle_assistant,
            on_assist_release_cb=_tray_toggle_assistant,
        )
        ok = hotkey_listener.start()
    else:
        # Atomic rebind preserves adapter state (KGA signal handler, pynput
        # thread, D-Bus loop) — avoids the transient "no shortcuts" window
        # that full teardown+rebuild used to create.
        ok = hotkey_listener.rebind(
            dict_combo=config.HOTKEY,
            asst_combo=config.ASSISTANT_HOTKEY,
        )
        if not ok:
            log.warning("Hotkey rebind returned partial failure — check logs.")
            if widget:
                widget.show_message(locales.get("hotkey_rebind_failed"), 3000)
    if tray:
        _refresh_tray_labels()
    return ok


def _refresh_tray_labels():
    if tray:
        tray.update_hotkey_labels(
            locales.get("tray_dictate", shortcut=config.HOTKEY),
            locales.get("tray_assistant", shortcut=config.ASSISTANT_HOTKEY),
        )
        tray.set_tooltip(_build_tray_tip())


def _quit():
    global _shutting_down
    _shutting_down = True
    if hotkey_listener:
        try:
            hotkey_listener.stop()
        except Exception:
            pass
    try:
        dbus_service.stop()
    except Exception:
        pass
    log.info("Quitting...")
    clipboard_bridge.close()
    _llm_manager.shutdown()
    _pipeline_queue.put(_STOP)
    _assistant_queue.put(_STOP)
    if tray:
        try:
            tray.stop()
        except Exception:
            pass
    try:
        recorder.stop()
    except Exception:
        pass
    if widget:
        try:
            widget.close()
        except Exception:
            pass
    global transcriber
    transcriber = None
    if root:
        root.quit()
    log.info("Shutdown complete.")


def _cli_reconfigure_hotkeys() -> int:
    """Rebind the saved shortcuts without starting the desktop UI."""
    from hotkey import pick_adapter
    db.init()
    _load_settings()
    try:
        adapter = pick_adapter()
        if not adapter.is_available():
            print("Manual shortcut binding required for this compositor.")
            return 1
        dict_ok = adapter.register("dictate", config.HOTKEY,
                                   command=["vigil-trigger", "dictate"])
        assist_ok = adapter.register("assistant", config.ASSISTANT_HOTKEY,
                                     command=["vigil-trigger", "assistant"])
        result = adapter.name if dict_ok and assist_ok else adapter.name + "-partial"
        db.save_setting("hotkey_adapter", result)
    except Exception as exc:
        print(f"Reconfigure failed: {exc}", file=sys.stderr)
        return 1
    print(f"Hotkey adapter: {result}")
    return 0 if dict_ok and assist_ok else 1


def _cli_uninstall_hotkeys() -> int:
    """`vigil --uninstall-hotkeys` — remove all Vigil-managed bindings.

    Safe to call when Vigil is not running: iterates every known adapter
    that flagged is_available() and clears its managed state. Used by
    uninstall.sh before removing files.
    """
    from hotkey import pick_adapter
    db.init()
    adapter = pick_adapter()
    print(f"Compositor adapter: {adapter.name}")
    removed = 0
    for action_id in list(adapter.list_registered() or ["dictate", "assistant"]):
        if adapter.unregister(action_id):
            removed += 1
            print(f"  - unbound {action_id}")
    try:
        adapter.shutdown()
    except Exception:
        pass
    db.save_setting("hotkey_adapter", "")
    print(f"Done — {removed} action(s) cleared.")
    return 0


def main():
    global transcriber, tray, widget, root, settings_win
    global hotkey_listener, setup_win, setup_model, settings_model

    # CLI utilities short-circuit before Qt/UI initialization.
    if len(sys.argv) > 1:
        arg = sys.argv[1]
        if arg == "--reconfigure-hotkeys":
            sys.exit(_cli_reconfigure_hotkeys())
        if arg == "--uninstall-hotkeys":
            sys.exit(_cli_uninstall_hotkeys())
        if arg in ("-h", "--help"):
            print(
                "Vigil — voice dictation and AI assistant\n\n"
                "Usage:\n"
                "  vigil                       run the app\n"
                "  vigil --reconfigure-hotkeys rebind saved compositor shortcuts\n"
                "  vigil --uninstall-hotkeys   remove every vigil-managed binding\n"
                "  vigil -h | --help           show this help\n"
            )
            sys.exit(0)

    db.init()
    first_run = setup_utils.needs_first_run()
    # Fail fast if another Vigil is already running — avoid wasting ~1s on
    # Whisper load + widget/tray init before the bus name collision would kick
    # us out anyway.
    if dbus_service.is_running():
        log.info("Another Vigil instance is already running — exiting.")
        sys.exit(0)
    _load_settings()
    recovery.prune()
    if not first_run:
        from hotkey.kde import preflight_grab_install
        preflight_grab_install()
    # KWin/XWayland supports positioned, non-activating overlays. Native
    # XDG Shell does not provide client-controlled top-level placement.
    if (sys.platform.startswith("linux") and os.environ.get("XDG_SESSION_TYPE") == "wayland"
            and os.environ.get("XDG_CURRENT_DESKTOP", "").lower().find("kde") >= 0
            and os.environ.get("DISPLAY")):
        os.environ.setdefault("QT_QPA_PLATFORM", "xcb")

    root = QApplication.instance() or QApplication(sys.argv)
    root.setApplicationName("Vigil")
    root.setQuitOnLastWindowClosed(False)
    translator = TranslationBridge(config.LANGUAGE)
    widget = OverlayModel()
    widget.set_close_callback(assistant.reset_context)

    def _redo_setup():
        if recorder.recording or _pipeline_busy.is_set() or _model_loading.is_set():
            widget.show_message(locales.get("busy"), 3000)
            return
        setup_model.reopen()
        settings_win.hide()
        setup_win.show()
        setup_win.raise_()
        setup_win.requestActivate()

    settings_model = LiveSettingsModel(
        translator, on_whisper_change=_on_whisper_model_change,
        on_hotkey_change=_restart_hotkeys,
        on_language_change=_refresh_tray_labels,
        on_redo_setup=_redo_setup,
    )
    setup_model = SetupModel(translator, initial=first_run)
    engine, translator = create_engine(
        root, language=config.LANGUAGE, visible=False, translator=translator,
        settings_model=settings_model, overlay_model=widget, setup_model=setup_model,
    )
    if len(engine.rootObjects()) != 3:
        log.error("Fold UI failed to load")
        return 1
    settings_win, _, setup_win = engine.rootObjects()
    root._vigil_engine = engine
    root._vigil_settings_model = settings_model
    root._vigil_setup_model = setup_model
    root._vigil_overlay = widget

    level_sample = [0.0]
    recorder.on_level = lambda rms: level_sample.__setitem__(0, min(1.0, rms * 8))
    recorder.on_mic_error = lambda msg: _ui(lambda: widget.show_message(msg, 4000))
    recorder.on_timeout = _recording_expired

    def _pump_ui():
        if _shutting_down:
            return
        for _ in range(30):
            try:
                callback = _ui_actions.get_nowait()
            except queue.Empty:
                break
            try:
                callback()
            except Exception as exc:
                log.error("UI callback failed: %s", type(exc).__name__)
        if recorder.recording:
            widget.update_level(level_sample[0])

    pump = QTimer(root)
    pump.setInterval(50)
    pump.timeout.connect(_pump_ui)
    pump.start()

    def _start_runtime():
        global tray, hotkey_listener
        if first_run:
            from hotkey.kde import preflight_grab_install
            preflight_grab_install()
        _load_settings()
        tts.init()
        if not dbus_service.start(on_dictate=_tray_toggle_dictation,
                                  on_assistant=_tray_toggle_assistant):
            log.error("D-Bus service could not start")
            return False
        if os.environ.get("VIGIL_SKIP_HOTKEYS") != "1":
            hotkey_listener = HotkeyListener(
                on_press_cb=_tray_toggle_dictation,
                on_release_cb=_tray_toggle_dictation,
                on_assist_press_cb=_tray_toggle_assistant,
                on_assist_release_cb=_tray_toggle_assistant,
            )
            if not hotkey_listener.start():
                log.warning("Shortcut activation was incomplete")
                if first_run:
                    hotkey_listener.stop()
                    hotkey_listener = None
                    dbus_service.stop()
                    return False
        tray = TrayIcon(on_quit=_quit, on_show_settings=_show_settings,
                        on_dictate=_tray_toggle_dictation,
                        on_assist=_tray_toggle_assistant,
                        on_stop_tts=tts.stop,
                        on_clear_context=_clear_assistant_context)
        tray.start()
        translator.languageChanged.connect(tray.retranslate)
        clipboard_bridge.initialize()
        _refresh_tray_labels()
        warning = injector.check_deps()
        if warning:
            log.warning("Injection deps: %s", warning.replace("\n", " | "))
            QTimer.singleShot(2000, lambda: widget.show_message(warning, 6000))
        injector.prewarm()
        _on_whisper_model_change(config.MODEL_SIZE)
        threading.Thread(target=_dictation_worker, daemon=True).start()
        threading.Thread(target=_assistant_worker, daemon=True).start()
        log.info("Ready. %s", _build_tray_tip())
        return True

    def _activate_setup(initial):
        if recorder.recording or _pipeline_busy.is_set() or _model_loading.is_set():
            return False
        _setup_applying.set()
        try:
            if initial:
                if not _start_runtime():
                    return False
            else:
                _load_settings()
                tts.init()
                if not _restart_hotkeys():
                    return False
                from llm_manager import manager
                manager.shutdown()
                assistant.reload_backend()
                _on_whisper_model_change(config.MODEL_SIZE)
            settings_model.reload()
            setup_win.hide()
            return True
        finally:
            _setup_applying.clear()

    def _rollback_setup(initial):
        try:
            _load_settings()
            tts.init()
            if not initial:
                _restart_hotkeys()
                assistant.reload_backend()
        finally:
            settings_model.reload()

    def _setup_cancelled(initial):
        setup_win.hide()
        if initial:
            _quit()
        else:
            settings_win.show()

    setup_model.set_activation_callbacks(_activate_setup, _rollback_setup)
    setup_model.cancelled.connect(_setup_cancelled)
    if not first_run:
        if not _start_runtime():
            return 1

    def _signal_handler(sig, frame):
        log.info("Signal %s received — shutting down cleanly.", sig)
        _quit()

    signal.signal(signal.SIGTERM, _signal_handler)
    signal.signal(signal.SIGINT, _signal_handler)
    try:
        return root.exec()
    finally:
        dispose_engine(engine)


if __name__ == "__main__":
    main()
