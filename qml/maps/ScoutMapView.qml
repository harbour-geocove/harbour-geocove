
import QtQuick 2.2
import Sailfish.Silica 1.0
import QtPositioning 5.2
import MapboxMap 1.0
import "../components"
import "../components/Util.js" as Util

// Vector map from OSM Scout Server through MapboxMap.
// Marker sizes are matched to CacheBadge.qml and ClusterBadge.qml.

MapboxMap {
    id: root

    property var userCoordinate: QtPositioning.coordinate()
    property var items: []
    property bool layersReady: false
    property bool programmatic: false
    // Item pixels per css pixel: the world is 512 * 2^zoom css pixels wide, the map draws css pixels
    // pixelRatio times larger (see the badge sizes below). The correction is a setting, 1.0 = automatic.
    property real scaleFactor: pixelRatio * Backend.settings.scout_scale

    readonly property string textFont: Backend.settings.scout_text_font

    // Match the QML badge dimensions.
    readonly property real cacheBadgeSize:
        Theme.itemSizeExtraSmall * 0.75 / Theme.pixelRatio * 0.85

    readonly property real cacheBadgeRadius:
        cacheBadgeSize / 2

    readonly property real clusterBadgeBaseSize:
        Theme.itemSizeExtraSmall / Theme.pixelRatio * 0.85

    property string desiredStyleUrl:
        Util.scoutStyleUrl(
            Backend.settings.osmscout_style_url,
            Backend.scoutDark
        )

    property string appliedStyleUrl: ""

    readonly property string info:
        "OSM Scout Server (MapboxMap, native layers)" +
        "\nlayers: " + (layersReady ? "ready" : "waiting") +
        ", " + items.length + " items" +
        "\nfont: " + textFont +
        "\nm/px module " +
        (typeof metersPerPixel === "number"
            ? metersPerPixel.toFixed(2) : "?") +
        " own " + ownMetersPerPixel().toFixed(2)

    signal viewChanged()
    signal userMoved()
    signal markerClicked(string geocode)
    signal clusterClicked(real lat, real lon)

    function ownMetersPerPixel() {
        return 40075016.686 *
            Math.cos(center.latitude * Math.PI / 180) /
            (512 * Math.pow(2, zoomLevel) * scaleFactor)
    }

    function jumpTo(coordinate, zoom) {
        programmatic = true

        if (zoom > 0)
            zoomLevel = zoom

        setCenter(coordinate)
        releaseTimer.restart()
    }

    function bounds() {
        var corners = [
            [0, 0],
            [width, 0],
            [0, height],
            [width, height]
        ]

        var latMin = 90
        var latMax = -90
        var lonMin = 180
        var lonMax = -180

        for (var i = 0; i < corners.length; i++) {
            var c = Util.unprojectFromPixel(
                corners[i][0],
                corners[i][1],
                center.latitude,
                center.longitude,
                zoomLevel,
                scaleFactor,
                width,
                height
            )

            latMin = Math.min(latMin, c.lat)
            latMax = Math.max(latMax, c.lat)
            lonMin = Math.min(lonMin, c.lon)
            lonMax = Math.max(lonMax, c.lon)
        }

        var padLat = (latMax - latMin) * 0.05
        var padLon = (lonMax - lonMin) * 0.05

        return [
            Math.max(-85, latMin - padLat),
            lonMin - padLon,
            Math.min(85, latMax + padLat),
            lonMax + padLon
        ]
    }

    function emptyCollection() {
        return {
            "type": "geojson",
            "data": {
                "type": "FeatureCollection",
                "features": []
            }
        }
    }

    function initLayers() {
        if (layersReady)
            return

        addSource("caches", emptyCollection())
        addSource("clusters", emptyCollection())
        addSource("me", emptyCollection())

        // Cache circles: match CacheBadge.qml diameter.
        addLayer("caches-circle", {
            "type": "circle",
            "source": "caches",
            "paint": {
                "circle-radius": root.cacheBadgeRadius,
                "circle-color": ["get", "color"],
                "circle-opacity": ["get", "op"],
                "circle-stroke-width": 2,
                "circle-stroke-color": "#ffffff",
                "circle-stroke-opacity": ["get", "op"]
            }
        }, "")

        // Cache symbol or found check mark.
        addLayer("caches-label", {
            "type": "symbol",
            "source": "caches",
            "layout": {
                "text-field": ["get", "sym"],
                "text-font": [textFont],
                "text-size": root.cacheBadgeSize * 0.5,
                "text-allow-overlap": true,
                "text-ignore-placement": true
            },
            "paint": {
                "text-color": "#ffffff",
                "text-opacity": ["get", "op"]
            }
        }, "")

        // Cluster circles use the radius calculated in pushData().
        addLayer("clusters-circle", {
            "type": "circle",
            "source": "clusters",
            "paint": {
                "circle-radius": ["get", "r"],
                "circle-color": "#2c6fbb",
                "circle-opacity": 0.9,
                "circle-stroke-width": 2,
                "circle-stroke-color": "#ffffff"
            }
        }, "")

        // Cluster count.
        addLayer("clusters-label", {
            "type": "symbol",
            "source": "clusters",
            "layout": {
                "text-field": ["get", "label"],
                "text-font": [textFont],
                "text-size": Theme.fontSizeExtraSmall,
                "text-allow-overlap": true,
                "text-ignore-placement": true
            },
            "paint": {
                "text-color": "#ffffff"
            }
        }, "")

        // Current user location.
        addLayer("me-circle", {
            "type": "circle",
            "source": "me",
            "paint": {
                "circle-radius": 8,
                "circle-color": "#1e88e5",
                "circle-stroke-width": 3,
                "circle-stroke-color": "#ffffff"
            }
        }, "")

        layersReady = true
        pushData()
        updateMe()
    }

    // Recreate layers after a style change.
    function rebuildLayers() {
        var layers = [
            "me-circle",
            "clusters-label",
            "clusters-circle",
            "caches-label",
            "caches-circle"
        ]

        var sources = ["me", "clusters", "caches"]

        for (var i = 0; i < layers.length; i++) {
            try {
                removeLayer(layers[i])
            } catch (e) {
            }
        }

        for (var j = 0; j < sources.length; j++) {
            try {
                removeSource(sources[j])
            } catch (e) {
            }
        }

        layersReady = false
        initLayers()
    }

    function restyle() {
        if (!layersReady)
            return

        restyleTimer.attempts = 0
        restyleTimer.restart()
    }

    function setData(newItems) {
        items = newItems
        pushData()
    }

    function pushData() {
        if (!layersReady)
            return

        // Use the existing Util.js unchanged.
        var f = Util.scoutFeatures(items)

        // Recalculate cluster radii locally for this map only.
        // The formula matches ClusterBadge.qml.
        for (var i = 0; i < f.clusters.length; i++) {
            var props = f.clusters[i].properties
            var count = Math.max(Number(props.n) || 1, 1)

            var diameter = root.clusterBadgeBaseSize * (
                0.9 + Math.min(
                    0.9,
                    Math.log(count) / Math.LN10 * 0.4
                )
            )

            props.r = diameter / 2
        }

        updateSource("caches", {
            "type": "geojson",
            "data": {
                "type": "FeatureCollection",
                "features": f.caches
            }
        })

        updateSource("clusters", {
            "type": "geojson",
            "data": {
                "type": "FeatureCollection",
                "features": f.clusters
            }
        })
    }

    function updateMe() {
        if (!layersReady)
            return

        var features = []

        if (userCoordinate.isValid) {
            features.push({
                "type": "Feature",
                "properties": {},
                "geometry": {
                    "type": "Point",
                    "coordinates": [
                        userCoordinate.longitude,
                        userCoordinate.latitude
                    ]
                }
            })
        }

        updateSource("me", {
            "type": "geojson",
            "data": {
                "type": "FeatureCollection",
                "features": features
            }
        })
    }

    // Find the nearest cache or cluster within about 30 CSS pixels.
    function handleTap(coord) {
        var mpp = 78271.5 *
            Math.cos(coord.latitude * Math.PI / 180) /
            Math.pow(2, zoomLevel)

        var best = null
        var bestDistance = 30 * mpp

        for (var i = 0; i < items.length; i++) {
            var r = items[i]

            if (r.lat === null || r.lat === undefined)
                continue

            var d = Util.distanceMeters(
                coord.latitude,
                coord.longitude,
                r.lat,
                r.lon
            )

            if (d < bestDistance) {
                best = r
                bestDistance = d
            }
        }

        if (!best)
            return

        if (best.cluster === true)
            clusterClicked(best.lat, best.lon)
        else
            markerClicked(best.geocode)
    }

    anchors.fill: parent
    zoomLevel: 12
    pixelRatio: Theme.pixelRatio
    styleUrl: appliedStyleUrl

    MapboxMapGestureArea {
        map: root
        activeClickedGeo: true
        onClickedGeo: root.handleTap(geocoordinate)
    }

    Component.onCompleted: {
        appliedStyleUrl = desiredStyleUrl
        initTimer.start()
    }

    onDesiredStyleUrlChanged: styleDebounce.restart()
    onStyleUrlChanged: restyle()
    onUserCoordinateChanged: updateMe()

    onCenterChanged: {
        viewChanged()
        if (!programmatic)
            userMoved()
    }

    onZoomLevelChanged: viewChanged()

    Timer {
        id: initTimer
        interval: 800

        onTriggered: {
            root.initLayers()
            restyleTimer.attempts = 0
            restyleTimer.restart()
        }
    }

    Timer {
        id: restyleTimer
        property int attempts: 0

        interval: 1200
        repeat: true

        onTriggered: {
            root.rebuildLayers()

            if (++attempts >= 2)
                stop()
        }
    }

    Timer {
        id: styleDebounce
        interval: 1500

        onTriggered: {
            if (root.desiredStyleUrl !== root.appliedStyleUrl)
                root.appliedStyleUrl = root.desiredStyleUrl
        }
    }

    Timer {
        id: releaseTimer
        interval: 600

        onTriggered: root.programmatic = false
    }
}
