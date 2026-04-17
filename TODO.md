# WritHer Linux — TODO Polish

## UI / Fenêtres

- [ ] **Settings** : appliquer le changement de langue sans redémarrage (reload locales + update labels)
- [ ] **Settings** : overlay position picker visuel (prévisualisation des 3 positions)
- [ ] **Settings** : valider le champ LLM URL avant sauvegarde (ping test inline)
- [ ] **Notes** : ajouter un bouton "Nouveau" par onglet (note, RDV, rappel) directement dans la toolbar
- [ ] **Notes** : trier les RDV par date dans l'affichage
- [ ] **Widget overlay** : animation de transition entre états (recording → processing → answer)

## Hotkeys / Input

- [ ] Tester AltGr sur layout clavier français (AZERTY) — vérifier que pynput intercepte correctement
- [ ] Documenter le fallback tray (boutons dictée/assistant) dans l'UI settings quand Wayland sans KDE
- [ ] Option pour configurer les hotkeys depuis settings_window (actuellement hardcodé dans config.py)

## TTS (Text-to-Speech)

- [ ] **Implémenter le plan TTS** : `docs/superpowers/plans/2026-04-17-tts.md` (7 tâches — config, tts.py, first_run phases 0/2.5/3, main.py wiring, settings_window TTS section)

## LLM / Assistant

- [ ] Afficher un indicateur visuel quand llama-server est down au démarrage (pas juste un log)
- [ ] Timeout configurable pour les requêtes LLM (actuellement 60s hardcodé dans llm_backend.py)
- [ ] Améliorer le prompt système fr pour les tool calls vault Obsidian (trop de faux négatifs)

## Notifier / Rappels

- [ ] Tester les notifications de rappel sur KDE Plasma (notify-send + icône appli)
- [ ] Gérer les rappels récurrents (ex: "tous les lundis")

## Packaging / Distribution

- [ ] Créer un fichier `.desktop` pour autostart au login KDE
- [ ] Documenter la config llama-server recommandée (modèle, flags, port)
- [ ] Script d'install (`install.sh`) : deps système (xclip/wl-clipboard, libnotify), uv, llama-server

## Nettoyage code

- [ ] Supprimer ou documenter les scripts debug : `debug_keys.py`, `diag_hotkey.py`
- [ ] `tray_icon.py` vs `tray_qt.py` : clarifier lequel est actif, supprimer l'autre si mort
- [ ] Vérifier que `json_repair.py` est bien utilisé (sinon virer)
