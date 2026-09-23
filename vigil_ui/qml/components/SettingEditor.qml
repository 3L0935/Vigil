import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.Dialogs

Item {
    id: root
    property var field: ({})
    property var backend: settingsModel
    Component.onCompleted: backend = settingsModel
    property int editorHeight: field.kind === "multiline" ? 108 : 34
    property string currentValue: root.backend.value(field.key || "", root.backend.revision)

    Loader {
        anchors.fill: parent
        sourceComponent: {
            if (root.field.kind === "choice" || root.field.kind === "choice_editable") return choiceEditor
            if (root.field.kind === "color") return colorEditor
            if (root.field.kind === "toggle") return toggleEditor
            if (root.field.kind === "slider") return sliderEditor
            if (root.field.kind === "multiline") return multilineEditor
            if (root.field.kind === "action") return actionEditor
            return textEditor
        }
    }

    component FoldInput: TextField {
        implicitHeight: 34
        color: themeModel.text
        placeholderTextColor: themeModel.faint
        selectionColor: themeModel.line
        selectedTextColor: themeModel.text
        font.pixelSize: 13
        leftPadding: 11
        rightPadding: 11
        background: Rectangle {
            color: parent.activeFocus ? themeModel.raised : themeModel.control
            border.color: parent.activeFocus ? themeModel.accentReadable : themeModel.line
            radius: 6
        }
    }

    Component {
        id: colorEditor
        Item {
            enabled: root.field.key !== "theme_accent_b"
                     || root.backend.value("theme_gradient", root.backend.revision) === "true"
            RowLayout {
                anchors.fill: parent
                spacing: 8
                Button {
                    id: colorButton
                    objectName: "themeColorButton"
                    implicitWidth: 34
                    implicitHeight: 34
                    Accessible.name: i18n.text(root.field.labelKey, i18n.revision)
                    onClicked: picker.open()
                    background: Rectangle {
                        radius: 6
                        color: root.backend.themePreviewColor(root.field.key, root.backend.revision)
                        border.width: 2
                        border.color: colorButton.activeFocus ? themeModel.text : themeModel.line
                    }
                }
                FoldInput {
                    id: hexEntry
                    Layout.fillWidth: true
                    text: root.currentValue
                    maximumLength: 7
                    inputMethodHints: Qt.ImhNoPredictiveText
                    onEditingFinished: root.backend.setValue(root.field.key, text)
                }
            }
            ColorDialog {
                id: picker
                title: i18n.text(root.field.labelKey, i18n.revision)
                selectedColor: root.backend.themePreviewColor(root.field.key, root.backend.revision)
                onAccepted: root.backend.setValue(root.field.key, selectedColor.toString())
            }
        }
    }
    Component {
        id: textEditor
        FoldInput {
            text: root.currentValue
            echoMode: root.field.kind === "secret" ? TextInput.Password : TextInput.Normal
            onEditingFinished: root.backend.setValue(root.field.key, text)
        }
    }
    Component {
        id: choiceEditor
        ComboBox {
            id: combo
            editable: root.field.kind === "choice_editable"
            model: root.field.options.map(function(option) {
                return option.labelKey ? i18n.text(option.labelKey, i18n.revision) : option.value
            })
            currentIndex: {
                for (var i = 0; i < root.field.options.length; i++) {
                    if (root.field.options[i].value === root.currentValue) return i
                }
                return -1
            }
            onActivated: root.backend.setValue(root.field.key, root.field.options[index].value)
            onAccepted: root.backend.setValue(root.field.key, editText)
            onEditTextChanged: if (editable && activeFocus) root.backend.setValue(root.field.key, editText)
            delegate: ItemDelegate {
                id: option
                width: combo.width
                text: modelData
                highlighted: combo.highlightedIndex === index
                contentItem: Text {
                    text: option.text
                    color: themeModel.text
                    font.pixelSize: 13
                    verticalAlignment: Text.AlignVCenter
                    leftPadding: 8
                }
                background: Rectangle { color: option.highlighted ? themeModel.raised : themeModel.control; radius: 4 }
            }
            popup: Popup {
                y: combo.height - 1
                width: combo.width
                implicitHeight: Math.min(contentItem.implicitHeight + 8, 290)
                padding: 4
                contentItem: ListView {
                    clip: true
                    implicitHeight: contentHeight
                    model: combo.popup.visible ? combo.delegateModel : null
                    currentIndex: combo.highlightedIndex
                    ScrollIndicator.vertical: ScrollIndicator {}
                }
                background: Rectangle { color: themeModel.control; border.color: themeModel.line; radius: 6 }
            }
            contentItem: TextField {
                text: combo.editable ? combo.editText : combo.displayText
                readOnly: !combo.editable
                color: themeModel.text
                font.pixelSize: 13
                verticalAlignment: Text.AlignVCenter
                background: null
            }
            background: Rectangle {
                color: themeModel.control
                border.color: combo.activeFocus ? themeModel.accentReadable : themeModel.line
                radius: 6
            }
        }
    }
    Component {
        id: toggleEditor
        Switch {
            id: toggle
            checked: root.currentValue === "true"
            onToggled: root.backend.setValue(root.field.key, checked ? "true" : "false")
            indicator: Rectangle {
                implicitWidth: 44
                implicitHeight: 24
                x: toggle.leftPadding
                y: (toggle.height - height) / 2
                radius: 12
                color: toggle.checked ? themeModel.accentA : themeModel.line
                border.color: toggle.activeFocus ? themeModel.accentReadable : "transparent"
                Behavior on color { ColorAnimation { duration: themeModel.reducedMotion ? 0 : 130 } }
                Rectangle {
                    x: toggle.checked ? parent.width - width - 3 : 3
                    y: 3
                    width: 18; height: 18; radius: 9
                    color: themeModel.text
                    Behavior on x { NumberAnimation { duration: themeModel.reducedMotion ? 0 : 130 } }
                }
            }
        }
    }
    Component {
        id: sliderEditor
        Row {
            spacing: 8
            Slider {
                id: slider
                width: parent.width - 44
                from: root.field.key === "theme_glass_opacity" ? 0.25 : 0
                to: 1
                value: Number(root.currentValue)
                onMoved: root.backend.setValue(root.field.key, value.toFixed(2))
                background: Rectangle {
                    x: slider.leftPadding
                    y: slider.topPadding + slider.availableHeight / 2 - height / 2
                    width: slider.availableWidth
                    height: 5
                    radius: 3
                    color: themeModel.line
                    Rectangle {
                        width: parent.width * slider.visualPosition
                        height: parent.height
                        radius: 3
                        color: themeModel.accentA
                    }
                }
                handle: Rectangle {
                    x: slider.leftPadding + slider.visualPosition * (slider.availableWidth - width)
                    y: slider.topPadding + slider.availableHeight / 2 - height / 2
                    width: 17; height: 17; radius: 9
                    color: themeModel.accentReadable
                    border.width: 2
                    border.color: themeModel.background
                }
            }
            Text {
                text: Math.round(slider.value * 100) + "%"
                color: themeModel.muted
                verticalAlignment: Text.AlignVCenter
                height: parent.height
                font.pixelSize: 12
            }
        }
    }
    Component {
        id: multilineEditor
        TextArea {
            text: root.currentValue
            placeholderText: root.field.key === "dictation_vocabulary"
                ? i18n.text("vocabulary_example", i18n.revision)
                : i18n.text("priming_example", i18n.revision)
            placeholderTextColor: themeModel.faint
            color: themeModel.text
            wrapMode: TextEdit.Wrap
            font.pixelSize: 13
            leftPadding: 10
            topPadding: 9
            onActiveFocusChanged: if (!activeFocus) root.backend.setValue(root.field.key, text)
            background: Rectangle {
                color: themeModel.control
                border.color: parent.activeFocus ? themeModel.accentReadable : themeModel.line
                radius: 6
            }
        }
    }
    Component {
        id: actionEditor
        Button {
            text: i18n.text(root.field.labelKey, i18n.revision)
            onClicked: root.backend.action(root.field.key)
            background: Rectangle {
                color: parent.down ? themeModel.control : themeModel.raised
                border.color: themeModel.line
                radius: 6
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
}
