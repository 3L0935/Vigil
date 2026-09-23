import QtQuick
import QtQuick.Shapes

Item {
    id: eye
    property color eyeColor: themeModel.accentA
    property color irisColor: themeModel.text
    property bool showRing: true
    property bool engaged: false
    property bool processing: false
    property bool reducedMotion: themeModel.reducedMotion
    implicitWidth: 32
    implicitHeight: 32

    Item {
        width: 40
        height: 40
        anchors.centerIn: parent
        scale: Math.min(eye.width, eye.height) / 40

        Rectangle {
            x: 1; y: 1; width: 38; height: 38; radius: 19
            visible: eye.showRing
            color: "#25111e2d"
            border.width: 1.5
            border.color: eye.eyeColor
            opacity: 0.8
        }

        Shape {
            x: 5; y: 5; width: 30; height: 30
            ShapePath {
                strokeColor: eye.eyeColor
                strokeWidth: 1.7
                fillColor: "#35111e2d"
                startX: 0; startY: 15
                PathQuad { x: 30; y: 15; controlX: 15; controlY: 3 }
                PathQuad { x: 0; y: 15; controlX: 15; controlY: 27 }
            }
        }

        Rectangle {
            id: iris
            x: 12; y: 12; width: 16; height: 16; radius: 8
            color: "#102030"
            border.width: 2.5
            border.color: eye.irisColor
            transformOrigin: Item.Center
            SequentialAnimation on scale {
                running: !eye.reducedMotion && (eye.engaged || eye.processing)
                loops: Animation.Infinite
                NumberAnimation { from: 0.88; to: 1.1; duration: 630; easing.type: Easing.InOutSine }
                NumberAnimation { from: 1.1; to: 0.88; duration: 630; easing.type: Easing.InOutSine }
            }
            Rectangle {
                x: 4; y: 4; width: 8; height: 8; radius: 4
                color: eye.irisColor
            }
            Rectangle {
                x: 3; y: 2; width: 4; height: 4; radius: 2
                color: "#ffffff"
            }
        }

        Item {
            id: orbit
            anchors.fill: parent
            visible: eye.processing
            Rectangle {
                x: 18; y: 0; width: 4; height: 4; radius: 2
                color: themeModel.gradientEnabled ? themeModel.accentB : eye.eyeColor
            }
            RotationAnimator on rotation {
                from: 0; to: 360; duration: 1600
                loops: Animation.Infinite
                running: eye.processing && !eye.reducedMotion
            }
        }
    }
}
