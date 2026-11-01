import QtQuick 2.2
import Sailfish.Silica 1.0
import QtPositioning 5.2
import "../components"
import "../components/Util.js" as Util

// mode: "nearby" (offline caches around you), "list" (a saved list), "search"
// search: searchKind 0 = cache (name / GC code), 1 = place (city, address -> jump on the map)
Page {
    id: page
    allowedOrientations: Orientation.All

    property string mode: "nearby"
    property string title: qsTr("Nearby")
    property int listId: -1
    property int searchKind: 0
    property string query: ""
    property var rows: []
    property var places: []
    property real radiusKm: 10
    property bool usingFallbackPosition: false
    property string pendingGeocode: ""

    readonly property bool placeMode: mode === "search" && searchKind === 1

    function looksLikeCode(text) {
        return /^GC[0-9A-Za-z]{1,7}$/.test(text.trim())
    }

    function origin() {
        if (pos.position.coordinate.isValid) {
            usingFallbackPosition = false
            return [pos.position.coordinate.latitude, pos.position.coordinate.longitude]
        }
        usingFallbackPosition = true
        return [Backend.settings.last_lat, Backend.settings.last_lon]
    }

    function reload() {
        if (!Backend.ready) return
        if (mode === "nearby") {
            var o = origin()
            Backend.call("nearby", [o[0], o[1], radiusKm, Backend.baseFilter(), 200], function(r) { page.rows = r })
        } else if (mode === "list") {
            Backend.call("list_caches", [listId], function(r) { page.rows = r })
        } else if (!placeMode) {
            if (query.length >= 2) Backend.call("search_text", [query], function(r) { page.rows = r })
            else rows = []
        }
    }

    function requireLogin() {
        banner.show(qsTr("Sign in to search on geocaching.com."))
        pageStack.push(Qt.resolvedUrl("LoginPage.qml"))
    }

    function loadOnline() {
        if (!Backend.loggedIn) { requireLogin(); return }
        var o = origin()
        Backend.startBusy(qsTr("Searching on geocaching.com…"))
        Backend.call("search_online_nearby", [o[0], o[1], radiusKm, Backend.baseFilter(), 0])
    }

    // Enter in the search field
    function runSearch() {
        if (query.length < 2) return
        if (placeMode) {
            Backend.startBusy(qsTr("Searching for the place…"))
            Backend.call("geocode", [query])
        } else if (looksLikeCode(query)) {
            var code = query.trim().toUpperCase()
            for (var i = 0; i < rows.length; i++) {
                if (rows[i].geocode === code) {          // already stored: open it
                    pageStack.push(Qt.resolvedUrl("CachePage.qml"), { geocode: code })
                    return
                }
            }
            if (!Backend.loggedIn) { requireLogin(); return }
            pendingGeocode = code
            Backend.startBusy(qsTr("Downloading %1…").arg(code))
            Backend.call("load_cache_online", [code])
        } else {
            if (!Backend.loggedIn) { requireLogin(); return }
            var o = origin()
            Backend.startBusy(qsTr("Searching on geocaching.com…"))
            Backend.call("search_online_name", [query, o[0], o[1], Backend.baseFilter()])
        }
    }

    function addToList(geocode) {
        var picker = pageStack.push(Qt.resolvedUrl("ListPickerPage.qml"))
        picker.picked.connect(function(id) {
            Backend.call("add_to_list", [id, [geocode]], function() { Backend.dataVersion++ })
        })
    }

    function showPlace(place) {
        Backend.showOnMap(place.lat, place.lon, 13)
        pageStack.pop(null)       // back to the map
    }

    Component.onCompleted: reload()

    Connections {
        target: Backend
        onReadyChanged: page.reload()
        onDataVersionChanged: if (page.mode !== "search") page.reload()
        onOnlineSearchDone: {
            if (result.error) {
                banner.show(qsTr("Search failed: %1").arg(Util.statusText(result.error)) + (result.detail ? " [" + result.detail + "]" : ""))
            } else if (result.kind === "name" && page.mode === "search") {
                page.rows = result.results
                banner.show(result.count === 0
                            ? qsTr("Nothing found. The search matches whole words in the cache name.")
                            : qsTr("Found %1 caches, nearest first.").arg(result.count))
            }
        }
        onCacheLoaded: {
            if (page.pendingGeocode === "" || result.geocode !== page.pendingGeocode) return
            page.pendingGeocode = ""
            if (result.status === "no_error" || result.status === "premium_only")
                pageStack.push(Qt.resolvedUrl("CachePage.qml"), { geocode: result.geocode })
            else
                banner.show(Util.statusText(result.status))
        }
        onGeocodeDone: {
            page.places = result.places
            if (result.places.length === 0) banner.show(qsTr("Place not found."))
        }
        onErrorOccurred: banner.show(qsTr("Error (%1): %2").arg(event).arg(message))
    }

    PositionSource {
        id: pos
        active: page.mode === "nearby" || (page.mode === "search" && !page.placeMode)
        updateInterval: 5000
        property bool first: true
        onPositionChanged: {
            if (first && position.coordinate.isValid) {
                first = false
                if (page.mode === "nearby") page.reload()
            }
        }
    }

    Component {
        id: cacheDelegate
        ListItem {
            id: item
            width: view.width
            contentHeight: Theme.itemSizeMedium

            menu: ContextMenu {
                MenuItem {
                    text: qsTr("Add to list")
                    onClicked: page.addToList(modelData.geocode)
                }
                MenuItem {
                    visible: page.mode === "list"
                    text: qsTr("Remove from list")
                    onClicked: item.remorseAction(qsTr("Removing"), function() {
                        Backend.call("remove_from_list", [page.listId, [modelData.geocode]], function() { Backend.dataVersion++ })
                    })
                }
                MenuItem {
                    text: qsTr("Delete from phone")
                    onClicked: item.remorseAction(qsTr("Deleting"), function() {
                        Backend.call("delete_caches", [[modelData.geocode]], function() { Backend.dataVersion++ })
                    })
                }
            }

            onClicked: pageStack.push(Qt.resolvedUrl("CachePage.qml"), { geocode: modelData.geocode })

            CacheBadge {
                id: badge
                anchors { left: parent.left; leftMargin: Theme.horizontalPageMargin; verticalCenter: parent.verticalCenter }
                typeId: modelData.type_id
                found: modelData.found === 1 || modelData.found === true
                disabled: modelData.disabled === 1 || modelData.disabled === true
            }

            Column {
                anchors {
                    left: badge.right; leftMargin: Theme.paddingMedium
                    right: distanceLabel.left; rightMargin: Theme.paddingSmall
                    verticalCenter: parent.verticalCenter
                }
                Label {
                    width: parent.width
                    text: modelData.name
                    color: item.highlighted ? Theme.highlightColor : Theme.primaryColor
                    truncationMode: TruncationMode.Fade
                    font.strikeout: modelData.archived === 1 || modelData.archived === true
                }
                Label {
                    width: parent.width
                    text: modelData.geocode + " · D" + Util.formatRating(modelData.difficulty) +
                          "/T" + Util.formatRating(modelData.terrain) + " · " + Util.sizeName(modelData.size_id)
                    color: item.highlighted ? Theme.secondaryHighlightColor : Theme.secondaryColor
                    font.pixelSize: Theme.fontSizeExtraSmall
                    truncationMode: TruncationMode.Fade
                }
            }

            Label {
                id: distanceLabel
                anchors { right: parent.right; rightMargin: Theme.horizontalPageMargin; verticalCenter: parent.verticalCenter }
                visible: modelData.distance_km !== undefined
                text: visible ? Util.formatDistance(modelData.distance_km * 1000, Backend.imperial) : ""
                color: Theme.highlightColor
                font.pixelSize: Theme.fontSizeSmall
            }
        }
    }

    Component {
        id: placeDelegate
        BackgroundItem {
            width: view.width
            height: placeLabel.height + 2 * Theme.paddingMedium
            onClicked: page.showPlace(modelData)

            Label {
                id: placeLabel
                anchors {
                    left: parent.left; right: parent.right; leftMargin: Theme.horizontalPageMargin
                    rightMargin: Theme.horizontalPageMargin; verticalCenter: parent.verticalCenter
                }
                text: modelData.name
                wrapMode: Text.Wrap
                maximumLineCount: 3
                color: highlighted ? Theme.highlightColor : Theme.primaryColor
            }
        }
    }

    SilicaListView {
        id: view
        anchors.fill: parent
        model: page.placeMode ? page.places : page.rows
        delegate: page.placeMode ? placeDelegate : cacheDelegate

        header: Column {
            width: view.width

            PageHeader {
                title: page.title
                description: page.mode === "nearby"
                    ? qsTr("within %1").arg(Util.formatDistance(page.radiusKm * 1000, Backend.imperial)) +
                      (page.usingFallbackPosition ? qsTr(" (position from the map)") : "")
                    : (page.placeMode ? qsTr("%1 places").arg(page.places.length) : qsTr("%1 caches").arg(page.rows.length))
            }

            ComboBox {
                visible: page.mode === "search"
                width: parent.width
                label: qsTr("Search")
                currentIndex: page.searchKind
                menu: ContextMenu {
                    MenuItem { text: qsTr("Cache (name or GC code)") }
                    MenuItem { text: qsTr("Place (city, address)") }
                }
                onCurrentIndexChanged: {
                    page.searchKind = currentIndex
                    page.reload()
                }
            }

            SearchField {
                visible: page.mode === "search"
                width: parent.width
                placeholderText: page.placeMode ? qsTr("Prague, London, an address…") : qsTr("Name or GC code…")
                EnterKey.iconSource: "image://theme/icon-m-enter-accept"
                EnterKey.onClicked: {
                    page.query = text.trim()
                    page.runSearch()
                    focus = false
                }
                onTextChanged: {
                    page.query = text.trim()
                    if (!page.placeMode) searchTimer.restart()
                }
            }

            Label {
                visible: page.mode === "search"
                x: Theme.horizontalPageMargin
                width: parent.width - 2 * Theme.horizontalPageMargin
                wrapMode: Text.Wrap
                font.pixelSize: Theme.fontSizeExtraSmall
                color: Theme.secondaryColor
                text: page.placeMode
                      ? qsTr("Confirm with Enter. The selected place is shown on the map and (when signed in) caches are downloaded from geocaching.com.")
                      : qsTr("While typing, stored caches are searched. Enter: a GC code is downloaded, otherwise whole words in cache names are searched on geocaching.com (nearest first).")
            }
        }

        PullDownMenu {
            MenuItem {
                visible: page.mode === "nearby"
                text: qsTr("Radius: %1 (change)").arg(Util.formatDistance(page.radiusKm * 1000, Backend.imperial))
                onClicked: {
                    var steps = [5, 10, 25, 50]
                    page.radiusKm = steps[(steps.indexOf(page.radiusKm) + 1) % steps.length]
                    page.reload()
                }
            }
            MenuItem {
                visible: page.mode === "nearby"
                text: qsTr("Load from geocaching.com")
                onClicked: page.loadOnline()
            }
            MenuItem {
                visible: !page.placeMode
                text: qsTr("Refresh")
                onClicked: page.reload()
            }
        }

        ViewPlaceholder {
            enabled: !Backend.busy && (page.placeMode ? page.places.length === 0 : page.rows.length === 0)
            text: page.mode === "search" ? qsTr("Enter a search text") : qsTr("No caches")
            hintText: page.mode === "nearby" ? qsTr("Pull down the menu → Load from geocaching.com, or import a GPX file") : ""
        }

        VerticalScrollDecorator {}
    }

    Timer {
        id: searchTimer
        interval: 350
        onTriggered: page.reload()
    }

    BusyBar {
        running: Backend.busy
        text: Backend.busyText
    }

    StatusBanner { id: banner }
}
