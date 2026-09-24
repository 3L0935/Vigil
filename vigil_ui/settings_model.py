"""QML settings contract with a lightweight, in-memory visual fixture."""

from PySide6.QtCore import Property, QObject, Signal, Slot

from .settings_schema import BY_KEY, FIELDS, IMMEDIATE_KEYS
from .theme import DEFAULTS, PRESETS, matching_preset, validated_theme


class SettingsModel(QObject):
    valuesChanged = Signal()
    catalogChanged = Signal()
    statusChanged = Signal()
    downloadChanged = Signal()

    def __init__(self, translator, *, initial=None, preview=True, parent=None):
        super().__init__(parent)
        self._translator = translator
        self._values = {field.key: field.default for field in FIELDS if field.kind != "action"}
        self._values.update(initial or {})
        self._preview = preview
        self._revision = 0
        self._catalog_revision = 0
        self._status = ""
        self._download_active = False
        self._download_done = 0
        self._download_total = 0
        self._catalogs = {}

    @Property(bool, constant=True)
    def preview(self):
        return self._preview

    @Property(int, notify=valuesChanged)
    def revision(self):
        return self._revision

    @Property(int, notify=catalogChanged)
    def catalogRevision(self):
        return self._catalog_revision

    @Property(str, notify=statusChanged)
    def status(self):
        return self._status

    @Property(bool, notify=downloadChanged)
    def downloadActive(self):
        return self._download_active

    @Property(bool, notify=downloadChanged)
    def downloadDeterminate(self):
        return self._download_total > 0

    @Property(float, notify=downloadChanged)
    def downloadValue(self):
        return min(1.0, self._download_done / self._download_total) if self._download_total else 0.0

    def begin_download(self):
        self._download_active = True
        self._download_done = 0
        self._download_total = 0
        self.downloadChanged.emit()

    def update_download(self, done, total):
        self._download_done = max(0, done)
        self._download_total = max(0, total)
        self.downloadChanged.emit()

    def finish_download(self):
        self._download_active = False
        self.downloadChanged.emit()

    def set_status(self, value):
        if value != self._status:
            self._status = value
            self.statusChanged.emit()

    @Slot(str, int, result=str)
    def value(self, key, _revision=0):
        return str(self._values.get(key, ""))

    @Slot(str, int, result=str)
    def themePreviewColor(self, key, _revision=0):
        if key not in DEFAULTS or not BY_KEY.get(key) or BY_KEY[key].kind != "color":
            return DEFAULTS["theme_accent_a"]
        try:
            return validated_theme({key: self.value(key)})[key]
        except ValueError:
            return DEFAULTS[key]

    @Slot(result="QVariantList")
    def themePresets(self):
        return [{"id": name, "labelKey": "theme_preset_" + name,
                 "background": colors["theme_background"],
                 "surface": colors["theme_surface"],
                 "accent": colors["theme_accent_a"]}
                for name, colors in PRESETS.items()]

    @Slot(int, result=str)
    def themePreset(self, _revision=0):
        return matching_preset(self._values)

    @Slot(str)
    def applyThemePreset(self, name):
        if name in PRESETS:
            self._set_theme_values(PRESETS[name])

    def _set_theme_values(self, values):
        changed = False
        for key, value in values.items():
            if self._values.get(key) != value:
                self._values[key] = value
                changed = True
        if changed:
            self._revision += 1
            self.valuesChanged.emit()

    @Slot(str, str)
    def setValue(self, key, value):
        if key not in BY_KEY or BY_KEY[key].kind == "action":
            return
        value = str(value)
        previous = self._values.get(key)
        if previous == value:
            return
        self._values[key] = value
        self._revision += 1
        self.valuesChanged.emit()
        if key == "language":
            self._translator.language = value
        if key in IMMEDIATE_KEYS:
            if self.apply_immediate(key, value) is False:
                self._values[key] = previous
                self._revision += 1
                self.valuesChanged.emit()

    def apply_immediate(self, key, value):
        """Overridden by the runtime model; fixtures keep changes in memory."""

    def options_for(self, key):
        field = BY_KEY[key]
        if key in self._catalogs:
            return self._catalogs[key]
        return [{"value": value, "labelKey": _option_label(key, value)}
                for value in field.options]

    def set_catalog(self, key, values):
        self._catalogs[key] = [{"value": value, "labelKey": _option_label(key, value)}
                               for value in values]
        self._catalog_revision += 1
        self.catalogChanged.emit()

    @Slot(str, int, result="QVariantList")
    def fieldsFor(self, group, _revision=0):
        return [{
            "key": field.key,
            "labelKey": field.label,
            "kind": field.kind,
            "provider": list(field.provider),
            "options": self.options_for(field.key),
            "hintKey": field.hint,
        } for field in FIELDS if field.group == group]

    @Slot(str, int, result=bool)
    def fieldVisible(self, key, _revision=0):
        field = BY_KEY.get(key)
        if field is None:
            return False
        if field.provider and self.value("llm_provider") not in field.provider:
            return False
        if key.startswith("tts_speaker_"):
            lang = key[-2:]
            return self.speaker_count(lang) > 1
        return True

    def speaker_count(self, lang):
        return 1

    @Slot(str)
    def action(self, key):
        """Fixtures deliberately do not run downloads or system actions."""

    @Slot()
    def resetTheme(self):
        self._set_theme_values(DEFAULTS)

    @Slot()
    def invalidateRequests(self):
        """Fixtures have no asynchronous requests."""

    @Slot(result=bool)
    def save(self):
        return False


def _option_label(key, value):
    if key == "llm_profile":
        return "choice_llm_" + value
    if key == "llm_provider":
        return "provider_" + value
    if key == "language":
        return "language_" + value
    if key == "whisper_language" and value == "auto":
        return "setting_auto_language"
    if key == "mic_device" and not value:
        return "mic_default"
    if key == "overlay_screen" and value == "auto":
        return "setting_auto_screen"
    if key == "overlay_position":
        return "position_" + value.replace("middle", "center").replace("-", "_")
    if key == "tts_mode":
        return "choice_" + value
    if value == "off":
        return "choice_off"
    if value == "0" and key == "llama_unload_timeout":
        return "choice_never"
    return ""
