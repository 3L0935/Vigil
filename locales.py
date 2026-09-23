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
        'language_en': 'English',
        'language_fr': 'French',
        'language_it': 'Italian',
        'setting_auto_language': 'Automatic',
        'setting_hotkeys_conflict': 'Dictation and assistant shortcuts must differ.',
        'setting_invalid_value': 'Check the selected values.',
        'setting_save_failed': 'Could not activate these settings. Check the logs.',
        'answer_copy': 'Copy',
        'widget_listening': 'Listening…',
        'widget_assistant': 'Ask Vigil…',
        'widget_processing': 'Processing…',
        'widget_done': 'Done',
        'setup_title': 'Set up Vigil',
        'setup_welcome': 'Welcome & language',
        'setup_engine': 'Assistant engine',
        'setup_model': 'Assistant model',
        'setup_dictation': 'Dictation',
        'setup_voice': 'Speech output',
        'setup_shortcuts': 'Shortcuts',
        'setup_review': 'Review & prepare',
        'setup_ready': 'Ready',
        'setup_welcome_body': 'Choose a language. Vigil keeps your settings on this computer.',
        'setup_engine_body': 'Choose where the assistant runs. Local engines stay on this computer; cloud inference sends requests to your chosen endpoint.',
        'setup_remote_notice': 'Cloud inference requires local-only mode to be disabled in Settings.',
        'setup_allow_cloud': 'Allow cloud inference',
        'setup_model_body': 'Reuse installed files, select a catalog model, or enter a model name for Ollama.',
        'setup_backend': 'GPU backend',
        'setup_binary': 'Existing llama-server binary (optional)',
        'setup_use_existing_binary': 'Choose an existing llama-server binary',
        'setup_use_existing_model': 'Choose an existing GGUF model',
        'setup_dictation_body': 'Choose a speech model. It loads on startup; download it explicitly in Settings if missing.',
        'setup_voice_body': 'Choose overlay text, spoken output, or both. Selected Piper voices download during preparation.',
        'setup_shortcuts_body': 'Choose different shortcuts for dictation and the assistant.',
        'setup_shortcuts_notice': 'Some compositors write managed shortcut entries to your user configuration when you finish.',
        'setup_hotkey_consent': 'Allow Vigil to edit my compositor shortcut configuration',
        'setup_hotkey_consent_required': 'Allow the shortcut configuration change to continue.',
        'setup_manual_hotkeys': 'Bind these commands in your compositor: vigil-trigger dictate and vigil-trigger assistant.',
        'setup_review_body': 'Review your choices. Preparation reuses installed assets and downloads missing files.',
        'setup_ready_body': 'Configuration is prepared. Finish to save it and start Vigil.',
        'setup_cancel': 'Cancel',
        'setup_back': 'Back',
        'setup_next': 'Continue',
        'setup_prepare': 'Download & configure',
        'setup_finish': 'Finish',
        'setup_reset_choices': 'Reset setup choices',
        'setup_preparing': 'Preparing…',
        'setup_progress_binary': 'Downloading llama-server…',
        'setup_progress_model': 'Preparing the assistant model…',
        'setup_progress_voice_fr': 'Downloading the French voice…',
        'setup_progress_voice_en': 'Downloading the English voice…',
        'setup_choose_ollama_model': 'Choose or enter an Ollama model.',
        'setup_choose_gguf': 'Choose a GGUF file or a catalog model.',
        'setup_choose_voice': 'Choose a voice for the selected language.',
        'setup_piper_missing': 'Piper is not installed. Install the desktop speech profile or choose text only.',
        'setup_binary_invalid': 'The selected llama-server file is empty or cannot be executed.',
        'setup_prepare_failed': 'Preparation failed. Check the connection or selected files.',
        'setup_activation_failed': 'Could not activate this configuration. Active settings were restored.',
        'setup_rollback_failed': 'Activation failed and previous settings could not be restored. Check the logs.',
        'setting_download_failed': 'Download failed. Try again.',
        # Local-first policy and dictation preferences
        'privacy_bad_url': 'Invalid server URL. Use HTTP(S) without credentials in the URL.',
        'privacy_remote_blocked': 'Remote access blocked by local mode. Check Settings.',
        'privacy_data_blocked': 'Sharing local data with a remote server is disabled.',
        'privacy_web_blocked': 'Web access is disabled. Check Settings.',
        'setting_privacy': 'Local mode and privacy',
        'setting_local_only': 'Strict local mode (loopback servers only)',
        'setting_allow_web': 'Allow web searches and opening websites',
        'setting_share_local_data': 'Allow local tools with remote inference',
        'setting_log_content': 'Include transcripts and responses in logs',
        'privacy_hint': 'Save to apply. Strict mode blocks remote inference and web tools. Outside strict mode, speech is sent to the selected server. Local-tool permission also shares note excerpts, file names and app results. Model/voice downloads are explicit exceptions. Launched apps manage their own network access.',
        'setting_recovery_days': 'Failed-paste recovery: days to keep (0 = off)',
        'setting_purge': 'Clear logs and recovered dictations…',
        'purge_confirm': 'Delete Vigil logs and recovered dictations? Settings and notes are kept.',
        'purge_done': 'Logs and recovery cleared.',
        'setting_dictation': 'Dictation',
        'setting_whisper_language': 'Recognition language (auto = automatic detection)',
        'setting_max_record_seconds': 'Recording limit in seconds (audio discarded at limit)',
        'setting_clipboard_restore_ms': 'Clipboard restore delay in milliseconds',
        'setting_mic_device': 'Microphone',
        'mic_default': 'System default',
        'setting_refresh_mics': 'Refresh microphones',
        'mic_refresh_hint': 'Reconnect a missing microphone, refresh, then try recording again.',
        'mic_unavailable': 'Microphone unavailable. Reconnect it or choose another in Settings.',
        'setting_vocabulary': 'Personal vocabulary',
        'vocabulary_hint': 'One spoken form = written form per line. Applied to dictation only. Example: vigil local = Vigil Local',
        'vocabulary_invalid': 'Invalid or duplicate vocabulary entry on line {line}. Use spoken = written.',
        'setting_priming': 'Recognition hints',
        'priming_hint': 'Names and technical terms, e.g. Vigil, ROCm, Obsidian. Best effort; not a guaranteed correction.',
        'speech_download_hint': 'Models always load from disk. If the selected model is missing, download it explicitly below. Internet is needed only for this download.',
        'setting_download_speech': 'Download / repair selected speech model',
        'speech_downloading': 'Downloading model…',
        'speech_loading': 'Loading local model…',
        'speech_missing': 'Model unavailable — open Settings',
        'speech_ready': 'Dictation ready',
        'busy': 'Another operation is in progress',
        'recording_expired': 'Time limit: audio discarded',
        'paste_recovered': 'Paste failed — text saved for recovery',
        'paste_failed': 'Paste failed — text could not be saved',
        'mode_local': 'local only',
        'mode_network': 'network enabled',

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
            "Interpret the user's request. If an action or search is needed, call the appropriate tool. "
            "If the user just wants to chat, greet you, or asks a question you can answer directly, "
            "respond in plain text without calling any tool. "
            "For web or vault searches, synthesize into 2-4 concise sentences readable by TTS. "
            "To OPEN something: app_action for apps, open_url for websites, open_folder for standard folders. "
            "To CLOSE an app: app_action(name, 'close'). "
            "To FIND specific files: search_files(folder, query). "
            "Never use emojis or emoticons — output is read aloud by TTS."
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

        # open_url / open_folder
        "url_opened":           "Opening {url}.",
        "url_invalid":          "Cannot open '{target}' — unknown site.",
        "folder_opened":        "Opening {path}.",
        "folder_unknown":       "Folder '{name}' is not a known standard folder.",
        "folder_missing":       "Folder '{path}' does not exist.",
        "retry_launch_url_hint": (
            "NOTE: \"{name}\" is also the name of a popular website. If the user "
            "meant the website (not an installed app), call open_url(\"{name}\") "
            "instead."
        ),

        # search_files
        "file_no_results":      "No files matching '{query}' in {folder}.",
        "file_results_found":   "Found in {folder}:\n{list}",
        "file_results_similar": "No exact match for '{query}' in {folder}. Similar files:\n{list}",
        "file_opened":          "Opening {name}.",
        "file_open_failed":     "Could not open '{path}'.",
        "retry_launch_ctx": (
            "Application \"{name}\" was not found on this system.\n\n"
            "Installed apps that may match the user's request "
            "(shown as `- Name (GenericName) [Keywords]`):\n{list}\n\n"
            "Rules:\n"
            "1. If ONE app clearly matches the user's intent best (its generic name or "
            "keywords directly match what the user asked for), call app_action with its "
            "exact name copied from the list and action='launch'.\n"
            "2. If the user's request is generic (e.g. 'music', 'browser', 'terminal') "
            "and two or more apps could reasonably fit, call ask_user_choice with 2-4 "
            "candidates rather than guessing — let the user pick.\n"
            "3. If nothing in the list fits, reply in plain text (in English) that the "
            "app is not installed. Do not call any tool."
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

        # Settings UI
        "setting_saved":            "Settings saved",
        "setting_whisper_model":    "Whisper model",
        "setting_llm_model":        "LLM model (.gguf)",
        "setting_llm_unload":       "LLM unload timeout",
        "setting_llm_gpu_layers":   "GPU layers (ngl)",
        "setting_llm_ctx_size":     "Context size (tokens)",
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
        "setting_rerun_setup":      "Redo setup",
        "setting_uninstall":        "Uninstall",
        "setting_assistant_name":   "Assistant name",
        "settings_title":           "Settings",
        "settings_intro":           "Voice, models and desktop behavior",
        "group_voice_models":       "Voice & models",
        "group_general":            "General",
        "group_overlay":            "Overlay",
        "group_speech_output":      "Speech output",
        "group_maintenance":        "Maintenance",
        "setting_llm_provider":     "Assistant engine",
        "provider_llama_cpp":       "llama.cpp (local)",
        "provider_ollama_local":    "Ollama (local)",
        "provider_ollama_cloud":    "Ollama Cloud",
        "setting_ollama_url":       "Ollama URL",
        "setting_ollama_model":     "Ollama model",
        "setting_ollama_api_key":   "API key",
        "setting_refresh":          "Refresh",
        "setting_fetching_models":  "Fetching models…",
        "setting_tts":              "Text to speech",
        "setting_tts_mode":         "Output mode",
        "setting_tts_speaker":      "Speaker",
        "setting_tts_sample":       "Play sample",
        "setting_save":             "Save settings",
        "setting_saved_status":     "Changes saved",
        "setting_auto_screen":      "Automatic (active screen)",
        "setting_model_path_hint":  "Choose a GGUF model file",
        "action_copy":              "Copy",
        "status_waiting":           "Waiting…",
        "tray_dictate":             "Dictate ({shortcut})",
        "tray_assistant":           "Assistant ({shortcut})",
        "accordion_expand":         "Expand {section}",
        "accordion_collapse":       "Collapse {section}",
        "choice_never":             "Never",
        "choice_off":               "Off",
        "choice_overlay":           "Overlay",
        "choice_tts":               "Speech only",
        "choice_both":              "Overlay and speech",
        "position_top_left":        "Top left",
        "position_top_center":      "Top center",
        "position_top_right":       "Top right",
        "position_center_left":     "Center left",
        "position_center":          "Center",
        "position_center_right":    "Center right",
        "position_bottom_left":     "Bottom left",
        "position_bottom_center":   "Bottom center",
        "position_bottom_right":    "Bottom right",
        "answer_closes_in":         "Closes in {seconds}s",
        "hotkey_rebind_failed":     "Hotkey update failed — see logs",
        "tray_shortcuts_status":    "{dict_shortcut}=dictation, {assist_shortcut}=assistant",
        "setting_no_models":        "No models — press Refresh",
        "setting_models_available": "{count} model(s) available",
        "setting_model_fetch_failed": "{detail} — enter the model manually",
        "setting_ollama_unreachable": "Cannot reach the Ollama API",
        "setting_voices_available": "{count} voice(s) available",
        "setting_voices_title": "Voices",
        "tray_dictation_action": "Dictate",
        "tray_assistant_action": "Assistant",
        "ui_preview": "UI preview",
        "dialog_select_gguf": "Select a GGUF model",
        "dialog_gguf_files": "GGUF files",
        "dialog_all_files": "All files",
        "dialog_select_vault": "Select an Obsidian vault",
    },

    "it": {
        'language_en': 'Inglese',
        'language_fr': 'Francese',
        'language_it': 'Italiano',
        'setting_auto_language': 'Automatico',
        'setting_hotkeys_conflict': 'Le scorciatoie per dettatura e assistente devono essere diverse.',
        'setting_invalid_value': 'Controlla i valori selezionati.',
        'setting_save_failed': 'Impossibile attivare le impostazioni. Controlla i log.',
        'answer_copy': 'Copia',
        'widget_listening': 'In ascolto…',
        'widget_assistant': 'Chiedi a Vigil…',
        'widget_processing': 'Elaborazione…',
        'widget_done': 'Fatto',
        'setup_title': 'Configura Vigil',
        'setup_welcome': 'Benvenuto e lingua',
        'setup_engine': 'Motore assistente',
        'setup_model': 'Modello assistente',
        'setup_dictation': 'Dettatura',
        'setup_voice': 'Uscita vocale',
        'setup_shortcuts': 'Scorciatoie',
        'setup_review': 'Riepilogo e preparazione',
        'setup_ready': 'Pronto',
        'setup_welcome_body': 'Scegli una lingua. Vigil conserva le impostazioni su questo computer.',
        'setup_engine_body': 'Scegli dove gira l’assistente. I motori locali restano qui; il cloud invia richieste all’endpoint scelto.',
        'setup_remote_notice': 'L’inferenza cloud richiede di disattivare la modalità solo locale nelle impostazioni.',
        'setup_allow_cloud': 'Consenti l’inferenza cloud',
        'setup_model_body': 'Riutilizza i file installati, scegli un modello dal catalogo o inserisci un nome Ollama.',
        'setup_backend': 'Backend GPU',
        'setup_binary': 'Binario llama-server esistente (facoltativo)',
        'setup_use_existing_binary': 'Scegli un binario llama-server esistente',
        'setup_use_existing_model': 'Scegli un modello GGUF esistente',
        'setup_dictation_body': 'Scegli un modello vocale. Si carica all’avvio; se manca, scaricalo dalle impostazioni.',
        'setup_voice_body': 'Scegli testo, voce o entrambi. Le voci Piper scelte vengono scaricate durante la preparazione.',
        'setup_shortcuts_body': 'Scegli scorciatoie diverse per dettatura e assistente.',
        'setup_shortcuts_notice': 'Alcuni compositor scrivono scorciatoie gestite nella configurazione utente al termine.',
        'setup_hotkey_consent': 'Consenti a Vigil di modificare le scorciatoie del compositor',
        'setup_hotkey_consent_required': 'Consenti la modifica delle scorciatoie per continuare.',
        'setup_manual_hotkeys': 'Associa questi comandi nel compositor: vigil-trigger dictate e vigil-trigger assistant.',
        'setup_review_body': 'Controlla le scelte. La preparazione riutilizza i file installati e scarica quelli mancanti.',
        'setup_ready_body': 'Configurazione pronta. Termina per salvare e avviare Vigil.',
        'setup_cancel': 'Annulla',
        'setup_back': 'Indietro',
        'setup_next': 'Continua',
        'setup_prepare': 'Scarica e configura',
        'setup_finish': 'Termina',
        'setup_reset_choices': 'Ripristina le scelte',
        'setup_preparing': 'Preparazione…',
        'setup_progress_binary': 'Download di llama-server…',
        'setup_progress_model': 'Preparazione del modello assistente…',
        'setup_progress_voice_fr': 'Download della voce francese…',
        'setup_progress_voice_en': 'Download della voce inglese…',
        'setup_choose_ollama_model': 'Scegli o inserisci un modello Ollama.',
        'setup_choose_gguf': 'Scegli un file GGUF o un modello dal catalogo.',
        'setup_choose_voice': 'Scegli una voce per la lingua selezionata.',
        'setup_piper_missing': 'Piper non è installato. Installa il profilo vocale desktop o scegli solo testo.',
        'setup_binary_invalid': 'Il file llama-server scelto è vuoto o non eseguibile.',
        'setup_prepare_failed': 'Preparazione non riuscita. Controlla la connessione o i file scelti.',
        'setup_activation_failed': 'Impossibile attivare la configurazione. Le impostazioni precedenti sono state ripristinate.',
        'setup_rollback_failed': 'Attivazione fallita; impossibile ripristinare le impostazioni precedenti. Controlla i log.',
        'setting_download_failed': 'Download non riuscito. Riprova.',
        # Local-first policy and dictation preferences
        'privacy_bad_url': 'URL del server non valido. Usa HTTP(S) senza credenziali nell’URL.',
        'privacy_remote_blocked': 'Accesso remoto bloccato dalla modalità locale. Controlla le impostazioni.',
        'privacy_data_blocked': 'La condivisione di dati locali con server remoti è disattivata.',
        'privacy_web_blocked': 'Accesso web disattivato. Controlla le impostazioni.',
        'setting_privacy': 'Modalità locale e privacy',
        'setting_local_only': 'Modalità locale rigorosa (solo server su questo computer)',
        'setting_allow_web': 'Consenti ricerche web e apertura di siti',
        'setting_share_local_data': 'Consenti strumenti locali con inferenza remota',
        'setting_log_content': 'Includi trascrizioni e risposte nei log',
        'privacy_hint': 'Salva per applicare. La modalità rigorosa blocca inferenza remota e strumenti web. Altrimenti le trascrizioni sono inviate al server scelto. Il permesso per gli strumenti locali condivide anche note, nomi di file e risultati delle app. I download di modelli/voci sono eccezioni esplicite. Le app avviate gestiscono la propria rete.',
        'setting_recovery_days': 'Recupero di incolla falliti: giorni (0 = disattivato)',
        'setting_purge': 'Cancella log e dettature recuperate…',
        'purge_confirm': 'Eliminare i log e le dettature recuperate? Impostazioni e note vengono conservate.',
        'purge_done': 'Log e recupero cancellati.',
        'setting_dictation': 'Dettatura',
        'setting_whisper_language': 'Lingua di riconoscimento (auto = rilevamento automatico)',
        'setting_max_record_seconds': 'Limite in secondi (audio scartato al limite)',
        'setting_clipboard_restore_ms': 'Attesa ripristino appunti in millisecondi',
        'setting_mic_device': 'Microfono',
        'mic_default': 'Predefinito di sistema',
        'setting_refresh_mics': 'Aggiorna microfoni',
        'mic_refresh_hint': 'Ricollega il microfono, aggiorna e riprova a registrare.',
        'mic_unavailable': 'Microfono non disponibile. Ricollegalo o scegline un altro.',
        'setting_vocabulary': 'Vocabolario personale',
        'vocabulary_hint': 'Una forma parlata = forma scritta per riga. Solo per dettatura. Esempio: vigil locale = Vigil Local',
        'vocabulary_invalid': 'Voce non valida o duplicata alla riga {line}. Usa parlato = scritto.',
        'setting_priming': 'Suggerimenti di riconoscimento',
        'priming_hint': 'Nomi e termini tecnici: Vigil, ROCm, Obsidian. Suggerimenti, non correzioni garantite.',
        'speech_download_hint': 'I modelli vengono caricati dal disco. Se manca il modello scelto, scaricalo qui sotto. Internet serve per questo download.',
        'setting_download_speech': 'Scarica / ripara il modello vocale scelto',
        'speech_downloading': 'Download modello…',
        'speech_loading': 'Caricamento locale…',
        'speech_missing': 'Modello non disponibile — impostazioni',
        'speech_ready': 'Dettatura pronta',
        'busy': 'Un’operazione è già in corso',
        'recording_expired': 'Tempo scaduto: audio scartato',
        'paste_recovered': 'Incolla fallito — testo recuperato',
        'paste_failed': 'Incolla fallito — testo non salvato',
        'mode_local': 'solo locale',
        'mode_network': 'rete abilitata',

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
            "Sei {name}, un assistente vocale per la produttività. "
            "Interpreta la richiesta. Se serve un'azione o ricerca, chiama lo strumento appropriato. "
            "Se l'utente vuole solo chattare, salutarti o fare una domanda, "
            "rispondi in testo semplice senza chiamare alcuno strumento. "
            "Per ricerche web o note, sintetizza in 2-4 frasi concise leggibili dal TTS. "
            "Per APRIRE qualcosa: app_action per app, open_url per siti, open_folder per cartelle standard. "
            "Per CHIUDERE un'app: app_action(name, 'close'). "
            "Per CERCARE file specifici: search_files(folder, query). "
            "Mai emoji o emoticon — l'output è letto ad alta voce dal TTS."
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

        "url_opened":           "Apro {url}.",
        "url_invalid":          "Impossibile aprire '{target}' — sito sconosciuto.",
        "folder_opened":        "Apro {path}.",
        "folder_unknown":       "La cartella '{name}' non è una cartella standard riconosciuta.",
        "folder_missing":       "La cartella '{path}' non esiste.",
        "retry_launch_url_hint": (
            "NOTA: \"{name}\" è anche il nome di un sito web popolare. Se l'utente "
            "intendeva il sito (e non un'app installata), chiama open_url(\"{name}\") "
            "invece."
        ),

        "file_no_results":      "Nessun file corrispondente a '{query}' in {folder}.",
        "file_results_found":   "Trovato in {folder}:\n{list}",
        "file_results_similar": "Nessuna corrispondenza esatta per '{query}' in {folder}. File simili:\n{list}",
        "file_opened":          "Apro {name}.",
        "file_open_failed":     "Impossibile aprire '{path}'.",
        "retry_launch_ctx": (
            "L'applicazione \"{name}\" non è stata trovata su questo sistema.\n\n"
            "Applicazioni installate che potrebbero corrispondere alla richiesta "
            "(formato `- Nome (GenericName) [Keywords]`):\n{list}\n\n"
            "Regole:\n"
            "1. Se UNA singola app corrisponde chiaramente meglio all'intento "
            "dell'utente (il suo generic name o le keywords corrispondono direttamente "
            "a ciò che l'utente ha chiesto), chiama app_action con il suo nome esatto "
            "copiato dalla lista e action='launch'.\n"
            "2. Se la richiesta dell'utente è generica (es. 'musica', 'browser', "
            "'terminale') e due o più applicazioni potrebbero ragionevolmente andare "
            "bene, chiama ask_user_choice con 2-4 candidati invece di indovinare — "
            "lascia scegliere all'utente.\n"
            "3. Se nulla nella lista corrisponde, rispondi in testo normale (in "
            "italiano) che l'applicazione non è installata. Non chiamare alcuno "
            "strumento."
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
        "setting_llm_ctx_size":     "Dimensione contesto (token)",
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
        "setting_rerun_setup":      "Ripeti la configurazione",
        "setting_uninstall":        "Disinstalla",
        "setting_assistant_name":   "Nome dell'assistente",
        "settings_title":           "Impostazioni",
        "settings_intro":           "Voce, modelli e comportamento del desktop",
        "group_voice_models":       "Voce e modelli",
        "group_general":            "Generale",
        "group_overlay":            "Overlay",
        "group_speech_output":      "Sintesi vocale",
        "group_maintenance":        "Manutenzione",
        "setting_llm_provider":     "Motore dell'assistente",
        "provider_llama_cpp":       "llama.cpp (locale)",
        "provider_ollama_local":    "Ollama (locale)",
        "provider_ollama_cloud":    "Ollama Cloud",
        "setting_ollama_url":       "URL Ollama",
        "setting_ollama_model":     "Modello Ollama",
        "setting_ollama_api_key":   "Chiave API",
        "setting_refresh":          "Aggiorna",
        "setting_fetching_models":  "Caricamento modelli…",
        "setting_tts":              "Sintesi vocale",
        "setting_tts_mode":         "Modalità di uscita",
        "setting_tts_speaker":      "Voce",
        "setting_tts_sample":       "Riproduci esempio",
        "setting_save":             "Salva impostazioni",
        "setting_saved_status":     "Modifiche salvate",
        "setting_auto_screen":      "Automatico (schermo attivo)",
        "setting_model_path_hint":  "Scegli un file modello GGUF",
        "action_copy":              "Copia",
        "status_waiting":           "In attesa…",
        "tray_dictate":             "Dettatura ({shortcut})",
        "tray_assistant":           "Assistente ({shortcut})",
        "accordion_expand":         "Espandi {section}",
        "accordion_collapse":       "Comprimi {section}",
        "choice_never":             "Mai",
        "choice_off":               "Disattivato",
        "choice_overlay":           "Overlay",
        "choice_tts":               "Solo voce",
        "choice_both":              "Overlay e voce",
        "position_top_left":        "In alto a sinistra",
        "position_top_center":      "In alto al centro",
        "position_top_right":       "In alto a destra",
        "position_center_left":     "Al centro a sinistra",
        "position_center":          "Al centro",
        "position_center_right":    "Al centro a destra",
        "position_bottom_left":     "In basso a sinistra",
        "position_bottom_center":   "In basso al centro",
        "position_bottom_right":    "In basso a destra",
        "answer_closes_in":         "Chiusura tra {seconds}s",
        "hotkey_rebind_failed":     "Aggiornamento scorciatoie non riuscito — consulta i log",
        "tray_shortcuts_status":    "{dict_shortcut}=dettatura, {assist_shortcut}=assistente",
        "setting_no_models":        "Nessun modello — premi Aggiorna",
        "setting_models_available": "{count} modelli disponibili",
        "setting_model_fetch_failed": "{detail} — inserisci il modello manualmente",
        "setting_ollama_unreachable": "Impossibile raggiungere l’API Ollama",
        "setting_voices_available": "{count} voci disponibili",
        "setting_voices_title": "Voci",
        "tray_dictation_action": "Dettatura",
        "tray_assistant_action": "Assistente",
        "ui_preview": "Anteprima interfaccia",
        "dialog_select_gguf": "Seleziona un modello GGUF",
        "dialog_gguf_files": "File GGUF",
        "dialog_all_files": "Tutti i file",
        "dialog_select_vault": "Seleziona un vault Obsidian",
    },

    "fr": {
        'language_en': 'Anglais',
        'language_fr': 'Français',
        'language_it': 'Italien',
        'setting_auto_language': 'Automatique',
        'setting_hotkeys_conflict': 'Les raccourcis de dictée et d’assistant doivent être différents.',
        'setting_invalid_value': 'Vérifiez les valeurs sélectionnées.',
        'setting_save_failed': 'Impossible d’activer ces paramètres. Consultez les journaux.',
        'answer_copy': 'Copier',
        'widget_listening': 'Écoute…',
        'widget_assistant': 'Demander à Vigil…',
        'widget_processing': 'Traitement…',
        'widget_done': 'Terminé',
        'setup_title': 'Configurer Vigil',
        'setup_welcome': 'Bienvenue et langue',
        'setup_engine': 'Moteur de l’assistant',
        'setup_model': 'Modèle de l’assistant',
        'setup_dictation': 'Dictée',
        'setup_voice': 'Sortie vocale',
        'setup_shortcuts': 'Raccourcis',
        'setup_review': 'Résumé et préparation',
        'setup_ready': 'Prêt',
        'setup_welcome_body': 'Choisissez une langue. Vigil garde vos réglages sur cet ordinateur.',
        'setup_engine_body': 'Choisissez où tourne l’assistant. Les moteurs locaux restent ici ; le cloud envoie les requêtes à l’adresse choisie.',
        'setup_remote_notice': 'L’inférence cloud exige de désactiver le mode strictement local dans les paramètres.',
        'setup_allow_cloud': 'Autoriser l’inférence cloud',
        'setup_model_body': 'Réutilisez les fichiers installés, choisissez un modèle du catalogue ou saisissez un nom Ollama.',
        'setup_backend': 'Moteur GPU',
        'setup_binary': 'Binaire llama-server existant (facultatif)',
        'setup_use_existing_binary': 'Choisir un binaire llama-server existant',
        'setup_use_existing_model': 'Choisir un modèle GGUF existant',
        'setup_dictation_body': 'Choisissez un modèle vocal. Il se charge au démarrage ; s’il manque, téléchargez-le depuis les paramètres.',
        'setup_voice_body': 'Choisissez le texte, la voix ou les deux. Les voix Piper sélectionnées seront téléchargées lors de la préparation.',
        'setup_shortcuts_body': 'Choisissez deux raccourcis différents pour la dictée et l’assistant.',
        'setup_shortcuts_notice': 'Certains compositeurs écrivent des raccourcis gérés dans votre configuration utilisateur à la fin.',
        'setup_hotkey_consent': 'Autoriser Vigil à modifier les raccourcis du compositeur',
        'setup_hotkey_consent_required': 'Autorisez la modification des raccourcis pour continuer.',
        'setup_manual_hotkeys': 'Associez ces commandes dans votre compositeur : vigil-trigger dictate et vigil-trigger assistant.',
        'setup_review_body': 'Vérifiez vos choix. La préparation réutilise les fichiers installés et télécharge les éléments manquants.',
        'setup_ready_body': 'La configuration est prête. Terminez pour enregistrer et lancer Vigil.',
        'setup_cancel': 'Annuler',
        'setup_back': 'Retour',
        'setup_next': 'Continuer',
        'setup_prepare': 'Télécharger et configurer',
        'setup_finish': 'Terminer',
        'setup_reset_choices': 'Réinitialiser les choix',
        'setup_preparing': 'Préparation…',
        'setup_progress_binary': 'Téléchargement de llama-server…',
        'setup_progress_model': 'Préparation du modèle de l’assistant…',
        'setup_progress_voice_fr': 'Téléchargement de la voix française…',
        'setup_progress_voice_en': 'Téléchargement de la voix anglaise…',
        'setup_choose_ollama_model': 'Choisissez ou saisissez un modèle Ollama.',
        'setup_choose_gguf': 'Choisissez un fichier GGUF ou un modèle du catalogue.',
        'setup_choose_voice': 'Choisissez une voix pour la langue sélectionnée.',
        'setup_piper_missing': 'Piper n’est pas installé. Installez le profil vocal de bureau ou choisissez le texte seul.',
        'setup_binary_invalid': 'Le fichier llama-server choisi est vide ou non exécutable.',
        'setup_prepare_failed': 'La préparation a échoué. Vérifiez la connexion ou les fichiers choisis.',
        'setup_activation_failed': 'Impossible d’activer cette configuration. Les réglages précédents ont été rétablis.',
        'setup_rollback_failed': 'L’activation a échoué et les anciens réglages n’ont pas pu être rétablis. Consultez les journaux.',
        'setting_download_failed': 'Échec du téléchargement. Réessayez.',
        # Local-first policy and dictation preferences
        'privacy_bad_url': 'URL du serveur invalide. Utilisez HTTP(S) sans identifiants dans l’URL.',
        'privacy_remote_blocked': 'Accès distant bloqué par le mode local. Voir les paramètres.',
        'privacy_data_blocked': 'Le partage des données locales avec un serveur distant est désactivé.',
        'privacy_web_blocked': 'L’accès web est désactivé. Voir les paramètres.',
        'setting_privacy': 'Mode local et confidentialité',
        'setting_local_only': 'Mode local strict (serveurs sur cette machine)',
        'setting_allow_web': 'Autoriser les recherches web et l’ouverture de sites',
        'setting_share_local_data': 'Autoriser les outils locaux avec un LLM distant',
        'setting_log_content': 'Inclure les transcriptions et réponses dans les logs',
        'privacy_hint': 'Sauvegardez pour appliquer. Le mode strict bloque les LLM distants et les outils web. Hors mode strict, la parole transcrite est envoyée au serveur choisi. Autoriser les outils locaux partage aussi extraits de notes, noms de fichiers et résultats d’applications. Les téléchargements de modèles/voix sont des exceptions explicites. Les applications lancées gèrent leur propre accès réseau.',
        'setting_recovery_days': 'Récupération des collages échoués : jours (0 = désactivée)',
        'setting_purge': 'Effacer les logs et les dictées récupérées…',
        'purge_confirm': 'Supprimer les logs de Vigil et les dictées récupérées ? Les réglages et notes sont conservés.',
        'purge_done': 'Logs et récupération effacés.',
        'setting_dictation': 'Dictée',
        'setting_whisper_language': 'Langue de reconnaissance (auto = détection automatique)',
        'setting_max_record_seconds': 'Limite en secondes (audio abandonné à la limite)',
        'setting_clipboard_restore_ms': 'Délai de restauration du presse-papiers en millisecondes',
        'setting_mic_device': 'Microphone',
        'mic_default': 'Défaut du système',
        'setting_refresh_mics': 'Actualiser les microphones',
        'mic_refresh_hint': 'Rebranchez le microphone, actualisez puis relancez la dictée.',
        'mic_unavailable': 'Micro indisponible. Rebranchez-le ou choisissez-en un autre.',
        'setting_vocabulary': 'Vocabulaire personnel',
        'vocabulary_hint': 'Une forme prononcée = forme écrite par ligne. Appliqué à la dictée uniquement. Exemple : roque aime = ROCm',
        'vocabulary_invalid': 'Entrée invalide ou doublon à la ligne {line}. Format : prononcé = écrit.',
        'setting_priming': 'Termes pour guider la reconnaissance',
        'priming_hint': 'Noms et termes techniques : Vigil, ROCm, Obsidian. Aide la reconnaissance sans garantir la correction.',
        'speech_download_hint': 'Les modèles sont toujours chargés depuis le disque. Si le modèle choisi manque, téléchargez-le ci-dessous. Internet est requis pour ce téléchargement.',
        'setting_download_speech': 'Télécharger / réparer le modèle vocal choisi',
        'speech_downloading': 'Téléchargement…',
        'speech_loading': 'Chargement local…',
        'speech_missing': 'Modèle indisponible — paramètres',
        'speech_ready': 'Dictée prête',
        'busy': 'Une opération est déjà en cours',
        'recording_expired': 'Durée limite : audio abandonné',
        'paste_recovered': 'Collage échoué — texte récupéré',
        'paste_failed': 'Collage échoué — texte non sauvegardé',
        'mode_local': 'local uniquement',
        'mode_network': 'réseau autorisé',

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
            "Tu es {name}, assistant vocal pour la productivite. "
            "Interprete la demande. Si une action ou recherche est necessaire, appelle le bon outil. "
            "Si l'utilisateur veut juste discuter, te saluer ou pose une question, "
            "reponds en texte brut sans appeler d'outil. "
            "Pour les recherches (web ou notes), synthetise en 2-4 phrases concises lisibles par TTS. "
            "Pour OUVRIR quelque chose : app_action pour les applis, open_url pour les sites, "
            "open_folder pour les dossiers standards. "
            "Pour FERMER une app : app_action(name, 'close'). "
            "Pour TROUVER un fichier precis : search_files(folder, query). "
            "Jamais d'emoji ou emoticone — la reponse est lue par TTS."
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

        "url_opened":           "Ouverture de {url}.",
        "url_invalid":          "Impossible d'ouvrir « {target} » — site inconnu.",
        "folder_opened":        "Ouverture de {path}.",
        "folder_unknown":       "Le dossier « {name} » n'est pas un dossier standard reconnu.",
        "folder_missing":       "Le dossier « {path} » n'existe pas.",
        "retry_launch_url_hint": (
            "NOTE : « {name} » est aussi le nom d'un site web populaire. Si "
            "l'utilisateur voulait le site (et non une application installée), "
            "appelle open_url(\"{name}\") à la place."
        ),

        "file_no_results":      "Aucun fichier correspondant à « {query} » dans {folder}.",
        "file_results_found":   "Trouvé dans {folder} :\n{list}",
        "file_results_similar": "Aucune correspondance exacte pour « {query} » dans {folder}. Fichiers similaires :\n{list}",
        "file_opened":          "Ouverture de {name}.",
        "file_open_failed":     "Impossible d'ouvrir « {path} ».",
        "retry_launch_ctx": (
            "L'application \"{name}\" n'a pas été trouvée sur ce système.\n\n"
            "Applications installées pouvant correspondre à la demande de l'utilisateur "
            "(format `- Nom (GenericName) [Keywords]`) :\n{list}\n\n"
            "Règles :\n"
            "1. Si UNE seule app correspond clairement mieux à l'intention de l'utilisateur "
            "(son generic name ou ses keywords correspondent directement à ce qu'il "
            "demande), appelle app_action avec son nom exact copié depuis la liste et action='launch'.\n"
            "2. Si la demande de l'utilisateur est générique (ex: 'musique', 'navigateur', "
            "'terminal') et que plusieurs applications pourraient raisonnablement "
            "convenir, appelle ask_user_choice avec 2-4 candidats plutôt que de deviner — "
            "laisse l'utilisateur choisir.\n"
            "3. Si rien dans la liste ne convient, réponds en texte simple (en français) "
            "que l'application n'est pas installée. N'appelle aucun outil."
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

        # Settings UI
        "setting_saved":            "Paramètres enregistrés",
        "setting_whisper_model":    "Modèle Whisper",
        "setting_llm_model":        "Modèle LLM (.gguf)",
        "setting_llm_unload":       "Déchargement LLM (inactivité)",
        "setting_llm_gpu_layers":   "Couches GPU (ngl)",
        "setting_llm_ctx_size":     "Taille du contexte (tokens)",
        "setting_llm_url":          "URL du serveur LLM",
        "setting_obsidian_vault":   "Coffre Obsidian",
        "setting_language":         "Langue",
        "setting_overlay_position": "Position de l’affichage flottant",
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
        "setting_rerun_setup":      "Relancer la configuration",
        "setting_uninstall":        "Désinstaller",
        "setting_assistant_name":   "Nom de l'assistant",
        "settings_title":           "Paramètres",
        "settings_intro":           "Voix, modèles et comportement du bureau",
        "group_voice_models":       "Voix et modèles",
        "group_general":            "Général",
        "group_overlay":            "Affichage flottant",
        "group_speech_output":      "Sortie vocale",
        "group_maintenance":        "Maintenance",
        "setting_llm_provider":     "Moteur de l’assistant",
        "provider_llama_cpp":       "llama.cpp (local)",
        "provider_ollama_local":    "Ollama (local)",
        "provider_ollama_cloud":    "Ollama Cloud",
        "setting_ollama_url":       "URL Ollama",
        "setting_ollama_model":     "Modèle Ollama",
        "setting_ollama_api_key":   "Clé API",
        "setting_refresh":          "Actualiser",
        "setting_fetching_models":  "Récupération des modèles…",
        "setting_tts":              "Synthèse vocale",
        "setting_tts_mode":         "Mode de sortie",
        "setting_tts_speaker":      "Locuteur",
        "setting_tts_sample":       "Écouter un extrait",
        "setting_save":             "Enregistrer les paramètres",
        "setting_saved_status":     "Modifications enregistrées",
        "setting_auto_screen":      "Automatique (écran actif)",
        "setting_model_path_hint":  "Choisir un fichier de modèle GGUF",
        "action_copy":              "Copier",
        "status_waiting":           "En attente…",
        "tray_dictate":             "Dicter ({shortcut})",
        "tray_assistant":           "Assistant ({shortcut})",
        "accordion_expand":         "Développer {section}",
        "accordion_collapse":       "Réduire {section}",
        "choice_never":             "Jamais",
        "choice_off":               "Désactivé",
        "choice_overlay":           "Overlay",
        "choice_tts":               "Voix uniquement",
        "choice_both":              "Overlay et voix",
        "position_top_left":        "En haut à gauche",
        "position_top_center":      "En haut au centre",
        "position_top_right":       "En haut à droite",
        "position_center_left":     "Au centre à gauche",
        "position_center":          "Au centre",
        "position_center_right":    "Au centre à droite",
        "position_bottom_left":     "En bas à gauche",
        "position_bottom_center":   "En bas au centre",
        "position_bottom_right":    "En bas à droite",
        "answer_closes_in":         "Fermeture dans {seconds}s",
        "hotkey_rebind_failed":     "Échec de la mise à jour des raccourcis — voir les logs",
        "tray_shortcuts_status":    "{dict_shortcut}=dictée, {assist_shortcut}=assistant",
        "setting_no_models":        "Aucun modèle — cliquez sur Actualiser",
        "setting_models_available": "{count} modèle(s) disponible(s)",
        "setting_model_fetch_failed": "{detail} — saisissez le modèle manuellement",
        "setting_ollama_unreachable": "Impossible de joindre l’API Ollama",
        "setting_voices_available": "{count} voix disponible(s)",
        "setting_voices_title": "Voix",
        "tray_dictation_action": "Dicter",
        "tray_assistant_action": "Assistant",
        "ui_preview": "Aperçu de l’interface",
        "dialog_select_gguf": "Choisir un modèle GGUF",
        "dialog_gguf_files": "Fichiers GGUF",
        "dialog_all_files": "Tous les fichiers",
        "dialog_select_vault": "Choisir un coffre Obsidian",
    },
}

_FALLBACK = "en"


# ── Public API ────────────────────────────────────────────────────────────

def translate(key: str, language: str | None = None, **kwargs) -> str:
    """Return *key* in an explicit language without changing global state."""
    lang = language or getattr(config, "LANGUAGE", _FALLBACK)
    table = _STRINGS.get(lang, _STRINGS[_FALLBACK])
    template = table.get(key, _STRINGS[_FALLBACK].get(key, key))
    if kwargs:
        try:
            return template.format(**kwargs)
        except (KeyError, IndexError):
            return template
    return template


def get(key: str, **kwargs) -> str:
    """Return the localised string for *key*, formatted with *kwargs*.

    Falls back to English if the key is missing in the active language.
    """
    return translate(key, **kwargs)
