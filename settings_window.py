"""Settings window — CustomTkinter + Pandora Blackboard theme.

Allows the user to configure:
  - Recording mode: hold-to-record vs toggle (press to start/stop)
  - Max recording duration in seconds (toggle mode only)
  - LLM server URL (llama-server endpoint)
  - Obsidian vault path (optional, enables vault search tool)
  - Language (en / it / fr)
"""

import tkinter as tk
import tkinter.filedialog as fd
import customtkinter as ctk
from PIL import ImageTk

from logger import log
import config
import database as db
import locales
from brand import make_title_bar_image
import theme as T

_WIN_W, _WIN_H = 480, 600
_TITLE_H = 40


class SettingsWindow:
    def __init__(self, root: tk.Tk):
        self._root = root
        self._win = None
        self._drag_x = 0
        self._drag_y = 0
        self._title_eye_tk = None
        self._hold_btn = None
        self._toggle_btn = None
        self._slider = None
        self._slider_val_label = None
        self._slider_section = None
        self._llm_url_var = None
        self._vault_path_var = None
        self._lang_var = None
        self._overlay_pos_var = None

    def show(self):
        if self._win is not None:
            try:
                if self._win.winfo_exists():
                    self._win.attributes("-topmost", True)
                    self._win.lift()
                    self._win.focus_force()
                    self._win.after(100, lambda: self._win.attributes("-topmost", True)
                                    if self._win and self._win.winfo_exists() else None)
                    self._sync_ui()
                    return
            except Exception:
                pass
        self._build()
        self._sync_ui()

    # ── Build ─────────────────────────────────────────────────────────────

    def _build(self):
        win = ctk.CTkToplevel(self._root)
        win.overrideredirect(True)
        win.configure(fg_color=T.BG_DEEP)
        win.attributes("-topmost", True)

        sx = win.winfo_screenwidth()
        sy = win.winfo_screenheight()
        x = (sx - _WIN_W) // 2
        y = (sy - _WIN_H) // 2
        win.geometry(f"{_WIN_W}x{_WIN_H}+{x}+{y}")
        self._win = win

        outer = ctk.CTkFrame(win, fg_color=T.BG_DEEP, border_color=T.BORDER,
                             border_width=1, corner_radius=0)
        outer.pack(fill="both", expand=True)

        # ── Title bar ────────────────────────────────────────────────
        title_bar = ctk.CTkFrame(outer, fg_color=T.TITLE_BG, height=_TITLE_H,
                                 corner_radius=0)
        title_bar.pack(fill="x")
        title_bar.pack_propagate(False)

        # Close button — canvas draws text immune to GTK theme overrides
        # 1px separator makes it visible without hover
        tk.Frame(title_bar, width=1, bg=T.BORDER).pack(side="right", fill="y")
        close_frame = tk.Frame(title_bar, width=48, bg=T.TITLE_BG)
        close_frame.pack(side="right", fill="y")
        close_frame.pack_propagate(False)
        close_cv = tk.Canvas(close_frame, bg=T.TITLE_BG,
                             highlightthickness=0, cursor="hand2")
        close_cv.pack(fill="both", expand=True)
        close_cv.create_text(24, 20, text="×", fill="#ffffff",
                             font=(T.FONT_FAMILY, 14, "bold"), anchor="center")
        close_cv.bind("<Button-1>", lambda e: self._close())
        close_cv.bind("<Enter>", lambda e: close_cv.configure(bg=T.CLOSE_HOVER))
        close_cv.bind("<Leave>", lambda e: close_cv.configure(bg=T.TITLE_BG))

        eye_img = make_title_bar_image(size=20)
        self._title_eye_tk = ImageTk.PhotoImage(eye_img)
        eye_lbl = tk.Label(title_bar, image=self._title_eye_tk, bg=T.TITLE_BG)
        eye_lbl.pack(side="left", padx=(14, 8))

        title_lbl = ctk.CTkLabel(title_bar, text=locales.get("settings_title"),
                                 font=T.FONT_TITLE, text_color=T.FG)
        title_lbl.pack(side="left")

        win.bind("<Escape>", lambda e: self._close())

        for w in (eye_lbl, title_lbl):
            w.bind("<Button-1>", self._start_drag)
            w.bind("<B1-Motion>", self._on_drag)

        # ── Content ──────────────────────────────────────────────────
        content = ctk.CTkFrame(outer, fg_color=T.BG, corner_radius=0)
        content.pack(fill="both", expand=True, padx=1, pady=(0, 1))

        pad = ctk.CTkFrame(content, fg_color="transparent")
        pad.pack(fill="both", expand=True, padx=T.PAD_XL, pady=T.PAD_L)

        # Recording mode label
        ctk.CTkLabel(pad, text=locales.get("setting_record_mode"),
                     font=T.FONT_TITLE, text_color=T.FG,
                     anchor="w").pack(fill="x", pady=(0, T.PAD_M))

        # Mode buttons
        btn_row = ctk.CTkFrame(pad, fg_color="transparent")
        btn_row.pack(fill="x", pady=(0, T.PAD_L))

        self._hold_btn = ctk.CTkButton(
            btn_row, text=locales.get("setting_hold"),
            font=T.FONT_SMALL, height=36, corner_radius=6,
            fg_color=T.BG_CARD, hover_color=T.BG_HOVER,
            border_color=T.BORDER, border_width=1,
            text_color=T.FG, command=lambda: self._set_mode(True),
        )
        self._hold_btn.pack(side="left", padx=(0, T.PAD_M))

        self._toggle_btn = ctk.CTkButton(
            btn_row, text=locales.get("setting_toggle"),
            font=T.FONT_SMALL, height=36, corner_radius=6,
            fg_color=T.BG_CARD, hover_color=T.BG_HOVER,
            border_color=T.BORDER, border_width=1,
            text_color=T.FG, command=lambda: self._set_mode(False),
        )
        self._toggle_btn.pack(side="left")

        # Separator
        ctk.CTkFrame(pad, fg_color=T.BORDER, height=1,
                     corner_radius=0).pack(fill="x", pady=(0, T.PAD_L))

        # Max duration section (toggle mode only)
        self._slider_section = ctk.CTkFrame(pad, fg_color="transparent")
        self._slider_section.pack(fill="x")

        lbl_row = ctk.CTkFrame(self._slider_section, fg_color="transparent")
        lbl_row.pack(fill="x", pady=(0, T.PAD_M))

        ctk.CTkLabel(lbl_row, text=locales.get("setting_max_duration"),
                     font=T.FONT_TITLE, text_color=T.FG,
                     anchor="w").pack(side="left")

        self._slider_val_label = ctk.CTkLabel(
            lbl_row, text="120s", font=T.FONT_TITLE,
            text_color=T.ACCENT, anchor="e",
        )
        self._slider_val_label.pack(side="right")

        self._slider = ctk.CTkSlider(
            self._slider_section, from_=30, to=300,
            fg_color=T.BG_INPUT, progress_color=T.ACCENT,
            button_color=T.ACCENT, button_hover_color=T.ACCENT_HOVER,
            height=18, corner_radius=9,
            command=self._on_slider_change,
        )
        self._slider.pack(fill="x")

        # Separator
        ctk.CTkFrame(pad, fg_color=T.BORDER, height=1,
                     corner_radius=0).pack(fill="x", pady=(T.PAD_L, T.PAD_M))

        # ── LLM Server URL ────────────────────────────────────────────
        ctk.CTkLabel(pad, text="LLM Server URL",
                     font=T.FONT_TITLE, text_color=T.FG,
                     anchor="w").pack(fill="x", pady=(0, T.PAD_M))

        self._llm_url_var = tk.StringVar(value=getattr(config, "LLAMA_SERVER_URL", ""))
        ctk.CTkEntry(pad, textvariable=self._llm_url_var,
                     fg_color=T.BG_INPUT, border_color=T.BORDER,
                     text_color=T.FG, font=T.FONT_SMALL,
                     height=32, corner_radius=6).pack(fill="x", pady=(0, T.PAD_L))

        # Separator
        ctk.CTkFrame(pad, fg_color=T.BORDER, height=1,
                     corner_radius=0).pack(fill="x", pady=(0, T.PAD_M))

        # ── Obsidian Vault Path ───────────────────────────────────────
        ctk.CTkLabel(pad, text="Obsidian Vault",
                     font=T.FONT_TITLE, text_color=T.FG,
                     anchor="w").pack(fill="x", pady=(0, T.PAD_M))

        self._vault_path_var = tk.StringVar(
            value=getattr(config, "OBSIDIAN_VAULT_PATH", ""))
        vault_row = ctk.CTkFrame(pad, fg_color="transparent")
        vault_row.pack(fill="x", pady=(0, T.PAD_L))

        ctk.CTkEntry(vault_row, textvariable=self._vault_path_var,
                     fg_color=T.BG_INPUT, border_color=T.BORDER,
                     text_color=T.FG, font=T.FONT_SMALL,
                     height=32, corner_radius=6).pack(side="left", fill="x",
                                                       expand=True, padx=(0, T.PAD_M))

        ctk.CTkButton(vault_row, text="Browse", width=80, height=32,
                      fg_color=T.BG_CARD, hover_color=T.BG_HOVER,
                      border_color=T.BORDER, border_width=1,
                      text_color=T.FG, font=T.FONT_SMALL,
                      corner_radius=6,
                      command=self._browse_vault).pack(side="right")

        # Separator
        ctk.CTkFrame(pad, fg_color=T.BORDER, height=1,
                     corner_radius=0).pack(fill="x", pady=(0, T.PAD_M))

        # ── Language ──────────────────────────────────────────────────
        ctk.CTkLabel(pad, text="Language",
                     font=T.FONT_TITLE, text_color=T.FG,
                     anchor="w").pack(fill="x", pady=(0, T.PAD_M))

        self._lang_var = tk.StringVar(value=getattr(config, "LANGUAGE", "en"))
        lang_menu = ctk.CTkOptionMenu(
            pad,
            values=["en", "it", "fr"],
            variable=self._lang_var,
            fg_color=T.BG_CARD, button_color=T.BG_HOVER,
            button_hover_color=T.BG_HOVER, text_color=T.FG,
            dropdown_fg_color=T.BG_CARD, dropdown_text_color=T.FG,
            dropdown_hover_color=T.BG_HOVER,
            font=T.FONT_SMALL, corner_radius=6,
            command=self._on_lang_change,
        )
        lang_menu.pack(fill="x", pady=(0, T.PAD_L))

        # Separator
        ctk.CTkFrame(pad, fg_color=T.BORDER, height=1,
                     corner_radius=0).pack(fill="x", pady=(0, T.PAD_M))

        # ── Overlay Position ──────────────────────────────────────────
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

        # ── Save button ───────────────────────────────────────────────
        ctk.CTkButton(
            pad, text=locales.get("setting_saved"), height=36,
            fg_color=T.ACCENT, hover_color=T.ACCENT_HOVER,
            text_color=T.BG_DEEP, font=T.FONT_TITLE,
            corner_radius=6, command=self._save_linux_settings,
        ).pack(fill="x")

    # ── Drag ──────────────────────────────────────────────────────────────

    def _start_drag(self, event):
        self._drag_x = event.x
        self._drag_y = event.y

    def _on_drag(self, event):
        if self._win:
            x = self._win.winfo_x() + (event.x - self._drag_x)
            y = self._win.winfo_y() + (event.y - self._drag_y)
            self._win.geometry(f"+{x}+{y}")

    def _close(self):
        win = self._win
        self._win = None
        if win:
            try:
                win.withdraw()
                win.after(1, win.destroy)
            except Exception:
                pass

    # ── UI sync ───────────────────────────────────────────────────────────

    def _sync_ui(self):
        hold = getattr(config, "HOLD_TO_RECORD", True)
        self._update_mode_buttons(hold)
        max_sec = getattr(config, "MAX_RECORD_SECONDS", 120)
        if self._slider:
            self._slider.set(max_sec)
        if self._slider_val_label:
            self._slider_val_label.configure(text=f"{max_sec}s")
        self._update_slider_visibility(hold)

    def _update_mode_buttons(self, hold: bool):
        if self._hold_btn:
            self._hold_btn.configure(
                fg_color=T.FG if hold else T.BG_CARD,
                text_color=T.BG_DEEP if hold else T.FG,
                border_color=T.FG if hold else T.BORDER,
            )
        if self._toggle_btn:
            self._toggle_btn.configure(
                fg_color=T.FG if not hold else T.BG_CARD,
                text_color=T.BG_DEEP if not hold else T.FG,
                border_color=T.FG if not hold else T.BORDER,
            )

    def _update_slider_visibility(self, hold: bool):
        if self._slider_section:
            if hold:
                self._slider_section.pack_forget()
            else:
                self._slider_section.pack(fill="x")

    # ── Callbacks ─────────────────────────────────────────────────────────

    def _set_mode(self, hold: bool):
        config.HOLD_TO_RECORD = hold
        db.save_setting("hold_to_record", "1" if hold else "0")
        self._update_mode_buttons(hold)
        self._update_slider_visibility(hold)
        log.info("Recording mode set to %s", "hold" if hold else "toggle")

    def _on_slider_change(self, value):
        seconds = int(float(value))
        config.MAX_RECORD_SECONDS = seconds
        db.save_setting("max_record_seconds", str(seconds))
        if self._slider_val_label:
            self._slider_val_label.configure(text=f"{seconds}s")

    def _browse_vault(self):
        path = fd.askdirectory(title="Select Obsidian Vault")
        if path and self._vault_path_var:
            self._vault_path_var.set(path)

    def _on_lang_change(self, value: str):
        config.LANGUAGE = value
        db.save_setting("language", value)
        log.info("Language changed to %s", value)

    def _on_overlay_pos_change(self, value: str):
        config.OVERLAY_POSITION = value
        db.save_setting("overlay_position", value)
        log.info("Overlay position set to %s", value)

    def _save_linux_settings(self):
        if self._llm_url_var:
            url = self._llm_url_var.get().strip()
            if url:
                config.LLAMA_SERVER_URL = url
                db.save_setting("llama_server_url", url)
        if self._vault_path_var:
            path = self._vault_path_var.get().strip()
            config.OBSIDIAN_VAULT_PATH = path
            db.save_setting("obsidian_vault_path", path)
        if self._lang_var:
            lang = self._lang_var.get()
            config.LANGUAGE = lang
            db.save_setting("language", lang)
        if self._overlay_pos_var:
            pos = self._overlay_pos_var.get()
            config.OVERLAY_POSITION = pos
            db.save_setting("overlay_position", pos)
        log.info("Linux settings saved.")
