import QtQuick
import QtQuick.Layouts

Item {
    id: root
    property string label: ""
    property string description: ""
    property int editorHeight: 34
    property real naturalHeight: Math.max(52, editorHeight + 18, labels.implicitHeight + 18)
    default property alias editor: editorHost.data
    implicitHeight: naturalHeight
    Layout.fillWidth: true

    RowLayout {
        anchors.fill: parent
        spacing: 18

        ColumnLayout {
            id: labels
            Layout.preferredWidth: 205
            Layout.fillWidth: true
            spacing: 3

            Text {
                text: root.label
                color: themeModel.text
                font.pixelSize: 14
                font.weight: Font.Medium
                wrapMode: Text.WordWrap
                Layout.fillWidth: true
            }

            Text {
                visible: root.description.length > 0
                text: root.description
                color: themeModel.muted
                font.pixelSize: 12
                wrapMode: Text.WordWrap
                Layout.fillWidth: true
            }
        }

        Item {
            id: editorHost
            Layout.preferredWidth: 280
            Layout.fillWidth: true
            implicitHeight: root.editorHeight
        }
    }
}
