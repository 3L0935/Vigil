"""Centralised i18n string table for Writher.

All user-facing strings are stored here, keyed by language code.
Use ``get(key)`` to retrieve the string for the current ``config.LANGUAGE``.
Supports format placeholders via ``get(key, **kwargs)``.

To add a new language, add a new entry to ``_STRINGS`` with the same keys.
"""

import config

# ── String tables ─────────────────────────────────────────────────────────

_STRINGS: dict[str, dict[str, str]] = {
    "en": {
        # assistant.py — dispatch confirmations
        "note_saved":           "Note saved (#{nid})",
        "list_saved":           "List '{title}' saved ({count} items)",
        "added_to_list":        "Added to '{title}'",
        "list_not_found":       "List '{title}' not found",
        "appointment_created":  "Appointment created: {title} ({dt})",
        "reminder_set":         "Reminder set: {dt}",
        "unknown_command":      "Unknown command: {name}",
        "error":                "Error: {detail}",
        "not_understood":       "I didn't understand the command",

        # assistant.py — system prompt fragments
        "system_prompt": (
            "You are Writher, a voice assistant for productivity. "
            "Current date and time: {now} ({weekday}). "
            "The user speaks in {lang_name}. "
            "Interpret their request and call the appropriate function. "
            "When the user says relative times like 'tomorrow', 'in one hour', "
            "'next Monday', convert them to absolute ISO datetimes. "
            "Always respond by calling a function — never reply with plain text "
            "unless no function fits."
        ),
        "lang_name": "English",

        # main.py — widget messages
        "show_notes":           "📝 Here are your notes",
        "show_appointments":    "📅 Here is your agenda",
        "show_reminders":       "⏰ Here are your reminders",
        "assistant_error":      "Assistant error",

        # tray_icon.py
        "tray_idle":            "Writher — idle",
        "tray_recording":       "Writher — recording...",
        "tray_ollama_down":     "Writher — Ollama not reachable",
        "tray_notes_agenda":    "Notes & Agenda",
        "tray_quit":            "Quit",

        # notes_window.py — UI labels
        "no_notes":             "No notes",
        "no_appointments":      "No appointments",
        "no_reminders":         "No reminders",
        "tab_notes":            "📝  Notes",
        "tab_agenda":           "📅  Agenda",
        "tab_reminders":        "⏰  Reminders",
        "default_list_title":   "List",
        "default_note_title":   "Note",

        # notifier.py
        "reminder_toast_title":     "Writher Reminder",
        "appointment_toast_title":  "Writher Appointment",
        "appointment_toast_body":   "📅 {title} — in {minutes} min",
        "appointment_toast_now":    "📅 {title} — now!",

        # tray_icon.py — settings menu
        "tray_settings":            "Settings",

        # settings_window.py
        "settings_title":           "Settings",
        "setting_record_mode":      "Recording mode",
        "setting_hold":             "Hold to record",
        "setting_toggle":           "Press to start / stop",
        "setting_max_duration":     "Max recording (seconds)",
        "setting_saved":            "Settings saved",

        # obsidian vault (new)
        "vault_no_results":         "No notes found for '{query}' in the vault",
    },

    "it": {
        "note_saved":           "Nota salvata (#{nid})",
        "list_saved":           "Lista '{title}' salvata ({count} elementi)",
        "added_to_list":        "Aggiunto a '{title}'",
        "list_not_found":       "Lista '{title}' non trovata",
        "appointment_created":  "Appuntamento creato: {title} ({dt})",
        "reminder_set":         "Reminder impostato: {dt}",
        "unknown_command":      "Comando sconosciuto: {name}",
        "error":                "Errore: {detail}",
        "not_understood":       "Non ho capito il comando",

        "system_prompt": (
            "You are Writher, a voice assistant for productivity. "
            "Current date and time: {now} ({weekday}). "
            "The user speaks in {lang_name}. "
            "Interpret their request and call the appropriate function. "
            "When the user says relative times like 'domani', 'tra un'ora', "
            "'lunedì prossimo', convert them to absolute ISO datetimes. "
            "Always respond by calling a function — never reply with plain text "
            "unless no function fits."
        ),
        "lang_name": "Italian",

        "show_notes":           "📝 Ecco le note",
        "show_appointments":    "📅 Ecco l'agenda",
        "show_reminders":       "⏰ Ecco i reminder",
        "assistant_error":      "Errore assistente",

        "tray_idle":            "Writher — inattivo",
        "tray_recording":       "Writher — registrazione...",
        "tray_ollama_down":     "Writher — Ollama non raggiungibile",
        "tray_notes_agenda":    "Note & Agenda",
        "tray_quit":            "Esci",

        "no_notes":             "Nessuna nota",
        "no_appointments":      "Nessun appuntamento",
        "no_reminders":         "Nessun reminder",
        "tab_notes":            "📝  Note",
        "tab_agenda":           "📅  Agenda",
        "tab_reminders":        "⏰  Reminder",
        "default_list_title":   "Lista",
        "default_note_title":   "Nota",

        "reminder_toast_title":     "Writher Promemoria",
        "appointment_toast_title":  "Writher Appuntamento",
        "appointment_toast_body":   "📅 {title} — tra {minutes} min",
        "appointment_toast_now":    "📅 {title} — adesso!",

        # tray_icon.py — settings menu
        "tray_settings":            "Impostazioni",

        # settings_window.py
        "settings_title":           "Impostazioni",
        "setting_record_mode":      "Modalità registrazione",
        "setting_hold":             "Tieni premuto per registrare",
        "setting_toggle":           "Premi per avviare / fermare",
        "setting_max_duration":     "Durata max registrazione (secondi)",
        "setting_saved":            "Impostazioni salvate",

        # obsidian vault (new)
        "vault_no_results":         "Nessuna nota trovata per '{query}' nella vault",
    },

    "fr": {
        # assistant.py — dispatch confirmations
        "note_saved":           "Note enregistrée (#{nid})",
        "list_saved":           "Liste '{title}' enregistrée ({count} éléments)",
        "added_to_list":        "Ajouté à '{title}'",
        "list_not_found":       "Liste '{title}' introuvable",
        "appointment_created":  "Rendez-vous créé : {title} ({dt})",
        "reminder_set":         "Rappel défini : {dt}",
        "unknown_command":      "Commande inconnue : {name}",
        "error":                "Erreur : {detail}",
        "not_understood":       "Je n'ai pas compris la commande",

        # assistant.py — system prompt
        "system_prompt": (
            "Tu es WritHer, un assistant vocal de productivité. "
            "Date et heure actuelles : {now} ({weekday}). "
            "L'utilisateur parle en {lang_name}. "
            "Interprète sa demande et appelle la fonction appropriée. "
            "Quand l'utilisateur dit des temps relatifs comme 'demain', 'dans une heure', "
            "'lundi prochain', convertis-les en dates ISO absolues. "
            "Si l'utilisateur demande de chercher dans sa vault Obsidian, "
            "utilise search_obsidian_vault. "
            "Réponds toujours en appelant une fonction — "
            "jamais en texte libre sauf si aucune fonction ne correspond."
        ),
        "lang_name": "French",

        # main.py — widget messages
        "show_notes":           "📝 Voici vos notes",
        "show_appointments":    "📅 Voici votre agenda",
        "show_reminders":       "⏰ Voici vos rappels",
        "assistant_error":      "Erreur de l'assistant",

        # tray_icon.py
        "tray_idle":            "WritHer — en attente",
        "tray_recording":       "WritHer — enregistrement...",
        "tray_ollama_down":     "WritHer — serveur LLM inaccessible",
        "tray_notes_agenda":    "Notes & Agenda",
        "tray_quit":            "Quitter",

        # notes_window.py
        "no_notes":             "Aucune note",
        "no_appointments":      "Aucun rendez-vous",
        "no_reminders":         "Aucun rappel",
        "tab_notes":            "📝  Notes",
        "tab_agenda":           "📅  Agenda",
        "tab_reminders":        "⏰  Rappels",
        "default_list_title":   "Liste",
        "default_note_title":   "Note",

        # notifier.py
        "reminder_toast_title":     "WritHer — Rappel",
        "appointment_toast_title":  "WritHer — Rendez-vous",
        "appointment_toast_body":   "📅 {title} — dans {minutes} min",
        "appointment_toast_now":    "📅 {title} — maintenant !",

        # tray_icon.py — settings menu
        "tray_settings":            "Paramètres",

        # settings_window.py
        "settings_title":           "Paramètres",
        "setting_record_mode":      "Mode d'enregistrement",
        "setting_hold":             "Maintenir pour enregistrer",
        "setting_toggle":           "Appuyer pour démarrer / arrêter",
        "setting_max_duration":     "Durée max d'enregistrement (secondes)",
        "setting_saved":            "Paramètres enregistrés",

        # obsidian vault (new)
        "vault_no_results":         "Aucune note trouvée pour '{query}' dans la vault",
    },
}

_FALLBACK = "en"


# ── Public API ────────────────────────────────────────────────────────────

def get(key: str, **kwargs) -> str:
    """Return the localised string for *key*, formatted with *kwargs*.

    Falls back to English if the key is missing in the active language.
    """
    lang = getattr(config, "LANGUAGE", _FALLBACK)
    table = _STRINGS.get(lang, _STRINGS[_FALLBACK])
    template = table.get(key, _STRINGS[_FALLBACK].get(key, key))
    if kwargs:
        try:
            return template.format(**kwargs)
        except (KeyError, IndexError):
            return template
    return template
