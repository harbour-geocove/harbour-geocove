import QtQuick 2.2
import Sailfish.Silica 1.0

// One picture; tap switches between "fit to screen" and a larger view that can be panned.
Page {
    id: page
    allowedOrientations: Orientation.All

    property string url
    property string title
    property bool zoomed: false

    SilicaFlickable {
        id: flick
        anchors.fill: parent
        contentWidth: Math.max(width, image.width)
        contentHeight: Math.max(height, image.height)

        Image {
            id: image
            width: page.zoomed ? flick.width * 2.5 : flick.width
            height: page.zoomed ? flick.height * 2.5 : flick.height
            sourceSize: Qt.size(2048, 2048)
            fillMode: Image.PreserveAspectFit
            asynchronous: true
            source: page.url

            MouseArea {
                anchors.fill: parent
                onClicked: page.zoomed = !page.zoomed
            }
        }

        VerticalScrollDecorator {}
        HorizontalScrollDecorator {}
    }

    BusyIndicator {
        anchors.centerIn: parent
        size: BusyIndicatorSize.Large
        running: image.status === Image.Loading
    }

    Label {
        visible: image.status === Image.Error
        anchors.centerIn: parent
        text: qsTr("The image cannot be loaded")
        color: Theme.secondaryColor
    }

    Label {
        visible: page.title !== "" && !page.zoomed
        anchors { left: parent.left; right: parent.right; bottom: parent.bottom; margins: Theme.horizontalPageMargin }
        horizontalAlignment: Text.AlignHCenter
        wrapMode: Text.Wrap
        text: page.title
        font.pixelSize: Theme.fontSizeSmall
        style: Text.Outline
        styleColor: "black"
    }
}
