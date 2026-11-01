import QtQuick 2.2
import Sailfish.Silica 1.0
import "../components"
import "../components/Util.js" as Util

// Offline log (field note); upload geocache_visits.txt on geocaching.com afterwards.
Dialog {
    id: dialog

    property string geocode
    property string cacheName
    property var types: []

    canAccept: types.length > 0

    Component.onCompleted: {
        Backend.call("log_types", [], function(t) {
            dialog.types = t
            Backend.call("get_cache", [dialog.geocode], function(c) {
                if (c && c.offline_log) {
                    var idx = t.indexOf(c.offline_log.log_type)
                    if (idx >= 0) typeBox.currentIndex = idx
                    textArea.text = c.offline_log.text || ""
                    favSwitch.checked = c.offline_log.favorite === 1
                }
            })
        })
    }

    onAccepted: {
        Backend.call("save_offline_log",
                     [geocode, types[typeBox.currentIndex], textArea.text, favSwitch.checked],
                     function() { Backend.dataVersion++ })
    }

    SilicaFlickable {
        anchors.fill: parent
        contentHeight: column.height

        Column {
            id: column
            width: parent.width

            DialogHeader {
                title: dialog.geocode
                acceptText: qsTr("Save")
            }

            Label {
                x: Theme.horizontalPageMargin
                width: parent.width - 2 * Theme.horizontalPageMargin
                text: dialog.cacheName
                wrapMode: Text.Wrap
                color: Theme.highlightColor
            }

            ComboBox {
                id: typeBox
                label: qsTr("Log type")
                menu: ContextMenu {
                    Repeater {
                        model: dialog.types
                        MenuItem { text: Util.logTypeName(modelData) }
                    }
                }
            }

            TextArea {
                id: textArea
                width: parent.width
                label: qsTr("Log text")
                placeholderText: label
            }

            TextSwitch {
                id: favSwitch
                text: qsTr("Give a favorite point")
                visible: false   // favorite points are not part of field notes
            }
        }

        VerticalScrollDecorator {}
    }
}
