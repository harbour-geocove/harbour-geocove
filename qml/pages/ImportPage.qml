import QtQuick 2.2
import Sailfish.Silica 1.0
import Sailfish.Pickers 1.0
import "../components"

Page {
    id: page
    allowedOrientations: Orientation.All

    property string filePath: ""
    property string resultText: ""

    function baseName(path) {
        var name = path.substring(path.lastIndexOf("/") + 1)
        return name.replace(/\.gpx$/i, "")
    }

    Component {
        id: pickerComponent
        FilePickerPage {
            nameFilters: ["*.gpx", "*.GPX"]
            onSelectedContentPropertiesChanged: {
                page.filePath = selectedContentProperties.filePath
                listName.text = page.baseName(page.filePath)
            }
        }
    }

    Connections {
        target: Backend
        onGpxImported: {
            page.resultText = qsTr("Imported %1 caches and %2 waypoints (%3 waypoints without a cache skipped).")
                .arg(result.caches).arg(result.waypoints).arg(result.skipped_waypoints)
        }
        onErrorOccurred: if (event === "gpx_imported") page.resultText = qsTr("Import failed: %1").arg(message)
    }

    SilicaFlickable {
        anchors.fill: parent
        contentHeight: column.height + Theme.paddingLarge

        Column {
            id: column
            width: parent.width

            PageHeader { title: qsTr("Import GPX") }

            Label {
                x: Theme.horizontalPageMargin
                width: parent.width - 2 * Theme.horizontalPageMargin
                wrapMode: Text.Wrap
                font.pixelSize: Theme.fontSizeSmall
                color: Theme.secondaryColor
                text: qsTr("Download a Pocket Query (GPX, or a ZIP unpacked to GPX) on geocaching.com and pick the file. Import the file with additional waypoints only after the file with the caches.")
            }

            Button {
                anchors.horizontalCenter: parent.horizontalCenter
                text: qsTr("Choose a GPX file")
                onClicked: pageStack.push(pickerComponent)
            }

            Label {
                visible: page.filePath !== ""
                x: Theme.horizontalPageMargin
                width: parent.width - 2 * Theme.horizontalPageMargin
                text: page.filePath
                font.pixelSize: Theme.fontSizeExtraSmall
                truncationMode: TruncationMode.Fade
                color: Theme.highlightColor
            }

            TextField {
                id: listName
                visible: page.filePath !== ""
                width: parent.width
                label: qsTr("Add to list (empty = no list)")
                placeholderText: qsTr("List name")
            }

            Button {
                visible: page.filePath !== ""
                anchors.horizontalCenter: parent.horizontalCenter
                enabled: !Backend.busy
                text: qsTr("Import")
                onClicked: {
                    page.resultText = ""
                    Backend.startBusy(qsTr("Importing…"))
                    Backend.call("import_gpx_file", [page.filePath, listName.text.trim()])
                }
            }

            Label {
                visible: page.resultText !== ""
                x: Theme.horizontalPageMargin
                width: parent.width - 2 * Theme.horizontalPageMargin
                wrapMode: Text.Wrap
                color: Theme.highlightColor
                text: page.resultText
            }
        }

        VerticalScrollDecorator {}
    }

    BusyBar {
        running: Backend.busy
        text: Backend.busyText
    }
}
