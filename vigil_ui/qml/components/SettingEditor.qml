import QtQuick
import QtQuick.Controls

Item {
    id: root
    property var field: ({})
    property var backend: settingsModel
    Component.onCompleted: backend = settingsModel
    property int editorHeight: field.kind === "multiline" ? 88 : 34
    property string currentValue: root.backend.value(field.key || "", root.backend.revision)

    Loader {
        anchors.fill: parent
        sourceComponent: {
            if (root.field.kind === "choice" || root.field.kind === "choice_editable") return choiceEditor
            if (root.field.kind === "toggle") return toggleEditor
            if (root.field.kind === "slider") return sliderEditor
            if (root.field.kind === "multiline") return multilineEditor
            if (root.field.kind === "action") return actionEditor
            return textEditor
        }
    }

    component FoldInput: TextField {
        implicitHeight: 34
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
            contentItem: TextField {
                text: combo.editable ? combo.editText : combo.displayText
                readOnly: !combo.editable
                color: "#e1e5ed"
                font.pixelSize: 12
                verticalAlignment: Text.AlignVCenter
                background: null
            }
            background: Rectangle {
                color: "#111823"
                border.color: combo.activeFocus ? "#687386" : "#27303e"
                radius: 6
            }
        }
    }
    Component {
        id: toggleEditor
        Switch {
            checked: root.currentValue === "true"
            onToggled: root.backend.setValue(root.field.key, checked ? "true" : "false")
        }
    }
    Component {
        id: sliderEditor
        Row {
            spacing: 8
            Slider {
                id: slider
                width: parent.width - 44
                from: 0
                to: 1
                value: Number(root.currentValue)
                onMoved: root.backend.setValue(root.field.key, value.toFixed(2))
            }
            Text {
                text: Math.round(slider.value * 100) + "%"
                color: "#9ca6b7"
                verticalAlignment: Text.AlignVCenter
                height: parent.height
                font.pixelSize: 11
            }
        }
    }
    Component {
        id: multilineEditor
        TextArea {
            text: root.currentValue
            color: "#e1e5ed"
            wrapMode: TextEdit.Wrap
            font.pixelSize: 12
            onActiveFocusChanged: if (!activeFocus) root.backend.setValue(root.field.key, text)
            background: Rectangle {
                color: "#111823"
                border.color: parent.activeFocus ? "#687386" : "#27303e"
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
                color: parent.down ? "#263141" : "#192231"
                border.color: "#354357"
                radius: 6
            }
            contentItem: Text {
                text: parent.text
                color: "#d3dae5"
                font.pixelSize: 11
                horizontalAlignment: Text.AlignHCenter
                verticalAlignment: Text.AlignVCenter
            }
        }
    }
}
