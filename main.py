import sys
import signal
import queue
import threading
import tkinter as tk
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
from injector import inject
from hotkey import HotkeyListener
from tray_qt import TrayIcon
from widget import RecordingWidget
import assistant
from llm_manager import manager as _llm_manager
import config
import database as db
import locales
from notifier import ReminderScheduler
from notes_window import NotesWindow
from settings_window import SettingsWindow

_pipeline_queue   = queue.Queue()
_assistant_queue  = queue.Queue()

recorder    = Recorder()
transcriber = None
tray        = None
widget      = None
root        = None
notes_win   = None
settings_win = None
scheduler   = None
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


# ── Dictation callbacks (AltGr) ──────────────────────────────────────────

def _on_hotkey_press():
    recorder.start()
    if tray:
        tray.set_recording(True)
    if widget:
        widget.hide_answer()
        widget.show_recording()
    log.info("Recording started (dictation).")


def _on_hotkey_release():
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
    recorder.start()
    if tray:
        tray.set_recording(True)
    if widget:
        widget.hide_answer()
        widget.show_assistant()
        widget.set_expression("listening")
    log.info("Recording started (assistant).")


def _on_assist_release():
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
            else:
                log.info("No speech detected.")
        except Exception as exc:
            log.error("Dictation pipeline error: %s", exc)
        finally:
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
            result = assistant.process(text)
            log.info("Assistant result: %s", result)

            # Handle special show commands
            if result == "__show_notes__":
                if notes_win:
                    root.after(0, lambda: notes_win.show("notes"))
                if widget:
                    widget.set_expression("happy")
                    widget.show_message(locales.get("show_notes"), 2000)
            elif result == "__show_appointments__":
                if notes_win:
                    root.after(0, lambda: notes_win.show("appointments"))
                if widget:
                    widget.set_expression("happy")
                    widget.show_message(locales.get("show_appointments"), 2000)
            elif result == "__show_reminders__":
                if notes_win:
                    root.after(0, lambda: notes_win.show("reminders"))
                if widget:
                    widget.set_expression("happy")
                    widget.show_message(locales.get("show_reminders"), 2000)
            elif result == locales.get("not_understood") or result.startswith(locales.get("error", detail="")):
                if widget:
                    widget.set_expression("sad")
                    widget.show_message(result, 3000)
            else:
                if widget:
                    widget.set_expression("happy")
                    widget.show_answer(result)

        except Exception as exc:
            log.error("Assistant pipeline error: %s", exc)
            if widget:
                widget.set_expression("error")
                widget.show_message(locales.get("assistant_error"), 2000)


# ── Quit & Main ───────────────────────────────────────────────────────────

def _show_notes():
    if notes_win:
        root.after(0, lambda: notes_win.show("notes"))


def _show_settings():
    if settings_win:
        root.after(0, lambda: settings_win.show())


# Tray fallback for Wayland (no global hotkeys available)
_tray_dict_recording = False
_tray_assist_recording = False


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


def _quit():
    log.info("Quitting...")
    _llm_manager.shutdown()
    _pipeline_queue.put(_STOP)
    _assistant_queue.put(_STOP)
    if scheduler:
        scheduler.stop()
    if hotkey_listener:
        try:
            hotkey_listener.stop()
        except Exception:
            pass
    if tray:
        try:
            tray.stop()
        except Exception:
            pass
    try:
        recorder.stop()
    except Exception:
        pass
    if root:
        try:
            root.after(0, root.destroy)
        except Exception:
            pass
    log.info("Shutdown complete.")


def main():
    global transcriber, tray, widget, root, notes_win, settings_win, scheduler
    global hotkey_listener

    db.init()
    _load_settings()

    root = tk.Tk()
    root.withdraw()

    widget = RecordingWidget(root)
    notes_win = NotesWindow(root)
    settings_win = SettingsWindow(root)

    recorder.on_level = lambda rms: widget.update_level(min(1.0, rms * 8))
    recorder.on_mic_error = lambda msg: widget.show_message(msg, 4000)

    tray = TrayIcon(on_quit=_quit, on_show_notes=_show_notes,
                    on_show_settings=_show_settings,
                    on_dictate=_tray_toggle_dictation,
                    on_assist=_tray_toggle_assistant)
    tray.start()

    # Check llama-server connectivity at startup
    if not assistant.ping_llama_server():
        log.warning("llama-server is not reachable at %s", config.LLAMA_SERVER_URL)
        tray.set_tooltip(locales.get("tray_ollama_down"))

    transcriber = Transcriber()

    scheduler = ReminderScheduler()
    scheduler.start()

    t1 = threading.Thread(target=_dictation_worker, daemon=True)
    t1.start()
    t2 = threading.Thread(target=_assistant_worker, daemon=True)
    t2.start()

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

    log.info("Ready. AltGr=dictate, Ctrl+R=assistant.")
    root.after(50, _pump_qt)
    root.mainloop()


if __name__ == "__main__":
    main()
