import QtQuick 2.0
import Sailfish.Silica 1.0

// Compact "working…" bar at the bottom edge of a page. Unlike BusyLabel it does not sit in the
// middle of the page, so it never covers the text being read. Same API: running, text.
Rectangle {
    id: bar

    property bool running: false
    property string text
    property real bottomOffset: Theme.paddingLarge     // raise it above docked controls

    z: 100
    anchors {
        horizontalCenter: parent.horizontalCenter
        bottom: parent.bottom
        bottomMargin: bar.bottomOffset
    }
    width: Math.min(parent.width - 2 * Theme.horizontalPageMargin, content.width + 2 * Theme.paddingLarge)
    height: content.height + 2 * Theme.paddingMedium
    radius: Theme.paddingSmall
    color: Theme.rgba(Theme.overlayBackgroundColor, 0.92)
    opacity: running ? 1 : 0
    visible: opacity > 0

    Behavior on opacity { FadeAnimation {} }

    Row {
        id: content
        anchors.centerIn: parent
        spacing: Theme.paddingMedium

        BusyIndicator {
            size: BusyIndicatorSize.Small
            running: bar.running
            anchors.verticalCenter: parent.verticalCenter
        }
        Label {
            anchors.verticalCenter: parent.verticalCenter
            width: Math.min(implicitWidth, bar.parent.width - 2 * Theme.horizontalPageMargin - Theme.itemSizeExtraSmall - 2 * Theme.paddingLarge)
            text: bar.text
            truncationMode: TruncationMode.Fade
            font.pixelSize: Theme.fontSizeSmall
        }
    }
}
