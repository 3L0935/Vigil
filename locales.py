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
        "settings_opened":      "Opening settings.",
        "app_launched":         "Opening {name}.",
        "app_not_found":        "Application '{name}' not found.",

        # assistant.py — system prompt fragments
        "system_prompt": (
            "You are Writher, a voice assistant for productivity. "
            "Current date and time: {now} ({weekday}). "
            "The user speaks in {lang_name}. "
            "Interpret their request and call the appropriate function. "
            "When the user asks you to search the web or their notes, call the search tool, "
            "then synthesize the results into a concise 2-4 sentence spoken answer. "
            "For all other requests, call the appropriate function. "
            "Never use emojis or emoticons in any response — your output is read aloud by TTS."
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
        "tray_ollama_down":     "Writher — LLM server not reachable",
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

        # tray_icon.py — settings menu + wayland fallback buttons
        "tray_settings":            "Settings",
        "tray_stop_tts":            "Stop TTS",
        "tray_dictate":             "Dictate (AltGr)",
        "tray_assist":              "Assistant (Ctrl+R)",

        # settings_window.py
        "settings_title":           "Settings",
        "setting_record_mode":      "Recording mode",
        "setting_toggle":           "Press to start / stop",
        "setting_max_duration":     "Max recording (seconds)",
        "setting_saved":            "Settings saved",

        # obsidian vault (new)
        "vault_not_configured":     "Obsidian vault is not configured. Set the vault path in Settings.",
        "vault_no_results":         "No notes found for '{query}' in the vault",

        # web search
        "web_no_results":           "No web results found for '{query}'",

        # settings_window.py
        "setting_whisper_model":    "Whisper model",
        "setting_llm_model":        "LLM model (.gguf)",
        "setting_llm_unload":       "LLM unload timeout",
        "setting_llm_gpu_layers":   "GPU layers (ngl)",
        "setting_llm_url":          "LLM server URL",
        "setting_obsidian_vault":   "Obsidian vault",
        "setting_language":         "Language",
        "setting_overlay_position": "Overlay position",
        "setting_overlay_screen":   "Lock to screen",
        "setting_answer_timeout":   "Answer card timeout (s)",
        "setting_hotkeys":          "Hotkeys",
        "setting_hotkey_dict_hint": "Dictation  (e.g. Ctrl+Alt+W)",
        "setting_hotkey_asst_hint": "Assistant  (e.g. Ctrl+Alt+R)",
        "setting_hotkey_hint":      "Save to apply — format: Ctrl+Alt+W, Meta+D…",
        "setting_tts_engine":       "Engine",
        "setting_tts_voice_fr":     "Voice (FR)",
        "setting_tts_voice_en":     "Voice (EN)",
        "setting_tts_volume":       "Volume",
        "setting_browse":           "Browse",
        "setting_more_voices":      "More voices…",
        "setting_download":         "Download",
        "setting_loading":          "Loading…",
        "setting_rerun_setup":      "Re-run setup",
        "setting_uninstall":        "Uninstall",
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
        "settings_opened":      "Apro le impostazioni.",
        "app_launched":         "Apro {name}.",
        "app_not_found":        "Applicazione '{name}' non trovata.",

        "system_prompt": (
            "You are Writher, a voice assistant for productivity. "
            "Current date and time: {now} ({weekday}). "
            "The user speaks in {lang_name}. "
            "Interpret their request and call the appropriate function. "
            "When the user asks you to search the web or their notes, call the search tool, "
            "then synthesize the results into a concise 2-4 sentence spoken answer. "
            "For all other requests, call the appropriate function. "
            "Never use emojis or emoticons in any response — your output is read aloud by TTS."
        ),
        "lang_name": "Italian",

        "show_notes":           "📝 Ecco le note",
        "show_appointments":    "📅 Ecco l'agenda",
        "show_reminders":       "⏰ Ecco i reminder",
        "assistant_error":      "Errore assistente",

        "tray_idle":            "Writher — inattivo",
        "tray_recording":       "Writher — registrazione...",
        "tray_ollama_down":     "Writher — server LLM non raggiungibile",
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

        # tray_icon.py — settings menu + wayland fallback buttons
        "tray_settings":            "Impostazioni",
        "tray_stop_tts":            "Ferma TTS",
        "tray_dictate":             "Ditta (AltGr)",
        "tray_assist":              "Assistente (Ctrl+R)",

        # settings_window.py
        "settings_title":           "Impostazioni",
        "setting_record_mode":      "Modalità registrazione",
        "setting_toggle":           "Premi per avviare / fermare",
        "setting_max_duration":     "Durata max registrazione (secondi)",
        "setting_saved":            "Impostazioni salvate",

        # obsidian vault (new)
        "vault_not_configured":     "La vault Obsidian non è configurata. Imposta il percorso nelle Impostazioni.",
        "vault_no_results":         "Nessuna nota trovata per '{query}' nella vault",

        # web search
        "web_no_results":           "Nessun risultato web per '{query}'",

        # settings_window.py
        "setting_whisper_model":    "Modello Whisper",
        "setting_llm_model":        "Modello LLM (.gguf)",
        "setting_llm_unload":       "Scarico LLM (inattività)",
        "setting_llm_gpu_layers":   "Layer GPU (ngl)",
        "setting_llm_url":          "URL server LLM",
        "setting_obsidian_vault":   "Vault Obsidian",
        "setting_language":         "Lingua",
        "setting_overlay_position": "Posizione overlay",
        "setting_overlay_screen":   "Blocca sullo schermo",
        "setting_answer_timeout":   "Durata risposta (s)",
        "setting_hotkeys":          "Scorciatoie",
        "setting_hotkey_dict_hint": "Dettatura  (es. Ctrl+Alt+W)",
        "setting_hotkey_asst_hint": "Assistente  (es. Ctrl+Alt+R)",
        "setting_hotkey_hint":      "Salva per applicare — formato: Ctrl+Alt+W, Meta+D…",
        "setting_tts_engine":       "Motore",
        "setting_tts_voice_fr":     "Voce (FR)",
        "setting_tts_voice_en":     "Voce (EN)",
        "setting_tts_volume":       "Volume",
        "setting_browse":           "Sfoglia",
        "setting_more_voices":      "Altre voci…",
        "setting_download":         "Scarica",
        "setting_loading":          "Caricamento…",
        "setting_rerun_setup":      "Riavvia setup",
        "setting_uninstall":        "Disinstalla",
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
        "settings_opened":      "Ouverture des paramètres.",
        "app_launched":         "Ouverture de {name}.",
        "app_not_found":        "Application '{name}' introuvable.",

        # assistant.py — system prompt
        "system_prompt": (
            "Tu es WritHer, un assistant vocal de productivité. "
            "Date et heure actuelles : {now} ({weekday}). "
            "L'utilisateur parle en {lang_name}. "
            "Interprète sa demande et appelle la fonction appropriée. "
            "Quand l'utilisateur te demande de chercher sur le web ou dans ses notes, "
            "appelle l'outil de recherche, puis synthétise les résultats en une réponse "
            "concise de 2 à 4 phrases, formulée pour être lue à voix haute. "
            "Pour toutes les autres demandes, appelle la fonction appropriée. "
            "N'utilise jamais d'emoji ni d'émoticônes dans tes réponses — "
            "ta réponse est lue à voix haute par un TTS."
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

        # tray_icon.py — settings menu + wayland fallback buttons
        "tray_settings":            "Paramètres",
        "tray_stop_tts":            "Arrêter TTS",
        "tray_dictate":             "Dicter (AltGr)",
        "tray_assist":              "Assistant (Ctrl+R)",

        # settings_window.py
        "settings_title":           "Paramètres",
        "setting_record_mode":      "Mode d'enregistrement",
        "setting_toggle":           "Appuyer pour démarrer / arrêter",
        "setting_max_duration":     "Durée max d'enregistrement (secondes)",
        "setting_saved":            "Paramètres enregistrés",

        # obsidian vault (new)
        "vault_not_configured":     "La vault Obsidian n'est pas configurée. Définis le chemin dans les Paramètres.",
        "vault_no_results":         "Aucune note trouvée pour '{query}' dans la vault",

        # web search
        "web_no_results":           "Aucun résultat web pour '{query}'",

        # settings_window.py
        "setting_whisper_model":    "Modèle Whisper",
        "setting_llm_model":        "Modèle LLM (.gguf)",
        "setting_llm_unload":       "Déchargement LLM (inactivité)",
        "setting_llm_gpu_layers":   "Couches GPU (ngl)",
        "setting_llm_url":          "URL du serveur LLM",
        "setting_obsidian_vault":   "Vault Obsidian",
        "setting_language":         "Langue",
        "setting_overlay_position": "Position de l'overlay",
        "setting_overlay_screen":   "Verrouiller à l'écran",
        "setting_answer_timeout":   "Durée d'affichage de la réponse (s)",
        "setting_hotkeys":          "Raccourcis clavier",
        "setting_hotkey_dict_hint": "Dictée  (ex. Ctrl+Alt+W)",
        "setting_hotkey_asst_hint": "Assistant  (ex. Ctrl+Alt+R)",
        "setting_hotkey_hint":      "Sauvegarder pour appliquer — format : Ctrl+Alt+W, Meta+D…",
        "setting_tts_engine":       "Moteur",
        "setting_tts_voice_fr":     "Voix (FR)",
        "setting_tts_voice_en":     "Voix (EN)",
        "setting_tts_volume":       "Volume",
        "setting_browse":           "Parcourir",
        "setting_more_voices":      "Plus de voix…",
        "setting_download":         "Télécharger",
        "setting_loading":          "Chargement…",
        "setting_rerun_setup":      "Relancer le setup",
        "setting_uninstall":        "Désinstaller",
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
