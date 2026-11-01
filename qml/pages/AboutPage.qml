import QtQuick 2.0
import Sailfish.Silica 1.0
import "../components"

Page {
    allowedOrientations: Orientation.All

    SilicaFlickable {
        anchors.fill: parent
        contentHeight: column.height + Theme.paddingLarge

        Column {
            id: column
            width: parent.width

            PageHeader { title: qsTr("About") }

            Label {
                x: Theme.horizontalPageMargin
                width: parent.width - 2 * Theme.horizontalPageMargin
                wrapMode: Text.Wrap
                text: qsTr("GeoCove %1\n\nA geocaching client for Sailfish OS (Python + QML), a port of parts of c:geo (https://www.cgeo.org/).").arg(Backend.version)
            }
            Label {
                x: Theme.horizontalPageMargin
                width: parent.width - 2 * Theme.horizontalPageMargin
                wrapMode: Text.Wrap
                color: Theme.secondaryColor
                font.pixelSize: Theme.fontSizeSmall
                text: qsTr("\nNot an official Groundspeak or c:geo application. Access to geocaching.com through the website is unofficial and may violate the terms of service.\n\nMap data © OpenStreetMap contributors.")
            }
        }

        VerticalScrollDecorator {}
    }
}
