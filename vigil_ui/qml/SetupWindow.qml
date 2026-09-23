import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

ApplicationWindow {
    id: wizard
    objectName: "setupWindow"
    width: 620
    height: 620
    minimumWidth: 540
    minimumHeight: 540
    visible: setupVisible
    title: i18n.text("setup_title", i18n.revision) + " — Vigil"
    color: "#080b11"
    property var backend: setupModel
    Component.onCompleted: backend = setupModel
    onClosing: function(close) { close.accepted = false; wizard.backend.cancel() }

    component WizardInput: TextField {
        property string settingKey: ""
        implicitHeight: 36
        text: wizard.backend.value(settingKey)
        color: "#e1e5ed"
        font.pixelSize: 13
        onEditingFinished: wizard.backend.setValue(settingKey, text)
        background: Rectangle { color: "#111823"; border.color: parent.activeFocus ? "#687386" : "#27303e"; radius: 6 }
    }
    component WizardChoice: ComboBox {
        id: control
        property string settingKey: ""
        property var choices: []
        implicitHeight: 36
        model: choices.map(function(option) { return option.label })
        currentIndex: {
            for (var i = 0; i < choices.length; i++) {
                if (choices[i].value === wizard.backend.value(settingKey)) return i
            }
            return 0
        }
        onActivated: wizard.backend.setValue(settingKey, choices[index].value)
        delegate: ItemDelegate {
            id: option
            width: control.width
            text: modelData
            highlighted: control.highlightedIndex === index
            contentItem: Text {
                text: option.text
                color: "#e1e5ed"
                font.pixelSize: 13
                verticalAlignment: Text.AlignVCenter
                leftPadding: 8
            }
            background: Rectangle { color: option.highlighted ? "#263141" : "#111823"; radius: 4 }
        }
        popup: Popup {
            y: control.height - 1
            width: control.width
            implicitHeight: Math.min(contentItem.implicitHeight + 8, 290)
            padding: 4
            contentItem: ListView {
                clip: true
                implicitHeight: contentHeight
                model: control.popup.visible ? control.delegateModel : null
                currentIndex: control.highlightedIndex
                ScrollIndicator.vertical: ScrollIndicator {}
            }
            background: Rectangle { color: "#111823"; border.color: "#354357"; radius: 6 }
        }
        contentItem: Text {
            text: control.displayText
            color: "#e1e5ed"
            font.pixelSize: 13
            verticalAlignment: Text.AlignVCenter
            leftPadding: 10
        }
        background: Rectangle { color: "#111823"; border.color: control.activeFocus ? "#687386" : "#27303e"; radius: 6 }
    }
    component WizardLabel: Text {
        color: "#aeb8c8"
        font.pixelSize: 13
        wrapMode: Text.WordWrap
        Layout.fillWidth: true
    }
    component WizardButton: Button {
        property bool primary: false
        implicitHeight: 36
        leftPadding: 14
        rightPadding: 14
        background: Rectangle {
            color: !parent.enabled ? "#27303e" : parent.primary
                ? (parent.down ? "#aeb5c4" : "#c6cbd8")
                : (parent.down ? "#263141" : "#192231")
            border.color: parent.primary ? "transparent" : "#354357"
            radius: 7
        }
        contentItem: Text {
            text: parent.text
            color: !parent.enabled ? "#8791a0" : parent.primary ? "#11151c" : "#e1e5ed"
            font.pixelSize: 13
            font.weight: Font.DemiBold
            horizontalAlignment: Text.AlignHCenter
            verticalAlignment: Text.AlignVCenter
        }
    }
    component WizardCheck: CheckBox {
        id: control
        implicitHeight: 30
        spacing: 9
        indicator: Rectangle {
            implicitWidth: 18
            implicitHeight: 18
            x: control.leftPadding
            y: (control.height - height) / 2
            radius: 4
            color: control.checked ? "#c6cbd8" : "#111823"
            border.color: control.checked ? "#c6cbd8" : "#596579"
            Text {
                anchors.centerIn: parent
                text: "✓"
                visible: control.checked
                color: "#11151c"
                font.pixelSize: 14
                font.weight: Font.Bold
            }
        }
        contentItem: Text {
            text: control.text
            color: control.enabled ? "#d3dae5" : "#8791a0"
            font.pixelSize: 13
            verticalAlignment: Text.AlignVCenter
            leftPadding: control.indicator.width + control.spacing
            wrapMode: Text.WordWrap
        }
    }

    header: Rectangle {
        height: 90
        color: "#0e131d"
        border.color: "#27303e"
        ColumnLayout {
            anchors.fill: parent
            anchors.margins: 22
            spacing: 3
            Text {
                text: i18n.text("setup_title", i18n.revision)
                color: "#e1e5ed"
                font.pixelSize: 22
                font.weight: Font.DemiBold
            }
            Text {
                text: i18n.text(["setup_welcome", "setup_engine", "setup_model", "setup_dictation",
                    "setup_voice", "setup_shortcuts", "setup_review", "setup_ready"][wizard.backend.page], i18n.revision)
                color: "#9ca6b7"
                font.pixelSize: 13
            }
        }
    }

    footer: Rectangle {
        height: 66
        color: "#0e131d"
        border.color: "#27303e"
        RowLayout {
            anchors.fill: parent
            anchors.margins: 18
            spacing: 10
            WizardButton { text: i18n.text("setup_cancel", i18n.revision); onClicked: wizard.backend.cancel() }
            Item { Layout.fillWidth: true }
            WizardButton {
                visible: wizard.backend.page > 0 && wizard.backend.page < 7
                enabled: !wizard.backend.busy
                text: i18n.text("setup_back", i18n.revision)
                onClicked: wizard.backend.back()
            }
            WizardButton {
                primary: true
                text: i18n.text(wizard.backend.page === 6 ? "setup_prepare"
                    : wizard.backend.page === 7 ? "setup_finish" : "setup_next", i18n.revision)
                enabled: !wizard.backend.busy
                onClicked: wizard.backend.next()
            }
        }
    }

    ScrollView {
        anchors.fill: parent
        clip: true
        ColumnLayout {
            width: wizard.width - 48
            x: 24
            y: 22
            spacing: 12

            ColumnLayout {
                visible: wizard.backend.page === 0
                Layout.fillWidth: true
                spacing: 14
                WizardLabel { text: i18n.text("setup_welcome_body", i18n.revision) }
                WizardLabel { text: i18n.text("setting_language", i18n.revision) }
                WizardChoice {
                    settingKey: "language"
                    choices: [
                        {value: "en", label: i18n.text("language_en", i18n.revision)},
                        {value: "fr", label: i18n.text("language_fr", i18n.revision)},
                        {value: "it", label: i18n.text("language_it", i18n.revision)}
                    ]
                    Layout.fillWidth: true
                }
            }

            ColumnLayout {
                visible: wizard.backend.page === 1
                Layout.fillWidth: true
                WizardLabel { text: i18n.text("setup_engine_body", i18n.revision) }
                WizardChoice {
                    settingKey: "llm_provider"
                    choices: [
                        {value: "llama_cpp", label: i18n.text("provider_llama_cpp", i18n.revision)},
                        {value: "ollama_local", label: i18n.text("provider_ollama_local", i18n.revision)},
                        {value: "ollama_cloud", label: i18n.text("provider_ollama_cloud", i18n.revision)}
                    ]
                    Layout.fillWidth: true
                }
                WizardLabel { text: i18n.text("setup_remote_notice", i18n.revision) }
                WizardCheck {
                    visible: wizard.backend.value("llm_provider") === "ollama_cloud"
                    text: i18n.text("setup_allow_cloud", i18n.revision)
                    checked: wizard.backend.value("local_only") === "false"
                    onToggled: wizard.backend.setValue("local_only", checked ? "false" : "true")
                }
            }

            ColumnLayout {
                visible: wizard.backend.page === 2
                Layout.fillWidth: true
                spacing: 9
                WizardLabel { text: i18n.text("setup_model_body", i18n.revision) }
                ColumnLayout {
                    visible: wizard.backend.value("llm_provider") === "llama_cpp"
                    Layout.fillWidth: true
                    WizardLabel { text: i18n.text("setup_backend", i18n.revision) }
                    WizardChoice {
                        settingKey: "llama_backend"
                        choices: [ {value:"cpu",label:"CPU"}, {value:"vulkan",label:"Vulkan"},
                            {value:"rocm",label:"ROCm"}, {value:"cuda",label:"CUDA"} ]
                        Layout.fillWidth: true
                    }
                    WizardLabel { text: i18n.text("setup_binary", i18n.revision) }
                    WizardCheck {
                        text: i18n.text("setup_use_existing_binary", i18n.revision)
                        checked: wizard.backend.value("use_existing_binary") === "true"
                        onToggled: wizard.backend.setValue("use_existing_binary", checked ? "true" : "false")
                    }
                    RowLayout {
                        Layout.fillWidth: true
                        enabled: wizard.backend.value("use_existing_binary") === "true"
                        WizardInput { settingKey: "llama_server_bin"; Layout.fillWidth: true }
                        WizardButton { text: i18n.text("setting_browse", i18n.revision); onClicked: wizard.backend.browseBinary() }
                    }
                    WizardLabel { text: i18n.text("setting_llm_model", i18n.revision) }
                    WizardChoice {
                        objectName: "llamaCatalogChoice"
                        settingKey: "llama_catalog_model"
                        choices: wizard.backend.models()
                        enabled: wizard.backend.value("use_existing_model") !== "true"
                        Layout.fillWidth: true
                    }
                    WizardCheck {
                        text: i18n.text("setup_use_existing_model", i18n.revision)
                        checked: wizard.backend.value("use_existing_model") === "true"
                        onToggled: wizard.backend.setValue("use_existing_model", checked ? "true" : "false")
                    }
                    RowLayout {
                        Layout.fillWidth: true
                        enabled: wizard.backend.value("use_existing_model") === "true"
                        WizardInput { settingKey: "llama_model"; Layout.fillWidth: true }
                        WizardButton { text: i18n.text("setting_browse", i18n.revision); onClicked: wizard.backend.browseModel() }
                    }
                    WizardLabel { text: i18n.text("setting_llm_gpu_layers", i18n.revision) }
                    WizardChoice {
                        settingKey: "llm_gpu_layers"
                        choices: [ {value:"off",label:"CPU"}, {value:"10",label:"10"},
                            {value:"20",label:"20"}, {value:"33",label:"33"}, {value:"99",label:"99"} ]
                        Layout.fillWidth: true
                    }
                }
                ColumnLayout {
                    visible: wizard.backend.value("llm_provider") !== "llama_cpp"
                    Layout.fillWidth: true
                    WizardLabel { text: i18n.text("setting_ollama_url", i18n.revision) }
                    WizardInput {
                        settingKey: wizard.backend.value("llm_provider") === "ollama_cloud" ? "ollama_cloud_url" : "ollama_local_url"
                        Layout.fillWidth: true
                    }
                    WizardLabel { visible: wizard.backend.value("llm_provider") === "ollama_cloud"; text: i18n.text("setting_ollama_api_key", i18n.revision) }
                    WizardInput { visible: wizard.backend.value("llm_provider") === "ollama_cloud"; settingKey: "ollama_api_key"; echoMode: TextInput.Password; Layout.fillWidth: true }
                    WizardLabel { text: i18n.text("setting_ollama_model", i18n.revision) }
                    RowLayout {
                        Layout.fillWidth: true
                        WizardChoice { settingKey: "ollama_model"; choices: wizard.backend.ollamaModels(); Layout.fillWidth: true }
                        WizardButton { text: i18n.text("setting_refresh", i18n.revision); onClicked: wizard.backend.refreshOllama() }
                    }
                    WizardInput { settingKey: "ollama_model"; Layout.fillWidth: true }
                }
            }

            ColumnLayout {
                visible: wizard.backend.page === 3
                Layout.fillWidth: true
                WizardLabel { text: i18n.text("setup_dictation_body", i18n.revision) }
                WizardLabel { text: i18n.text("setting_whisper_model", i18n.revision) }
                WizardChoice {
                    settingKey: "whisper_model"
                    choices: [ {value:"tiny",label:"tiny"}, {value:"base",label:"base"},
                        {value:"small",label:"small"}, {value:"medium",label:"medium"},
                        {value:"large-v3",label:"large-v3"} ]
                    Layout.fillWidth: true
                }
                WizardLabel { text: i18n.text("speech_download_hint", i18n.revision) }
            }

            ColumnLayout {
                visible: wizard.backend.page === 4
                Layout.fillWidth: true
                WizardLabel { text: i18n.text("setup_voice_body", i18n.revision) }
                WizardChoice {
                    settingKey: "tts_mode"
                    choices: [ {value:"overlay",label:i18n.text("choice_overlay",i18n.revision)},
                        {value:"tts",label:i18n.text("choice_tts",i18n.revision)},
                        {value:"both",label:i18n.text("choice_both",i18n.revision)} ]
                    Layout.fillWidth: true
                }
                WizardLabel { text: i18n.text("setting_tts_voice_fr", i18n.revision) }
                WizardChoice { settingKey: "tts_voice_fr"; choices: wizard.backend.voices("fr"); Layout.fillWidth: true }
                WizardLabel { text: i18n.text("setting_tts_voice_en", i18n.revision) }
                WizardChoice { settingKey: "tts_voice_en"; choices: wizard.backend.voices("en"); Layout.fillWidth: true }
            }

            ColumnLayout {
                visible: wizard.backend.page === 5
                Layout.fillWidth: true
                WizardLabel { text: i18n.text("setup_shortcuts_body", i18n.revision) }
                WizardLabel { text: i18n.text("setting_hotkey_dict_hint", i18n.revision) }
                WizardInput { settingKey: "hotkey_dict"; Layout.fillWidth: true }
                WizardLabel { text: i18n.text("setting_hotkey_asst_hint", i18n.revision) }
                WizardInput { settingKey: "hotkey_assist"; Layout.fillWidth: true }
                WizardLabel { text: i18n.text("setup_shortcuts_notice", i18n.revision) }
                WizardLabel {
                    visible: wizard.backend.manualHotkeys
                    text: i18n.text("setup_manual_hotkeys", i18n.revision)
                }
                WizardCheck {
                    visible: wizard.backend.requiresHotkeyConsent
                    text: i18n.text("setup_hotkey_consent", i18n.revision)
                    checked: wizard.backend.hotkeyConsent
                    onToggled: wizard.backend.setHotkeyConsent(checked)
                }
            }

            ColumnLayout {
                visible: wizard.backend.page === 6
                Layout.fillWidth: true
                WizardLabel { text: i18n.text("setup_review_body", i18n.revision) }
                WizardLabel { text: i18n.text("setting_llm_provider", i18n.revision) + ": " + wizard.backend.value("llm_provider") }
                WizardLabel { text: i18n.text("setting_llm_model", i18n.revision) + ": " + (wizard.backend.value("llm_provider") === "llama_cpp" ? (wizard.backend.value("use_existing_model") === "true" ? wizard.backend.value("llama_model") : wizard.backend.value("llama_catalog_model")) : wizard.backend.value("ollama_model")) }
                WizardLabel { text: i18n.text("setting_whisper_model", i18n.revision) + ": " + wizard.backend.value("whisper_model") }
                WizardLabel { text: i18n.text("setting_tts_mode", i18n.revision) + ": " + wizard.backend.value("tts_mode") }
                ProgressBar {
                    id: downloadBar
                    objectName: "setupDownloadProgress"
                    visible: wizard.backend.busy
                    indeterminate: wizard.backend.progressIndeterminate
                    value: wizard.backend.progressValue
                    Layout.fillWidth: true
                }
                WizardLabel {
                    visible: wizard.backend.busy && !wizard.backend.progressIndeterminate
                    text: Math.round(wizard.backend.progressValue * 100) + "%"
                }
            }

            ColumnLayout {
                visible: wizard.backend.page === 7
                Layout.fillWidth: true
                WizardLabel { text: i18n.text("setup_ready_body", i18n.revision) }
            }
            Text {
                text: wizard.backend.status
                color: "#d89976"
                font.pixelSize: 13
                wrapMode: Text.WordWrap
                Layout.fillWidth: true
            }
            WizardButton {
                visible: !wizard.backend.initial && wizard.backend.page === 0
                text: i18n.text("setup_reset_choices", i18n.revision)
                onClicked: wizard.backend.resetDraft()
            }
        }
    }
}
