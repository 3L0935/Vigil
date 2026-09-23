import QtQuick
import QtQuick.Controls

ProgressBar {
    id: control
    implicitHeight: 5
    background: Rectangle {
        color: themeModel.control
        radius: 2
    }
    contentItem: Item {
        Rectangle {
            id: fill
            height: parent.height
            width: control.indeterminate ? parent.width * 0.32 : parent.width * control.position
            radius: 2
            gradient: Gradient {
                orientation: Gradient.Horizontal
                GradientStop { position: 0; color: themeModel.accentA }
                GradientStop { position: 1; color: themeModel.gradientEnabled ? themeModel.accentB : themeModel.accentA }
            }
            SequentialAnimation on x {
                running: control.visible && control.indeterminate && !themeModel.reducedMotion
                loops: Animation.Infinite
                NumberAnimation { from: 0; to: Math.max(0, control.width - fill.width); duration: 900; easing.type: Easing.InOutSine }
                NumberAnimation { from: Math.max(0, control.width - fill.width); to: 0; duration: 900; easing.type: Easing.InOutSine }
            }
        }
    }
}
