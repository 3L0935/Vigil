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
    property bool previewMode: true
    property int fieldHeight: 34
    signal saveRequested()

    component FoldTextField: TextField {
        implicitHeight: window.fieldHeight
        color: "#e1e5ed"
        placeholderTextColor: "#667085"
        selectionColor: "#596579"
        selectedTextColor: "#ffffff"
        font.pixelSize: 12
        leftPadding: 11
        rightPadding: 11
        background: Rectangle {
            color: parent.activeFocus ? "#151c28" : "#111823"
            border.color: parent.activeFocus ? "#687386" : "#27303e"
            radius: 6
        }
    }

    component FoldCombo: ComboBox {
        implicitHeight: window.fieldHeight
        leftPadding: 11
        rightPadding: 28
        font.pixelSize: 12
        contentItem: Text {
            leftPadding: 0
            text: parent.displayText
            color: "#e1e5ed"
            verticalAlignment: Text.AlignVCenter
            elide: Text.ElideRight
        }
        indicator: Text {
            x: parent.width - width - 10
            height: parent.height
            text: "⌄"
            color: "#9ca6b7"
            font.pixelSize: 13
            verticalAlignment: Text.AlignVCenter
        }
        background: Rectangle {
            color: parent.activeFocus || parent.down ? "#151c28" : "#111823"
            border.color: parent.activeFocus ? "#687386" : "#27303e"
            radius: 6
        }
    }

    background: Rectangle { color: "#080b11" }

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
                id: savedLabel
                opacity: window.previewMode ? 1 : 0
                text: window.previewMode
                    ? i18n.text("ui_preview", i18n.revision)
                    : i18n.text("setting_saved_status", i18n.revision)
                color: "#9ca6b7"
                font.pixelSize: 11
                elide: Text.ElideRight
                Layout.fillWidth: true
                Behavior on opacity { NumberAnimation { duration: window.reducedMotion ? 0 : 150 } }
            }
            Button {
                id: saveButton
                objectName: "saveButton"
                text: i18n.text("setting_save", i18n.revision)
                implicitHeight: 36
                implicitWidth: Math.max(170, saveButtonText.implicitWidth + 26)
                enabled: !window.previewMode
                onClicked: {
                    window.saveRequested()
                }
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

                FieldRow {
                    label: i18n.text("setting_llm_provider", i18n.revision)
                    FoldCombo {
                        anchors.fill: parent
                        model: [
                            i18n.text("provider_llama_cpp", i18n.revision),
                            i18n.text("provider_ollama_local", i18n.revision),
                            i18n.text("provider_ollama_cloud", i18n.revision)
                        ]
                    }
                }
                FieldRow {
                    label: i18n.text("setting_whisper_model", i18n.revision)
                    FoldCombo { anchors.fill: parent; model: ["tiny", "base", "small", "medium", "large-v3"] }
                }
                FieldRow {
                    label: i18n.text("setting_llm_model", i18n.revision)
                    FoldTextField {
                        anchors.fill: parent
                        placeholderText: i18n.text("setting_model_path_hint", i18n.revision)
                    }
                }
                FieldRow {
                    label: i18n.text("setting_llm_unload", i18n.revision)
                    FoldCombo { anchors.fill: parent; model: ["1 min", "2 min", "5 min", i18n.text("choice_never", i18n.revision)] }
                }
                FieldRow {
                    label: i18n.text("setting_llm_gpu_layers", i18n.revision)
                    FoldCombo { anchors.fill: parent; model: [i18n.text("choice_off", i18n.revision), "10", "20", "33", "99"] }
                }
                FieldRow {
                    label: i18n.text("setting_llm_ctx_size", i18n.revision)
                    FoldCombo { anchors.fill: parent; model: ["2048", "4096", "8192", "16384", "32768"] }
                }
            }

            FoldGroup {
                objectName: "generalGroup"
                title: i18n.text("group_general", i18n.revision)
                reducedMotion: window.reducedMotion
                FieldRow {
                    label: i18n.text("setting_assistant_name", i18n.revision)
                    FoldTextField { anchors.fill: parent; text: "Vigil" }
                }
                FieldRow {
                    label: i18n.text("setting_language", i18n.revision)
                    FoldCombo {
                        anchors.fill: parent
                        model: ["English", "Français", "Italiano"]
                        currentIndex: i18n.language === "fr" ? 1 : (i18n.language === "it" ? 2 : 0)
                        onActivated: i18n.language = ["en", "fr", "it"][currentIndex]
                    }
                }
                FieldRow {
                    label: i18n.text("setting_obsidian_vault", i18n.revision)
                    FoldTextField { anchors.fill: parent; text: "~/Documents/Obsidian" }
                }
                FieldRow {
                    label: i18n.text("setting_hotkeys", i18n.revision)
                    FoldTextField { anchors.fill: parent; text: "Ctrl+Alt+W / Ctrl+Alt+R" }
                }
            }

            FoldGroup {
                objectName: "dictationGroup"
                title: i18n.text("setting_dictation", i18n.revision)
                reducedMotion: window.reducedMotion
                FieldRow {
                    label: i18n.text("setting_whisper_language", i18n.revision)
                    FoldCombo { anchors.fill: parent; model: ["auto", "en", "fr", "it"] }
                }
                FieldRow {
                    label: i18n.text("setting_mic_device", i18n.revision)
                    FoldCombo { anchors.fill: parent; model: [i18n.text("mic_default", i18n.revision)] }
                }
                FieldRow {
                    label: i18n.text("setting_max_record_seconds", i18n.revision)
                    FoldTextField { anchors.fill: parent; text: "120" }
                }
            }

            FoldGroup {
                objectName: "overlayGroup"
                title: i18n.text("group_overlay", i18n.revision)
                reducedMotion: window.reducedMotion
                FieldRow {
                    label: i18n.text("setting_overlay_position", i18n.revision)
                    FoldCombo {
                        anchors.fill: parent
                        model: [
                            i18n.text("position_top_left", i18n.revision),
                            i18n.text("position_top_center", i18n.revision),
                            i18n.text("position_top_right", i18n.revision),
                            i18n.text("position_center_left", i18n.revision),
                            i18n.text("position_center", i18n.revision),
                            i18n.text("position_center_right", i18n.revision),
                            i18n.text("position_bottom_left", i18n.revision),
                            i18n.text("position_bottom_center", i18n.revision),
                            i18n.text("position_bottom_right", i18n.revision)
                        ]
                        currentIndex: 7
                    }
                }
                FieldRow {
                    label: i18n.text("setting_overlay_screen", i18n.revision)
                    FoldCombo { anchors.fill: parent; model: [i18n.text("setting_auto_screen", i18n.revision)] }
                }
                FieldRow {
                    label: i18n.text("setting_answer_timeout", i18n.revision)
                    FoldCombo { anchors.fill: parent; model: ["5", "8", "10", "15", "20", "30"] }
                }
            }

            FoldGroup {
                objectName: "speechOutputGroup"
                title: i18n.text("group_speech_output", i18n.revision)
                reducedMotion: window.reducedMotion
                FieldRow {
                    label: i18n.text("setting_tts_mode", i18n.revision)
                    FoldCombo {
                        anchors.fill: parent
                        model: [
                            i18n.text("choice_off", i18n.revision),
                            i18n.text("choice_overlay", i18n.revision),
                            i18n.text("choice_tts", i18n.revision),
                            i18n.text("choice_both", i18n.revision)
                        ]
                    }
                }
                FieldRow {
                    label: i18n.text("setting_tts_voice_fr", i18n.revision)
                    FoldCombo { anchors.fill: parent; model: ["siwis-medium", "upmc-medium"] }
                }
                FieldRow {
                    label: i18n.text("setting_tts_voice_en", i18n.revision)
                    FoldCombo { anchors.fill: parent; model: ["lessac-medium", "amy-medium"] }
                }
                FieldRow {
                    label: i18n.text("setting_tts_volume", i18n.revision)
                    Slider { anchors.fill: parent; from: 0; to: 1; value: 0.8 }
                }
            }

            FoldGroup {
                objectName: "maintenanceGroup"
                title: i18n.text("group_maintenance", i18n.revision)
                reducedMotion: window.reducedMotion
                FieldRow {
                    label: i18n.text("setting_rerun_setup", i18n.revision)
                    Button { anchors.fill: parent; text: i18n.text("setting_rerun_setup", i18n.revision) }
                }
                FieldRow {
                    label: i18n.text("setting_uninstall", i18n.revision)
                    Button { anchors.fill: parent; text: i18n.text("setting_uninstall", i18n.revision) }
                }
            }

            Item { Layout.fillWidth: true; Layout.preferredHeight: 8 }
        }
    }
}
