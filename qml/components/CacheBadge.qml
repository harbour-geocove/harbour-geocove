import QtQuick 2.0
import Sailfish.Silica 1.0
import "Util.js" as Util

// Round marker with the cache type symbol (check mark when found)
Rectangle {
    id: badge

    property string typeId: "unknown"
    property bool found: false
    property bool disabled: false
    property real size: Theme.itemSizeExtraSmall * 0.75

    width: size
    height: size
    radius: size / 2
    color: found ? "#616161" : Util.typeColor(typeId)
    opacity: disabled ? 0.5 : 1
    border.width: 2
    border.color: "white"

    Label {
        anchors.centerIn: parent
        text: badge.found ? "✓" : Util.typeSymbol(badge.typeId)
        color: "white"
        font.bold: true
        font.pixelSize: badge.size * 0.5
    }
}
