"""Settings window — CustomTkinter + Pandora Blackboard theme.

Allows the user to configure:
  - Whisper model selection (tiny / base / small / medium / large-v3)
  - LLM model path (.gguf file) and unload timeout
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
import tts
_WIN_W, _WIN_H = 480, 680
_TITLE_H = 40


class SettingsWindow:
    def __init__(self, root: tk.Tk, on_whisper_change=None, on_hotkey_change=None):
        self._root = root
        self._win = None
        self._drag_x = 0
        self._drag_y = 0
        self._title_eye_tk = None
        self._on_whisper_change_cb = on_whisper_change
        self._on_hotkey_change_cb = on_hotkey_change
        self._whisper_var = None
        self._llm_model_var = None
        self._llm_timeout_var = None
        self._llm_url_var = None
        self._vault_path_var = None
        self._lang_var = None
        self._overlay_pos_var = None
        self._overlay_screen_var = None
        self._tts_mode_var = None
        self._tts_voice_fr_var = None
        self._tts_voice_en_var = None
        self._tts_volume_var = None
        self._tts_voice_fr_menu = None
        self._tts_voice_en_menu = None
        self._hotkey_dict_var = None
        self._hotkey_asst_var = None
        self._answer_timeout_var = None
        self._llm_gpu_layers_var = None

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

        pad = ctk.CTkScrollableFrame(content, fg_color="transparent", corner_radius=0,
                                     scrollbar_button_color=T.BG_HOVER,
                                     scrollbar_button_hover_color=T.ACCENT)
        pad.pack(fill="both", expand=True, padx=T.PAD_XL, pady=T.PAD_L)

        # ── Whisper Model ──────────────────────────────────────────────────────
        ctk.CTkFrame(pad, fg_color=T.BORDER, height=1, corner_radius=0).pack(
            fill="x", pady=(0, T.PAD_M))
        ctk.CTkLabel(pad, text=locales.get("setting_whisper_model"),
                     font=T.FONT_TITLE, text_color=T.FG,
                     anchor="w").pack(fill="x", pady=(0, T.PAD_M))
        self._whisper_var = tk.StringVar(master=self._win, value=getattr(config, "MODEL_SIZE", "base"))
        ctk.CTkOptionMenu(
            pad,
            values=["tiny", "base", "small", "medium", "large-v3"],
            variable=self._whisper_var,
            fg_color=T.BG_CARD, button_color=T.BG_HOVER,
            button_hover_color=T.BG_HOVER, text_color=T.FG,
            dropdown_fg_color=T.BG_CARD, dropdown_text_color=T.FG,
            dropdown_hover_color=T.BG_HOVER,
            font=T.FONT_SMALL, corner_radius=6,
            command=self._on_whisper_change,
        ).pack(fill="x", pady=(0, T.PAD_L))

        # ── LLM Model ──────────────────────────────────────────────────────
        ctk.CTkFrame(pad, fg_color=T.BORDER, height=1, corner_radius=0).pack(
            fill="x", pady=(0, T.PAD_M))
        ctk.CTkLabel(pad, text=locales.get("setting_llm_model"),
                     font=T.FONT_TITLE, text_color=T.FG,
                     anchor="w").pack(fill="x", pady=(0, T.PAD_M))
        llm_row = ctk.CTkFrame(pad, fg_color="transparent")
        llm_row.pack(fill="x", pady=(0, T.PAD_L))
        self._llm_model_var = tk.StringVar(master=self._win, value=db.get_setting("llama_model", ""))
        ctk.CTkEntry(llm_row, textvariable=self._llm_model_var,
                     fg_color=T.BG_INPUT, border_color=T.BORDER,
                     text_color=T.FG, font=T.FONT_SMALL,
                     height=32, corner_radius=6).pack(
            side="left", fill="x", expand=True, padx=(0, T.PAD_M))
        ctk.CTkButton(llm_row, text=locales.get("setting_browse"), width=80, height=32,
                      fg_color=T.BG_CARD, hover_color=T.BG_HOVER,
                      border_color=T.BORDER, border_width=1,
                      text_color=T.FG, font=T.FONT_SMALL, corner_radius=6,
                      command=self._browse_model).pack(side="right")

        # ── LLM Unload Timeout ────────────────────────────────────────────
        ctk.CTkFrame(pad, fg_color=T.BORDER, height=1, corner_radius=0).pack(
            fill="x", pady=(0, T.PAD_M))
        ctk.CTkLabel(pad, text=locales.get("setting_llm_unload"),
                     font=T.FONT_TITLE, text_color=T.FG,
                     anchor="w").pack(fill="x", pady=(0, T.PAD_M))
        self._llm_timeout_var = tk.StringVar(
            master=self._win, value=db.get_setting("llama_unload_timeout", "120"))
        ctk.CTkOptionMenu(
            pad,
            values=["60", "120", "300", "0"],
            variable=self._llm_timeout_var,
            fg_color=T.BG_CARD, button_color=T.BG_HOVER,
            button_hover_color=T.BG_HOVER, text_color=T.FG,
            dropdown_fg_color=T.BG_CARD, dropdown_text_color=T.FG,
            dropdown_hover_color=T.BG_HOVER,
            font=T.FONT_SMALL, corner_radius=6,
            command=self._on_llm_timeout_change,
        ).pack(fill="x", pady=(0, T.PAD_L))

        # ── GPU Layers (ngl) ──────────────────────────────────────────
        ctk.CTkLabel(pad, text=locales.get("setting_llm_gpu_layers"),
                     font=T.FONT_TITLE, text_color=T.FG,
                     anchor="w").pack(fill="x", pady=(0, T.PAD_M))
        self._llm_gpu_layers_var = tk.StringVar(
            master=self._win, value=db.get_setting("llm_gpu_layers", "off"))
        ctk.CTkOptionMenu(
            pad,
            values=["off", "10", "20", "33", "99"],
            variable=self._llm_gpu_layers_var,
            fg_color=T.BG_CARD, button_color=T.BG_HOVER,
            button_hover_color=T.BG_HOVER, text_color=T.FG,
            dropdown_fg_color=T.BG_CARD, dropdown_text_color=T.FG,
            dropdown_hover_color=T.BG_HOVER,
            font=T.FONT_SMALL, corner_radius=6,
        ).pack(fill="x", pady=(0, T.PAD_L))

        # ── LLM Server URL ────────────────────────────────────────────
        ctk.CTkLabel(pad, text=locales.get("setting_llm_url"),
                     font=T.FONT_TITLE, text_color=T.FG,
                     anchor="w").pack(fill="x", pady=(0, T.PAD_M))

        self._llm_url_var = tk.StringVar(master=self._win, value=getattr(config, "LLAMA_SERVER_URL", ""))
        ctk.CTkEntry(pad, textvariable=self._llm_url_var,
                     fg_color=T.BG_INPUT, border_color=T.BORDER,
                     text_color=T.FG, font=T.FONT_SMALL,
                     height=32, corner_radius=6).pack(fill="x", pady=(0, T.PAD_L))

        # Separator
        ctk.CTkFrame(pad, fg_color=T.BORDER, height=1,
                     corner_radius=0).pack(fill="x", pady=(0, T.PAD_M))

        # ── Obsidian Vault Path ───────────────────────────────────────
        ctk.CTkLabel(pad, text=locales.get("setting_obsidian_vault"),
                     font=T.FONT_TITLE, text_color=T.FG,
                     anchor="w").pack(fill="x", pady=(0, T.PAD_M))

        self._vault_path_var = tk.StringVar(
            master=self._win, value=getattr(config, "OBSIDIAN_VAULT_PATH", ""))
        vault_row = ctk.CTkFrame(pad, fg_color="transparent")
        vault_row.pack(fill="x", pady=(0, T.PAD_L))

        ctk.CTkEntry(vault_row, textvariable=self._vault_path_var,
                     fg_color=T.BG_INPUT, border_color=T.BORDER,
                     text_color=T.FG, font=T.FONT_SMALL,
                     height=32, corner_radius=6).pack(side="left", fill="x",
                                                       expand=True, padx=(0, T.PAD_M))

        ctk.CTkButton(vault_row, text=locales.get("setting_browse"), width=80, height=32,
                      fg_color=T.BG_CARD, hover_color=T.BG_HOVER,
                      border_color=T.BORDER, border_width=1,
                      text_color=T.FG, font=T.FONT_SMALL,
                      corner_radius=6,
                      command=self._browse_vault).pack(side="right")

        # Separator
        ctk.CTkFrame(pad, fg_color=T.BORDER, height=1,
                     corner_radius=0).pack(fill="x", pady=(0, T.PAD_M))

        # ── Language ──────────────────────────────────────────────────
        ctk.CTkLabel(pad, text=locales.get("setting_language"),
                     font=T.FONT_TITLE, text_color=T.FG,
                     anchor="w").pack(fill="x", pady=(0, T.PAD_M))

        self._lang_var = tk.StringVar(master=self._win, value=getattr(config, "LANGUAGE", "en"))
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
        ctk.CTkLabel(pad, text=locales.get("setting_overlay_position"),
                     font=T.FONT_TITLE, text_color=T.FG,
                     anchor="w").pack(fill="x", pady=(0, T.PAD_M))

        self._overlay_pos_var = tk.StringVar(
            master=self._win, value=getattr(config, "OVERLAY_POSITION", "bottom-center"))
        ctk.CTkOptionMenu(
            pad,
            values=["bottom-center", "bottom-left", "bottom-right",
                    "middle-center", "middle-left", "middle-right",
                    "top-center", "top-left", "top-right"],
            variable=self._overlay_pos_var,
            fg_color=T.BG_CARD, button_color=T.BG_HOVER,
            button_hover_color=T.BG_HOVER, text_color=T.FG,
            dropdown_fg_color=T.BG_CARD, dropdown_text_color=T.FG,
            dropdown_hover_color=T.BG_HOVER,
            font=T.FONT_SMALL, corner_radius=6,
            command=self._on_overlay_pos_change,
        ).pack(fill="x", pady=(0, T.PAD_L))

        # ── Lock to screen ────────────────────────────────────────────
        ctk.CTkLabel(pad, text=locales.get("setting_overlay_screen"),
                     font=T.FONT_TITLE, text_color=T.FG,
                     anchor="w").pack(fill="x", pady=(0, T.PAD_M))

        try:
            from platform_linux import get_xrandr_screens
            _screen_choices = ["auto"] + get_xrandr_screens()
        except Exception:
            _screen_choices = ["auto"]

        self._overlay_screen_var = tk.StringVar(
            master=self._win, value=getattr(config, "OVERLAY_SCREEN", "auto"))
        ctk.CTkOptionMenu(
            pad,
            values=_screen_choices,
            variable=self._overlay_screen_var,
            fg_color=T.BG_CARD, button_color=T.BG_HOVER,
            button_hover_color=T.BG_HOVER, text_color=T.FG,
            dropdown_fg_color=T.BG_CARD, dropdown_text_color=T.FG,
            dropdown_hover_color=T.BG_HOVER,
            font=T.FONT_SMALL, corner_radius=6,
            command=self._on_overlay_screen_change,
        ).pack(fill="x", pady=(0, T.PAD_L))

        # ── Answer card timeout ───────────────────────────────────────────
        ctk.CTkFrame(pad, fg_color=T.BORDER, height=1,
                     corner_radius=0).pack(fill="x", pady=(0, T.PAD_M))
        ctk.CTkLabel(pad, text=locales.get("setting_answer_timeout"),
                     font=T.FONT_TITLE, text_color=T.FG,
                     anchor="w").pack(fill="x", pady=(0, T.PAD_M))
        self._answer_timeout_var = tk.StringVar(
            master=self._win,
            value=str(db.get_setting("overlay_answer_timeout", "8")))
        ctk.CTkOptionMenu(
            pad,
            values=["5", "8", "10", "15", "20", "30"],
            variable=self._answer_timeout_var,
            fg_color=T.BG_CARD, button_color=T.BG_HOVER,
            button_hover_color=T.BG_HOVER, text_color=T.FG,
            dropdown_fg_color=T.BG_CARD, dropdown_text_color=T.FG,
            dropdown_hover_color=T.BG_HOVER,
            font=T.FONT_SMALL, corner_radius=6,
        ).pack(fill="x", pady=(0, T.PAD_L))

        # Separator
        ctk.CTkFrame(pad, fg_color=T.BORDER, height=1,
                     corner_radius=0).pack(fill="x", pady=(0, T.PAD_M))

        # ── Hotkeys ──────────────────────────────────────────────────────────
        ctk.CTkLabel(pad, text=locales.get("setting_hotkeys"),
                     font=T.FONT_TITLE, text_color=T.FG,
                     anchor="w").pack(fill="x", pady=(0, T.PAD_M))

        ctk.CTkLabel(pad, text=locales.get("setting_hotkey_dict_hint"),
                     font=T.FONT_SMALL, text_color=T.FG_DIM,
                     anchor="w").pack(fill="x")
        self._hotkey_dict_var = tk.StringVar(
            master=self._win, value=getattr(config, "HOTKEY", "Ctrl+Alt+W"))
        ctk.CTkEntry(pad, textvariable=self._hotkey_dict_var,
                     fg_color=T.BG_INPUT, border_color=T.BORDER,
                     text_color=T.FG, font=T.FONT_SMALL,
                     height=32, corner_radius=6).pack(fill="x", pady=(0, T.PAD_M))

        ctk.CTkLabel(pad, text=locales.get("setting_hotkey_asst_hint"),
                     font=T.FONT_SMALL, text_color=T.FG_DIM,
                     anchor="w").pack(fill="x")
        self._hotkey_asst_var = tk.StringVar(
            master=self._win, value=getattr(config, "ASSISTANT_HOTKEY", "Ctrl+Alt+R"))
        ctk.CTkEntry(pad, textvariable=self._hotkey_asst_var,
                     fg_color=T.BG_INPUT, border_color=T.BORDER,
                     text_color=T.FG, font=T.FONT_SMALL,
                     height=32, corner_radius=6).pack(fill="x", pady=(0, T.PAD_M))

        ctk.CTkLabel(pad, text=locales.get("setting_hotkey_hint"),
                     font=T.FONT_SMALL, text_color=T.FG_DIM,
                     anchor="w").pack(fill="x", pady=(0, T.PAD_L))

        # ── TTS ───────────────────────────────────────────────────────
        ctk.CTkFrame(pad, fg_color=T.BORDER, height=1,
                     corner_radius=0).pack(fill="x", pady=(0, T.PAD_M))
        ctk.CTkLabel(pad, text="TTS", font=T.FONT_TITLE, text_color=T.FG,
                     anchor="w").pack(fill="x", pady=(0, T.PAD_M))

        ctk.CTkLabel(pad, text="Mode", font=T.FONT_SMALL,
                     text_color=T.FG_DIM, anchor="w").pack(fill="x")
        self._tts_mode_var = tk.StringVar(
            master=self._win, value=db.get_setting("tts_mode", "overlay"))
        ctk.CTkOptionMenu(
            pad,
            values=["off", "overlay", "tts", "both"],
            variable=self._tts_mode_var,
            fg_color=T.BG_CARD, button_color=T.BG_HOVER,
            button_hover_color=T.BG_HOVER, text_color=T.FG,
            dropdown_fg_color=T.BG_CARD, dropdown_text_color=T.FG,
            dropdown_hover_color=T.BG_HOVER,
            font=T.FONT_SMALL, corner_radius=6,
            command=self._on_tts_mode_change,
        ).pack(fill="x", pady=(0, T.PAD_M))

        engine_row = ctk.CTkFrame(pad, fg_color="transparent")
        engine_row.pack(fill="x", pady=(0, T.PAD_M))
        ctk.CTkLabel(engine_row, text=locales.get("setting_tts_engine"), font=T.FONT_SMALL,
                     text_color=T.FG_DIM, anchor="w").pack(side="left")
        ctk.CTkLabel(engine_row,
                     text=db.get_setting("tts_engine", "off"),
                     font=T.FONT_SMALL, text_color=T.FG,
                     anchor="e").pack(side="right")

        ctk.CTkLabel(pad, text=locales.get("setting_tts_voice_fr"), font=T.FONT_SMALL,
                     text_color=T.FG_DIM, anchor="w").pack(fill="x")
        fr_voices = [v["name"] for v in tts.list_voices("fr")] or ["(none)"]
        self._tts_voice_fr_var = tk.StringVar(
            master=self._win,
            value=db.get_setting("tts_voice_fr", fr_voices[0]))
        fr_row = ctk.CTkFrame(pad, fg_color="transparent")
        fr_row.pack(fill="x", pady=(0, T.PAD_M))
        self._tts_voice_fr_menu = ctk.CTkOptionMenu(
            fr_row,
            values=fr_voices,
            variable=self._tts_voice_fr_var,
            fg_color=T.BG_CARD, button_color=T.BG_HOVER,
            button_hover_color=T.BG_HOVER, text_color=T.FG,
            dropdown_fg_color=T.BG_CARD, dropdown_text_color=T.FG,
            dropdown_hover_color=T.BG_HOVER,
            font=T.FONT_SMALL, corner_radius=6,
            command=lambda v: (db.save_setting("tts_voice_fr", v), tts.init()),
        )
        self._tts_voice_fr_menu.pack(side="left", fill="x", expand=True, padx=(0, T.PAD_M))
        ctk.CTkButton(
            fr_row, text=locales.get("setting_more_voices"), width=110, height=32,
            fg_color=T.BG_CARD, hover_color=T.BG_HOVER,
            border_color=T.BORDER, border_width=1,
            text_color=T.FG, font=T.FONT_SMALL, corner_radius=6,
            command=lambda: self._show_more_voices("fr"),
        ).pack(side="right")

        ctk.CTkLabel(pad, text=locales.get("setting_tts_voice_en"), font=T.FONT_SMALL,
                     text_color=T.FG_DIM, anchor="w").pack(fill="x")
        en_voices = [v["name"] for v in tts.list_voices("en")] or ["(none)"]
        self._tts_voice_en_var = tk.StringVar(
            master=self._win,
            value=db.get_setting("tts_voice_en", en_voices[0]))
        en_row = ctk.CTkFrame(pad, fg_color="transparent")
        en_row.pack(fill="x", pady=(0, T.PAD_L))
        self._tts_voice_en_menu = ctk.CTkOptionMenu(
            en_row,
            values=en_voices,
            variable=self._tts_voice_en_var,
            fg_color=T.BG_CARD, button_color=T.BG_HOVER,
            button_hover_color=T.BG_HOVER, text_color=T.FG,
            dropdown_fg_color=T.BG_CARD, dropdown_text_color=T.FG,
            dropdown_hover_color=T.BG_HOVER,
            font=T.FONT_SMALL, corner_radius=6,
            command=lambda v: (db.save_setting("tts_voice_en", v), tts.init()),
        )
        self._tts_voice_en_menu.pack(side="left", fill="x", expand=True, padx=(0, T.PAD_M))
        ctk.CTkButton(
            en_row, text=locales.get("setting_more_voices"), width=110, height=32,
            fg_color=T.BG_CARD, hover_color=T.BG_HOVER,
            border_color=T.BORDER, border_width=1,
            text_color=T.FG, font=T.FONT_SMALL, corner_radius=6,
            command=lambda: self._show_more_voices("en"),
        ).pack(side="right")

        # ── Volume ───────────────────────────────────────────────────
        vol_row = ctk.CTkFrame(pad, fg_color="transparent")
        vol_row.pack(fill="x", pady=(0, T.PAD_M))
        ctk.CTkLabel(vol_row, text=locales.get("setting_tts_volume"), font=T.FONT_SMALL,
                     text_color=T.FG_DIM, anchor="w").pack(side="left")
        self._tts_volume_label = ctk.CTkLabel(vol_row, text="100%",
                                               font=T.FONT_SMALL, text_color=T.FG)
        self._tts_volume_label.pack(side="right")
        try:
            _vol_init = float(db.get_setting("tts_volume", "1.0"))
        except (ValueError, TypeError):
            _vol_init = 1.0
        self._tts_volume_var = tk.DoubleVar(master=self._win, value=_vol_init)

        def _on_volume_slide(v):
            val = round(float(v), 2)
            self._tts_volume_label.configure(text=f"{int(val * 100)}%")
            db.save_setting("tts_volume", str(val))
            tts.init()

        ctk.CTkSlider(
            pad,
            from_=0.0, to=1.0,
            variable=self._tts_volume_var,
            fg_color=T.BG_HOVER, progress_color=T.ACCENT,
            button_color=T.ACCENT, button_hover_color=T.ACCENT_HOVER,
            command=_on_volume_slide,
        ).pack(fill="x", pady=(0, T.PAD_L))

        # ── Save button ───────────────────────────────────────────────
        ctk.CTkButton(
            pad, text=locales.get("setting_saved"), height=36,
            fg_color=T.ACCENT, hover_color=T.ACCENT_HOVER,
            text_color=T.BG_DEEP, font=T.FONT_TITLE,
            corner_radius=6, command=self._save_linux_settings,
        ).pack(fill="x")

        # ── Maintenance ───────────────────────────────────────────────
        ctk.CTkFrame(pad, fg_color=T.BORDER, height=1,
                     corner_radius=0).pack(fill="x", pady=(T.PAD_L, T.PAD_M))
        ctk.CTkButton(
            pad, text=locales.get("setting_rerun_setup"), height=32,
            fg_color=T.BG_CARD, hover_color=T.BG_HOVER,
            border_color=T.BORDER, border_width=1,
            text_color=T.FG_DIM, font=T.FONT_SMALL,
            corner_radius=6, command=self._rerun_setup,
        ).pack(fill="x", pady=(0, T.PAD_M))
        ctk.CTkButton(
            pad, text=locales.get("setting_uninstall"), height=32,
            fg_color=T.BG_CARD, hover_color="#5a0000",
            border_color="#8B0000", border_width=1,
            text_color="#FF6B6B", font=T.FONT_SMALL,
            corner_radius=6, command=self._uninstall,
        ).pack(fill="x", pady=(0, T.PAD_L))

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
        if self._whisper_var:
            self._whisper_var.set(
                db.get_setting("whisper_model", getattr(config, "MODEL_SIZE", "base")))
        if self._llm_model_var:
            self._llm_model_var.set(db.get_setting("llama_model", ""))
        if self._llm_timeout_var:
            self._llm_timeout_var.set(db.get_setting("llama_unload_timeout", "120"))
        if self._llm_url_var:
            self._llm_url_var.set(getattr(config, "LLAMA_SERVER_URL", ""))
        if self._vault_path_var:
            self._vault_path_var.set(getattr(config, "OBSIDIAN_VAULT_PATH", ""))
        if self._lang_var:
            self._lang_var.set(getattr(config, "LANGUAGE", "en"))
        if self._overlay_pos_var:
            self._overlay_pos_var.set(getattr(config, "OVERLAY_POSITION", "bottom-center"))
        if self._overlay_screen_var:
            self._overlay_screen_var.set(getattr(config, "OVERLAY_SCREEN", "auto"))
        if self._tts_mode_var:
            self._tts_mode_var.set(db.get_setting("tts_mode", "overlay"))
        if self._tts_voice_fr_var:
            self._tts_voice_fr_var.set(db.get_setting("tts_voice_fr", ""))
        if self._tts_voice_en_var:
            self._tts_voice_en_var.set(db.get_setting("tts_voice_en", ""))
        if self._tts_volume_var:
            try:
                v = float(db.get_setting("tts_volume", "1.0"))
            except (ValueError, TypeError):
                v = 1.0
            self._tts_volume_var.set(v)
            self._tts_volume_label.configure(text=f"{int(v * 100)}%")
        if self._hotkey_dict_var:
            self._hotkey_dict_var.set(getattr(config, "HOTKEY", "Ctrl+Alt+W"))
        if self._hotkey_asst_var:
            self._hotkey_asst_var.set(getattr(config, "ASSISTANT_HOTKEY", "Ctrl+Alt+R"))
        if self._answer_timeout_var:
            self._answer_timeout_var.set(
                str(db.get_setting("overlay_answer_timeout", "8")))
        if self._llm_gpu_layers_var:
            self._llm_gpu_layers_var.set(db.get_setting("llm_gpu_layers", "off"))

    # ── Callbacks ─────────────────────────────────────────────────────────

    def _on_whisper_change(self, value: str):
        if self._on_whisper_change_cb:
            self._on_whisper_change_cb(value)

    def _browse_model(self):
        self._win.withdraw()
        try:
            path = fd.askopenfilename(
                parent=self._root,
                title="Select GGUF model",
                filetypes=[("GGUF files", "*.gguf"), ("All files", "*")],
            )
        finally:
            self._win.deiconify()
            self._win.attributes("-topmost", True)
            self._win.lift()
        if path and self._llm_model_var:
            self._llm_model_var.set(path)

    def _on_llm_timeout_change(self, value: str):
        db.save_setting("llama_unload_timeout", value)
        log.info("LLM unload timeout set to %ss", value)

    def _browse_vault(self):
        self._win.withdraw()
        try:
            path = fd.askdirectory(parent=self._root, title="Select Obsidian Vault")
        finally:
            self._win.deiconify()
            self._win.attributes("-topmost", True)
            self._win.lift()
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

    def _on_overlay_screen_change(self, value: str):
        config.OVERLAY_SCREEN = value
        db.save_setting("overlay_screen", value)
        log.info("Overlay screen set to %s", value)

    def _on_tts_mode_change(self, value: str):
        db.save_setting("tts_mode", value)
        config.TTS_MODE = value
        tts.init()
        log.info("TTS mode set to %s", value)

    def _show_more_voices(self, lang: str):
        import threading
        dialog = ctk.CTkToplevel(self._win)
        dialog.title(f"Voices ({lang.upper()})")
        dialog.geometry("500x420")
        dialog.attributes("-topmost", True)

        list_frame = ctk.CTkScrollableFrame(dialog, fg_color=T.BG)
        list_frame.pack(fill="both", expand=True, padx=T.PAD_L, pady=T.PAD_L)

        status_lbl = ctk.CTkLabel(dialog, text=locales.get("setting_loading"),
                                   font=T.FONT_SMALL, text_color=T.FG_DIM)
        status_lbl.pack(pady=T.PAD_M)

        def _populate(voices):
            status_lbl.configure(text=f"{len(voices)} voices available")
            for w in list_frame.winfo_children():
                w.destroy()
            for v in voices:
                row = ctk.CTkFrame(list_frame, fg_color="transparent")
                row.pack(fill="x", pady=2)
                ctk.CTkLabel(row, text=v["name"], font=T.FONT_SMALL,
                             text_color=T.FG, anchor="w").pack(
                    side="left", fill="x", expand=True)
                ctk.CTkButton(
                    row, text=locales.get("setting_download"), width=90, height=28,
                    fg_color=T.BG_CARD, hover_color=T.BG_HOVER,
                    border_color=T.BORDER, border_width=1,
                    text_color=T.FG, font=T.FONT_SMALL, corner_radius=6,
                    command=lambda voice=v: self._download_piper_voice(voice, lang, dialog),
                ).pack(side="right")

        def _fetch():
            voices = tts.fetch_voices(lang)
            dialog.after(0, lambda: _populate(voices))

        threading.Thread(target=_fetch, daemon=True).start()

    def _download_piper_voice(self, voice: dict, lang: str, dialog):
        import threading
        import urllib.request
        from pathlib import Path

        def _do():
            dest_dir = Path.home() / ".local" / "share" / "writher" / "tts" / "piper"
            dest_dir.mkdir(parents=True, exist_ok=True)
            lang_full, rest = voice["name"].split("-", 1)
            lang_short = lang_full.split("_")[0].lower()
            speaker, quality = rest.rsplit("-", 1)
            base = (
                f"https://huggingface.co/rhasspy/piper-voices/resolve/main"
                f"/{lang_short}/{lang_full}/{speaker}/{quality}/{voice['name']}"
            )
            for ext in (".onnx", ".onnx.json"):
                dest = dest_dir / f"{voice['name']}{ext}"
                if not dest.exists():
                    urllib.request.urlretrieve(base + ext, str(dest))
            db.save_setting(f"tts_voice_{lang}", voice["name"])
            tts.init()
            dialog.after(0, lambda: (
                self._refresh_voice_dropdown(lang),
                dialog.destroy(),
            ))

        threading.Thread(target=_do, daemon=True).start()

    def _refresh_voice_dropdown(self, lang: str):
        voices = [v["name"] for v in tts.list_voices(lang)] or ["(none)"]
        current = db.get_setting(f"tts_voice_{lang}", voices[0])
        if lang == "fr":
            if self._tts_voice_fr_menu:
                self._tts_voice_fr_menu.configure(values=voices)
            if self._tts_voice_fr_var:
                self._tts_voice_fr_var.set(current)
        elif lang == "en":
            if self._tts_voice_en_menu:
                self._tts_voice_en_menu.configure(values=voices)
            if self._tts_voice_en_var:
                self._tts_voice_en_var.set(current)

    def _save_linux_settings(self):
        if self._llm_url_var:
            url = self._llm_url_var.get().strip()
            if url:
                config.LLAMA_SERVER_URL = url
                db.save_setting("llama_server_url", url)
                import assistant as _assistant
                _assistant.reload_backend()
        if self._llm_model_var:
            model = self._llm_model_var.get().strip()
            if model:
                old = db.get_setting("llama_model", "")
                db.save_setting("llama_model", model)
                if model != old:
                    from llm_manager import manager as _mgr
                    _mgr.shutdown()
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
        if self._overlay_screen_var:
            screen = self._overlay_screen_var.get()
            config.OVERLAY_SCREEN = screen
            db.save_setting("overlay_screen", screen)
        hk_dict = self._hotkey_dict_var.get().strip() if self._hotkey_dict_var else ""
        hk_asst = self._hotkey_asst_var.get().strip() if self._hotkey_asst_var else ""
        if hk_dict and hk_asst and hk_dict == hk_asst:
            log.warning("Dictation and assistant hotkeys must differ — not saved.")
        else:
            if hk_dict:
                config.HOTKEY = hk_dict
                db.save_setting("hotkey_dict", hk_dict)
            if hk_asst:
                config.ASSISTANT_HOTKEY = hk_asst
                db.save_setting("hotkey_assist", hk_asst)
        if self._answer_timeout_var:
            t = self._answer_timeout_var.get().strip()
            try:
                config.OVERLAY_ANSWER_TIMEOUT = int(t)
                db.save_setting("overlay_answer_timeout", t)
            except ValueError:
                pass
        if self._llm_gpu_layers_var:
            ngl = self._llm_gpu_layers_var.get()
            old_ngl = db.get_setting("llm_gpu_layers", "off")
            db.save_setting("llm_gpu_layers", ngl)
            if ngl != old_ngl:
                from llm_manager import manager as _mgr
                _mgr.shutdown()
        if self._on_hotkey_change_cb:
            self._on_hotkey_change_cb()
        log.info("Settings saved.")

    def _rerun_setup(self):
        import setup_utils
        launched = setup_utils.launch_in_terminal(
            f'uv run python "{setup_utils.REPO_DIR / "first_run.py"}"'
        )
        if not launched:
            log.error("No terminal emulator found. Run: uv run python first_run.py")

    def _uninstall(self):
        import setup_utils
        setup_utils.launch_in_terminal(
            f'bash "{setup_utils.REPO_DIR / "uninstall.sh"}"'
        )
