# WritHer Overlay UI — Design Spec
Date: 2026-04-17

## Overview

Redesign the floating overlay to support three distinct visual states (Dictate, Listening/Assistant, Answer) and introduce a new answer card for displaying LLM responses with typewriter effect, smart dismiss, and configurable position.

---

## States

### 1. Dictate (transcription en cours)
- Pill 220×44px, bottom-center
- Yeux blancs pulsés (animation scale 1→1.35)
- Point indicateur rouge animé (blink) à gauche du label
- Label "Listening..." blanc à 55% d'opacité
- Waveform 5 barres blanches animées

### 2. Listening / Assistant (mode assistant, enregistrement)
- Pill 220×44px, bottom-center
- Yeux violet (#a090ff) pulsés (animation scale 1→1.30)
- Point indicateur violet animé à gauche du label
- Label "Assistant..." violet à 70% d'opacité
- Waveform 5 barres violettes animées
- Bordure pill : `rgba(120,100,255,0.2)` (vs blanc pour dictate)

### 3. Thinking (traitement LLM)
- Pill existante, expression "thinking" (yeux qui dérivent gauche/droite)
- Label "Thinking..." — pas de changement

### 4. Answer (réponse LLM affichée)
Fenêtre séparée (Toplevel) qui apparaît au-dessus de la pill.

**Header**
- Avatar (yeux Pandora Blackboard blancs, statiques) + séparateur + label "WritHer" + bouton ✕

**Corps**
- Texte affiché token-by-token (typewriter, timer Tk à 30ms/token)
- `max-height` configurable (défaut : 200px), overflow-y scroll
- Scrollbar minimaliste (4px, fond transparent)
- Police : Segoe UI 11px, couleur #c8c8d4, line-height 1.65

**Footer**
- Bouton "⌘ Copier" (copie le texte dans le clipboard via pyperclip)
- Countdown "ferme dans Xs" + barre de progression qui se vide sur la durée

**Dismiss logic (smart dismiss)**
- Auto-fermeture après `OVERLAY_ANSWER_TIMEOUT` secondes (défaut : 8)
- Hover sur la card → countdown pausé, reprend au mouse-leave
- Scroll sur la card → countdown reset à la valeur initiale
- Clic sur ✕ → fermeture immédiate
- Prochain raccourci hotkey → fermeture immédiate de la card

**Transition**
- Card : fade-in (même mécanique que la pill, `_FADE_STEPS`)
- Pill reste visible en état "happy" pendant que la card est ouverte
- Card fermée → pill fade-out

---

## Position & Configuration

Position configurable via `config.OVERLAY_POSITION` (persisté en DB).

| Valeur | Description |
|--------|-------------|
| `bottom-center` | Centré en bas (défaut) |
| `bottom-right` | Coin bas-droit, offset 16px |
| `top-right` | Coin haut-droit, offset 16px |

La pill et la card suivent le même ancrage. Offset vertical entre les deux : 8px.

---

## Architecture

### Fichiers modifiés
- **`widget.py`** : ajout état Listening/assistant (couleurs violettes), méthode `show_answer(text: str)`
- **`config.py`** : `OVERLAY_POSITION = "bottom-center"`, `OVERLAY_ANSWER_TIMEOUT = 8`
- **`main.py`** : `_assistant_worker()` appelle `widget.show_answer(result)` au lieu de `widget.show_message(result, 3000)` ; `_on_hotkey_press()` et `_on_assist_press()` appellent `widget.hide_answer()` pour fermer la card si ouverte ; `_load_settings()` charge `overlay_position` depuis DB
- **`settings_window.py`** : dropdown "Overlay position" (bottom-center / bottom-right / top-right)
- **`database.py`** : clé `overlay_position` dans settings (si pas déjà présente)

### Nouveau dans widget.py

```python
class AnswerCard:
    """Fenêtre flottante pour afficher la réponse LLM avec typewriter + smart dismiss."""
    def show(self, text: str): ...    # timeout lu depuis config.OVERLAY_ANSWER_TIMEOUT
    def hide(self): ...
    def _typewriter_tick(self): ...   # root.after(30, ...) token-by-token
    def _reset_countdown(self): ...   # appelé sur scroll
    def _pause_countdown(self): ...   # appelé sur <Enter> (hover)
    def _resume_countdown(self): ...  # appelé sur <Leave>
    def _copy_to_clipboard(self): ... # pyperclip.copy(self._full_text)
```

`RecordingWidget` garde une référence à `AnswerCard` et la crée à la demande.

---

## Config defaults

```python
OVERLAY_POSITION = "bottom-center"   # bottom-center | bottom-right | top-right
OVERLAY_ANSWER_TIMEOUT = 8           # secondes avant auto-fermeture
```

---

## Out of scope (v1)

- Streaming SSE depuis llama-server (typewriter côté client suffit)
- Redimensionnement drag de la card
- Historique des réponses
