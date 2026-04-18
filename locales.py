"""Centralised i18n string table for Vigil.

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
        "unknown_command":      "Unknown command: {name}",
        "error":                "Error: {detail}",
        "not_understood":       "I didn't understand the command",
        "settings_opened":      "Opening settings.",
        "settings_closed":      "Settings closed.",
        "app_launched":         "Opening {name}.",
        "app_not_found":        "Application '{name}' not found.",
        "app_closed":           "{name} closed.",
        "app_close_failed":     "Could not find a running instance of '{name}'.",

        # assistant.py — system prompt fragments
        "system_prompt": (
            "You are {name}, a voice assistant for productivity. "
            "Your name is {name} — use it when introducing yourself or when the user addresses you by name. "
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
        "assistant_error":      "Assistant error",

        # tray_qt.py
        "tray_idle":            "Vigil — idle",
        "tray_recording":       "Vigil — recording...",
        "tray_ollama_down":     "Vigil — LLM server not reachable",
        "tray_quit":            "Quit",
        "tray_settings":        "Settings",
        "tray_stop_tts":        "Stop TTS",
        "tray_clear_context":   "Clear context",

        # multi-turn context
        "context_cleared":      "Conversation cleared.",
        "app_candidates":       "Multiple apps found:\n{list}\nReply with the number.",
        "retry_launch_ctx": (
            "Application \"{name}\" was not found on this system.\n\n"
            "Installed apps that may match the user's request:\n{list}\n\n"
            "Pick the single best match for the user's intent and call launch_app with "
            "its exact name copied from the list above. "
            "If two or more apps fit the user's intent equally well, call ask_user_choice "
            "with those candidates so the user can pick. "
            "If nothing in the list fits, reply in plain text (in English) that the app "
            "is not installed — do not call any tool."
        ),
        "retry_launch_ctx_empty": (
            "Application \"{name}\" was not found on this system, and no similar apps "
            "are installed. Reply in plain text (in English) that the app is not "
            "installed. Do not call any tool."
        ),

        # obsidian vault
        "vault_not_configured": "Obsidian vault is not configured. Set the vault path in Settings.",
        "vault_no_results":     "No notes found for '{query}' in the vault",

        # web search
        "web_no_results":       "No web results found for '{query}'",

        # settings_window.py
        "setting_saved":            "Settings saved",
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
        "setting_assistant_name":   "Assistant name",
    },

    "it": {
        "unknown_command":      "Comando sconosciuto: {name}",
        "error":                "Errore: {detail}",
        "not_understood":       "Non ho capito il comando",
        "settings_opened":      "Apro le impostazioni.",
        "settings_closed":      "Impostazioni chiuse.",
        "app_launched":         "Apro {name}.",
        "app_not_found":        "Applicazione '{name}' non trovata.",
        "app_closed":           "{name} chiuso.",
        "app_close_failed":     "Nessuna istanza in esecuzione di '{name}'.",

        "system_prompt": (
            "You are {name}, a voice assistant for productivity. "
            "Your name is {name} — use it when introducing yourself or when the user addresses you by name. "
            "Current date and time: {now} ({weekday}). "
            "The user speaks in {lang_name}. "
            "Interpret their request and call the appropriate function. "
            "When the user asks you to search the web or their notes, call the search tool, "
            "then synthesize the results into a concise 2-4 sentence spoken answer. "
            "For all other requests, call the appropriate function. "
            "Never use emojis or emoticons in any response — your output is read aloud by TTS."
        ),
        "lang_name": "Italian",

        "assistant_error":      "Errore assistente",

        "tray_idle":            "Vigil — inattivo",
        "tray_recording":       "Vigil — registrazione...",
        "tray_ollama_down":     "Vigil — server LLM non raggiungibile",
        "tray_quit":            "Esci",
        "tray_settings":        "Impostazioni",
        "tray_stop_tts":        "Ferma TTS",
        "tray_clear_context":   "Cancella contesto",

        "context_cleared":      "Conversazione cancellata.",
        "app_candidates":       "Più applicazioni trovate:\n{list}\nRispondi con il numero.",
        "retry_launch_ctx": (
            "L'applicazione \"{name}\" non è stata trovata su questo sistema.\n\n"
            "Applicazioni installate che potrebbero corrispondere alla richiesta:\n{list}\n\n"
            "Scegli la singola corrispondenza migliore per l'intento dell'utente e chiama "
            "launch_app con il nome esatto copiato dalla lista sopra. "
            "Se due o più applicazioni corrispondono all'intento dell'utente in modo "
            "equivalente, chiama ask_user_choice con quei candidati per far scegliere "
            "all'utente. "
            "Se nulla nella lista corrisponde, rispondi in testo normale (in italiano) "
            "che l'applicazione non è installata — non chiamare alcuno strumento."
        ),
        "retry_launch_ctx_empty": (
            "L'applicazione \"{name}\" non è stata trovata su questo sistema, e nessuna "
            "applicazione simile è installata. Rispondi in testo normale (in italiano) "
            "che l'applicazione non è installata. Non chiamare alcuno strumento."
        ),

        "vault_not_configured": "La vault Obsidian non è configurata. Imposta il percorso nelle Impostazioni.",
        "vault_no_results":     "Nessuna nota trovata per '{query}' nella vault",

        "web_no_results":       "Nessun risultato web per '{query}'",

        "setting_saved":            "Impostazioni salvate",
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
        "setting_assistant_name":   "Nome dell'assistente",
    },

    "fr": {
        # assistant.py — dispatch confirmations
        "unknown_command":      "Commande inconnue : {name}",
        "error":                "Erreur : {detail}",
        "not_understood":       "Je n'ai pas compris la commande",
        "settings_opened":      "Ouverture des paramètres.",
        "settings_closed":      "Paramètres fermés.",
        "app_launched":         "Ouverture de {name}.",
        "app_not_found":        "Application '{name}' introuvable.",
        "app_closed":           "{name} fermé.",
        "app_close_failed":     "Aucune instance de '{name}' en cours d'exécution.",

        # assistant.py — system prompt
        "system_prompt": (
            "Tu es {name}, un assistant vocal de productivité. "
            "Ton nom est {name} — utilise-le quand tu te présentes ou quand l'utilisateur t'appelle par ton nom. "
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
        "assistant_error":      "Erreur de l'assistant",

        # tray_qt.py
        "tray_idle":            "Vigil — en attente",
        "tray_recording":       "Vigil — enregistrement...",
        "tray_ollama_down":     "Vigil — serveur LLM inaccessible",
        "tray_quit":            "Quitter",
        "tray_settings":        "Paramètres",
        "tray_stop_tts":        "Arrêter TTS",
        "tray_clear_context":   "Effacer le contexte",

        # multi-turn context
        "context_cleared":      "Conversation effacée.",
        "app_candidates":       "Plusieurs applications trouvées :\n{list}\nRépondez par le numéro.",
        "retry_launch_ctx": (
            "L'application \"{name}\" n'a pas été trouvée sur ce système.\n\n"
            "Applications installées pouvant correspondre à la demande de l'utilisateur :\n{list}\n\n"
            "Choisis la meilleure correspondance unique pour l'intention de l'utilisateur et "
            "appelle launch_app avec son nom exact copié depuis la liste ci-dessus. "
            "Si deux applications ou plus correspondent à l'intention de l'utilisateur de façon "
            "équivalente, appelle ask_user_choice avec ces candidats pour que l'utilisateur "
            "puisse choisir. "
            "Si rien dans la liste ne convient, réponds en texte simple (en français) que "
            "l'application n'est pas installée — n'appelle aucun outil."
        ),
        "retry_launch_ctx_empty": (
            "L'application \"{name}\" n'a pas été trouvée sur ce système, et aucune "
            "application similaire n'est installée. Réponds en texte simple (en français) "
            "que l'application n'est pas installée. N'appelle aucun outil."
        ),

        # obsidian vault
        "vault_not_configured": "La vault Obsidian n'est pas configurée. Définis le chemin dans les Paramètres.",
        "vault_no_results":     "Aucune note trouvée pour '{query}' dans la vault",

        # web search
        "web_no_results":       "Aucun résultat web pour '{query}'",

        # settings_window.py
        "setting_saved":            "Paramètres enregistrés",
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
        "setting_assistant_name":   "Nom de l'assistant",
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
