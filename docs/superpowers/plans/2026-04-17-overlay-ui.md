# Overlay UI Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add visual distinction between Dictate/Assistant pill states and a new answer card with typewriter text, smart dismiss, and configurable position.

**Architecture:** All changes live in `widget.py` (new `AnswerCard` class + pill indicator dot + violet assistant colors), `config.py` (two new constants), `main.py` (wire-up + load settings), and `settings_window.py` (position dropdown). No new files needed.

**Tech Stack:** Python 3.11, tkinter (Toplevel, Canvas, Text, Frame, Label), pyperclip, CustomTkinter (settings only)

---

## File Map

| File | Change |
|------|--------|
| `widget.py` | Add `_dot_id` indicator dot to pill, violet assistant colors, `AnswerCard` class, `show_answer`/`hide_answer` on `RecordingWidget` |
| `config.py` | Add `OVERLAY_POSITION = "bottom-center"` and `OVERLAY_ANSWER_TIMEOUT = 8` |
| `main.py` | Load `overlay_position` in `_load_settings()`, call `hide_answer()` on hotkey press, call `show_answer()` in `_assistant_worker()` |
| `settings_window.py` | Add overlay position dropdown, increase `_WIN_H` to 600, add `_on_overlay_pos_change` callback |

---

## Task 1 — Config: add OVERLAY_POSITION + OVERLAY_ANSWER_TIMEOUT

**Files:**
- Modify: `config.py`
- Modify: `main.py` — `_load_settings()` function (lines 59–79)

- [ ] **Step 1: Add constants to config.py**

In `config.py`, append after `APPOINTMENT_REMIND_MINUTES = 15`:

```python
# ── Overlay ──────────────────────────────────────────────────────────────────
# Position of the pill and answer card on screen.
# Values: "bottom-center" | "bottom-right" | "top-right"
OVERLAY_POSITION = "bottom-center"

# Seconds before the answer card auto-closes (smart dismiss resets this).
OVERLAY_ANSWER_TIMEOUT = 8
```

- [ ] **Step 2: Load overlay_position from DB in main.py**

In `main.py`, inside `_load_settings()`, add after the `lang` block (after line 79):

```python
    pos = db.get_setting("overlay_position", "")
    if pos:
        config.OVERLAY_POSITION = pos
```

- [ ] **Step 3: Verify**

Run: `python -c "import config; print(config.OVERLAY_POSITION, config.OVERLAY_ANSWER_TIMEOUT)"`

Expected output: `bottom-center 8`

- [ ] **Step 4: Commit**

```bash
git add config.py main.py
git commit -m "feat: add OVERLAY_POSITION and OVERLAY_ANSWER_TIMEOUT config keys"
```

---

## Task 2 — widget.py: violet assistant state + indicator dot

**Files:**
- Modify: `widget.py`

### 2a — Add imports and new constants

- [ ] **Step 1: Add missing imports at top of widget.py**

After `import threading` (line 22), add:

```python
import re
import time
import config
```

- [ ] **Step 2: Replace `_TEXT_X` and add `_DOT_X` constant**

Replace the existing line:
```python
_TEXT_X    = _SEP_X + 10     # status text start x
```
with:
```python
_DOT_X     = _SEP_X + 10     # indicator dot center x = 58
_TEXT_X    = _SEP_X + 22     # status text start x = 70 (shifted 12px right for dot)
```

### 2b — Update assistant state colors

- [ ] **Step 3: Update `_STATE_STYLE["assistant"]` to violet**

Replace:
```python
    "assistant":  {"accent": (255, 255, 255), "glow": (255, 255, 255), "border": (255, 255, 255), "border_a": 0.08, "label": ""},
```
with:
```python
    "assistant":  {"accent": (160, 144, 255), "glow": (160, 144, 255), "border": (120, 100, 255), "border_a": 0.15, "label": "Assistant..."},
```

- [ ] **Step 4: Update `_EYE_THEME["assistant"]` to violet**

Replace:
```python
    "assistant":  {"eye": (255, 255, 255), "glow": (255, 255, 255)},
```
with:
```python
    "assistant":  {"eye": (160, 144, 255), "glow": (120, 100, 255)},
```

- [ ] **Step 5: Fix `_show()` to use "assistant" expression for ASSISTANT mode**

