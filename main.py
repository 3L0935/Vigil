import os
import sys
import signal
import queue
import threading

try:
    import tkinter as tk
except ImportError as _tk_err:
    print(
        f"ERROR: cannot import tkinter — {_tk_err}\n"
        "Install the system Tk package, then retry:\n"
        "  Arch / Manjaro / CachyOS : sudo pacman -S tk\n"
        "  Ubuntu / Debian           : sudo apt install python3-tk\n"
        "  Fedora                    : sudo dnf install python3-tkinter\n"
    )
    sys.exit(1)

import customtkinter as ctk
ctk.set_appearance_mode("dark")

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

from logger import log
from recorder import Recorder
from transcriber import Transcriber
import injector
from injector import inject
from hotkey import HotkeyListener
from tray_qt import TrayIcon
from widget import RecordingWidget
import assistant
import service as dbus_service
import tts
from llm_manager import manager as _llm_manager
import config
import database as db
import locales
from settings_window import SettingsWindow
import setup_utils

_pipeline_queue   = queue.Queue()
_assistant_queue  = queue.Queue()

recorder    = Recorder()
transcriber = None
tray        = None
widget      = None
root        = None
settings_win = None
hotkey_listener = None

# ── Load persisted settings into config at startup ────────────────────────

def _load_settings():
    """Read settings from DB and apply them to config module."""
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


def _on_whisper_model_change(model_name: str):
    global transcriber
    config.MODEL_SIZE = model_name
    db.save_setting("whisper_model", model_name)
    log.info("Whisper model changed to %s, reloading...", model_name)
    transcriber = Transcriber()
    log.info("Whisper model reloaded.")


# ── Dictation callbacks (AltGr) ──────────────────────────────────────────

def _on_hotkey_press():
    if _shutting_down:
        return
    tts.stop()
    if not recorder.start():
        return
    if tray:
        tray.set_recording(True)
    if widget:
        widget.hide_answer()
        widget.show_recording()
    log.info("Recording started (dictation).")


def _on_hotkey_release():
    if _shutting_down:
        return
    audio = recorder.stop()
    if tray:
        tray.set_recording(False)
    log.info("Recording stopped (dictation).")

    if audio is not None and len(audio) > 0:
        if widget:
            widget.show_processing()
        _pipeline_queue.put(audio)
    else:
        if widget:
            widget.hide()
        log.info("Empty audio, skipping.")


# ── Assistant callbacks (Ctrl+R) ──────────────────────────────────────────

def _on_assist_press():
    if _shutting_down:
        return
    tts.stop()
    if not recorder.start():
        return
    if tray:
        tray.set_recording(True)
    if widget:
        widget.hide_answer()
        widget.show_assistant()
        widget.set_expression("listening")
    log.info("Recording started (assistant).")


def _on_assist_release():
    if _shutting_down:
        return
    audio = recorder.stop()
    if tray:
        tray.set_recording(False)
    log.info("Assistant recording stopped.")

    if audio is not None and len(audio) > 0:
        if widget:
            widget.show_processing()
            widget.set_expression("thinking")
        _assistant_queue.put(audio)
    else:
        if widget:
            widget.hide()
        log.info("Empty audio, skipping.")


# ── Pipeline workers ──────────────────────────────────────────────────────

def _dictation_worker():
    """Transcribe audio and paste the result into the active application."""
    while True:
        item = _pipeline_queue.get()
        if item is _STOP:
            break
        try:
            log.info("Transcribing (dictation)...")
            text = transcriber.transcribe(item)
            if text:
                log.info("Transcribed: %r", text)
                inject(text)
                if widget:
                    widget.set_expression("happy")
                    # Hold "Done!" long enough to register — 500ms proved too
                    # brief in practice once the 252ms fade-out is added on top.
                    root.after(1200, widget.hide)
            else:
                log.info("No speech detected.")
                if widget:
                    widget.hide()
        except Exception as exc:
            log.error("Dictation pipeline error: %s", exc)
            if widget:
                widget.hide()


