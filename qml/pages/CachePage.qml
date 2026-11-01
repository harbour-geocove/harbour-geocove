import QtQuick 2.2
import Sailfish.Silica 1.0
import "../components"
import "../components/Util.js" as Util

Page {
    id: page
    allowedOrientations: Orientation.All

    property string geocode
    property var cache: null
    property bool hintShown: false
    property int visibleLogs: 15
    readonly property bool hasCoords: cache !== null && cache.has_coords === true

    function reload() {
        Backend.call("get_cache", [geocode], function(c) { page.cache = c })
    }

    function refreshOnline() {
        if (!Backend.loggedIn) {
            pageStack.push(Qt.resolvedUrl("LoginPage.qml"))
            return
        }
        Backend.startBusy(qsTr("Downloading details…"))
        Backend.call("load_cache_online", [geocode])
    }

    // the "Gallery (N)" link of the listing opens our own gallery page instead of the browser
    function openLink(link) {
        if (link.indexOf("/seek/gallery.aspx") >= 0)
            pageStack.push(Qt.resolvedUrl("GalleryPage.qml"), { geocode: page.geocode, mode: "web" })
        else
            Qt.openUrlExternally(link)
    }

    // the listing as shown: readable colours / sizes for the current theme, images fitted to the width
    function listingHtml(width) {
        var html = page.cache.short_description + "<br/><br/>" + page.cache.description
        if (Backend.settings.readable_listings !== false)
            html = Util.readableHtml(html, Theme.colorScheme === Theme.LightOnDark, Theme.fontSizeSmall)
        return Util.fitHtml(html, width, Backend.settings.description_images)
    }

    function openCompass(title, lat, lon) {
        pageStack.push(Qt.resolvedUrl("CompassPage.qml"), { title: title, targetLat: lat, targetLon: lon })
    }

    Component.onCompleted: reload()

    Connections {
        target: Backend
        onDataVersionChanged: page.reload()
        onCacheLoaded: {
            if (result.geocode !== page.geocode) return
            if (result.status !== "no_error") banner.show(Util.statusText(result.status) + (result.detail ? " [" + result.detail + "]" : ""))
        }
        onErrorOccurred: banner.show(qsTr("Error (%1): %2").arg(event).arg(message))
    }

    RemorsePopup { id: remorse }

    SilicaFlickable {
        anchors.fill: parent
        contentHeight: column.height + Theme.paddingLarge

        PullDownMenu {
            MenuItem {
                text: qsTr("Refresh from geocaching.com")
                onClicked: page.refreshOnline()
            }
            MenuItem {
                text: qsTr("Write log (offline)")
                onClicked: pageStack.push(Qt.resolvedUrl("LogPage.qml"),
                                          { geocode: page.geocode, cacheName: page.cache ? page.cache.name : "" })
            }
            MenuItem {
                text: qsTr("Add to list")
                onClicked: {
                    var picker = pageStack.push(Qt.resolvedUrl("ListPickerPage.qml"))
                    picker.picked.connect(function(id) {
                        Backend.call("add_to_list", [id, [page.geocode]], function() { Backend.dataVersion++ })
                    })
                }
            }
            MenuItem {
                visible: page.hasCoords
                text: qsTr("Compass to the main point")
                onClicked: page.openCompass(page.cache.name, page.cache.lat, page.cache.lon)
            }
        }

        PushUpMenu {
            MenuItem {
                text: qsTr("Open on geocaching.com")
                onClicked: Qt.openUrlExternally("https://coord.info/" + page.geocode)
            }
            MenuItem {
                visible: page.hasCoords
                text: qsTr("Open location in a map app")
                onClicked: {
                    if (!Qt.openUrlExternally(Util.geoUrl(page.cache.lat, page.cache.lon)))
                        banner.show(qsTr("No application is registered to open geo: links."))
                }
            }
            MenuItem {
                visible: page.cache !== null
                text: qsTr("Save listing HTML to Documents")
                onClicked: Backend.call("export_listing_html", [page.geocode], function(r) {
                    banner.show(r.ok ? qsTr("Saved to %1").arg(r.path) : qsTr("The cache is not stored."))
                })
            }
            MenuItem {
                text: qsTr("Delete from phone")
                onClicked: remorse.execute(qsTr("Deleting cache"), function() {
                    Backend.call("delete_caches", [[page.geocode]], function() {
                        Backend.dataVersion++
                        pageStack.pop()
                    })
                })
            }
        }

        Column {
            id: column
            width: parent.width

            PageHeader {
                title: page.geocode
                description: page.cache ? page.cache.name : ""
            }

            Row {
                x: Theme.horizontalPageMargin
                spacing: Theme.paddingMedium
                visible: page.cache !== null

                CacheBadge {
                    typeId: page.cache ? page.cache.type_id : "unknown"
                    found: page.cache ? page.cache.found : false
                    size: Theme.itemSizeSmall
                    anchors.verticalCenter: parent.verticalCenter
                }
                Label {
                    anchors.verticalCenter: parent.verticalCenter
                    width: column.width - 2 * Theme.horizontalPageMargin - Theme.itemSizeSmall - Theme.paddingMedium
                    wrapMode: Text.Wrap
                    text: page.cache ? Util.typeName(page.cache.type_id) +
                          (page.cache.found ? qsTr(" · found") : "") +
                          (page.cache.disabled ? qsTr(" · disabled") : "") +
                          (page.cache.archived ? qsTr(" · archived") : "") +
                          (page.cache.premium_only ? qsTr(" · premium") : "") : ""
                    color: Theme.highlightColor
                }
            }

            Label {
                visible: page.cache === null
                x: Theme.horizontalPageMargin
                width: parent.width - 2 * Theme.horizontalPageMargin
                wrapMode: Text.Wrap
                color: Theme.secondaryHighlightColor
                text: qsTr("This cache is not stored. Download it from the menu (Refresh from geocaching.com).")
            }

            Item { width: 1; height: Theme.paddingMedium }

            DetailItem {
                visible: page.cache !== null
                label: qsTr("Difficulty / terrain")
                value: page.cache ? "D" + Util.formatRating(page.cache.difficulty) + " / T" + Util.formatRating(page.cache.terrain) : ""
            }
            DetailItem {
                visible: page.cache !== null
                label: qsTr("Size")
                value: page.cache ? Util.sizeName(page.cache.size_id) : ""
            }
            DetailItem {
                visible: page.cache !== null && page.cache.owner !== ""
                label: qsTr("Owner")
                value: page.cache ? page.cache.owner : ""
            }
            DetailItem {
                visible: page.cache !== null && page.cache.hidden !== ""
                label: qsTr("Hidden")
                value: page.cache ? Util.formatDate(page.cache.hidden) : ""
            }
            DetailItem {
                visible: page.cache !== null && page.cache.location !== ""
                label: qsTr("Area")
                value: page.cache ? page.cache.location : ""
            }
            DetailItem {
                visible: page.cache !== null && page.cache.favorite_points > 0
                label: qsTr("Favorite points")
                value: page.cache ? page.cache.favorite_points : ""
            }
            BackgroundItem {
                visible: page.hasCoords
                width: parent.width
                height: Theme.itemSizeSmall
                onClicked: page.openCompass(page.cache.name, page.cache.lat, page.cache.lon)
                Label {
                    anchors { left: parent.left; right: parent.right; margins: Theme.horizontalPageMargin; verticalCenter: parent.verticalCenter }
                    text: page.hasCoords ? Util.formatCoord(page.cache.lat, page.cache.lon) +
                          (page.cache.user_modified ? qsTr(" (corrected)") : "") : ""
                    color: highlighted ? Theme.highlightColor : Theme.primaryColor
                }
            }
            Label {
                visible: page.cache !== null && !page.cache.has_coords
                x: Theme.horizontalPageMargin
                width: parent.width - 2 * Theme.horizontalPageMargin
                wrapMode: Text.Wrap
                color: Theme.secondaryColor
                text: qsTr("Coordinates are not available (premium cache or insufficient rights).")
            }

            Label {
                visible: page.cache !== null && Util.attributeText(page.cache.attributes) !== ""
                x: Theme.horizontalPageMargin
                width: parent.width - 2 * Theme.horizontalPageMargin
                wrapMode: Text.Wrap
                font.pixelSize: Theme.fontSizeExtraSmall
                color: Theme.secondaryColor
                text: page.cache ? Util.attributeText(page.cache.attributes) : ""
            }

            // --- hint
            Button {
                visible: page.cache !== null && page.cache.hint !== ""
                anchors.horizontalCenter: parent.horizontalCenter
                text: page.hintShown ? qsTr("Hide hint") : qsTr("Show hint")
                onClicked: page.hintShown = !page.hintShown
            }
            Label {
                visible: page.hintShown && page.cache !== null
                x: Theme.horizontalPageMargin
                width: parent.width - 2 * Theme.horizontalPageMargin
                wrapMode: Text.Wrap
                text: page.cache ? page.cache.hint : ""
                color: Theme.highlightColor
            }

            // --- description
            SectionHeader {
                visible: page.cache !== null && page.cache.detailed === true
                text: qsTr("Description")
            }
            Label {
                visible: page.cache !== null && page.cache.detailed === true
                x: Theme.horizontalPageMargin
                width: parent.width - 2 * Theme.horizontalPageMargin
                wrapMode: Text.WrapAtWordBoundaryOrAnywhere
                textFormat: Text.RichText
                linkColor: Theme.highlightColor
                font.pixelSize: Theme.fontSizeSmall
                text: page.cache ? page.listingHtml(width) : ""
                onLinkActivated: page.openLink(link)
            }

            SectionHeader {
                visible: page.cache !== null && page.cache.personal_note !== ""
                text: qsTr("My note")
            }
            Label {
                visible: page.cache !== null && page.cache.personal_note !== ""
                x: Theme.horizontalPageMargin
                width: parent.width - 2 * Theme.horizontalPageMargin
                wrapMode: Text.Wrap
                text: page.cache ? page.cache.personal_note : ""
            }

            // --- offline log
            SectionHeader {
                visible: page.cache !== null && page.cache.offline_log !== null
                text: qsTr("Offline log")
            }
            Label {
                visible: page.cache !== null && page.cache.offline_log !== null
                x: Theme.horizontalPageMargin
                width: parent.width - 2 * Theme.horizontalPageMargin
                wrapMode: Text.Wrap
                color: Theme.highlightColor
                text: page.cache && page.cache.offline_log
                      ? Util.logTypeName(page.cache.offline_log.log_type) + (page.cache.offline_log.text ? ": " + page.cache.offline_log.text : "")
                      : ""
            }

            // --- waypoints
            SectionHeader {
                visible: page.cache !== null && page.cache.waypoints.length > 0
                text: qsTr("Waypoints")
            }
            Repeater {
                model: page.cache ? page.cache.waypoints : []
                delegate: BackgroundItem {
                    width: column.width
                    height: wpColumn.height + 2 * Theme.paddingSmall
                    enabled: modelData.lat !== null
                    onClicked: page.openCompass(modelData.name, modelData.lat, modelData.lon)

                    Column {
                        id: wpColumn
                        anchors {
                            left: parent.left; right: parent.right; margins: Theme.horizontalPageMargin
                            verticalCenter: parent.verticalCenter
                        }
                        Label {
                            width: parent.width
                            text: modelData.name + (modelData.type ? " · " + modelData.type : "")
                            color: highlighted ? Theme.highlightColor : Theme.primaryColor
                            truncationMode: TruncationMode.Fade
                        }
                        Label {
                            width: parent.width
                            text: modelData.lat !== null ? Util.formatCoord(modelData.lat, modelData.lon) : qsTr("coordinates unknown")
                            font.pixelSize: Theme.fontSizeExtraSmall
                            color: Theme.secondaryColor
                        }
                        Label {
                            visible: modelData.note !== ""
                            width: parent.width
                            text: Util.stripHtml(modelData.note)
                            wrapMode: Text.Wrap
                            font.pixelSize: Theme.fontSizeExtraSmall
                            color: Theme.secondaryColor
                        }
                    }
                }
            }

            // --- trackables
            SectionHeader {
                visible: page.cache !== null && page.cache.inventory.length > 0
                text: qsTr("Trackables")
            }
            Repeater {
                model: page.cache ? page.cache.inventory : []
                delegate: Label {
                    x: Theme.horizontalPageMargin
                    width: column.width - 2 * Theme.horizontalPageMargin
                    text: (modelData.geocode ? modelData.geocode + " · " : "") + modelData.name
                    truncationMode: TruncationMode.Fade
                }
            }

            // --- links to spoiler images
            SectionHeader {
                visible: page.cache !== null && page.cache.spoilers.length > 0
                text: qsTr("Images (%1)").arg(page.cache ? page.cache.spoilers.length : 0)
            }
            Repeater {
                model: page.cache ? page.cache.spoilers : []
                delegate: BackgroundItem {
                    width: column.width
                    onClicked: pageStack.push(Qt.resolvedUrl("ImageViewPage.qml"),
                                              { url: modelData.url, title: modelData.title })
                    Label {
                        anchors {
                            left: parent.left; right: parent.right; margins: Theme.horizontalPageMargin
                            verticalCenter: parent.verticalCenter
                        }
                        text: modelData.title || modelData.url
                        color: highlighted ? Theme.highlightColor : Theme.primaryColor
                        truncationMode: TruncationMode.Fade
                    }
                }
            }

            Button {
                visible: page.cache !== null && page.cache.spoilers.length > 1
                anchors.horizontalCenter: parent.horizontalCenter
                text: qsTr("Show all images")
                onClicked: pageStack.push(Qt.resolvedUrl("GalleryPage.qml"),
                                          { geocode: page.geocode, mode: "list", images: page.cache.spoilers })
            }

            // --- logs
            SectionHeader {
                visible: page.cache !== null && page.cache.logs.length > 0
                text: qsTr("Logs (%1)").arg(page.cache ? page.cache.logs.length : 0)
            }
            Repeater {
                model: page.cache ? Math.min(page.cache.logs.length, page.visibleLogs) : 0
                delegate: Column {
                    width: column.width
                    spacing: Theme.paddingSmall

                    Label {
                        x: Theme.horizontalPageMargin
                        width: parent.width - 2 * Theme.horizontalPageMargin
                        text: page.cache.logs[index].author + " · " + Util.logTypeName(page.cache.logs[index].type) +
                              " · " + Util.formatDate(page.cache.logs[index].date)
                        color: Theme.highlightColor
                        font.pixelSize: Theme.fontSizeSmall
                        truncationMode: TruncationMode.Fade
                    }
                    Label {
                        x: Theme.horizontalPageMargin
                        width: parent.width - 2 * Theme.horizontalPageMargin
                        wrapMode: Text.Wrap
                        textFormat: Text.StyledText
                        font.pixelSize: Theme.fontSizeExtraSmall
                        text: page.cache.logs[index].text
                    }
                    Item { width: 1; height: Theme.paddingMedium }
                }
            }
            Button {
                visible: page.cache !== null && page.cache.logs.length > page.visibleLogs
                anchors.horizontalCenter: parent.horizontalCenter
                text: qsTr("Show more logs")
                onClicked: page.visibleLogs += 15
            }
        }

        VerticalScrollDecorator {}
    }

    BusyBar {
        running: Backend.busy
        text: Backend.busyText
    }

    StatusBanner { id: banner }
}
