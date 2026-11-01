pragma Singleton
import QtQuick 2.0
import io.thp.pyotherside 1.5
import Nemo.Configuration 1.0
import Sailfish.Silica 1.0
import "Util.js" as Util

// Single access point to the Python side (python/gcconnector/bridge.py).
// Synchronous bridge functions: Backend.call("name", [args], function(result) {...})
// Network functions return at once and report through the signals below.
Item {
    id: backend

    readonly property string version: "0.8.6"
    // Settings in dconf (Nemo.Configuration): the session cookie, the nickname and the style of the OSM Scout map.
    // The path is the one Sailjail allows: /<OrganizationName>/<ApplicationName> from the .desktop file.
    readonly property string configPath: "/apps/harbour-geocove"
    ConfigurationValue { id: cookieStore; key: backend.configPath + "/gspkauth"; defaultValue: "" }
    ConfigurationValue { id: userStore; key: backend.configPath + "/user"; defaultValue: "" }
    ConfigurationValue { id: styleStore; key: backend.configPath + "/scoutStyle"; defaultValue: "auto" }

    // "light" | "dark" | "auto" (follows the ambience)
    property string scoutStyle: styleStore.value
    readonly property bool scoutDark: scoutStyle === "dark" ||
                                      (scoutStyle === "auto" && Theme.colorScheme === Theme.LightOnDark)

    function setScoutStyle(style) {
        styleStore.value = style
    }

    property bool ready: false
    property bool busy: false
    property string busyText: ""

    property bool loggedIn: false
    property string userName: ""
    property string memberType: ""
    property string loginMessage: ""
    property string loginDebug: ""
    property string testReport: ""
    property string scoutError: ""          // why the OSM Scout Server map could not be used
    property bool sessionExpired: false     // a saved session was rejected by geocaching.com

    property var settings: ({
        imperial: false, hide_found: false, hide_disabled: false, hide_archived: true,
        last_lat: 50.0878, last_lon: 14.4426, last_zoom: 12, debug_map: false, buttons_left: false,
        tile_server: "https://tile.openstreetmap.org/",
        readable_listings: true,
        description_images: "fit",
        map_types: ["traditional", "multi", "mystery", "letterbox", "earth", "virtual", "webcam", "wherigo", "events", "cito", "other"],
        map_source: "osm",
        osmscout_style_url: "http://localhost:8553/v1/mbgl/style?style=osmbright",
        scout_scale: 1.0,
        scout_text_font: "Noto Sans Regular"
    })
    property bool imperial: settings.imperial === true
    property string tileServer: settings.tile_server
    property string documentsDir: ""

    // bumped whenever the database changed; pages reload their data on it
    property int dataVersion: 0

    signal loginFinished(var result)
    signal onlineSearchDone(var result)
    signal cacheLoaded(var result)
    signal gpxImported(var result)
    signal geocodeDone(var result)
    signal galleryLoaded(var result)
    signal showOnMap(real lat, real lon, int zoom)   // pages ask the map to jump somewhere
    signal errorOccurred(string event, string message)

    function touch() { return ready }

    function call(fn, args, callback) {
        py.call("gcconnector.bridge." + fn, args || [], callback || function() {})
    }

    function startBusy(text) {
        busyText = text
        busy = true
    }

    function setSetting(key, value) {
        var copy = {}
        for (var k in settings) copy[k] = settings[k]
        copy[key] = value
        settings = copy
        call("set_setting", [key, value])
    }

    // the type filter of the map is active when some group of cache types is switched off
    property bool typeFilterActive: settings.map_types !== undefined && settings.map_types.length < Util.typeGroups().length

    // found / disabled / archived: used for lists and for downloads from geocaching.com
    function baseFilter() {
        return {
            hide_found: settings.hide_found === true,
            hide_disabled: settings.hide_disabled === true,
            hide_archived: settings.hide_archived !== false
        }
    }

    // what the map shows: the base filter plus the selected cache types
    function mapFilter() {
        var f = baseFilter()
        if (typeFilterActive) f.types = Util.typesForGroups(settings.map_types)
        return f
    }

    function login(user, password) {
        loginMessage = ""
        loginDebug = ""
        startBusy(qsTr("Signing in…"))
        call("login", [user, password])
    }

    // finish a login done in the embedded web view (cookieString = document.cookie of the page)
    function webviewLogin(cookieString, note) {
        loginMessage = ""
        loginDebug = ""
        startBusy(qsTr("Finishing login…"))
        call("login_webview", [cookieString || "", note || ""])
    }

    function runConnectionTest() {
        testReport = ""
        startBusy(qsTr("Testing the connection…"))
        call("connection_test", [])
    }

    function loginWithCookie(cookie) {
        loginMessage = ""
        startBusy(qsTr("Signing in…"))
        call("login_cookie", [cookie])
    }

    function logout() {
        call("logout", [], function() {
            loggedIn = false
            userName = ""
            memberType = ""
        })
    }

    // keeps the session alive (the site renews the cookie on use) and notices when it expired
    Timer {
        interval: 600000
        repeat: true
        running: backend.loggedIn
        onTriggered: backend.call("session_check", [])
    }

    Python {
        id: py

        Component.onCompleted: {
            addImportPath(Qt.resolvedUrl("../../python"))

            setHandler("login", function(r) {
                backend.busy = false
                backend.loggedIn = (r.ok === true)
                if (r.ok) backend.sessionExpired = false
                else if (r.restored === true && r.status === "wrong_login_data") backend.sessionExpired = true
                if (r.ok) {
                    backend.userName = r.user || ""
                    backend.memberType = r.member_type || ""
                    backend.loginMessage = ""
                    backend.loginDebug = ""
                } else {
                    backend.loginDebug = r.debug || ""
                    backend.loginMessage = Util.statusText(r.status) + (r.error ? " (" + r.error + ")" : "")
                }
                backend.loginFinished(r)
            })
            setHandler("online_search", function(r) {
                backend.busy = false
                backend.dataVersion++
                backend.onlineSearchDone(r)
            })
            setHandler("cache_loaded", function(r) {
                backend.busy = false
                backend.dataVersion++
                backend.cacheLoaded(r)
            })
            setHandler("session_cookie", function(r) {
                // published by the Python side when a login succeeded or the server renewed the cookie
                cookieStore.value = r.cookie
                userStore.value = r.user
            })
            setHandler("session_check", function(r) {
                if (r.state === "expired") {
                    backend.loggedIn = false
                    backend.sessionExpired = true
                }
            })
            setHandler("connection_test", function(r) {
                backend.busy = false
                backend.testReport = r.report
            })
            setHandler("gallery", function(r) {
                backend.galleryLoaded(r)
            })
            setHandler("geocode", function(r) {
                backend.busy = false
                backend.geocodeDone(r)
            })
            setHandler("gpx_imported", function(r) {
                backend.busy = false
                backend.dataVersion++
                backend.gpxImported(r)
            })
            setHandler("progress", function(what, value) {
                if (what === "gpx") backend.busyText = qsTr("Importing… %1 caches").arg(value)
                else if (what === "logs") backend.busyText = qsTr("Downloading logs…")
                else if (value === "logs") backend.busyText = qsTr("Downloading logs…")
                else if (value === "waypoints") backend.busyText = qsTr("Processing waypoints…")
            })
            setHandler("error", function(event, message) {
                backend.busy = false
                backend.errorOccurred(event, message)
            })

            importModule("gcconnector.bridge", function() {
                call("gcconnector.bridge.init", [""], function(r) {
                    backend.settings = r.settings
                    backend.documentsDir = r.documents_dir
                    backend.ready = true
                    if (cookieStore.value !== "")
                        call("gcconnector.bridge.restore_login", [String(cookieStore.value), String(userStore.value)])
                    else if (r.has_saved_login)
                        call("gcconnector.bridge.restore_login", [])      // auth.json of an older version: moved to dconf
                })
            })
        }

        onError: {
            console.log("Python error: " + traceback)
            // show the last lines of the traceback instead of failing silently
            backend.busy = false
            backend.errorOccurred("python", String(traceback).split("\n").slice(-4).join(" ").substring(0, 400))
        }
    }
}
