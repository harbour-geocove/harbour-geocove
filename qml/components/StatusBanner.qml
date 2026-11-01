import QtQuick 2.0
import Sailfish.Silica 1.0

// Small message bar at the top of a page: banner.show("text")
Rectangle {
    id: banner

    function show(text) {
        label.text = text
        opacity = 1
        hideTimer.restart()
    }

    z: 100
    anchors { left: parent.left; right: parent.right; top: parent.top }
    height: label.height + 2 * Theme.paddingMedium
    color: Theme.rgba(Theme.highlightDimmerColor, 0.95)
    opacity: 0
    visible: opacity > 0

    Behavior on opacity { FadeAnimation {} }

    Label {
        id: label
        anchors {
            left: parent.left; right: parent.right; leftMargin: Theme.horizontalPageMargin
            rightMargin: Theme.horizontalPageMargin; verticalCenter: parent.verticalCenter
        }
        wrapMode: Text.Wrap
        color: Theme.primaryColor
        font.pixelSize: Theme.fontSizeSmall
    }

    Timer {
        id: hideTimer
        interval: 5000
        onTriggered: banner.opacity = 0
    }

    MouseArea {
        anchors.fill: parent
        onClicked: banner.opacity = 0
    }
}
