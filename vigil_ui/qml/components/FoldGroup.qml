import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

Rectangle {
    id: root
    property string title: ""
    property string hint: ""
    property bool expanded: false
    property bool reducedMotion: false
    default property alias content: body.data
    signal toggled(bool expanded)

    Layout.fillWidth: true
    implicitHeight: header.height + bodyFrame.height
    color: themeModel.surface
    border.color: expanded ? themeModel.accentA : themeModel.line
    border.width: 1
    radius: 10
    clip: true
    gradient: Gradient {
        GradientStop { position: 0; color: "#ee1d2b3c" }
        GradientStop { position: 1; color: themeModel.panelGlass }
    }

    Behavior on border.color {
        ColorAnimation { duration: root.reducedMotion ? 0 : 140 }
    }

    Button {
        id: header
        objectName: "foldHeader"
        width: parent.width
        height: 50
        leftPadding: 16
        rightPadding: 14
        flat: true
        hoverEnabled: true
        Accessible.name: root.expanded
            ? i18n.textWithValue("accordion_collapse", root.title, i18n.revision)
            : i18n.textWithValue("accordion_expand", root.title, i18n.revision)
        onClicked: {
            root.expanded = !root.expanded
            root.toggled(root.expanded)
        }

        background: Rectangle {
            color: header.down ? "#1b2432" : (header.hovered ? themeModel.raised : "transparent")
            radius: 9
        }

        contentItem: RowLayout {
            spacing: 10
            Text {
                text: root.title
                color: themeModel.text
                font.pixelSize: 14
                font.weight: Font.DemiBold
                Layout.fillWidth: true
            }
            Text {
                visible: root.hint.length > 0
                text: root.hint
                color: themeModel.faint
                font.pixelSize: 11
            }
            Text {
                text: root.expanded ? "−" : "+"
                color: themeModel.text
                font.pixelSize: 19
                horizontalAlignment: Text.AlignHCenter
                Layout.preferredWidth: 18
            }
        }
    }

    Rectangle {
        id: separator
        anchors.top: header.bottom
        width: parent.width
        height: root.expanded ? 1 : 0
        color: themeModel.line
    }

    Item {
        id: bodyFrame
        anchors.top: separator.bottom
        width: parent.width
        height: root.expanded ? body.implicitHeight + 18 : 0
        opacity: root.expanded ? 1 : 0
        clip: true

        Behavior on height {
            NumberAnimation { duration: root.reducedMotion ? 0 : 150; easing.type: Easing.OutCubic }
        }
        Behavior on opacity {
            NumberAnimation { duration: root.reducedMotion ? 0 : 120 }
        }

        ColumnLayout {
            id: body
            x: 16
            y: 9
            width: parent.width - 32
            spacing: 2
        }
    }
}