In `RecordingWidget._show()`, replace:
```python
        elif mode == self.ASSISTANT:
            self._expression = "listening"
```
with:
```python
        elif mode == self.ASSISTANT:
            self._expression = "assistant"
```

### 2c — Add indicator dot to pill

- [ ] **Step 6: Add `_dot_id = None` to `RecordingWidget.__init__`**

In `RecordingWidget.__init__`, after `self._sep_ids = []`, add:
```python
        self._dot_id     = None   # pulsing color dot: red=dictate, violet=assistant
```

- [ ] **Step 7: Create dot in `_build()`**

In `RecordingWidget._build()`, after the separator creation block (after `self._sep_ids.append(sep)`), add:

```python
        # ── Indicator dot (red=dictate, violet=assistant) ─────────────
        self._dot_id = c.create_oval(
            _DOT_X - 3, _H // 2 - 3,
            _DOT_X + 3, _H // 2 + 3,
            fill="#ff4444", outline="", state="hidden",
        )
```

- [ ] **Step 8: Animate dot in `_animate()`**

In `RecordingWidget._animate()`, before the `# Waveform bars` comment block, add:

```python
        # Indicator dot — pulsing red for dictation, violet for assistant
        if self._dot_id is not None:
            if self._mode == self.RECORDING:
                val = 0.35 + 0.65 * abs(math.sin(self._tick * 0.1))
                r = int(100 + 155 * val)
                g = int(20 * val)
                b = int(20 * val)
                self._canvas.itemconfig(self._dot_id,
                                        fill=f"#{r:02x}{g:02x}{b:02x}",
                                        state="normal")
            elif self._mode == self.ASSISTANT:
                val = 0.35 + 0.65 * abs(math.sin(self._tick * 0.08))
                r = int(48 + 112 * val)
                g = int(40 + 104 * val)
                b = int(96 + 159 * val)
                self._canvas.itemconfig(self._dot_id,
                                        fill=f"#{r:02x}{g:02x}{b:02x}",
                                        state="normal")
            else:
                self._canvas.itemconfig(self._dot_id, state="hidden")

```

- [ ] **Step 9: Verify visually**

Run the app (`uv run python main.py`), trigger dictation hotkey → pill should show red pulsing dot + white eyes. Trigger assistant hotkey → pill should show violet pulsing dot + violet eyes.

- [ ] **Step 10: Commit**

```bash
git add widget.py
git commit -m "feat: violet assistant pill state + pulsing indicator dot"
```

---

## Task 3 — widget.py: AnswerCard class

**Files:**
- Modify: `widget.py` — add `AnswerCard` class before `RecordingWidget`, add `show_answer`/`hide_answer` to `RecordingWidget`

### Card layout constants

- [ ] **Step 1: Add card constants after existing pill constants (after `_ANIM_FPS_MS` line)**

```python
# ── Answer card constants ─────────────────────────────────────────────────────
_CARD_W          = 400
_CARD_HEADER_H   = 36
_CARD_BODY_MAX_H = 160
_CARD_FOOTER_H   = 28
_CARD_PROG_H     = 2
_CARD_GAP        = 8    # vertical gap between pill top and card bottom
_CARD_MARGIN     = 16   # edge margin for non-centered positions
_TYPEWRITER_MS   = 28   # ms between tokens during typewriter animation
```

### AnswerCard class

- [ ] **Step 2: Add `AnswerCard` class to widget.py**

Add this class just before the `RecordingWidget` class definition:

