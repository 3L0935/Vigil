import QtQuick
import QtQuick.Layouts

Item {
    id: root
    property string label: ""
    property string description: ""
    default property alias editor: editorHost.data
    implicitHeight: Math.max(52, editorHost.childrenRect.height + 18)
    Layout.fillWidth: true

    RowLayout {
        anchors.fill: parent
        spacing: 18

        ColumnLayout {
            Layout.preferredWidth: 205
            Layout.fillWidth: true
            spacing: 3

            Text {
                text: root.label
                color: "#e1e5ed"
                font.pixelSize: 13
                font.weight: Font.Medium
                wrapMode: Text.WordWrap
                Layout.fillWidth: true
            }

            Text {
                visible: root.description.length > 0
                text: root.description
                color: "#788397"
                font.pixelSize: 11
                wrapMode: Text.WordWrap
                Layout.fillWidth: true
            }
        }

        Item {
            id: editorHost
            Layout.preferredWidth: 280
            Layout.fillWidth: true
            implicitHeight: 34
        }
    }
}
