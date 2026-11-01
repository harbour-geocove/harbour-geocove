import QtQuick 2.2
import Sailfish.Silica 1.0
import "../components"
import "../components/Util.js" as Util

Page {
    id: page
    allowedOrientations: Orientation.All

    property var logs: []

    function reload() {
        Backend.call("offline_logs", [], function(r) { page.logs = r })
    }

    function exportNotes() {
        var path = Backend.documentsDir + "/geocache_visits.txt"
        Backend.call("export_field_notes", [path], function(r) {
            banner.show(qsTr("Saved %1 logs to %2. Upload the file on geocaching.com → Field Notes.")
                        .arg(r.count).arg(r.path))
        })
    }

    Component.onCompleted: reload()

    Connections {
        target: Backend
        onDataVersionChanged: page.reload()
        onErrorOccurred: banner.show(qsTr("Error (%1): %2").arg(event).arg(message))
    }

    SilicaListView {
        id: view
        anchors.fill: parent
        model: page.logs

        header: PageHeader {
            title: qsTr("Offline logs")
            description: qsTr("%1 entries").arg(page.logs.length)
        }

        PullDownMenu {
            MenuItem {
                text: qsTr("Export geocache_visits.txt")
                enabled: page.logs.length > 0
                onClicked: page.exportNotes()
            }
        }

        delegate: ListItem {
            id: item
            width: view.width
            contentHeight: Theme.itemSizeMedium

            menu: ContextMenu {
                MenuItem {
                    text: qsTr("Delete log")
                    onClicked: item.remorseAction(qsTr("Deleting"), function() {
                        Backend.call("delete_offline_log", [modelData.geocode], function() { Backend.dataVersion++ })
                    })
                }
            }

            onClicked: pageStack.push(Qt.resolvedUrl("LogPage.qml"),
                                      { geocode: modelData.geocode, cacheName: modelData.name || "" })

            Column {
                anchors {
                    left: parent.left; right: parent.right; leftMargin: Theme.horizontalPageMargin
                    rightMargin: Theme.horizontalPageMargin; verticalCenter: parent.verticalCenter
                }
                Label {
                    width: parent.width
                    text: modelData.geocode + " · " + (modelData.name || "")
                    color: item.highlighted ? Theme.highlightColor : Theme.primaryColor
                    truncationMode: TruncationMode.Fade
                }
                Label {
                    width: parent.width
                    text: Util.logTypeName(modelData.log_type) + (modelData.text ? " · " + modelData.text : "")
                    font.pixelSize: Theme.fontSizeExtraSmall
                    color: Theme.secondaryColor
                    truncationMode: TruncationMode.Fade
                }
            }
        }

        ViewPlaceholder {
            enabled: page.logs.length === 0
            text: qsTr("No offline logs")
            hintText: qsTr("On a cache page: pull down the menu → Write log")
        }

        VerticalScrollDecorator {}
    }

    StatusBanner { id: banner }
}