```python
class AnswerCard:
    """Floating answer card: typewriter text, smart dismiss, configurable position."""

    def __init__(self, root: tk.Tk):
        self._root = root
        self._win: tk.Toplevel | None = None
        self._text_widget: tk.Text | None = None
        self._footer_label: tk.Label | None = None
        self._prog_canvas: tk.Canvas | None = None
        self._prog_id = None
        self._full_text = ""
        self._tokens: list[str] = []
        self._token_idx = 0
        self._after_type: str | None = None
        self._after_countdown: str | None = None
        self._countdown_start = 0.0
        self._countdown_dur = 0.0
        self._paused = False
        self._alpha = 0.0
        self._after_fade: str | None = None
        self._fading: str | None = None

    # ── public API ────────────────────────────────────────────────────────────

    def show(self, text: str):
        self._root.after(0, lambda: self._show(text))

    def hide(self):
        self._root.after(0, self._start_fade_out)

    # ── internal ──────────────────────────────────────────────────────────────

    def _show(self, text: str):
        self._cancel_all_timers()
        self._full_text = text
        self._tokens = re.findall(r'\S+\s*|\n', text)
        self._token_idx = 0
        self._countdown_dur = float(getattr(config, "OVERLAY_ANSWER_TIMEOUT", 8))
        self._paused = False

        needs_build = self._win is None
        if not needs_build:
            try:
                needs_build = not self._win.winfo_exists()
            except Exception:
                needs_build = True

        if needs_build:
            self._build()
        else:
            self._win.deiconify()

        self._text_widget.config(state=tk.NORMAL)
        self._text_widget.delete("1.0", tk.END)
        self._text_widget.config(state=tk.DISABLED)

        self._alpha = 0.0
        self._fading = None
        self._win.wm_attributes("-alpha", 0.0)
        self._start_fade_in()
        self._typewriter_tick()
        self._countdown_start = time.monotonic()
        self._countdown_tick()

    def _build(self):
        win = tk.Toplevel(self._root)
        win.overrideredirect(True)
        win.wm_attributes("-topmost", True)
        win.wm_attributes("-alpha", 0.0)
        win.configure(bg="#0c0c0f")

        total_h = (_CARD_HEADER_H + 1 + _CARD_BODY_MAX_H
                   + 1 + _CARD_FOOTER_H + _CARD_PROG_H)
        x, y = self._calc_position(total_h)
        win.geometry(f"{_CARD_W}x{total_h}+{x}+{y}")

        # Outer frame with border
        outer = tk.Frame(win, bg="#0c0c0f",
                         highlightbackground="#1e1e2c", highlightthickness=1)
        outer.pack(fill=tk.BOTH, expand=True)

        # ── Header ────────────────────────────────────────────────────────
        hdr = tk.Frame(outer, bg="#0c0c0f", height=_CARD_HEADER_H)
        hdr.pack(fill=tk.X)
        hdr.pack_propagate(False)

        ava_c = tk.Canvas(hdr, width=22, height=_CARD_HEADER_H,
                          bg="#0c0c0f", highlightthickness=0)
        ava_c.pack(side=tk.LEFT, padx=(10, 0))
        cy = _CARD_HEADER_H // 2
        ava_c.create_oval(2, cy - 2, 8, cy + 2, fill="#ffffff", outline="")
        ava_c.create_oval(14, cy - 2, 20, cy + 2, fill="#ffffff", outline="")

        tk.Frame(hdr, bg="#1e1e2c", width=1).pack(
            side=tk.LEFT, fill=tk.Y, padx=8, pady=8)

        tk.Label(hdr, text="WritHer", bg="#0c0c0f", fg="#3a3a50",
                 font=("Segoe UI", 9)).pack(side=tk.LEFT)

        close_btn = tk.Label(hdr, text="✕", bg="#0c0c0f", fg="#3a3a50",
                             font=("Segoe UI", 9), cursor="hand2")
        close_btn.pack(side=tk.RIGHT, padx=10)
        close_btn.bind("<Button-1>", lambda e: self.hide())
        close_btn.bind("<Enter>", lambda e: close_btn.config(fg="#888899"))
        close_btn.bind("<Leave>", lambda e: close_btn.config(fg="#3a3a50"))

        # ── Divider ───────────────────────────────────────────────────────
        tk.Frame(outer, bg="#151520", height=1).pack(fill=tk.X)

        # ── Body (scrollable text) ────────────────────────────────────────
        body = tk.Frame(outer, bg="#0c0c0f", height=_CARD_BODY_MAX_H)
        body.pack(fill=tk.X)
        body.pack_propagate(False)

        text_w = tk.Text(
            body,
            bg="#0c0c0f", fg="#c8c8d4",
            font=("Segoe UI", 11),
            wrap=tk.WORD,
            relief=tk.FLAT,
            borderwidth=0,
            padx=14, pady=10,
            state=tk.DISABLED,
            cursor="arrow",
        )
        sb = tk.Scrollbar(body, orient=tk.VERTICAL, command=text_w.yview,
                          width=4, troughcolor="#0c0c0f", bg="#2a2a3a",
                          activebackground="#3a3a4a", relief=tk.FLAT,
                          borderwidth=0, highlightthickness=0)
        text_w.configure(yscrollcommand=sb.set)
        text_w.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        sb.pack(side=tk.RIGHT, fill=tk.Y)
        self._text_widget = text_w

        # ── Divider ───────────────────────────────────────────────────────
        tk.Frame(outer, bg="#151520", height=1).pack(fill=tk.X)

        # ── Footer ────────────────────────────────────────────────────────
        ftr = tk.Frame(outer, bg="#0c0c0f", height=_CARD_FOOTER_H)
        ftr.pack(fill=tk.X)
        ftr.pack_propagate(False)

        copy_btn = tk.Label(ftr, text="⌘ Copier", bg="#0c0c0f", fg="#3a3a50",
                            font=("Segoe UI", 9), cursor="hand2")
        copy_btn.pack(side=tk.LEFT, padx=14)
        copy_btn.bind("<Button-1>", lambda e: self._copy_to_clipboard())
        copy_btn.bind("<Enter>", lambda e: copy_btn.config(fg="#888899"))
        copy_btn.bind("<Leave>", lambda e: copy_btn.config(fg="#3a3a50"))

        self._footer_label = tk.Label(ftr, text="", bg="#0c0c0f", fg="#252535",
                                      font=("Segoe UI", 9))
        self._footer_label.pack(side=tk.RIGHT, padx=14)

        # ── Progress bar ──────────────────────────────────────────────────
        prog = tk.Canvas(outer, bg="#151520", height=_CARD_PROG_H,
                         highlightthickness=0)
        prog.pack(fill=tk.X, side=tk.BOTTOM)
        self._prog_canvas = prog
        self._prog_id = prog.create_rectangle(
            0, 0, _CARD_W, _CARD_PROG_H, fill="#2a2a3a", outline="")

        # ── Smart dismiss bindings ────────────────────────────────────────
        for w in [win, outer, hdr, body, text_w, ftr]:
            w.bind("<Enter>", self._pause_countdown)
            w.bind("<Leave>", self._on_leave)
            w.bind("<MouseWheel>", self._reset_countdown)
            w.bind("<Button-4>", self._reset_countdown)
            w.bind("<Button-5>", self._reset_countdown)

        self._win = win

    def _calc_position(self, card_h: int) -> tuple[int, int]:
        sw = self._root.winfo_screenwidth()
        sh = self._root.winfo_screenheight()
        pos = getattr(config, "OVERLAY_POSITION", "bottom-center")
        # pill top-y = sh - _H - 52  (matches RecordingWidget._build geometry)
        pill_top_y = sh - _H - 52

        if pos == "bottom-center":
            x = (sw - _CARD_W) // 2
            y = pill_top_y - _CARD_GAP - card_h
        elif pos == "bottom-right":
            x = sw - _CARD_W - _CARD_MARGIN
            y = sh - _H - _CARD_MARGIN - _CARD_GAP - card_h
        elif pos == "top-right":
            x = sw - _CARD_W - _CARD_MARGIN
            y = _CARD_MARGIN
        else:
            x = (sw - _CARD_W) // 2
            y = pill_top_y - _CARD_GAP - card_h
        return x, y

    # ── typewriter ────────────────────────────────────────────────────────────

    def _typewriter_tick(self):
        if self._token_idx >= len(self._tokens):
            self._after_type = None
            return
        chunk = self._tokens[self._token_idx]
        self._token_idx += 1
        self._text_widget.config(state=tk.NORMAL)
        self._text_widget.insert(tk.END, chunk)
        self._text_widget.config(state=tk.DISABLED)
        self._text_widget.see(tk.END)
        self._after_type = self._root.after(_TYPEWRITER_MS, self._typewriter_tick)

    # ── countdown ────────────────────────────────────────────────────────────

    def _countdown_tick(self):
        if self._paused:
            self._after_countdown = self._root.after(100, self._countdown_tick)
            return
        now = time.monotonic()
        remaining = self._countdown_dur - (now - self._countdown_start)
        if remaining <= 0:
            self._start_fade_out()
            return
        secs = max(1, int(remaining) + 1)
        if self._footer_label:
            self._footer_label.config(text=f"ferme dans {secs}s")
        if self._prog_canvas and self._prog_id is not None:
            ratio = max(0.0, remaining / self._countdown_dur)
            self._prog_canvas.coords(
                self._prog_id, 0, 0, int(_CARD_W * ratio), _CARD_PROG_H)
        self._after_countdown = self._root.after(100, self._countdown_tick)

    def _pause_countdown(self, event=None):
        self._paused = True

    def _on_leave(self, event=None):
        # Delay 50ms then check if pointer truly left the window
        self._root.after(50, self._check_resume)

    def _check_resume(self):
        if self._win is None:
            self._paused = False
            return
        try:
            mx = self._win.winfo_pointerx()
            my = self._win.winfo_pointery()
            wx = self._win.winfo_rootx()
            wy = self._win.winfo_rooty()
            ww = self._win.winfo_width()
            wh = self._win.winfo_height()
            if not (wx <= mx <= wx + ww and wy <= my <= wy + wh):
                self._paused = False
        except Exception:
            self._paused = False

    def _reset_countdown(self, event=None):
        self._countdown_start = time.monotonic()

    # ── copy ─────────────────────────────────────────────────────────────────

    def _copy_to_clipboard(self):
        try:
            import pyperclip
            pyperclip.copy(self._full_text)
        except Exception as exc:
            log.warning("AnswerCard copy failed: %s", exc)

    # ── fade ─────────────────────────────────────────────────────────────────

    def _start_fade_in(self):
        self._fading = "in"
        self._cancel_fade()
        self._fade_step()

    def _start_fade_out(self):
        self._cancel_all_timers()
        if self._win is None or self._alpha <= 0.0:
            self._do_hide()
            return
        self._fading = "out"
        self._cancel_fade()
        self._fade_step()

    def _fade_step(self):
        step = _ALPHA_MAX / _FADE_STEPS
        if self._fading == "in":
            new_a = self._alpha + step
            if new_a >= _ALPHA_MAX:
                self._alpha = _ALPHA_MAX
                try:
                    self._win.wm_attributes("-alpha", _ALPHA_MAX)
                except Exception:
                    pass
                self._fading = None
                return
            self._alpha = new_a
        elif self._fading == "out":
            new_a = self._alpha - step
            if new_a <= 0.0:
                self._alpha = 0.0
                self._fading = None
                self._do_hide()
                return
            self._alpha = new_a
        else:
            return
        try:
            self._win.wm_attributes("-alpha", self._alpha)
        except Exception:
            pass
        self._after_fade = self._root.after(_FADE_INTERVAL, self._fade_step)

    def _do_hide(self):
        if self._win:
            try:
                self._win.withdraw()
            except Exception:
                pass

    def _cancel_fade(self):
        if self._after_fade is not None:
            try:
                self._root.after_cancel(self._after_fade)
            except Exception:
                pass
            self._after_fade = None

    def _cancel_all_timers(self):
        for attr in ("_after_type", "_after_countdown"):
            after_id = getattr(self, attr, None)
            if after_id is not None:
                try:
                    self._root.after_cancel(after_id)
                except Exception:
                    pass
                setattr(self, attr, None)
```