def _assistant_worker():
    """Transcribe audio, send to Ollama, and execute the returned action."""
    while True:
        item = _assistant_queue.get()
        if item is _STOP:
            break
        try:
            log.info("Transcribing (assistant)...")
            text = transcriber.transcribe(item)
            if not text:
                log.info("No speech detected.")
                if widget:
                    widget.hide()
                continue

            log.info("Assistant heard: %r", text)
            result  = assistant.process(text)
            waiting = assistant.is_waiting()
            level   = assistant.context_level()
            log.info("Assistant result: %s (waiting=%s, level=%d)", result, waiting, level)

            if widget:
                widget.set_context_state(level, waiting)

            if result == locales.get("not_understood") or result.startswith(locales.get("error", detail="")):
                if widget:
                    widget.set_expression("sad")
                    widget.show_message(result, 3000)
            else:
                if widget:
                    widget.set_expression("happy")
                # TTS rule: skip while waiting on a numbered reply unless the
                # answer was synthesised (search_files etc. — those go through
                # a paraphrase pass and read fine aloud). Raw lists like
                # app_candidates stay silent.
                tts_ok = (not waiting) or assistant.was_last_synthesised()
                if tts.is_enabled() and tts_ok:
                    try:
                        tts.speak(result)
                    except Exception as tts_exc:
                        log.error("TTS error: %s", tts_exc)
                if config.TTS_MODE in ("overlay", "both", "off"):
                    if widget:
                        widget.show_answer(result)
                if widget:
                    # Keep the pill on "Done!" briefly — tts.speak is now async
                    # (commit 7ac42cd) so it no longer blocks here, meaning the
                    # happy state would otherwise be invisible.
                    root.after(1500, widget.hide)

        except Exception as exc:
            log.error("Assistant pipeline error: %s", exc)
            if widget:
                widget.set_expression("error")
                widget.show_message(locales.get("assistant_error"), 2000)


# ── Quit & Main ───────────────────────────────────────────────────────────

def _show_settings():
    if settings_win:
        root.after(0, lambda: settings_win.show())


def _hide_settings():
    if settings_win:
        root.after(0, lambda: settings_win.hide())


def _clear_assistant_context():
    assistant.reset_context()
    if widget and root:
        def _do():
            widget.set_context_state(0, False)
            widget.hide_answer()
            widget.hide()
        root.after(0, _do)


assistant.register_action("open_settings", _show_settings)
assistant.register_action("close_settings", _hide_settings)


# Tray fallback for Wayland (no global hotkeys available)
_tray_dict_recording = False
_tray_assist_recording = False
_shutting_down = False


def _tray_toggle_dictation():
    global _tray_dict_recording
    if not _tray_dict_recording:
        _tray_dict_recording = True
        _on_hotkey_press()
    else:
        _tray_dict_recording = False
        _on_hotkey_release()


def _tray_toggle_assistant():
    global _tray_assist_recording
    if not _tray_assist_recording:
        _tray_assist_recording = True
        _on_assist_press()
    else:
        _tray_assist_recording = False
        _on_assist_release()


def _build_tray_tip() -> str:
    return f"Vigil — {config.HOTKEY}=dictate, {config.ASSISTANT_HOTKEY}=assistant"


def _restart_hotkeys():
    global hotkey_listener
    if hotkey_listener is None:
        hotkey_listener = HotkeyListener(
            on_press_cb=_on_hotkey_press,
            on_release_cb=_on_hotkey_release,
            on_assist_press_cb=_on_assist_press,
            on_assist_release_cb=_on_assist_release,
        )
        hotkey_listener.start()
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
                widget.show_message("Hotkey rebind failed — see logs", 3000)
    if tray:
        tray.set_tooltip(_build_tray_tip())
        tray.update_hotkey_labels(
            f"Dictate ({config.HOTKEY})",
            f"Assistant ({config.ASSISTANT_HOTKEY})",
        )


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
    if root:
        def _destroy():
            global transcriber
            try:
                transcriber = None  # release faster-whisper before exit to avoid semaphore leak
            except Exception:
                pass
            try:
                root.destroy()
            except Exception:
                pass
            os._exit(0)
        try:
            root.after(0, _destroy)
        except Exception:
            os._exit(0)
    log.info("Shutdown complete.")


