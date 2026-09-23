import QtQuick
import QtQuick.Controls

Button {
    id: control
    property string kind: "copy"
    implicitWidth: 30
    implicitHeight: 30
    hoverEnabled: true
    focusPolicy: Qt.StrongFocus
    property color iconColor: hovered || activeFocus ? themeModel.accentReadable : themeModel.text

    background: Rectangle {
        radius: 9
        color: control.down ? themeModel.raised
             : control.hovered || control.activeFocus ? themeModel.glassTop : "transparent"
        border.width: 1
        border.color: control.activeFocus ? themeModel.accentReadable
                    : control.hovered ? themeModel.line : "transparent"
        Behavior on color { ColorAnimation { duration: themeModel.reducedMotion ? 0 : 140 } }
        Behavior on border.color { ColorAnimation { duration: themeModel.reducedMotion ? 0 : 140 } }
    }

    contentItem: Item {
        Rectangle {
            visible: control.kind === "copy"
            x: (parent.width - 18) / 2 + 3
            y: (parent.height - 18) / 2 + 3
            width: 10; height: 10; radius: 2
            color: "transparent"
            border.width: 1.5
            border.color: control.iconColor
        }
        Rectangle {
            visible: control.kind === "copy"
            x: (parent.width - 18) / 2 + 6
            y: (parent.height - 18) / 2 + 6
            width: 10; height: 10; radius: 2
            color: themeModel.control
            border.width: 1.5
            border.color: control.iconColor
        }
        Rectangle {
            visible: control.kind === "close"
            anchors.centerIn: parent
            width: 16; height: 2; radius: 1
            rotation: 45
            color: control.iconColor
        }
        Rectangle {
            visible: control.kind === "close"
            anchors.centerIn: parent
            width: 16; height: 2; radius: 1
            rotation: -45
            color: control.iconColor
        }
    }
}