### Wire AnswerCard into RecordingWidget

- [ ] **Step 3: Add `_answer_card` to `RecordingWidget.__init__`**

In `RecordingWidget.__init__`, after `self._pill_cache = {}`, add:

```python
        # Answer card (separate Toplevel, shown after LLM response)
        self._answer_card: AnswerCard | None = None
```

- [ ] **Step 4: Instantiate `_answer_card` in `RecordingWidget._build()`**

At the end of `RecordingWidget._build()` (after `win.after(30, ...)`), add:

```python
        if self._answer_card is None:
            self._answer_card = AnswerCard(self._root)
```

- [ ] **Step 5: Add `show_answer` and `hide_answer` to `RecordingWidget`**

In `RecordingWidget`, after the `hide()` method, add:

```python
    def show_answer(self, text: str):
        if self._answer_card is None:
            self._answer_card = AnswerCard(self._root)
        self._answer_card.show(text)

    def hide_answer(self):
        if self._answer_card is not None:
            self._answer_card.hide()
```

- [ ] **Step 6: Verify**

Run the app and trigger the assistant. After the LLM responds, you should see the answer card appear above the pill with typewriter text and countdown footer. Hover over the card — countdown should pause. Move mouse away — countdown should resume. Scroll on the card — countdown resets.

- [ ] **Step 7: Commit**

