import QtQuick 2.2
import Sailfish.Silica 1.0
import QtPositioning 5.2
import "../components"
import "../components/Util.js" as Util

// The map itself is one of two interchangeable views (qml/maps): OsmMapView (Qt Location, online tiles)
// or ScoutMapView (MapboxMap + OSM Scout Server). They are loaded dynamically, because a missing module
// must not break this page.
Page {
    id: page
    allowedOrientations: Orientation.All

    property var dbStats: ({})
    property var lastItems: []
    property string lastViewport: ""
    property int shown: 0
    property int total: 0
    property bool clustered: false
    property bool tooFar: false
    property bool userMoved: false          // the user has panned the map himself
    property bool userTracking: false       // armed shortly after loading, so the initial jump is not counted
    property bool settingsApplied: false
    property bool scoutFailed: false        // the MapboxMap module is not usable: the default map is shown
    property string mapInfo: ""

    property var map: mapLoader.item        // null until the backend is ready
    property var lastCenter: null           // kept so that a re-created map shows the same place
    property real lastZoom: 0

    // While another page (cache, settings, a dialog) covers the page, the map is shrunk to 1x1 px. A full-screen
    // map hidden under a page makes returning to the app after minimizing it slow (found in harbour-pidmap).
    // Minimizing the app with the map on top does not shrink anything: status stays Active then.
    readonly property bool covered: status === PageStatus.Inactive

    readonly property bool wantScout: Backend.settings.map_source === "osmscout"
    readonly property bool useScout: wantScout && !scoutFailed
    readonly property url mapSource: Qt.resolvedUrl(useScout ? "../maps/ScoutMapView.qml" : "../maps/OsmMapView.qml")

    onCoveredChanged: if (!covered) refreshTimer.restart()      // the map has its size back: show the caches again
    onMapSourceChanged: reloadMap()
    onWantScoutChanged: scoutFailed = false         // try again after the user changed the setting

    function reloadMap() {
        mapLoader.active = false
        mapLoader.source = mapSource
        mapLoader.active = Backend.ready
    }

    function scoutProblem(text) {
        scoutFailed = true
        Backend.scoutError = text
        banner.show(text)
    }

    // called by the Loader when a map view has been created
    function mapLoaded(item) {
        if (useScout) Backend.scoutError = ""
        item.userCoordinate = Qt.binding(function() { return pos.position.coordinate })
        item.viewChanged.connect(viewHasChanged)
        item.userMoved.connect(function() { if (page.userTracking) page.userMoved = true })
        item.markerClicked.connect(function(code) {
            pageStack.push(Qt.resolvedUrl("CachePage.qml"), { geocode: code })
        })
        item.clusterClicked.connect(function(lat, lon) {
            item.jumpTo(QtPositioning.coordinate(lat, lon), Math.min(18, item.zoomLevel + 2))
        })
        mapInfo = Qt.binding(function() { return item.info })
        item.setData(lastItems)
        userTracking = false
        if (lastZoom > 0) item.jumpTo(lastCenter, lastZoom)
        else applySettings()
        armTimer.restart()
        refresh()
    }

    function viewHasChanged() {
        if (!map || covered) return
        lastCenter = map.center
        lastZoom = map.zoomLevel
        refreshTimer.restart()
    }

    // what the map shows (the map view turns it into list models / GeoJSON)
    function fillModels(items) {
        lastItems = items
        shown = items.length
        if (map) map.setData(items)
    }

    function refresh() {
        if (!Backend.ready || !map || covered || map.width <= 1) return
        if (map.zoomLevel < 7) {
            fillModels([])
            tooFar = true
            return
        }
        var vp = map.bounds()
        if (!vp) return
        tooFar = false
        lastViewport = vp[0].toFixed(3) + ".." + vp[2].toFixed(3) + " / " + vp[1].toFixed(3) + ".." + vp[3].toFixed(3)
        Backend.call("map_view", [vp[0], vp[1], vp[2], vp[3], Backend.mapFilter(), 250], function(r) {
            console.log("map_view " + lastViewport + " -> total " + r.total + ", items " + r.items.length +
                        (r.error ? ", error " + r.error : ""))
            if (r.error) banner.show(qsTr("Map: %1").arg(r.error))
            page.fillModels(r.items)
            page.total = r.total
            page.clustered = r.clustered
        })
        if (Backend.settings.debug_map === true) Backend.call("db_stats", [], function(st) { page.dbStats = st })
    }

    function applySettings() {
        if (settingsApplied || !Backend.ready || !map) return
        settingsApplied = true
        map.jumpTo(QtPositioning.coordinate(Backend.settings.last_lat, Backend.settings.last_lon),
                   Backend.settings.last_zoom)
    }

    function saveView() {
        if (!map) return
        Backend.setSetting("last_lat", map.center.latitude)
        Backend.setSetting("last_lon", map.center.longitude)
        Backend.setSetting("last_zoom", Math.round(map.zoomLevel))
    }

    function centerOnMe() {
        if (!map) return
        if (pos.position.coordinate.isValid) {
            map.jumpTo(pos.position.coordinate, map.zoomLevel < 13 ? 14 : 0)
        } else {
            banner.show(qsTr("Waiting for GPS…"))
        }
    }

    function searchOnline() {
        if (!Backend.loggedIn) {
            pageStack.push(Qt.resolvedUrl("LoginPage.qml"))
            return
        }
        if (!map) return
        if (map.zoomLevel < 11) {
            banner.show(qsTr("Zoom in to search on geocaching.com."))
            return
        }
        var vp = map.bounds()
        if (!vp) return
        Backend.startBusy(qsTr("Searching on geocaching.com…"))
        Backend.call("search_online_viewport", [vp[0], vp[1], vp[2], vp[3], Backend.baseFilter()])
    }

    function showExpiredNotice() {
        banner.show(qsTr("Your geocaching.com session has expired. Paste a new cookie in the account settings."))
    }

    Component.onCompleted: {
        if (Backend.ready) reloadMap()
        if (Backend.sessionExpired) showExpiredNotice()
    }

    onStatusChanged: {
        if (status === PageStatus.Deactivating) saveView()
        if (status === PageStatus.Active) refresh()
    }

    Connections {
        target: Backend
        onReadyChanged: page.reloadMap()
        onTileServerChanged: page.reloadMap()      // the plugin parameters are read when the map is created
        onDataVersionChanged: page.refresh()
        onSessionExpiredChanged: if (Backend.sessionExpired) page.showExpiredNotice()
        onShowOnMap: {
            if (!page.map) return
            page.userMoved = true
            page.map.jumpTo(QtPositioning.coordinate(lat, lon), zoom)
            page.refresh()
            if (Backend.loggedIn) onlineAfterJump.restart()
            else banner.show(qsTr("Showing stored caches. Sign in to geocaching.com to download new ones."))
        }
        onOnlineSearchDone: {
            if (result.error) {
                banner.show(qsTr("Search failed: %1").arg(Util.statusText(result.error)) + (result.detail ? " [" + result.detail + "]" : ""))
            } else if (result.count === 0) {
                banner.show(qsTr("Nothing found."))
            } else {
                var more = result.left_to_fetch > 0 ? qsTr(" (%1 more not shown, zoom in)").arg(result.left_to_fetch) : ""
                banner.show(qsTr("Downloaded %1 caches.").arg(result.count) + more)
            }
        }
        onErrorOccurred: banner.show(qsTr("Error (%1): %2").arg(event).arg(message))
    }

    PositionSource {
        id: pos
        active: true
        updateInterval: 3000
        onPositionChanged: {
            if (page.map && !page.userMoved && position.coordinate.isValid && !page.settingsApplied) {
                page.map.jumpTo(position.coordinate, 0)
            }
        }
    }

    Loader {
        id: mapLoader
        width: page.covered ? 1 : page.width
        height: page.covered ? 1 : page.height
        active: false
        onStatusChanged: {
            // a missing MapboxMap module makes loading ScoutMapView.qml fail: fall back to the default map
            if (status === Loader.Error && page.useScout) {
                page.scoutProblem(qsTr("The MapboxMap module is not available (install the mapbox-gl-qml package). The default map is used."))
            }
        }
        onLoaded: page.mapLoaded(item)
    }

    Timer {
        id: armTimer
        interval: 1500
        onTriggered: page.userTracking = true
    }

    Timer {
        id: onlineAfterJump
        interval: 800
        onTriggered: page.searchOnline()
    }

    Timer {
        id: refreshTimer
        interval: 400
        onTriggered: page.refresh()
    }

    // --- map buttons
    Column {
        // vertically centred at the screen edge: reachable with the thumb of one hand
        // (setting "buttons on the left" for left-handed use)
        anchors {
            right: Backend.settings.buttons_left === true ? undefined : parent.right
            left: Backend.settings.buttons_left === true ? parent.left : undefined
            verticalCenter: parent.verticalCenter
            margins: Theme.paddingMedium
        }
        spacing: Theme.paddingMedium

        Repeater {
            model: [
                { icon: "image://theme/icon-m-menu", action: "menu" },
                { icon: "image://theme/icon-m-search", action: "search" },
                { icon: "image://theme/icon-m-levels", action: "filter" },
                { icon: "image://theme/icon-m-gps", action: "me" },
                { icon: "image://theme/icon-m-cloud-download", action: "online" }
            ]
            delegate: Rectangle {
                width: Theme.itemSizeSmall
                height: width
                radius: Theme.paddingSmall
                // the filter button is highlighted while a type filter is active
                color: modelData.action === "filter" && Backend.typeFilterActive
                       ? Theme.rgba(Theme.highlightBackgroundColor, 0.85)
                       : Theme.rgba(Theme.overlayBackgroundColor, 0.75)
                IconButton {
                    anchors.centerIn: parent
                    icon.source: modelData.icon
                    onClicked: {
                        if (modelData.action === "menu") pageStack.push(Qt.resolvedUrl("MenuPage.qml"))
                        else if (modelData.action === "search")
                            pageStack.push(Qt.resolvedUrl("CacheListPage.qml"),
                                           { mode: "search", title: qsTr("Find place"), searchKind: 1 })
                        else if (modelData.action === "filter") pageStack.push(Qt.resolvedUrl("MapFilterPage.qml"))
                        else if (modelData.action === "me") page.centerOnMe()
                        else page.searchOnline()
                    }
                }
            }
        }
    }

    Rectangle {
        visible: page.tooFar || (page.total > 0 && Backend.ready)
        anchors { horizontalCenter: parent.horizontalCenter; bottom: parent.bottom; bottomMargin: Theme.paddingLarge }
        width: hint.width + 2 * Theme.paddingLarge
        height: hint.height + 2 * Theme.paddingMedium
        radius: Theme.paddingSmall
        color: Theme.rgba(Theme.overlayBackgroundColor, 0.8)
        Label {
            id: hint
            anchors.centerIn: parent
            font.pixelSize: Theme.fontSizeSmall
            text: page.tooFar ? qsTr("Zoom in to show caches")
                              : (page.clustered ? qsTr("%1 caches – zoom in for individual ones").arg(page.total)
                                                : qsTr("%1 caches").arg(page.total)) +
                                (Backend.typeFilterActive ? qsTr(" · type filter on") : "")
        }
    }

    Rectangle {
        visible: Backend.settings.debug_map === true
        anchors { left: parent.left; bottom: parent.bottom; margins: Theme.paddingSmall }
        width: page.width * 0.6 + 2 * Theme.paddingSmall
        height: debugLabel.height + Theme.paddingSmall
        color: Theme.rgba(Theme.overlayBackgroundColor, 0.8)
        Label {
            id: debugLabel
            anchors.centerIn: parent
            width: page.width * 0.6
            wrapMode: Text.Wrap
            font.pixelSize: Theme.fontSizeTiny
            text: "v" + Backend.version + " · zoom " + (page.map ? page.map.zoomLevel.toFixed(1) : "-") +
                  "\nmap: " + page.mapInfo +
                  "\nDB " + (page.dbStats.caches !== undefined ? page.dbStats.caches : "?") +
                  " (with position " + (page.dbStats.with_coords !== undefined ? page.dbStats.with_coords : "?") + ")" +
                  "\nview " + page.total + ", drawn " + page.shown +
                  "\n" + page.lastViewport +
                  (page.dbStats.lat_min !== undefined && page.dbStats.lat_min !== null
                   ? "\nDB: " + page.dbStats.lat_min.toFixed(2) + ".." + page.dbStats.lat_max.toFixed(2) + " / " +
                     page.dbStats.lon_min.toFixed(2) + ".." + page.dbStats.lon_max.toFixed(2) : "")
        }
    }

    BusyBar {
        bottomOffset: Backend.settings.debug_map === true ? Theme.itemSizeHuge : Theme.itemSizeMedium
        running: Backend.busy
        text: Backend.busyText
    }

    StatusBanner { id: banner }
}
