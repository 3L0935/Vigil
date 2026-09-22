"""QML-facing translation adapter."""

from PySide6.QtCore import Property, QObject, Signal, Slot

from locales import _STRINGS, translate


class TranslationBridge(QObject):
    languageChanged = Signal()

    def __init__(self, language: str = "en", parent: QObject | None = None):
        super().__init__(parent)
        self._language = language if language in _STRINGS else "en"
        self._revision = 0

    @Property(str, notify=languageChanged)
    def language(self) -> str:
        return self._language

    @language.setter
    def language(self, value: str) -> None:
        if value not in _STRINGS or value == self._language:
            return
        self._language = value
        self._revision += 1
        self.languageChanged.emit()

    @Property(int, notify=languageChanged)
    def revision(self) -> int:
        return self._revision

    @Slot(str, int, result=str)
    def text(self, key: str, _revision: int = 0) -> str:
        return translate(key, language=self._language)

    @Slot(str, str, int, result=str)
    def textWithValue(self, key: str, value: str, _revision: int = 0) -> str:
        return translate(key, language=self._language, section=value, shortcut=value)
