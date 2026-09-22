"""Focused Settings section for local data policy and speech preferences."""
import tkinter as tk
from tkinter import messagebox

import customtkinter as ctk

import database as db
import dictation
import locales
import privacy
import recorder
import recovery
import theme as T
from logger import configure_content_logging, purge_logs


class DictationSettings:
    def __init__(self, parent, model_var, on_model_change):
        self.parent = parent
        self.variables = {}
        self._heading('setting_privacy')
        for key, default in [('local_only', True), ('allow_web', False),
                             ('share_local_data', False), ('log_content', False)]:
            var = tk.BooleanVar(master=parent, value=privacy.enabled(key, default))
            self.variables[key] = var
            ctk.CTkCheckBox(parent, text=locales.get('setting_' + key), variable=var,
                            text_color=T.FG, font=T.FONT_SMALL).pack(
                                anchor='w', pady=(0, T.PAD_M))
        self._hint('privacy_hint')
        self._choice('recovery_days', ['0', '1', '7', '30'], '7')
        ctk.CTkButton(parent, text=locales.get('setting_purge'), command=self._purge,
                      fg_color=T.BG_CARD, hover_color=T.BG_HOVER, text_color=T.FG,
                      font=T.FONT_SMALL).pack(fill='x', pady=(0, T.PAD_L))

        self._heading('setting_dictation')
        self._choice('whisper_language', list(dictation.LANGUAGES),
                     db.get_setting('language', 'en'))
        self._choice('max_record_seconds', ['30', '60', '120', '300', '600'], '120')
        self._choice('clipboard_restore_ms', ['250', '500', '1000', '2000'], '500')
        self._label('setting_mic_device')
        self._mic_default = locales.get('mic_default')
        saved = db.get_setting('mic_device', '')
        self.variables['mic_device'] = tk.StringVar(master=parent, value=saved or self._mic_default)
        self._mic_menu = ctk.CTkOptionMenu(parent, values=[saved or self._mic_default],
                variable=self.variables['mic_device'], fg_color=T.BG_CARD,
                button_color=T.BG_HOVER, text_color=T.FG, font=T.FONT_SMALL)
        self._mic_menu.pack(fill='x', pady=(0, T.PAD_M))
        ctk.CTkButton(parent, text=locales.get('setting_refresh_mics'), command=self._refresh_mics,
                      fg_color=T.BG_CARD, hover_color=T.BG_HOVER, text_color=T.FG,
                      font=T.FONT_SMALL).pack(fill='x', pady=(0, T.PAD_M))
        self._mic_status = ctk.CTkLabel(parent, text='', text_color=T.FG,
                                       font=T.FONT_SMALL, wraplength=440)
        self._mic_status.pack(fill='x', pady=(0, T.PAD_M))
        self._refresh_mics()

        self._label('setting_vocabulary')
        self._hint('vocabulary_hint')
        self.vocab = ctk.CTkTextbox(parent, height=100, fg_color=T.BG_INPUT,
                                    text_color=T.FG, font=T.FONT_SMALL)
        self.vocab.pack(fill='x', pady=(0, T.PAD_L))
        self.vocab.insert('1.0', db.get_setting('dictation_vocabulary', ''))
        self._label('setting_priming')
        self.priming = ctk.CTkTextbox(parent, height=65, fg_color=T.BG_INPUT,
                                     text_color=T.FG, font=T.FONT_SMALL)
        self.priming.pack(fill='x', pady=(0, T.PAD_M))
        self.priming.insert('1.0', db.get_setting('whisper_priming', ''))
        self._hint('priming_hint')
        self._hint('speech_download_hint')
        ctk.CTkButton(parent, text=locales.get('setting_download_speech'),
                      command=lambda: on_model_change(model_var.get(), download=True),
                      fg_color=T.BG_CARD, hover_color=T.BG_HOVER, text_color=T.FG,
                      font=T.FONT_SMALL).pack(fill='x', pady=(0, T.PAD_L))

    def _heading(self, key):
        ctk.CTkFrame(self.parent, fg_color=T.BORDER, height=1).pack(fill='x', pady=T.PAD_M)
        ctk.CTkLabel(self.parent, text=locales.get(key), text_color=T.FG,
                     font=T.FONT_TITLE, anchor='w').pack(fill='x', pady=(0, T.PAD_M))

    def _label(self, key):
        ctk.CTkLabel(self.parent, text=locales.get(key), text_color=T.FG,
                     font=T.FONT_SMALL, anchor='w').pack(fill='x', pady=(0, T.PAD_M))

    def _hint(self, key):
        ctk.CTkLabel(self.parent, text=locales.get(key), text_color=T.FG,
                     font=T.FONT_SMALL, anchor='w', justify='left', wraplength=440).pack(
                         fill='x', pady=(0, T.PAD_M))

    def _choice(self, key, values, default):
        self._label('setting_' + key)
        saved = db.get_setting(key, default)
        if saved not in values:
            saved = default if default in values else values[0]
        var = tk.StringVar(master=self.parent, value=saved)
        self.variables[key] = var
        ctk.CTkOptionMenu(self.parent, values=values, variable=var, fg_color=T.BG_CARD,
                          button_color=T.BG_HOVER, text_color=T.FG, font=T.FONT_SMALL).pack(
                              fill='x', pady=(0, T.PAD_L))

    def _refresh_mics(self):
        try:
            values = [self._mic_default] + recorder.input_devices()
            selected = self.variables['mic_device'].get()
            if selected not in values:
                values.append(selected)
            self._mic_menu.configure(values=values)
            self._mic_status.configure(text=locales.get('mic_refresh_hint'))
        except Exception:
            self._mic_status.configure(text=locales.get('mic_unavailable'))

    def _purge(self):
        if messagebox.askyesno('Vigil', locales.get('purge_confirm'), parent=self.parent.winfo_toplevel()):
            recovery.purge()
            purge_logs()
            messagebox.showinfo('Vigil', locales.get('purge_done'), parent=self.parent.winfo_toplevel())

    def save(self) -> bool:
        vocab = self.vocab.get('1.0', 'end-1c')
        try:
            dictation.parse_vocabulary(vocab)
        except ValueError as exc:
            messagebox.showerror('Vigil', locales.get('vocabulary_invalid', line=str(exc)),
                                 parent=self.parent.winfo_toplevel())
            return False
        for key, variable in self.variables.items():
            value = variable.get()
            if isinstance(value, bool):
                value = 'true' if value else 'false'
            if key == 'mic_device' and value == self._mic_default:
                value = ''
            db.save_setting(key, value)
        db.save_setting('dictation_vocabulary', vocab)
        db.save_setting('whisper_priming', self.priming.get('1.0', 'end-1c').strip())
        configure_content_logging(privacy.enabled('log_content'))
        recovery.prune()
        return True
