import QtQuick 2.2
import Sailfish.Silica 1.0
import QtPositioning 5.2
import QtSensors 5.0
import "../components"
import "../components/Util.js" as Util

Page {
    id: page
    allowedOrientations: Orientation.Portrait

    property string title
    property real targetLat
    property real targetLon
    property real heading: 0

    readonly property var me: pos.position.coordinate
    readonly property var target: QtPositioning.coordinate(targetLat, targetLon)
    readonly property bool hasFix: me.isValid
    readonly property real bearing: hasFix ? me.azimuthTo(target) : 0
    readonly property real distance: hasFix ? me.distanceTo(target) : -1

    PositionSource {
        id: pos
        active: true
        updateInterval: 1000
    }

    Compass {
        id: compass
        active: true
        dataRate: 10
        onReadingChanged: if (reading) page.heading = reading.azimuth
    }

    PageHeader {
        id: header
        title: page.title
    }

    Item {
        id: dial
        anchors { horizontalCenter: parent.horizontalCenter; top: header.bottom; topMargin: Theme.paddingLarge }
        width: Math.min(page.width, page.height / 2) - 2 * Theme.horizontalPageMargin
        height: width

        Rectangle {
            anchors.fill: parent
            radius: width / 2
            color: "transparent"
            border.width: 3
            border.color: Theme.rgba(Theme.highlightColor, 0.5)
        }

        // arrow towards the target: bearing relative to where the phone points
        Canvas {
            id: arrow
            anchors.fill: parent
            rotation: page.hasFix ? page.bearing - page.heading : 0
            opacity: page.hasFix ? 1 : 0.3

            Behavior on rotation {
                RotationAnimation { direction: RotationAnimation.Shortest; duration: 250 }
            }

            onPaint: {
                var ctx = getContext("2d")
                ctx.reset()
                var w = width, h = height
                ctx.fillStyle = Theme.highlightColor
                ctx.beginPath()
                ctx.moveTo(w / 2, h * 0.08)
                ctx.lineTo(w * 0.68, h * 0.55)
                ctx.lineTo(w / 2, h * 0.46)
                ctx.lineTo(w * 0.32, h * 0.55)
                ctx.closePath()
                ctx.fill()
                ctx.fillStyle = Theme.rgba(Theme.highlightColor, 0.35)
                ctx.beginPath()
                ctx.moveTo(w / 2, h * 0.46)
                ctx.lineTo(w * 0.68, h * 0.55)
                ctx.lineTo(w / 2, h * 0.92)
                ctx.lineTo(w * 0.32, h * 0.55)
                ctx.closePath()
                ctx.fill()
            }
            Component.onCompleted: requestPaint()
        }
    }

    Column {
        anchors { top: dial.bottom; topMargin: Theme.paddingLarge; left: parent.left; right: parent.right }
        spacing: Theme.paddingSmall

        Label {
            width: parent.width
            horizontalAlignment: Text.AlignHCenter
            text: page.hasFix ? Util.formatDistance(page.distance, Backend.imperial) : qsTr("Waiting for GPS…")
            font.pixelSize: Theme.fontSizeHuge
            color: Theme.highlightColor
        }
        Label {
            width: parent.width
            horizontalAlignment: Text.AlignHCenter
            visible: page.hasFix
            text: qsTr("bearing %1°").arg(Math.round(page.bearing))
            color: Theme.secondaryColor
        }
        Label {
            width: parent.width
            horizontalAlignment: Text.AlignHCenter
            text: Util.formatCoord(page.targetLat, page.targetLon)
            font.pixelSize: Theme.fontSizeSmall
        }
        Label {
            width: parent.width
            horizontalAlignment: Text.AlignHCenter
            visible: page.hasFix && pos.position.horizontalAccuracyValid
            text: qsTr("GPS accuracy ±%1").arg(Util.formatDistance(pos.position.horizontalAccuracy, Backend.imperial))
            font.pixelSize: Theme.fontSizeExtraSmall
            color: Theme.secondaryColor
        }
        Label {
            width: parent.width - 2 * Theme.horizontalPageMargin
            x: Theme.horizontalPageMargin
            horizontalAlignment: Text.AlignHCenter
            wrapMode: Text.Wrap
            visible: compass.reading && compass.reading.calibrationLevel < 0.5
            text: qsTr("The compass is inaccurate – move the phone in a figure of eight.")
            font.pixelSize: Theme.fontSizeExtraSmall
            color: Theme.secondaryHighlightColor
        }
    }
}
