import QtQuick 2.0
import Sailfish.Silica 1.0

// Round marker with a number: several caches in one place on the map
Rectangle {
    id: badge

    property int count: 0

    // bigger circle for more caches
    width: Theme.itemSizeExtraSmall * (0.9 + Math.min(0.9, Math.log(Math.max(count, 1)) / Math.LN10 * 0.4))
    height: width
    radius: width / 2
    color: Theme.rgba(Theme.highlightBackgroundColor, 0.85)
    border.width: 2
    border.color: "white"

    Label {
        anchors.centerIn: parent
        text: badge.count
        color: "white"
        font.bold: true
        font.pixelSize: Theme.fontSizeExtraSmall
    }
}
