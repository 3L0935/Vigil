"""Freedesktop notifications (notify-send) and reminder/appointment scheduler thread."""

import shutil
import subprocess
import threading
import time
from datetime import datetime
from logger import log
import config
import database as db
import locales


def _send_toast(title: str, message: str):
    """Show a desktop notification via notify-send (freedesktop standard)."""
    if shutil.which("notify-send"):
        try:
            subprocess.Popen(
                ["notify-send", "-a", "WritHer", "-i", "dialog-information",
                 title, message],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            log.info("Toast sent via notify-send.")
        except Exception as exc:
            log.warning("notify-send failed: %s", exc)
    else:
        log.warning("notify-send not found — install libnotify for desktop notifications.")


class ReminderScheduler:
    """Background thread that checks for due reminders and upcoming
    appointments every 30 seconds."""

    def __init__(self):
        self._stop = threading.Event()
        self._thread = None

    def start(self):
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def stop(self):
        self._stop.set()

    def _loop(self):
        while not self._stop.is_set():
            self._check_reminders()
            self._check_appointments()
            self._stop.wait(30)

    def _check_reminders(self):
        """Fire toast for reminders that are due."""
        try:
            pending = db.get_pending_reminders()
            for rem in pending:
                _send_toast(locales.get("reminder_toast_title"), rem["message"])
                db.mark_reminder_notified(rem["id"])
                log.info("Reminder notified: %s", rem["message"])
        except Exception as exc:
            log.error("Reminder scheduler error: %s", exc)

    def _check_appointments(self):
        """Fire toast for appointments within the configured lead time."""
        try:
            lead = getattr(config, "APPOINTMENT_REMIND_MINUTES", 15)
            upcoming = db.get_upcoming_appointments(within_minutes=lead)
            now = datetime.now()

            for appt in upcoming:
                try:
                    appt_dt = datetime.fromisoformat(appt["dt"])
                    delta_min = max(0, int((appt_dt - now).total_seconds() / 60))
                except (ValueError, TypeError):
                    delta_min = 0

                title = appt.get("title", "")
                if delta_min <= 0:
                    body = locales.get("appointment_toast_now", title=title)
                else:
                    body = locales.get("appointment_toast_body",
                                       title=title, minutes=delta_min)

                _send_toast(locales.get("appointment_toast_title"), body)
                db.mark_appointment_notified(appt["id"])
                log.info("Appointment notified: %s (in %d min)", title, delta_min)
        except Exception as exc:
            log.error("Appointment scheduler error: %s", exc)
