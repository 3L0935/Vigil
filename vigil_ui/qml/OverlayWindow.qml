import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

Window {
    id: overlay
    objectName: "overlayWindow"
    width: 420
    height: overlay.backend.hasAnswer ? 248 : 54
    visible: false
    color: "transparent"
    flags: Qt.Tool | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.WindowDoesNotAcceptFocus
    title: "Vigil"
    property var backend: overlayModel
    Component.onCompleted: backend = overlayModel

    Rectangle {
        id: answerCard
        visible: overlay.backend.hasAnswer
        width: parent.width
        height: 184
        color: "#101722"
        border.color: "#354357"
        radius: 10

        ColumnLayout {
            anchors.fill: parent
            anchors.margins: 12
            spacing: 5
            RowLayout {
                Layout.fillWidth: true
                Text { text: "VIGIL"; color: "#9ca6b7"; font.pixelSize: 10; font.weight: Font.Bold; Layout.fillWidth: true }
                Button {
                    text: i18n.text("answer_copy", i18n.revision)
                    onClicked: overlay.backend.copyAnswer()
                }
                Button {
                    text: "×"
                    onClicked: overlay.backend.closeOverlay()
                }
            }
            ScrollView {
                Layout.fillWidth: true
                Layout.fillHeight: true
                TextArea {
                    text: overlay.backend.answer
                    readOnly: true
                    selectByMouse: true
                    wrapMode: TextEdit.Wrap
                    color: "#e1e5ed"
                    font.pixelSize: 13
                    background: null
                }
            }
        }
        HoverHandler { onHoveredChanged: overlay.backend.setHover(hovered) }
    }

    Rectangle {
        anchors.bottom: parent.bottom
        anchors.horizontalCenter: parent.horizontalCenter
        width: 252
        height: 50
        color: "#101722"
        border.color: overlay.backend.mode === "message" ? "#bf6666"
            : overlay.backend.mode === "recording" || overlay.backend.mode === "assistant" ? "#5a91a1" : "#354357"
        radius: 10
        RowLayout {
            anchors.fill: parent
            anchors.leftMargin: 14
            anchors.rightMargin: 12
            spacing: 10
            Text {
                text: overlay.backend.mode === "processing" ? "◐" : "◉"
                color: overlay.backend.mode === "message" ? "#d87373" : "#6aafbe"
                font.pixelSize: 19
            }
            Rectangle { width: 1; height: 20; color: "#354357" }
            Text {
                text: overlay.backend.message.length ? overlay.backend.message
                    : i18n.text(overlay.backend.mode === "recording" ? "widget_listening"
                    : overlay.backend.mode === "assistant" ? "widget_assistant"
                    : overlay.backend.mode === "processing" ? "widget_processing"
                    : "widget_done", i18n.revision)
                color: "#e1e5ed"
                font.pixelSize: 12
                elide: Text.ElideRight
                Layout.fillWidth: true
            }
            Row {
                visible: overlay.backend.mode === "recording" || overlay.backend.mode === "assistant"
                spacing: 3
                Repeater {
                    model: 5
                    Rectangle {
                        width: 3
                        height: 4 + (index % 2 === 0 ? 20 : 13) * overlay.backend.level
                        color: "#6aafbe"
                        radius: 2
                        anchors.verticalCenter: parent.verticalCenter
                    }
                }
            }
        }
    }
}
