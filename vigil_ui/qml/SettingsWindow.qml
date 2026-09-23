import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "components"

ApplicationWindow {
    id: window
    objectName: "settingsWindow"
    width: 600
    height: 640
    minimumWidth: 520
    minimumHeight: 520
    visible: startVisible
    title: i18n.text("settings_title", i18n.revision) + " — Vigil"
    color: themeModel.background
    background: Rectangle {
        gradient: Gradient {
            GradientStop { position: 0; color: "#101c2a" }
            GradientStop { position: 1; color: themeModel.background }
        }
    }
    property bool reducedMotion: themeModel.reducedMotion
    property var settingsBackend: settingsModel
    Component.onCompleted: settingsBackend = settingsModel
    property bool previewMode: window.settingsBackend.preview
    onVisibleChanged: if (!visible && window.settingsBackend) window.settingsBackend.invalidateRequests()

    component SettingsRows: Repeater {
        property string groupKey: ""
        model: window.settingsBackend.fieldsFor(groupKey, window.settingsBackend.catalogRevision)
        delegate: FieldRow {
            visible: window.settingsBackend.fieldVisible(modelData.key, window.settingsBackend.revision)
            implicitHeight: visible ? naturalHeight : 0
            editorHeight: editor.editorHeight
            label: i18n.text(modelData.labelKey, i18n.revision)
            description: modelData.hintKey ? i18n.text(modelData.hintKey, i18n.revision) : ""
            SettingEditor {
                id: editor
                anchors.fill: parent
                field: modelData
            }
        }
    }

    header: Rectangle {
        implicitHeight: 76
        color: themeModel.panelGlass
        border.color: themeModel.line
        Rectangle {
            anchors.top: parent.top
            width: parent.width
            height: 2
            gradient: Gradient {
                orientation: Gradient.Horizontal
                GradientStop { position: 0; color: themeModel.accentA }
                GradientStop { position: 1; color: themeModel.gradientEnabled ? themeModel.accentB : themeModel.accentA }
            }
        }
        ColumnLayout {
            anchors.fill: parent
            anchors.leftMargin: 23
            anchors.rightMargin: 23
            spacing: 2
            Item { Layout.fillHeight: true }
            Text {
                text: i18n.text("settings_title", i18n.revision)
                color: themeModel.text
                font.pixelSize: 22
                font.weight: Font.DemiBold
            }
            Text {
                text: i18n.text("settings_intro", i18n.revision)
                color: themeModel.muted
                font.pixelSize: 12
            }
            Item { Layout.fillHeight: true }
        }
    }

    footer: Rectangle {
        implicitHeight: 62
        color: themeModel.panelGlass
        border.color: themeModel.line
        AccentProgressBar {
            id: settingsDownloadBar
            objectName: "settingsDownloadProgress"
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.top: parent.top
            visible: window.settingsBackend.downloadActive
            indeterminate: !window.settingsBackend.downloadDeterminate
            value: window.settingsBackend.downloadValue
        }
        RowLayout {
            anchors.fill: parent
            anchors.leftMargin: 23
            anchors.rightMargin: 23
            Text {
                text: window.settingsBackend.status.length ? window.settingsBackend.status
                    : (window.previewMode ? i18n.text("ui_preview", i18n.revision) : "")
                color: themeModel.muted
                font.pixelSize: 12
                elide: Text.ElideRight
                Layout.fillWidth: true
            }
            Button {
                id: saveButton
                objectName: "saveButton"
                text: i18n.text("setting_save", i18n.revision)
                implicitHeight: 36
                implicitWidth: Math.max(170, saveButtonText.implicitWidth + 26)
                enabled: !window.previewMode
                onClicked: window.settingsBackend.save()
                background: Rectangle {
                    color: !saveButton.enabled ? themeModel.faint
                        : (saveButton.down ? themeModel.accentA : themeModel.accentReadable)
                    radius: 7
                    border.color: saveButton.activeFocus ? themeModel.text : themeModel.accentA
                }
                contentItem: Text {
                    id: saveButtonText
                    text: saveButton.text
                    color: themeModel.background
                    font.pixelSize: 12
                    font.weight: Font.DemiBold
                    horizontalAlignment: Text.AlignHCenter
                    verticalAlignment: Text.AlignVCenter
                }
            }
        }
    }

    ScrollView {
        id: scroll
        objectName: "settingsScroll"
        anchors.fill: parent
        clip: true
        contentWidth: availableWidth
        contentHeight: groups.implicitHeight + 36
        ScrollBar.horizontal.policy: ScrollBar.AlwaysOff
        ScrollBar.vertical.policy: ScrollBar.AsNeeded

        ColumnLayout {
            id: groups
            objectName: "settingsGroups"
            x: 22
            y: 18
            width: scroll.availableWidth - 44
            spacing: 10

            FoldGroup {
                objectName: "voiceModelsGroup"
                title: i18n.text("group_voice_models", i18n.revision)
                hint: "Whisper · LLM"
                expanded: true
                reducedMotion: window.reducedMotion
                SettingsRows { groupKey: "voice" }
            }
            FoldGroup {
                objectName: "generalGroup"
                title: i18n.text("group_general", i18n.revision)
                reducedMotion: window.reducedMotion
                SettingsRows { groupKey: "general" }
            }
            FoldGroup {
                objectName: "dictationGroup"
                title: i18n.text("setting_dictation", i18n.revision)
                reducedMotion: window.reducedMotion
                SettingsRows { groupKey: "dictation" }
            }
            FoldGroup {
                objectName: "privacyGroup"
                title: i18n.text("setting_privacy", i18n.revision)
                reducedMotion: window.reducedMotion
                SettingsRows { groupKey: "privacy" }
            }
            FoldGroup {
                objectName: "overlayGroup"
                title: i18n.text("group_overlay", i18n.revision)
                reducedMotion: window.reducedMotion
                SettingsRows { groupKey: "overlay" }
            }
            FoldGroup {
                objectName: "themeGroup"
                title: i18n.text("group_theme", i18n.revision)
                reducedMotion: window.reducedMotion
                ColumnLayout {
                    Layout.fillWidth: true
                    spacing: 7
                    Text {
                        text: i18n.text("theme_preview", i18n.revision)
                        color: themeModel.muted
                        font.pixelSize: 11
                    }
                    Rectangle {
                        Layout.fillWidth: true
                        height: 38
                        radius: 9
                        border.width: 1
                        border.color: themeModel.line
                        gradient: Gradient {
                            orientation: Gradient.Horizontal
                            GradientStop { position: 0; color: window.settingsBackend.themePreviewColor("theme_accent_a", window.settingsBackend.revision) }
                            GradientStop { position: 1; color: window.settingsBackend.value("theme_gradient", window.settingsBackend.revision) === "true"
                                ? window.settingsBackend.themePreviewColor("theme_accent_b", window.settingsBackend.revision)
                                : window.settingsBackend.themePreviewColor("theme_accent_a", window.settingsBackend.revision) }
                        }
                    }
                }
                SettingsRows { groupKey: "theme" }
                Button {
                    text: i18n.text("theme_reset", i18n.revision)
                    onClicked: window.settingsBackend.resetTheme()
                    background: Rectangle {
                        radius: 7
                        color: parent.hovered ? themeModel.raised : themeModel.control
                        border.color: themeModel.line
                    }
                    contentItem: Text {
                        text: parent.text
                        color: themeModel.text
                        font.pixelSize: 12
                        horizontalAlignment: Text.AlignHCenter
                        verticalAlignment: Text.AlignVCenter
                    }
                }
            }
            FoldGroup {
                objectName: "speechOutputGroup"
                title: i18n.text("group_speech_output", i18n.revision)
                reducedMotion: window.reducedMotion
                SettingsRows { groupKey: "speech" }
            }
            FoldGroup {
                objectName: "maintenanceGroup"
                title: i18n.text("group_maintenance", i18n.revision)
                reducedMotion: window.reducedMotion
                SettingsRows { groupKey: "maintenance" }
            }
            Item { Layout.fillWidth: true; Layout.preferredHeight: 8 }
        }
    }
}