```bash
git add widget.py
git commit -m "feat: AnswerCard with typewriter, smart dismiss, configurable position"
```

---

## Task 4 — main.py: wire show_answer / hide_answer

**Files:**
- Modify: `main.py`

- [ ] **Step 1: Call `hide_answer()` when a hotkey starts recording**

In `main.py`, in `_on_hotkey_press()`, after `widget.show_recording()`, add:

```python
    if widget:
        widget.hide_answer()
```

In `_on_assist_press()`, after `widget.show_assistant()`, add:

```python
    if widget:
        widget.hide_answer()
```

- [ ] **Step 2: Replace `show_message` with `show_answer` for text LLM responses**

In `_assistant_worker()`, replace the `else` branch (currently lines ~258–260):

```python
            else:
                if widget:
                    widget.set_expression("happy")
                    widget.show_message(result, 3000)
```

with:

```python
            else:
                if widget:
                    widget.set_expression("happy")
                    widget.show_answer(result)
```

- [ ] **Step 3: Verify end-to-end**

Run the app. Trigger assistant with a voice command that produces a text response. Expected:
1. Pill shows "Assistant..." with violet eyes during recording
2. Pill shows "Thinking..." with drifting eyes during processing
3. Pill shows "Done ✓" (happy expression) and answer card appears with typewriter text
4. Pressing dictation hotkey closes the card

