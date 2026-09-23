import QtQuick
import QtQuick.Shapes

Item {
    id: eye
    property color frameColor: themeModel.accentReadable
    property color irisColor: themeModel.text
    property bool reactiveRing: true
    property bool contextActive: false
    property bool engaged: false
    property bool processing: false
    implicitWidth: 34
    implicitHeight: 34

    Item {
        width: 40
        height: 40
        anchors.centerIn: parent
        scale: Math.min(eye.width, eye.height) / 40

        Rectangle {
            x: 1; y: 1; width: 38; height: 38; radius: 19
            color: themeModel.glass
            border.width: 1.5
            border.color: eye.reactiveRing && eye.contextActive
                          ? eye.irisColor : eye.frameColor
        }

        Shape {
            x: 4; y: 9; width: 32; height: 22
            ShapePath {
                strokeColor: eye.frameColor
                strokeWidth: 1.2
                fillColor: themeModel.glassTop
                startX: 0; startY: 11
                PathCubic { x: 32; y: 11; control1X: 0; control1Y: 0; control2X: 32; control2Y: 0 }
                PathCubic { x: 0; y: 11; control1X: 32; control1Y: 22; control2X: 0; control2Y: 22 }
            }
        }

        Rectangle {
            id: irisGlow
            x: 9; y: 9; width: 22; height: 22; radius: 11
            color: eye.irisColor
            opacity: 0.13
            SequentialAnimation on opacity {
                running: eye.processing && !themeModel.reducedMotion
                loops: Animation.Infinite
                NumberAnimation { from: 0.08; to: 0.3; duration: 520; easing.type: Easing.InOutSine }
                NumberAnimation { from: 0.3; to: 0.08; duration: 520; easing.type: Easing.InOutSine }
            }
        }

        Rectangle {
            id: iris
            x: 12; y: 12; width: 16; height: 16; radius: 8
            color: themeModel.background
            border.width: 2.3
            border.color: eye.irisColor
            transformOrigin: Item.Center
            SequentialAnimation on scale {
                running: !themeModel.reducedMotion && (eye.engaged || eye.processing)
                loops: Animation.Infinite
                NumberAnimation { from: 0.88; to: 1.13; duration: 650; easing.type: Easing.InOutSine }
                NumberAnimation { from: 1.13; to: 0.88; duration: 650; easing.type: Easing.InOutSine }
            }
            Rectangle {
                x: 4; y: 4; width: 8; height: 8; radius: 4
                color: eye.irisColor
            }
            Rectangle {
                x: 2.5; y: 2.5; width: 4; height: 4; radius: 2
                color: "#ffffff"
            }
        }
    }
}
