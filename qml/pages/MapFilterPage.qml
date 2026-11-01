import QtQuick 2.2
import Sailfish.Silica 1.0
import "../components"
import "../components/Util.js" as Util

// Which caches the map shows: cache types and the found / disabled / archived switches.
// Changes apply at once (the map refreshes when this page is closed or the data version changes).
Page {
    id: page
    allowedOrientations: Orientation.All

    function isOn(groupId) {
        return Backend.settings.map_types.indexOf(groupId) >= 0
    }

    function toggle(groupId) {
        var list = Backend.settings.map_types.slice()
        var index = list.indexOf(groupId)
        if (index >= 0) list.splice(index, 1)
        else list.push(groupId)
        Backend.setSetting("map_types", list)
        Backend.dataVersion++
    }

    function setAll(on) {
        var ids = []
        if (on) {
            var groups = Util.typeGroups()
            for (var i = 0; i < groups.length; i++) ids.push(groups[i].id)
        }
        Backend.setSetting("map_types", ids)
        Backend.dataVersion++
    }

    SilicaFlickable {
        anchors.fill: parent
        contentHeight: column.height + Theme.paddingLarge

        Column {
            id: column
            width: parent.width

            PageHeader { title: qsTr("Map filter") }

            SectionHeader { text: qsTr("Cache types") }

            Row {
                anchors.horizontalCenter: parent.horizontalCenter
                spacing: Theme.paddingLarge
                Button {
                    text: qsTr("All")
                    onClicked: page.setAll(true)
                }
                Button {
                    text: qsTr("None")
                    onClicked: page.setAll(false)
                }
            }

            Repeater {
                model: Util.typeGroups()
                delegate: TextSwitch {
                    automaticCheck: false              // the switch follows the setting
                    text: modelData.name
                    checked: Backend.settings.map_types.indexOf(modelData.id) >= 0
                    onClicked: page.toggle(modelData.id)
                }
            }

            SectionHeader { text: qsTr("Display") }

            TextSwitch {
                automaticCheck: false
                text: qsTr("Hide found caches")
                checked: Backend.settings.hide_found === true
                onClicked: { Backend.setSetting("hide_found", !checked); Backend.dataVersion++ }
            }
            TextSwitch {
                automaticCheck: false
                text: qsTr("Hide disabled caches")
                checked: Backend.settings.hide_disabled === true
                onClicked: { Backend.setSetting("hide_disabled", !checked); Backend.dataVersion++ }
            }
            TextSwitch {
                automaticCheck: false
                text: qsTr("Hide archived caches")
                checked: Backend.settings.hide_archived !== false
                onClicked: { Backend.setSetting("hide_archived", !checked); Backend.dataVersion++ }
            }

            Label {
                x: Theme.horizontalPageMargin
                width: parent.width - 2 * Theme.horizontalPageMargin
                wrapMode: Text.Wrap
                font.pixelSize: Theme.fontSizeExtraSmall
                color: Theme.secondaryColor
                text: qsTr("The filter only changes what is shown on the map. Downloads from geocaching.com are not limited by type.")
            }
        }

        VerticalScrollDecorator {}
    }
}