def _cli_reconfigure_hotkeys() -> int:
    """`vigil --reconfigure-hotkeys` — re-run the hotkey wizard standalone.

    Useful after a WM switch or when the initial first_run bind failed.
    Does not start the full app.
    """
    import first_run
    db.init()
    _load_settings()
    try:
        result = first_run.setup_hotkeys()
    except Exception as exc:
        print(f"Reconfigure failed: {exc}", file=sys.stderr)
        return 1
    print(f"Hotkey adapter: {result}")
    return 0


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
    global hotkey_listener

    # CLI utilities short-circuit before the full Tk/UI init.
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
                "  vigil --reconfigure-hotkeys re-run the compositor hotkey wizard\n"
                "  vigil --uninstall-hotkeys   remove every vigil-managed binding\n"
                "  vigil -h | --help           show this help\n"
            )
            sys.exit(0)

    db.init()
    if setup_utils.needs_first_run():
        script = str(setup_utils.REPO_DIR / "first_run.py")
        launched = setup_utils.launch_in_terminal(f'uv run python "{script}"')
        if not launched:
            print(
                "First-run setup required but no terminal found.\n"
                "Run manually: uv run python first_run.py",
                flush=True,
            )
        sys.exit(0)
    # Fail fast if another Vigil is already running — avoid wasting ~1s on
    # Whisper load + widget/tray init before the bus name collision would kick
    # us out anyway.
    if dbus_service.is_running():
        log.info("Another Vigil instance is already running — exiting.")
        sys.exit(0)
    _load_settings()

    # KDE Plasma 6 Wayland workaround: the first vigil process of a session
    # registers KGA actions but never installs the Wayland keyboard grab.
    # Re-exec from a fresh D-Bus client name so the actual grab installs.
    # No-op on every other compositor and on subsequent same-session vigils.
    from hotkey.kde import preflight_grab_install
    preflight_grab_install()

    tts.init()

    root = tk.Tk()
    root.withdraw()

    widget = RecordingWidget(root)
    widget.set_close_callback(lambda: assistant.reset_context())
    settings_win = SettingsWindow(root, on_whisper_change=_on_whisper_model_change,
                                   on_hotkey_change=_restart_hotkeys)

    recorder.on_level = lambda rms: widget.update_level(min(1.0, rms * 8))
    recorder.on_mic_error = lambda msg: widget.show_message(msg, 4000)

    tray = TrayIcon(on_quit=_quit, on_show_settings=_show_settings,
                    on_dictate=_tray_toggle_dictation,
                    on_assist=_tray_toggle_assistant,
                    on_stop_tts=tts.stop,
                    on_clear_context=_clear_assistant_context)
    tray.start()
    tray.update_hotkey_labels(
        f"Dictate ({config.HOTKEY})",
        f"Assistant ({config.ASSISTANT_HOTKEY})",
    )

    tray.set_tooltip(_build_tray_tip())

    # Check dictation injection tools
    _inj_warn = injector.check_deps()
    if _inj_warn:
        log.warning("Injection deps: %s", _inj_warn.replace("\n", " | "))
        root.after(2000, lambda: widget.show_message(_inj_warn, 6000))

    # KDE Plasma 6 Wayland: trigger the Fake-Input permission prompt now,
    # while the user is already watching the app start, so the first real
    # dictation isn't swallowed by the dialog. Cheap no-op for everyone else.
    injector.prewarm()

    # Check llama-server connectivity at startup
    if not assistant.ping_llama_server():
        log.warning("llama-server is not reachable at %s", config.LLAMA_SERVER_URL)
        tray.set_tooltip(locales.get("tray_ollama_down"))

    transcriber = Transcriber()

    t1 = threading.Thread(target=_dictation_worker, daemon=True)
    t1.start()
    t2 = threading.Thread(target=_assistant_worker, daemon=True)
    t2.start()

    # D-Bus service: exposes org.vigil.Service.Trigger(action) so external
    # callers (vigil-trigger CLI, compositor key bindings) can toggle
    # recording. Also functions as a single-instance lock via bus-name
    # ownership.
    if not dbus_service.start(on_dictate=_tray_toggle_dictation,
                              on_assistant=_tray_toggle_assistant):
        log.info("D-Bus service failed to start — another Vigil may have "
                 "claimed the name between probe and start. Exiting.")
        sys.exit(0)

    hotkey_listener = HotkeyListener(
        on_press_cb=_on_hotkey_press,
        on_release_cb=_on_hotkey_release,
        on_assist_press_cb=_on_assist_press,
        on_assist_release_cb=_on_assist_release,
    )
    hotkey_listener.start()

    def _pump_qt():
        if tray:
            tray.process_events()
        root.after(50, _pump_qt)

    def _signal_handler(sig, frame):
        log.info("Signal %s received — shutting down cleanly.", sig)
        _quit()

    signal.signal(signal.SIGTERM, _signal_handler)
    signal.signal(signal.SIGINT, _signal_handler)

    log.info("Ready. %s", _build_tray_tip())
    root.after(50, _pump_qt)
    root.mainloop()


if __name__ == "__main__":
    main()
