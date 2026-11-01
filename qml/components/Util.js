// Not a ".pragma library": qsTr() needs the QML context so that these texts can be translated.
// The tables are built on first use.

var _types = null
var _sizes = null
var _logTypes = null
var _statuses = null

// [name, map/list symbol, colour] for gcconnector CacheType ids
function typeTable() {
    if (_types === null) {
        _types = {
            traditional: [qsTr("Traditional"), "T", "#2e7d32"],
            multi: [qsTr("Multi"), "M", "#ef6c00"],
            mystery: [qsTr("Mystery"), "?", "#1565c0"],
            letterbox: [qsTr("Letterbox"), "L", "#1565c0"],
            event: [qsTr("Event"), "E", "#c62828"],
            mega: [qsTr("Mega event"), "E", "#c62828"],
            giga: [qsTr("Giga event"), "E", "#c62828"],
            cito: [qsTr("CITO"), "C", "#c62828"],
            communceleb: [qsTr("Community event"), "E", "#c62828"],
            gchqceleb: [qsTr("HQ event"), "E", "#c62828"],
            block: [qsTr("Block Party"), "E", "#c62828"],
            earth: [qsTr("EarthCache"), "Z", "#6d4c41"],
            virtual: [qsTr("Virtual"), "V", "#00838f"],
            webcam: [qsTr("Webcam"), "W", "#00838f"],
            locationless: [qsTr("Locationless"), "R", "#00838f"],
            wherigo: [qsTr("Wherigo"), "G", "#1565c0"],
            ape: [qsTr("Project APE"), "A", "#6a1b9a"],
            gchq: [qsTr("Geocaching HQ"), "H", "#6a1b9a"],
            gps: [qsTr("GPS Adventures"), "X", "#6a1b9a"],
            advlab: [qsTr("Lab"), "L", "#6a1b9a"],
            userdefined: [qsTr("User defined"), "U", "#757575"],
            unknown: [qsTr("Unknown"), "?", "#757575"]
        }
    }
    return _types
}

function sizeTable() {
    if (_sizes === null) {
        _sizes = {
            nano: qsTr("Nano"), micro: qsTr("Micro"), small: qsTr("Small"), regular: qsTr("Regular"),
            large: qsTr("Large"), virtual: qsTr("Virtual"), other: qsTr("Other"), not_chosen: qsTr("Not chosen"),
            unknown: "?"
        }
    }
    return _sizes
}

// keys are the values used by geocaching.com field notes (bridge.log_types())
function logTypeTable() {
    if (_logTypes === null) {
        _logTypes = {
            "Found it": qsTr("Found it"),
            "Didn't find it": qsTr("Didn't find it"),
            "Write note": qsTr("Write note"),
            "Needs Archived": qsTr("Needs archiving"),
            "Needs Maintenance": qsTr("Needs maintenance"),
            "Owner Maintenance": qsTr("Owner maintenance"),
            "Will Attend": qsTr("Will attend"),
            "Attended": qsTr("Attended"),
            "Webcam Photo Taken": qsTr("Webcam photo taken")
        }
    }
    return _logTypes
}

// keys are StatusCode values of the Python side
function statusTable() {
    if (_statuses === null) {
        _statuses = {
            no_error: "",
            wrong_login_data: qsTr("Wrong username or password."),
            login_captcha_error: qsTr("geocaching.com requires a captcha. Use the web view login or the gspkauth cookie (see below)."),
            unvalidated_account: qsTr("The account has not been verified yet."),
            login_parse_error: qsTr("The sign-in page could not be processed."),
            connection_failed_gc: qsTr("Cannot connect to geocaching.com."),
            communication_error: qsTr("Communication error with the server."),
            maintenance: qsTr("geocaching.com is down for maintenance."),
            no_login_info_stored: qsTr("Login data is missing."),
            cache_not_found: qsTr("Cache not found."),
            unpublished_cache: qsTr("The cache has not been published yet."),
            premium_only: qsTr("Premium cache: details are not available."),
            unknown_error: qsTr("Unknown error.")
        }
    }
    return _statuses
}

