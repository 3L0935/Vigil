import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "components"

Window {
    id: overlay
    objectName: "overlayWindow"
    width: 420
    height: backend.hasAnswer ? 250 : 54
    visible: false
    color: "transparent"
    flags: Qt.Tool | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.WindowDoesNotAcceptFocus
    title: "Vigil"
    property var backend: overlayModel
    property color contextEyeColor: {
        var active = backend.mode === "recording" || backend.mode === "assistant"
        if (active) return themeModel.accentReadable
        if (backend.waiting) return "#ffd35a"
        if (backend.contextLevel > 0) {
            var turn = Math.min(1, backend.contextLevel / 3)
            return Qt.rgba(1, 1 - 0.68 * turn, 1 - 0.68 * turn, 1)
        }
        if (backend.expression === "sad") return "#ff858d"
        return themeModel.accentReadable
    }
    Component.onCompleted: backend = overlayModel
    onVisibleChanged: {
        if (visible && !themeModel.reducedMotion) pillAppear.restart()
    }

    GlassSurface {
        id: answerCard
        objectName: "answerCard"
        visible: backend.hasAnswer
        width: parent.width
        height: 188
        radius: 14
        accentEdge: false
        clip: true

        ColumnLayout {
            anchors.fill: parent
            anchors.margins: 14
            spacing: 8

            RowLayout {
                Layout.fillWidth: true
                spacing: 7
                VigilEye {
                    objectName: "answerEye"
                    width: 26; height: 26
                    reactiveRing: false
                    irisColor: overlay.contextEyeColor
                    contextActive: backend.waiting || backend.contextLevel > 0
                                   || backend.expression === "sad"
                }
                Text {
                    text: "VIGIL"
                    color: themeModel.muted
                    font.pixelSize: 11
                    font.weight: Font.DemiBold
                    font.letterSpacing: 1.4
                    Layout.fillWidth: true
                }
                GlassIconButton {
                    objectName: "answerCopyButton"
                    kind: "copy"
                    Accessible.name: i18n.text("answer_copy", i18n.revision)
                    onClicked: {
                        backend.copyAnswer()
                        copyFeedback.running = false
                        copied.visible = true
                        copyFeedback.start()
                    }
                }
                GlassIconButton {
                    objectName: "answerCloseButton"
                    kind: "close"
                    Accessible.name: i18n.text("answer_close", i18n.revision)
                    onClicked: backend.closeOverlay()
                }
            }

            ScrollView {
                Layout.fillWidth: true
                Layout.fillHeight: true
                clip: true
                TextArea {
                    text: backend.answer
                    readOnly: true
                    selectByMouse: true
                    wrapMode: TextEdit.Wrap
                    color: themeModel.text
                    selectionColor: themeModel.accentA
                    selectedTextColor: themeModel.background
                    font.pixelSize: 14
                    background: null
                }
            }

            Rectangle { Layout.fillWidth: true; height: 1; color: themeModel.line }
            RowLayout {
                Layout.fillWidth: true
                Text {
                    id: copied
                    visible: false
                    text: i18n.text("answer_copied", i18n.revision)
                    color: themeModel.accentReadable
                    font.pixelSize: 11
                }
                Item { Layout.fillWidth: true }
                Rectangle {
                    id: countdownTrack
                    objectName: "answerCountdownTrack"
                    Layout.preferredWidth: 94
                    Layout.preferredHeight: 4
                    radius: 2
                    color: themeModel.line
                    visible: backend.answerCountdownState === "counting"
                          || backend.answerCountdownState === "paused"
                    Rectangle {
                        objectName: "answerCountdownFill"
                        height: parent.height
                        width: parent.width * backend.answerProgress
                        radius: 2
                        gradient: Gradient {
                            orientation: Gradient.Horizontal
                            GradientStop { position: 0; color: themeModel.accentA }
                            GradientStop { position: 1; color: themeModel.gradientEnabled ? themeModel.accentB : themeModel.accentA }
                        }
                    }
                }
                Text {
                    objectName: "answerCountdownLabel"
                    text: {
                        var state = backend.answerCountdownState
                        if (state === "typing") return i18n.text("answer_typing", i18n.revision)
                        if (state === "waiting") return i18n.text("answer_waiting", i18n.revision)
                        if (state === "speaking") return i18n.text("answer_speaking", i18n.revision)
                        if (state === "paused") return i18n.text("answer_paused", i18n.revision)
                            + " · " + backend.answerSecondsRemaining + " s"
                        return backend.answerSecondsRemaining + " s"
                    }
                    color: backend.answerCountdownState === "counting" ? themeModel.accentReadable : themeModel.muted
                    font.pixelSize: 11
                    font.weight: Font.Medium
                }
            }
        }

        HoverHandler { onHoveredChanged: backend.setHover(hovered) }
        Timer { id: copyFeedback; interval: 1400; onTriggered: copied.visible = false }
    }

    GlassSurface {
        id: pill
        objectName: "statusPill"
        anchors.bottom: parent.bottom
        anchors.horizontalCenter: parent.horizontalCenter
        width: 252
        height: 50
        radius: 25
        accentEdge: backend.mode === "recording" || backend.mode === "assistant"
        border.color: backend.mode === "message" ? "#dd8b9b" : themeModel.accentA
        property string lastMode: ""
        Behavior on border.color { ColorAnimation { duration: themeModel.reducedMotion ? 0 : 170 } }

        Connections {
            target: backend
            function onChanged() {
                if (pill.lastMode === backend.mode) return
                pill.lastMode = backend.mode
                if (overlay.visible && !themeModel.reducedMotion
                        && (backend.mode === "answer" || backend.mode === "message"))
                    pillSettle.restart()
            }
        }

        RowLayout {
            anchors.fill: parent
            anchors.leftMargin: 15
            anchors.rightMargin: 16
            spacing: 10

            VigilEye {
                objectName: "pillEye"
                width: 34; height: 34
                irisColor: overlay.contextEyeColor
                contextActive: backend.waiting || backend.contextLevel > 0
                               || backend.expression === "sad"
                engaged: overlay.visible && (backend.mode === "recording" || backend.mode === "assistant")
                processing: overlay.visible && backend.mode === "processing"
            }

            Rectangle { width: 1; height: 20; color: themeModel.line }
            Text {
                text: backend.message.length ? backend.message
                    : i18n.text(backend.mode === "recording" ? "widget_listening"
                    : backend.mode === "assistant" ? "widget_assistant"
                    : backend.mode === "processing" ? "widget_processing"
                    : "widget_done", i18n.revision)
                color: themeModel.text
                font.pixelSize: 13
                elide: Text.ElideRight
                Layout.fillWidth: true
            }
            Row {
                visible: backend.mode === "recording" || backend.mode === "assistant"
                spacing: 3
                Repeater {
                    model: 5
                    Rectangle {
                        width: 3
                        height: 4 + (index % 2 === 0 ? 20 : 13) * backend.level
                        color: themeModel.gradientEnabled && index > 2 ? themeModel.accentB : themeModel.accentA
                        radius: 2
                        anchors.verticalCenter: parent.verticalCenter
                        Behavior on height { NumberAnimation { duration: themeModel.reducedMotion ? 0 : 90 } }
                    }
                }
            }
        }
    }

    ParallelAnimation {
        id: pillAppear
        NumberAnimation { target: pill; property: "opacity"; from: 0; to: 1; duration: 170 }
        NumberAnimation { target: pill; property: "scale"; from: 0.96; to: 1; duration: 170; easing.type: Easing.OutCubic }
    }
    NumberAnimation {
        id: pillSettle
        target: pill
        property: "scale"
        from: 1.04
        to: 1
        duration: 200
        easing.type: Easing.OutCubic
    }
}
