import QtQuick 2.0
import Sailfish.Silica 1.0
import "../components"

CoverBackground {
    Column {
        anchors.centerIn: parent
        width: parent.width - 2 * Theme.paddingLarge
        spacing: Theme.paddingSmall

        Image {
            anchors.horizontalCenter: parent.horizontalCenter
            width: Theme.iconSizeLarge
            height: Theme.iconSizeLarge
            source: "/usr/share/icons/hicolor/172x172/apps/harbour-geocove.png"
            fillMode: Image.PreserveAspectFit
        }

        Label {
            width: parent.width
            horizontalAlignment: Text.AlignHCenter
            text: "GeoCove"
            font.pixelSize: Theme.fontSizeLarge
        }

        Label {
            width: parent.width
            horizontalAlignment: Text.AlignHCenter
            text: Backend.loggedIn
                  ? Backend.userName
                  : qsTr("not signed in")
            color: Theme.secondaryColor
            font.pixelSize: Theme.fontSizeSmall
            truncationMode: TruncationMode.Fade
        }
    }
}

