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
    color: "#080b11"
    property bool reducedMotion: false
    property var settingsBackend: settingsModel
    Component.onCompleted: settingsBackend = settingsModel
    property bool previewMode: window.settingsBackend.preview
    onVisibleChanged: if (!visible && window.settingsBackend) window.settingsBackend.invalidateRequests()

    component SettingsRows: Repeater {
        property string groupKey: ""
        model: window.settingsBackend.fieldsFor(groupKey, window.settingsBackend.catalogRevision)
        delegate: FieldRow {
            visible: window.settingsBackend.fieldVisible(modelData.key, window.settingsBackend.revision)
            implicitHeight: visible ? Math.max(52, editor.editorHeight + 18) : 0
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
        color: "#0e131d"
        border.color: "#1f2835"
        ColumnLayout {
            anchors.fill: parent
            anchors.leftMargin: 23
            anchors.rightMargin: 23
            spacing: 2
            Item { Layout.fillHeight: true }
            Text {
                text: i18n.text("settings_title", i18n.revision)
                color: "#e1e5ed"
                font.pixelSize: 20
                font.weight: Font.DemiBold
            }
            Text {
                text: i18n.text("settings_intro", i18n.revision)
                color: "#9ca6b7"
                font.pixelSize: 11
            }
            Item { Layout.fillHeight: true }
        }
    }

    footer: Rectangle {
        implicitHeight: 62
        color: "#0e131d"
        border.color: "#1f2835"
        RowLayout {
            anchors.fill: parent
            anchors.leftMargin: 23
            anchors.rightMargin: 23
            Text {
                text: window.settingsBackend.status.length ? window.settingsBackend.status
                    : (window.previewMode ? i18n.text("ui_preview", i18n.revision) : "")
                color: "#9ca6b7"
                font.pixelSize: 11
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
                    color: !saveButton.enabled ? "#838c9d"
                        : (saveButton.down ? "#aeb5c4" : (saveButton.hovered ? "#d5d9e2" : "#c6cbd8"))
                    radius: 7
                }
                contentItem: Text {
                    id: saveButtonText
                    text: saveButton.text
                    color: "#11151c"
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