- [ ] **Step 4: Commit**

```bash
git add main.py
git commit -m "feat: wire show_answer/hide_answer in assistant pipeline"
```

---

## Task 5 — settings_window.py: overlay position dropdown

**Files:**
- Modify: `settings_window.py`

- [ ] **Step 1: Increase window height and add `_overlay_pos_var`**

Replace:
```python
_WIN_W, _WIN_H = 480, 520
```
with:
```python
_WIN_W, _WIN_H = 480, 600
```

In `SettingsWindow.__init__`, after `self._lang_var = None`, add:
```python
        self._overlay_pos_var = None
```

- [ ] **Step 2: Add overlay position section in `_build()`**

After the language `lang_menu.pack(...)` line and before the save button block, insert:

```python
        # Separator
        ctk.CTkFrame(pad, fg_color=T.BORDER, height=1,
                     corner_radius=0).pack(fill="x", pady=(0, T.PAD_M))

        # ── Overlay Position ──────────────────────────────────────────────
        ctk.CTkLabel(pad, text="Overlay position",
                     font=T.FONT_TITLE, text_color=T.FG,
                     anchor="w").pack(fill="x", pady=(0, T.PAD_M))

        self._overlay_pos_var = tk.StringVar(
            value=getattr(config, "OVERLAY_POSITION", "bottom-center"))
        ctk.CTkOptionMenu(
            pad,
            values=["bottom-center", "bottom-right", "top-right"],
            variable=self._overlay_pos_var,
            fg_color=T.BG_CARD, button_color=T.BG_HOVER,
            button_hover_color=T.BG_HOVER, text_color=T.FG,
            dropdown_fg_color=T.BG_CARD, dropdown_text_color=T.FG,
            dropdown_hover_color=T.BG_HOVER,
            font=T.FONT_SMALL, corner_radius=6,
            command=self._on_overlay_pos_change,
        ).pack(fill="x", pady=(0, T.PAD_L))
```

- [ ] **Step 3: Add `_on_overlay_pos_change` callback**

After `_on_lang_change`, add:

```python
    def _on_overlay_pos_change(self, value: str):
        config.OVERLAY_POSITION = value
        db.save_setting("overlay_position", value)
        log.info("Overlay position set to %s", value)
```

- [ ] **Step 4: Save position in `_save_linux_settings()`**

In `_save_linux_settings()`, after the `lang` block, add:

```python
        if self._overlay_pos_var:
            pos = self._overlay_pos_var.get()
            config.OVERLAY_POSITION = pos
            db.save_setting("overlay_position", pos)
```

- [ ] **Step 5: Verify**

Open Settings window, scroll to bottom — "Overlay position" dropdown should appear. Change to "bottom-right", save. Restart app. Answer card should appear bottom-right. Change back to "bottom-center".

- [ ] **Step 6: Commit**

```bash
git add settings_window.py
git commit -m "feat: overlay position setting (bottom-center/bottom-right/top-right)"
```

---

## Final: push

```bash
git push origin main
```