function typeInfo(id) { var t = typeTable(); return t[id] || t.unknown }
function typeName(id) { return typeInfo(id)[0] }
function typeSymbol(id) { return typeInfo(id)[1] }
function typeColor(id) { return typeInfo(id)[2] }
function sizeName(id) { return sizeTable()[id] || "?" }
function logTypeName(t) { return logTypeTable()[t] || t }
function statusText(code) { var s = statusTable(); return s[code] !== undefined ? s[code] : code }

function pad(n, len) {
    var s = "" + n
    while (s.length < len) s = "0" + s
    return s
}

function formatDistance(meters, imperial) {
    if (meters === undefined || meters === null || isNaN(meters) || meters < 0) return "–"
    if (imperial) {
        var ft = meters * 3.28084
        return ft < 1000 ? Math.round(ft) + " ft" : (meters / 1609.344).toFixed(1) + " mi"
    }
    if (meters < 1000) return Math.round(meters) + " m"
    if (meters < 10000) return (meters / 1000).toFixed(1) + " km"
    return Math.round(meters / 1000) + " km"
}

function coordPart(value, positive, negative, degDigits) {
    var hemi = value >= 0 ? positive : negative
    var v = Math.abs(value)
    var deg = Math.floor(v)
    var min = (v - deg) * 60
    var minText = min.toFixed(3)
    if (min < 10) minText = "0" + minText
    return hemi + " " + pad(deg, degDigits) + "° " + minText
}

// RFC 5870 geo URI ("geo:50.123456,15.123456"), decimal point regardless of the phone's locale
function geoUrl(lat, lon) {
    return "geo:" + lat.toFixed(6) + "," + lon.toFixed(6)
}

// "N 50° 12.345 E 015° 49.500"
function formatCoord(lat, lon) {
    if (lat === null || lat === undefined || lon === null || lon === undefined) return "–"
    return coordPart(lat, "N", "S", 2) + " " + coordPart(lon, "E", "W", 3)
}

// "2026-10-05T14:30:00Z" -> "5. 10. 2026"
function formatDate(iso) {
    if (!iso || iso.length < 10) return ""
    var p = iso.substr(0, 10).split("-")
    return parseInt(p[2], 10) + ". " + parseInt(p[1], 10) + ". " + p[0]
}

function formatRating(v) { return "" + (Math.round(v * 2) / 2) }

// attributes are "dogs_yes" / "gcattr8_no" style tokens
function attributeText(list) {
    if (!list || list.length === 0) return ""
    var out = []
    for (var i = 0; i < list.length; i++) {
        var a = list[i]
        var no = a.length > 3 && a.substr(a.length - 3) === "_no"
        var base = a.replace(/_(yes|no)$/, "").replace(/^gcattr/, "#").replace(/_/g, " ")
        out.push((no ? "✗ " : "") + base)
    }
    return out.join(", ")
}

function stripHtml(text) {
    return (text || "").replace(/<[^>]*>/g, " ").replace(/\s+/g, " ").trim()
}


// ---- cache descriptions: keep wide content (images, tables) inside the screen ---------------
// Qt's rich text shows an <img> in its natural size and never scales it down, so the HTML is
// rewritten first. ES5 only (the QML engine on the phone is old).

function attrValue(attrs, name) {
    var m = new RegExp("\\s" + name + "\\s*=\\s*(?:\"([^\"]*)\"|'([^']*)'|([^\\s>]+))", "i").exec(" " + attrs)
    if (!m) return null
    return m[1] !== undefined ? m[1] : (m[2] !== undefined ? m[2] : m[3])
}

function stripAttrs(attrs, names) {
    for (var i = 0; i < names.length; i++) {
        var re = new RegExp("\\s" + names[i] + "\\s*=\\s*(\"[^\"]*\"|'[^']*'|[^\\s>]+)", "gi")
        attrs = attrs.replace(re, "")
    }
    return attrs
}

