import QtQuick
import QtQuick.Controls

ScrollBar {
    id: bar
    policy: ScrollBar.AsNeeded
    implicitWidth: 8
    background: Item {}
    contentItem: Rectangle {
        implicitWidth: 6
        radius: 3
        color: bar.pressed ? themeModel.accentReadable : themeModel.line
        opacity: bar.active ? 0.9 : 0.45
    }
}
