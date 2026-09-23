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
    color: "transparent"
    background: Rectangle {
        objectName: "settingsBackdrop"
        color: themeModel.windowBackground
        gradient: Gradient {
            GradientStop { position: 0; color: themeModel.windowTop }
            GradientStop { position: 1; color: themeModel.windowBackground }
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
        ScrollBar.vertical: ThemedScrollBar {}
        WheelHandler {
            target: null
            acceptedDevices: PointerDevice.Mouse | PointerDevice.TouchPad
            onWheel: function(event) {
                var flick = scroll.contentItem
                var delta = event.pixelDelta.y !== 0 ? event.pixelDelta.y
                    : event.angleDelta.y * 0.75
                if (event.inverted) delta = -delta
                flick.contentY = Math.max(0, Math.min(
                    flick.contentHeight - flick.height, flick.contentY - delta))
                event.accepted = true
            }
        }

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
                Text {
                    text: i18n.text("theme_presets", i18n.revision)
                    color: themeModel.muted
                    font.pixelSize: 11
                }
                GridLayout {
                    Layout.fillWidth: true
                    columns: 2
                    rowSpacing: 6
                    columnSpacing: 6
                    Repeater {
                        model: window.settingsBackend.themePresets()
                        delegate: Button {
                            id: presetButton
                            objectName: "themePreset_" + modelData.id
                            Layout.fillWidth: true
                            Layout.preferredWidth: 200
                            implicitHeight: 44
                            hoverEnabled: true
                            Accessible.name: i18n.text(modelData.labelKey, i18n.revision)
                            onClicked: window.settingsBackend.applyThemePreset(modelData.id)
                            background: Rectangle {
                                radius: 7
                                color: presetButton.hovered ? themeModel.raised : themeModel.control
                                border.width: window.settingsBackend.themePreset(window.settingsBackend.revision)
                                              === modelData.id ? 2 : 1
                                border.color: border.width === 2 ? themeModel.accentReadable : themeModel.line
                            }
                            contentItem: RowLayout {
                                spacing: 7
                                Rectangle { width: 10; height: 10; radius: 5; color: modelData.background; border.color: themeModel.line }
                                Rectangle { width: 10; height: 10; radius: 5; color: modelData.surface; border.color: themeModel.line }
                                Rectangle { width: 10; height: 10; radius: 5; color: modelData.accent; border.color: themeModel.line }
                                Text {
                                    text: i18n.text(modelData.labelKey, i18n.revision)
                                    color: themeModel.text
                                    font.pixelSize: 11
                                    Layout.fillWidth: true
                                    elide: Text.ElideRight
                                }
                            }
                        }
                    }
                }
                ColumnLayout {
                    Layout.fillWidth: true
                    spacing: 7
                    Text {
                        text: i18n.text("theme_preview", i18n.revision)
                        color: themeModel.muted
                        font.pixelSize: 11
                    }
                    Rectangle {
                        id: themeSample
                        objectName: "themePreviewCard"
                        Layout.fillWidth: true
                        height: 112
                        radius: 9
                        border.width: 1
                        border.color: window.settingsBackend.themePreviewColor("theme_line", window.settingsBackend.revision)
                        color: themeModel.raised
                        Rectangle {
                            objectName: "themePreviewBackdrop"
                            anchors.fill: parent
                            anchors.margins: 1
                            radius: 8
                            color: window.settingsBackend.themePreviewColor("theme_background", window.settingsBackend.revision)
                            opacity: Number(window.settingsBackend.value("theme_window_opacity", window.settingsBackend.revision))
                        }
                        Rectangle {
                            objectName: "themePreviewPanel"
                            anchors.fill: parent
                            anchors.margins: 12
                            radius: 8
                            color: "transparent"
                            border.color: themeSample.border.color
                            Rectangle {
                                objectName: "themePreviewGlass"
                                anchors.fill: parent
                                anchors.margins: 1
                                radius: 7
                                color: window.settingsBackend.themePreviewColor("theme_surface", window.settingsBackend.revision)
                                opacity: Number(window.settingsBackend.value("theme_glass_opacity", window.settingsBackend.revision))
                            }
                            Rectangle {
                                x: 12; y: 10; width: 34; height: 4; radius: 2
                                gradient: Gradient {
                                    orientation: Gradient.Horizontal
                                    GradientStop { position: 0; color: window.settingsBackend.themePreviewColor("theme_accent_a", window.settingsBackend.revision) }
                                    GradientStop { position: 1; color: window.settingsBackend.value("theme_gradient", window.settingsBackend.revision) === "true"
                                        ? window.settingsBackend.themePreviewColor("theme_accent_b", window.settingsBackend.revision)
                                        : window.settingsBackend.themePreviewColor("theme_accent_a", window.settingsBackend.revision) }
                                }
                            }
                            Text {
                                x: 12; y: 20
                                text: "VIGIL"
                                color: window.settingsBackend.themePreviewColor("theme_text", window.settingsBackend.revision)
                                font.pixelSize: 13
                                font.weight: Font.DemiBold
                            }
                            Text {
                                x: 12; y: 44
                                text: i18n.text("theme_preview", i18n.revision)
                                color: window.settingsBackend.themePreviewColor("theme_muted", window.settingsBackend.revision)
                                font.pixelSize: 11
                            }
                            Rectangle {
                                x: 105; y: 22; width: 75; height: 32; radius: 6
                                color: window.settingsBackend.themePreviewColor("theme_control", window.settingsBackend.revision)
                                border.color: themeSample.border.color
                                Text {
                                    anchors.centerIn: parent
                                    text: "Aa"
                                    color: window.settingsBackend.themePreviewColor("theme_muted", window.settingsBackend.revision)
                                    font.pixelSize: 12
                                }
                            }
                            Rectangle {
                                anchors.right: parent.right
                                anchors.rightMargin: 12
                                y: 22; width: 75; height: 32; radius: 6
                                gradient: Gradient {
                                    orientation: Gradient.Horizontal
                                    GradientStop { position: 0; color: window.settingsBackend.themePreviewColor("theme_accent_a", window.settingsBackend.revision) }
                                    GradientStop { position: 1; color: window.settingsBackend.value("theme_gradient", window.settingsBackend.revision) === "true"
                                        ? window.settingsBackend.themePreviewColor("theme_accent_b", window.settingsBackend.revision)
                                        : window.settingsBackend.themePreviewColor("theme_accent_a", window.settingsBackend.revision) }
                                }
                                border.color: themeSample.border.color
                                Text {
                                    anchors.centerIn: parent
                                    text: "Aa"
                                    color: window.settingsBackend.themePreviewColor("theme_background", window.settingsBackend.revision)
                                    font.pixelSize: 12
                                    font.weight: Font.DemiBold
                                }
                            }
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