// mode: "fit" (scale images to the width), "links" (images become tappable links), "none" (hidden)
function fitHtml(html, maxWidth, mode) {
    if (!html) return ""
    var w = Math.max(60, Math.floor(maxWidth || 0))
    mode = mode || "fit"

    // Text that cannot wrap goes past the edge of the screen: <nobr>, nowrap and <pre> (rich text does not wrap
    // preformatted text). <pre> becomes a block with explicit line breaks and kept spaces that does wrap.
    html = html.replace(/<\/?nobr\b[^>]*>/gi, "")
    html = html.replace(/<([a-zA-Z][a-zA-Z0-9]*)\b([^>]*)>/g, function(m, tag, attrs) {
        var a = attrs.replace(/\snowrap(?:\s*=\s*(?:"[^"]*"|'[^']*'|[^\s>]+))?/gi, "")
        return a === attrs ? m : "<" + tag + a + ">"
    })
    html = html.replace(/<pre\b[^>]*>([\s\S]*?)<\/pre>/gi, function(m, content) {
        content = content.replace(/^\r?\n/, "").replace(/\r\n|\r|\n/g, "<br/>").replace(/ {2}/g, " &nbsp;")
        return '<div style="font-family:monospace">' + content + "</div>"
    })

    // fixed pixel widths of tables and cells would push the text out of the screen
    // A fixed height is taken literally by Qt: a listing that is one table with height="2675" overlaps the text after
    // it as soon as its content is taller. Heights are dropped from tables, rows and cells.
    html = html.replace(/<table\b([^>]*)>/gi, function(m, attrs) {
        return "<table" + stripAttrs(attrs, ["width", "height", "style"]) + ' width="100%">'
    })
    html = html.replace(/<(tr|td|th)\b([^>]*)>/gi, function(m, tag, attrs) {
        return "<" + tag + stripAttrs(attrs, ["width", "height", "style"]) + ">"
    })

    return html.replace(/<img\b([^>]*?)\/?>/gi, function(m, attrs) {
        var src = attrValue(attrs, "src")
        if (src === null || mode === "none") return ""
        if (mode === "links") return '<a href="' + src + '">' + qsTr("[image]") + "</a>"

        var alt = attrValue(attrs, "alt")
        var altPart = alt ? ' alt="' + alt + '"' : ""
        var width = attrValue(attrs, "width")
        var height = attrValue(attrs, "height")
        var n = width !== null ? parseInt(width, 10) : NaN
        var target = w                      // size unknown: assume a photo, use the full width
        if (!isNaN(n)) {
            target = /%\s*$/.test(width) ? Math.floor(w * Math.min(n, 100) / 100) : Math.min(n, w)
        } else if (height !== null && parseInt(height, 10) > 0 && parseInt(height, 10) <= 60) {
            // small inline picture (icon, smiley): keep it as it is
            return '<img src="' + src + '" height="' + parseInt(height, 10) + '"' + altPart + ">"
        }
        return '<img src="' + src + '" width="' + Math.max(1, target) + '"' + altPart + ">"
    })
}


// ---- web mercator, for map views that cannot convert coordinates <-> screen themselves ------
// Mapbox GL tiles are 512 css pixels wide at zoom 0: the world is 512 * 2^zoom css pixels wide, and the
// item is `pixelRatio` device pixels per css pixel. The map centre is in the middle of the item.

function mercatorX(lon) {
    return (lon + 180) / 360
}

function mercatorY(lat) {
    var s = Math.sin(lat * Math.PI / 180)
    s = Math.max(-0.9999, Math.min(0.9999, s))
    return 0.5 - Math.log((1 + s) / (1 - s)) / (4 * Math.PI)
}

function projectToPixel(lat, lon, centerLat, centerLon, zoom, pixelRatio, width, height) {
    var world = 512 * Math.pow(2, zoom) * pixelRatio
    return {
        x: width / 2 + (mercatorX(lon) - mercatorX(centerLon)) * world,
        y: height / 2 + (mercatorY(lat) - mercatorY(centerLat)) * world
    }
}

function unprojectFromPixel(x, y, centerLat, centerLon, zoom, pixelRatio, width, height) {
    var world = 512 * Math.pow(2, zoom) * pixelRatio
    var mx = mercatorX(centerLon) + (x - width / 2) / world
    var my = mercatorY(centerLat) + (y - height / 2) / world
    var n = Math.PI - 2 * Math.PI * my
    return {
        lat: 180 / Math.PI * Math.atan(0.5 * (Math.exp(n) - Math.exp(-n))),
        lon: mx * 360 - 180
    }
}


// ---- cache type groups of the map filter ---------------------------------------------------
// Every CacheType id (python/gcconnector/enums.py) belongs to exactly one group (tested in tests/test_util_js.py).

var _groups = null

function typeGroups() {
    if (_groups === null) {
        _groups = [
            { id: "traditional", name: qsTr("Traditional"), types: ["traditional"] },
            { id: "multi", name: qsTr("Multi"), types: ["multi"] },
            { id: "mystery", name: qsTr("Mystery"), types: ["mystery"] },
            { id: "letterbox", name: qsTr("Letterbox"), types: ["letterbox"] },
            { id: "earth", name: qsTr("EarthCache"), types: ["earth"] },
            { id: "virtual", name: qsTr("Virtual"), types: ["virtual"] },
            { id: "webcam", name: qsTr("Webcam"), types: ["webcam"] },
            { id: "wherigo", name: qsTr("Wherigo"), types: ["wherigo"] },
            { id: "events", name: qsTr("Events"),
              types: ["event", "mega", "giga", "communceleb", "gchqceleb", "block", "gps"] },
            { id: "cito", name: qsTr("CITO"), types: ["cito"] },
            { id: "other", name: qsTr("Other"), types: ["locationless", "ape", "gchq", "advlab", "userdefined", "unknown"] }
        ]
    }
    return _groups
}

// flat list of CacheType ids for the enabled group ids
function typesForGroups(enabledIds) {
    var groups = typeGroups(), out = []
    for (var i = 0; i < groups.length; i++) {
        if (enabledIds.indexOf(groups[i].id) >= 0) out = out.concat(groups[i].types)
    }
    return out
}


// ---- OSM Scout Server styles -------------------------------------------------------------
// The configured URL is the light style (style=osmbright). The dark style has the same URL with style=mc.
// A custom URL without a style parameter is used as it is.
function scoutStyleUrl(baseUrl, dark) {
    return (baseUrl || "").replace(/([?&]style=)[^&#]*/, "$1" + (dark ? "mc" : "osmbright"))
}


// ---- native layers of the OSM Scout map (ScoutMapView) ------------------------------------------
// The caches are drawn by the map itself from GeoJSON, like the vehicles in harbour-pidmap.

function clusterRadius(n) {
    return Math.min(30, 14 + 5 * Math.log(Math.max(n, 1)) / Math.LN10)      // css pixels
}

// items from bridge.map_view -> GeoJSON features: {caches: [...], clusters: [...]}
function scoutFeatures(items) {
    var caches = [], clusters = []
    for (var i = 0; i < items.length; i++) {
        var r = items[i]
        if (r.lat === null || r.lat === undefined || r.lon === null || r.lon === undefined) continue
        var geometry = { type: "Point", coordinates: [r.lon, r.lat] }
        if (r.cluster === true) {
            clusters.push({ type: "Feature", geometry: geometry,
                            properties: { n: r.n, label: "" + r.n, r: clusterRadius(r.n) } })
        } else {
            var found = r.found === 1 || r.found === true
            var disabled = r.disabled === 1 || r.disabled === true
            caches.push({ type: "Feature", geometry: geometry,
                          properties: { code: r.geocode, sym: typeSymbol(r.type_id),
                                        color: found ? "#616161" : typeColor(r.type_id), op: disabled ? 0.5 : 1 } })
        }
    }
    return { caches: caches, clusters: clusters }
}

// flat-earth distance in metres: good enough for hit testing a tap
function distanceMeters(lat1, lon1, lat2, lon2) {
    var kx = Math.cos((lat1 + lat2) / 2 * Math.PI / 180) * 111320
    var dx = (lon2 - lon1) * kx
    var dy = (lat2 - lat1) * 110540
    return Math.sqrt(dx * dx + dy * dy)
}


// ---- readable listings ------------------------------------------------------------------------
// Listing authors set text colours (black on a dark theme!), background colours and tiny font sizes in the HTML,
// and Qt's rich text takes them literally. readableHtml() removes background colours, keeps only text colours that
// contrast enough with the theme, and drops font sizes below a readable size. ES5 only.

var NAMED_COLORS = {
    black: [0, 0, 0], silver: [192, 192, 192], gray: [128, 128, 128], grey: [128, 128, 128], white: [255, 255, 255],
    maroon: [128, 0, 0], red: [255, 0, 0], purple: [128, 0, 128], fuchsia: [255, 0, 255], magenta: [255, 0, 255],
    green: [0, 128, 0], lime: [0, 255, 0], olive: [128, 128, 0], yellow: [255, 255, 0], navy: [0, 0, 128],
    blue: [0, 0, 255], teal: [0, 128, 128], aqua: [0, 255, 255], cyan: [0, 255, 255], orange: [255, 165, 0],
    brown: [165, 42, 42], pink: [255, 192, 203], darkblue: [0, 0, 139], darkgreen: [0, 100, 0], darkred: [139, 0, 0],
    gold: [255, 215, 0], violet: [238, 130, 238], indigo: [75, 0, 130], lightgray: [211, 211, 211],
    lightgrey: [211, 211, 211], darkgray: [169, 169, 169], darkgrey: [169, 169, 169], dimgray: [105, 105, 105],
    dimgrey: [105, 105, 105], crimson: [220, 20, 60], lightblue: [173, 216, 230]
}

function parseColor(value) {
    var v = String(value === null || value === undefined ? "" : value).replace(/!important/i, "").trim().toLowerCase()
    if (v === "") return null
    var m = /^#?([0-9a-f]{6})$/.exec(v)
    if (m) return [parseInt(m[1].substr(0, 2), 16), parseInt(m[1].substr(2, 2), 16), parseInt(m[1].substr(4, 2), 16)]
    m = /^#([0-9a-f]{3})$/.exec(v)
    if (m) {
        var h = m[1]
        return [parseInt(h.charAt(0) + h.charAt(0), 16), parseInt(h.charAt(1) + h.charAt(1), 16),
                parseInt(h.charAt(2) + h.charAt(2), 16)]
    }
    m = /^rgba?\(\s*(\d{1,3})\s*,\s*(\d{1,3})\s*,\s*(\d{1,3})/.exec(v)
    if (m) return [Math.min(255, parseInt(m[1], 10)), Math.min(255, parseInt(m[2], 10)), Math.min(255, parseInt(m[3], 10))]
    return NAMED_COLORS[v] || null
}

function luminance(rgb) {
    function channel(c) {
        c = c / 255
        return c <= 0.03928 ? c / 12.92 : Math.pow((c + 0.055) / 1.055, 2.4)
    }
    return 0.2126 * channel(rgb[0]) + 0.7152 * channel(rgb[1]) + 0.0722 * channel(rgb[2])
}

// WCAG contrast ratio against an assumed theme background (nearly black / nearly white)
function contrastOnTheme(rgb, darkBackground) {
    var l = luminance(rgb)
    var b = darkBackground ? 0.03 : 0.9
    return (Math.max(l, b) + 0.05) / (Math.min(l, b) + 0.05)
}

function colorReadable(value, darkBackground) {
    var rgb = parseColor(value)
    return rgb !== null && contrastOnTheme(rgb, darkBackground) >= 3.0
}

function tooSmallFontSize(value) {
    var v = String(value).replace(/!important/i, "").trim().toLowerCase()
    if (v === "xx-small" || v === "x-small" || v === "small" || v === "smaller") return true
    var m = /^([0-9.]+)\s*(px|pt|em|rem|%)?$/.exec(v)
    if (!m) return false
    var n = parseFloat(m[1]), unit = m[2] || "px"
    var px = unit === "pt" ? n * 1.333 : (unit === "px" ? n : (unit === "%" ? n * 0.16 : n * 16))
    return px < 14
}

// CSS font size as a multiple of the default 16 px, or null when it cannot be read
var FONT_KEYWORDS = { "xx-small": 0.6, "x-small": 0.75, "small": 0.89, "medium": 1, "large": 1.2, "x-large": 1.5,
                      "xx-large": 2, "smaller": 0.83, "larger": 1.2 }

function cssFontFactor(value) {
    var v = String(value).replace(/!important/i, "").trim().toLowerCase()
    if (FONT_KEYWORDS[v] !== undefined) return FONT_KEYWORDS[v]
    var m = /^([0-9.]+)\s*(px|pt|em|rem|%)?$/.exec(v)
    if (!m) return null
    var n = parseFloat(m[1]), unit = m[2] || "px"
    if (unit === "pt") return n * 1.333 / 16
    if (unit === "px") return n / 16
    if (unit === "%") return n / 100
    return n                                     // em, rem
}

// Sizes given in CSS pixels / points are tiny on a phone whose own fonts are 30 px and more: every declared size
// becomes a multiple of the app's font (basePx), never smaller than that font and at most three times as large.
function scaledFontSize(value, basePx) {
    var f = cssFontFactor(value)
    if (f === null) return null
    return Math.round(basePx * Math.min(3, Math.max(1, f))) + "px"
}

function cleanStyle(style, darkBackground, basePx) {
    var out = [], parts = style.split(";")
    for (var i = 0; i < parts.length; i++) {
        var at = parts[i].indexOf(":")
        if (at < 0) continue
        var name = parts[i].substring(0, at).trim().toLowerCase()
        var value = parts[i].substring(at + 1).trim()
        if (name === "background" || name === "background-color" || name === "background-image" || name === "font") continue
        if (name === "white-space" || name === "width" || name === "min-width") continue      // would not fit the screen
        if (name === "height" || name === "min-height" || name === "max-height") continue     // overlaps what follows
        if (name === "color" && !colorReadable(value, darkBackground)) continue
        if (name === "font-size") {
            if (basePx > 0) {
                var scaled = scaledFontSize(value, basePx)
                if (scaled === null) continue
                value = scaled
            } else if (tooSmallFontSize(value)) {
                continue
            }
        }
        out.push(name + ":" + value)
    }
    return out.join(";")
}

// basePx: the pixel size of the text the listing is shown in (optional; without it tiny sizes are only dropped)
function readableHtml(html, darkBackground, basePx) {
    if (!html) return ""
    html = html.replace(/<style\b[^>]*>[\s\S]*?<\/style>/gi, "")           // style sheets would bring their own sizes and colours
    html = html.replace(/<(\/?)h[56]\b/gi, "<$1h4")                          // h5 / h6 are smaller than the text
    html = html.replace(/<\/?small\b[^>]*>/gi, "")
    return html.replace(/<([a-zA-Z][a-zA-Z0-9]*)\b([^>]*)>/g, function(m, tag, attrs) {
        if (!attrs) return m
        var t = tag.toLowerCase()
        var a = stripAttrs(attrs, ["bgcolor", "background"])
        if (t === "body") a = stripAttrs(a, ["text", "link", "vlink", "alink"])
        var style = attrValue(a, "style")
        if (style !== null) {
            a = stripAttrs(a, ["style"])
            var cleaned = cleanStyle(style, darkBackground, basePx)
            if (cleaned !== "") a += ' style="' + cleaned + '"'
        }
        if (t === "font") {
            var color = attrValue(a, "color")
            if (color !== null && !colorReadable(color, darkBackground)) a = stripAttrs(a, ["color"])
            var size = attrValue(a, "size")
            if (size !== null) {
                var n = parseInt(size, 10)
                if (!isNaN(n) && n <= 2 && String(size).charAt(0) !== "+") a = stripAttrs(a, ["size"])
            }
        }
        return "<" + tag + a + ">"
    })
}
