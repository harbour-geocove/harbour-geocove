import QtQuick 2.0
import Sailfish.Silica 1.0
import "../components"

Page {
    id: page
    allowedOrientations: Orientation.All

    SilicaFlickable {
        anchors.fill: parent
        contentHeight: column.height + Theme.paddingLarge

        Column {
            id: column
            width: parent.width

            PageHeader { title: qsTr("Settings") }

            SectionHeader { text: qsTr("Display") }

            TextSwitch {
                text: qsTr("Miles and feet instead of kilometres")
                checked: Backend.settings.imperial === true
                onClicked: Backend.setSetting("imperial", checked)
            }
            TextSwitch {
                text: qsTr("Map buttons on the left side")
                description: qsTr("For left-handed use; the buttons are in the middle of the screen edge")
                checked: Backend.settings.buttons_left === true
                onClicked: Backend.setSetting("buttons_left", checked)
            }
            TextSwitch {
                text: qsTr("Hide found caches")
                checked: Backend.settings.hide_found === true
                onClicked: { Backend.setSetting("hide_found", checked); Backend.dataVersion++ }
            }
            TextSwitch {
                text: qsTr("Hide disabled caches")
                checked: Backend.settings.hide_disabled === true
                onClicked: { Backend.setSetting("hide_disabled", checked); Backend.dataVersion++ }
            }
            TextSwitch {
                text: qsTr("Hide archived caches")
                checked: Backend.settings.hide_archived !== false
                onClicked: { Backend.setSetting("hide_archived", checked); Backend.dataVersion++ }
            }

            TextSwitch {
                text: qsTr("Readable listings")
                description: qsTr("Removes background colours, replaces text colours that are hard to read on the current theme and enlarges tiny text in cache descriptions")
                checked: Backend.settings.readable_listings !== false
                onClicked: Backend.setSetting("readable_listings", checked)
            }

            ComboBox {
                width: parent.width
                label: qsTr("Images in descriptions")
                currentIndex: Backend.settings.description_images === "links" ? 1
                              : (Backend.settings.description_images === "none" ? 2 : 0)
                menu: ContextMenu {
                    MenuItem { text: qsTr("Fit to the screen width") }
                    MenuItem { text: qsTr("Only as links") }
                    MenuItem { text: qsTr("Hide") }
                }
                onCurrentIndexChanged: {
                    var wanted = ["fit", "links", "none"][currentIndex]
                    if (wanted !== Backend.settings.description_images) Backend.setSetting("description_images", wanted)
                }
            }

            SectionHeader { text: qsTr("Map") }

            TextSwitch {
                text: qsTr("Debug information on the map")
                description: qsTr("Version, number of stored caches and drawn markers")
                checked: Backend.settings.debug_map === true
                onClicked: Backend.setSetting("debug_map", checked)
            }

            ComboBox {
                width: parent.width
                label: qsTr("Map source")
                currentIndex: Backend.settings.map_source === "osmscout" ? 1 : 0
                menu: ContextMenu {
                    MenuItem { text: qsTr("OpenStreetMap (online tiles)") }
                    MenuItem { text: qsTr("OSM Scout Server (local, offline maps)") }
                }
                onCurrentIndexChanged: {
                    var wanted = currentIndex === 1 ? "osmscout" : "osm"
                    if (wanted !== Backend.settings.map_source) Backend.setSetting("map_source", wanted)
                }
            }

            ComboBox {
                visible: Backend.settings.map_source === "osmscout"
                width: parent.width
                label: qsTr("Map style")
                currentIndex: Backend.scoutStyle === "light" ? 0 : (Backend.scoutStyle === "dark" ? 1 : 2)
                menu: ContextMenu {
                    MenuItem { text: qsTr("Light") }
                    MenuItem { text: qsTr("Dark") }
                    MenuItem { text: qsTr("Automatic (follows the ambience)") }
                }
                onCurrentIndexChanged: {
                    var wanted = ["light", "dark", "auto"][currentIndex]
                    if (wanted !== Backend.scoutStyle) Backend.setScoutStyle(wanted)
                }
            }

            /*TextField {
                visible: Backend.settings.map_source === "osmscout"
                width: parent.width
                label: qsTr("Style URL of OSM Scout Server (the dark style uses mc instead of osmbright)")
                text: Backend.settings.osmscout_style_url
                inputMethodHints: Qt.ImhUrlCharactersOnly | Qt.ImhNoAutoUppercase
                EnterKey.iconSource: "image://theme/icon-m-enter-accept"
                EnterKey.onClicked: {
                    Backend.setSetting("osmscout_style_url", text.trim())
                    focus = false
                }
            }*/
            Label {
                visible: Backend.settings.map_source === "osmscout"
                x: Theme.horizontalPageMargin
                width: parent.width - 2 * Theme.horizontalPageMargin
                wrapMode: Text.Wrap
                font.pixelSize: Theme.fontSizeExtraSmall
                color: Theme.secondaryColor
                text: qsTr("Needs the mapboxgl-qml package. Start OSM Scout Server first and download a map region in it. The map is re-created when you change these settings.")
            }
            TextField {
                visible: Backend.settings.map_source === "osmscout"
                width: parent.width
                label: qsTr("Scale correction of the OSM Scout map (1.0 = automatic)")
                text: Backend.settings.scout_scale
                inputMethodHints: Qt.ImhFormattedNumbersOnly
                EnterKey.iconSource: "image://theme/icon-m-enter-accept"
                EnterKey.onClicked: {
                    var value = parseFloat(text.replace(",", "."))
                    if (value >= 0.3 && value <= 3) Backend.setSetting("scout_scale", value)
                    else text = Backend.settings.scout_scale
                    focus = false
                }
            }
            TextField {
                visible: Backend.settings.map_source === "osmscout"
                width: parent.width
                label: qsTr("Font of the map labels (a font stack of OSM Scout Server)")
                text: Backend.settings.scout_text_font
                EnterKey.iconSource: "image://theme/icon-m-enter-accept"
                EnterKey.onClicked: {
                    Backend.setSetting("scout_text_font", text.trim())
                    focus = false
                }
            }
            Label {
                visible: Backend.settings.map_source === "osmscout" && Backend.scoutError !== ""
                x: Theme.horizontalPageMargin
                width: parent.width - 2 * Theme.horizontalPageMargin
                wrapMode: Text.Wrap
                font.pixelSize: Theme.fontSizeExtraSmall
                color: Theme.secondaryHighlightColor
                text: Backend.scoutError
            }

            TextField {
                visible: Backend.settings.map_source === "osm"
                width: parent.width
                label: qsTr("Tile server of the OpenStreetMap source")
                text: Backend.settings.tile_server
                inputMethodHints: Qt.ImhUrlCharactersOnly | Qt.ImhNoAutoUppercase
                EnterKey.iconSource: "image://theme/icon-m-enter-accept"
                EnterKey.onClicked: {
                    Backend.setSetting("tile_server", text.trim())
                    focus = false
                }
            }
            Label {
                visible: Backend.settings.map_source === "osm"
                x: Theme.horizontalPageMargin
                width: parent.width - 2 * Theme.horizontalPageMargin
                wrapMode: Text.Wrap
                font.pixelSize: Theme.fontSizeExtraSmall
                color: Theme.secondaryColor
                text: qsTr("The default server tile.openstreetmap.org has a usage policy for reasonable use. For heavy use choose your own or a paid server.")
            }

            SectionHeader { text: qsTr("Diagnostics") }

            Button {
                anchors.horizontalCenter: parent.horizontalCenter
                text: qsTr("Test the connection to geocaching.com")
                enabled: !Backend.busy
                onClicked: Backend.runConnectionTest()
            }
            TextArea {
                visible: Backend.testReport !== ""
                width: parent.width
                readOnly: true
                label: qsTr("Report (contains no passwords or tokens)")
                text: Backend.testReport
                font.pixelSize: Theme.fontSizeExtraSmall
            }
        }

        VerticalScrollDecorator {}
    }

    BusyBar {
        running: Backend.busy
        text: Backend.busyText
    }
}
