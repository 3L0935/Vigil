import QtQuick

Rectangle {
    property bool accentEdge: false
    radius: 14
    color: themeModel.glass
    border.width: 1
    border.color: accentEdge ? themeModel.accentA : themeModel.line
    gradient: Gradient {
        GradientStop { position: 0.0; color: "#c1233549" }
        GradientStop { position: 1.0; color: themeModel.glass }
    }
}
