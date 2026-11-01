import QtQuick 2.2
import Sailfish.Silica 1.0
import QtLocation 5.0
import QtPositioning 5.2
import "../components"

// OpenStreetMap tiles through Qt Location.
//
// Both map views (this one and ScoutMapView.qml) have the same interface, MapPage only uses that:
//   set from outside: userCoordinate; setData(items) hands over what is shown (caches and clusters)
//   signals:          viewChanged(), userMoved(), markerClicked(geocode), clusterClicked(lat, lon)
//   functions:        jumpTo(coordinate, zoom), bounds() -> [latMin, lonMin, latMax, lonMax] or null
//   properties:       zoomLevel, center, info (text for the debug line), projectionAvailable
Map {
    id: root

    property var userCoordinate: QtPositioning.coordinate()
    readonly property string info: "Qt Location (osm), " + supportedMapTypes.length + " map types"
    readonly property bool projectionAvailable: true

    signal viewChanged()
    signal userMoved()
    signal markerClicked(string geocode)
    signal clusterClicked(real lat, real lon)

    // ListModel roles must have stable types: sanitize everything coming from Python
    function setData(items) {
        cacheModel.clear()
        clusterModel.clear()
        for (var i = 0; i < items.length; i++) {
            var r = items[i]
            if (r.lat === null || r.lat === undefined || r.lon === null || r.lon === undefined) continue
            if (r.cluster === true) {
                clusterModel.append({ lat: r.lat, lon: r.lon, n: r.n })
            } else {
                cacheModel.append({
                    geocode: r.geocode || "", type_id: r.type_id || "unknown", lat: r.lat, lon: r.lon,
                    isFound: r.found === 1 || r.found === true,
                    isDisabled: r.disabled === 1 || r.disabled === true
                })
            }
        }
    }

    function jumpTo(coordinate, zoom) {
        if (zoom > 0) zoomLevel = zoom
        center = coordinate
    }

    // all four corners: also correct when the map is rotated
    function bounds() {
        var c = [toCoordinate(Qt.point(0, 0)), toCoordinate(Qt.point(width, 0)),
                 toCoordinate(Qt.point(0, height)), toCoordinate(Qt.point(width, height))]
        var latMin = 90, latMax = -90, lonMin = 180, lonMax = -180
        for (var i = 0; i < c.length; i++) {
            if (!c[i].isValid) return null
            latMin = Math.min(latMin, c[i].latitude)
            latMax = Math.max(latMax, c[i].latitude)
            lonMin = Math.min(lonMin, c[i].longitude)
            lonMax = Math.max(lonMax, c[i].longitude)
        }
        return [latMin, lonMin, latMax, lonMax]
    }

    anchors.fill: parent
    plugin: Plugin {
        name: "osm"
        PluginParameter { name: "osm.useragent"; value: "harbour-geocache/" + Backend.version }
        // custom tile server (the parameter name differs between Qt versions, both are set)
        PluginParameter { name: "osm.mapping.host"; value: Backend.tileServer }
        PluginParameter { name: "osm.mapping.custom.host"; value: Backend.tileServer }
        PluginParameter { name: "osm.mapping.providersrepository.disabled"; value: true }
    }
    center: QtPositioning.coordinate(50.2092, 15.8328)
    zoomLevel: 12
    gesture.enabled: true

    onCenterChanged: viewChanged()
    onZoomLevelChanged: viewChanged()
    onWidthChanged: viewChanged()
    onHeightChanged: viewChanged()

    Connections {
        target: root.gesture
        onPanActiveChanged: if (root.gesture.panActive) root.userMoved()
    }

    ListModel { id: cacheModel }
    ListModel { id: clusterModel }

    MapItemView {
        model: cacheModel
        delegate: MapQuickItem {
            coordinate: QtPositioning.coordinate(model.lat, model.lon)
            anchorPoint.x: sourceItem.width / 2
            anchorPoint.y: sourceItem.height / 2
            sourceItem: CacheBadge {
                typeId: model.type_id
                found: model.isFound
                disabled: model.isDisabled
                MouseArea {
                    anchors.fill: parent
                    anchors.margins: -Theme.paddingSmall
                    onClicked: root.markerClicked(model.geocode)
                }
            }
        }
    }

    MapItemView {
        model: clusterModel
        delegate: MapQuickItem {
            coordinate: QtPositioning.coordinate(model.lat, model.lon)
            anchorPoint.x: sourceItem.width / 2
            anchorPoint.y: sourceItem.height / 2
            sourceItem: ClusterBadge {
                count: model.n
                MouseArea {
                    anchors.fill: parent
                    anchors.margins: -Theme.paddingSmall
                    onClicked: root.clusterClicked(model.lat, model.lon)
                }
            }
        }
    }

    MapQuickItem {
        visible: root.userCoordinate.isValid
        coordinate: root.userCoordinate
        anchorPoint.x: sourceItem.width / 2
        anchorPoint.y: sourceItem.height / 2
        sourceItem: Rectangle {
            width: Theme.paddingLarge * 1.2
            height: width
            radius: width / 2
            color: "#1e88e5"
            border.width: 3
            border.color: "white"
        }
    }
}
