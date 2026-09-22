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

        # settings_window.py
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
        "setting_rerun_setup":      "Re-run setup",
        "setting_uninstall":        "Uninstall",
        "setting_assistant_name":   "Assistant name",
    },

    "it": {
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
        "setting_rerun_setup":      "Riavvia setup",
        "setting_uninstall":        "Disinstalla",
        "setting_assistant_name":   "Nome dell'assistente",
    },

    "fr": {
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

        # settings_window.py
        "setting_saved":            "Paramètres enregistrés",
        "setting_whisper_model":    "Modèle Whisper",
        "setting_llm_model":        "Modèle LLM (.gguf)",
        "setting_llm_unload":       "Déchargement LLM (inactivité)",
        "setting_llm_gpu_layers":   "Couches GPU (ngl)",
        "setting_llm_ctx_size":     "Taille du contexte (tokens)",
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
