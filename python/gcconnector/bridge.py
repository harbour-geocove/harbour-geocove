"""PyOtherSide bridge: the only module QML talks to.

    import io.thp.pyotherside 1.5
    Python {
        id: py
        Component.onCompleted: {
            addImportPath(Qt.resolvedUrl("../python"))
            importModule("gcconnector.bridge", function() {
                py.call("gcconnector.bridge.init", [StandardPaths.data], function(r) { ... })
            })
            setHandler("cache_loaded", function(result) { ... })   // events sent by async calls
        }
    }

Synchronous functions return plain dicts/lists/strings/numbers (PyOtherSide converts them).
Functions that touch the network start a worker thread, return {"started": true} at once and
later deliver the result with pyotherside.send(<event>, <payload>); failures arrive as
send("error", <event>, <message>).

Works without PyOtherSide too (desktop tests): events are collected in EVENTS.
"""
import json
import os
import shutil
import threading
import traceback
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional

from . import gpx as gpx_import
from . import webcookies
from .db import FIELD_NOTE_TYPES, Database
from .geocode import geocode as _geocode
from .geopoint import Geopoint, Viewport
from .login import GCLogin
from .models import Geocache, StatusCode
from .parser import fetch_gallery, load_cache
from .search import SearchFilter, search_by_filter, search_by_viewport

try:  # pragma: no cover - only available inside PyOtherSide
    import pyotherside

    def _send(*args) -> None:
        pyotherside.send(*args)
except ImportError:
    pyotherside = None
    EVENTS: List[tuple] = []

    def _send(*args) -> None:
        EVENTS.append(args)

_state: Dict[str, Any] = {"db": None, "session": None, "dir": None}


# ------------------------------------------------------------------ helpers
def _db() -> Database:
    if _state["db"] is None:
        raise RuntimeError("bridge.init() has not been called")
    return _state["db"]


def _session() -> GCLogin:
    return _state["session"]


def _async(event: str, fn: Callable[[], Any]) -> Dict[str, bool]:
    def run():
        try:
            result = fn()
            _maybe_publish_session()
            _send(event, result)
        except Exception as e:  # noqa: BLE001 - report everything to the UI
            traceback.print_exc()
            _send("error", event, "%s: %s" % (type(e).__name__, e))
    threading.Thread(target=run, daemon=True).start()
    return {"started": True}


def _iso(dt: Optional[datetime]) -> str:
    if not dt:
        return ""
    d = dt.astimezone(timezone.utc)       # manual format: strftime is unreliable for years before 1000
    return "%04d-%02d-%02dT%02d:%02d:%02dZ" % (d.year, d.month, d.day, d.hour, d.minute, d.second)


def cache_to_dict(c: Geocache, full: bool = True) -> Dict[str, Any]:
    d: Dict[str, Any] = {
        "geocode": c.geocode, "name": c.name, "type_id": c.type_id, "size_id": c.size_id,
        "difficulty": c.difficulty, "terrain": c.terrain,
        "lat": c.coords.lat if c.coords else None, "lon": c.coords.lon if c.coords else None,
        "has_coords": c.coords is not None, "user_modified": c.user_modified_coords,
        "found": c.found, "dnf": c.dnf, "disabled": c.disabled, "archived": c.archived,
        "premium_only": c.premium_only, "favorite_points": c.favorite_points, "detailed": c.detailed,
    }
    if not full:
        return d
    d.update({
        "guid": c.guid, "cache_id": c.cache_id, "location": c.location,
        "owner": c.owner_display_name, "hidden": _iso(c.hidden), "last_found": _iso(c.last_found),
        "hint": c.hint, "personal_note": c.personal_note,
        "short_description": c.short_description, "description": c.description,
        "attributes": c.attributes, "log_counts": c.log_counts,
        "spoilers": [{"url": i.url, "title": i.title, "description": i.description} for i in c.spoilers],
        "inventory": [{"geocode": t.geocode, "name": t.name, "tracking_code": t.tracking_code}
                      for t in c.inventory],
        "waypoints": [{"id": getattr(w, "id", None), "name": w.name, "type": w.type_id, "lookup": w.lookup,
                       "lat": w.coords.lat if w.coords else None, "lon": w.coords.lon if w.coords else None,
                       "note": w.note, "user_defined": w.user_defined} for w in c.waypoints],
        "logs": [{"id": l.service_log_id, "author": l.author, "date": _iso(l.date), "type": l.log_type,
                  "text": l.log, "friend": l.friend, "favorite": l.favorite,
                  "images": [{"url": i.url, "title": i.title} for i in l.images]} for l in c.logs],
        "offline_log": _db().get_offline_log(c.geocode),
    })
    return d


def _filter_from_dict(d: Optional[Dict[str, Any]]) -> SearchFilter:
    d = d or {}
    f = SearchFilter()
    f.types = d.get("types") or None
    f.sizes = d.get("sizes") or None
    f.name_contains = d.get("name") or None
    f.difficulty = (d.get("difficulty_min"), d.get("difficulty_max"))
    f.terrain = (d.get("terrain_min"), d.get("terrain_max"))
    f.min_favorites = d.get("min_favorites")
    f.exclude_disabled = bool(d.get("hide_disabled"))
    f.exclude_archived = d.get("hide_archived", True)
    if d.get("hide_found"):
        f.status_found = False
    if d.get("hide_own"):
        f.status_owned = False
    return f


# --------------------------------------------------------------------- setup
APP_NAME = "harbour-geocove"
ORG_NAME = "org.geocove"       # must match OrganizationName in harbour-geocove.desktop ([X-Sailjail])
VERSION = "0.8.6"

DEFAULT_SETTINGS: Dict[str, Any] = {
    "imperial": False, "hide_found": False, "hide_disabled": False, "hide_archived": True,
    "last_lat": 50.0878, "last_lon": 14.4426, "last_zoom": 12, "debug_map": False, "buttons_left": False,
    "tile_server": "https://tile.openstreetmap.org/",
    # map source: "osm" (online tiles) or "osmscout" (OSM Scout Server through the mapboxgl plugin)
    "map_types": ["traditional", "multi", "mystery", "letterbox", "earth", "virtual", "webcam", "wherigo", "events", "cito", "other"],
    "readable_listings": True,          # theme colours / minimum font size in cache descriptions
    "description_images": "fit",        # images in cache descriptions: fit | links | none
    "map_source": "osm",
    "osmscout_style_url": "http://localhost:8553/v1/mbgl/style?style=osmbright",
    "scout_scale": 1.0,                          # correction of the pixel scale of the OSM Scout map (1.0 = automatic)
    "scout_text_font": "Noto Sans Regular",     # glyph stack for the labels on the OSM Scout map
}


def _data_home() -> str:
    return os.environ.get("XDG_DATA_HOME") or os.path.join(os.path.expanduser("~"), ".local", "share")


def default_data_dir() -> str:
    """~/.local/share/<OrganizationName>/<ApplicationName>: the only place under .local/share where an
    application running in the Sailjail sandbox may write."""
    return os.path.join(_data_home(), ORG_NAME, APP_NAME)


def _migrate_legacy_data(data_dir: str) -> None:
    """Older versions used ~/.local/share/<ApplicationName>, which the sandbox does not allow to write.
    Copy what is readable from there (best effort, the old files stay where they are)."""
    if os.path.exists(os.path.join(data_dir, "geocaches.sqlite")):
        return
    old = os.path.join(_data_home(), APP_NAME)
    if os.path.abspath(old) == os.path.abspath(data_dir):
        return
    for name in ("geocaches.sqlite", "settings.json", "auth.json"):
        src = os.path.join(old, name)
        try:
            if os.path.isfile(src) and not os.path.exists(os.path.join(data_dir, name)):
                shutil.copy2(src, os.path.join(data_dir, name))
        except OSError:
            pass


def documents_dir() -> str:
    return os.path.join(os.path.expanduser("~"), "Documents")


def init(data_dir: Optional[str] = None) -> Dict[str, Any]:
    """Open the database (default location if data_dir is empty); must be called first."""
    data_dir = data_dir or default_data_dir()
    os.makedirs(data_dir, exist_ok=True)
    if not data_dir_given(data_dir):
        _migrate_legacy_data(data_dir)
    _state["dir"] = data_dir
    if _state["db"] is None:
        _state["db"] = Database(os.path.join(data_dir, "geocaches.sqlite"))
    _state["session"] = GCLogin()
    return {"ok": True, "caches": _db().count_caches(), "has_saved_login": os.path.exists(_auth_path()),
            "settings": get_settings(), "documents_dir": documents_dir(), "data_dir": data_dir}


def data_dir_given(data_dir: str) -> bool:
    """True when init() was called with an explicit directory (tests) - no legacy migration then."""
    return os.path.abspath(data_dir) != os.path.abspath(default_data_dir())


def _settings_path() -> str:
    return os.path.join(_state["dir"], "settings.json")


def get_settings() -> Dict[str, Any]:
    settings = dict(DEFAULT_SETTINGS)
    try:
        with open(_settings_path()) as f:
            settings.update({k: v for k, v in json.load(f).items() if k in DEFAULT_SETTINGS})
    except (OSError, ValueError):
        pass
    return settings


def set_setting(key: str, value: Any) -> Dict[str, bool]:
    if key not in DEFAULT_SETTINGS:
        raise KeyError("unknown setting %r" % key)
    settings = get_settings()
    settings[key] = value
    tmp = _settings_path() + ".tmp"
    with open(tmp, "w") as f:
        json.dump(settings, f)
    os.replace(tmp, _settings_path())
    return {"ok": True}


def _auth_path() -> str:
    """auth.json of older versions: only read once to move the cookie to dconf, then deleted."""
    return os.path.join(_state["dir"], "auth.json")


def _publish_session(clear: bool = False) -> None:
    """Hand the session cookie to the QML side, which keeps it in dconf (Nemo.Configuration).
    Only the cookie and the nickname are stored - never the password. Event "session_cookie"."""
    if clear:
        _state["saved_cookie"] = ""
        _send("session_cookie", {"cookie": "", "user": ""})
        return
    s = _session()
    cookie = s.http.cookies.get("gspkauth")
    if cookie:
        _state["saved_cookie"] = cookie
        _send("session_cookie", {"cookie": cookie, "user": s.user_name or ""})


def _maybe_publish_session() -> None:
    """The server renews the session cookie while we are active: keep the stored copy current,
    otherwise the cookie from the first login would be the one that expires."""
    try:
        cookie = _session().http.cookies.get("gspkauth")
        if cookie and cookie != _state.get("saved_cookie") and _session().logged_in:
            _publish_session()
    except (AttributeError, OSError):
        pass


def _login_result(status: StatusCode) -> Dict[str, Any]:
    s = _session()
    ok = status == StatusCode.NO_ERROR
    if ok:
        _publish_session()
    return {"status": status.value, "ok": ok, "user": s.user_name, "member_type": s.member_type,
            "caches_found": s.caches_found, "error": s.last_error,
            "debug": "" if ok else s.debug_report()}


def login(username: str, password: str) -> Dict[str, bool]:
    s = _session()
    s.username, s.password = username, password
    return _async("login", lambda: _login_result(s.login()))


def login_cookie(gspkauth: str) -> Dict[str, bool]:
    """`gspkauth` may be the bare value, `gspkauth=VALUE` or a whole Cookie line."""
    value = webcookies.extract_gspkauth(gspkauth) or (gspkauth or "").strip()
    return _async("login", lambda: _login_result(_session().set_auth_cookie(value)))


def _webview_roots() -> List[str]:
    home = os.path.expanduser("~")
    roots = [_state["dir"], os.path.join(home, ".local", "share"),
             os.path.join(home, ".mozilla"), os.path.join(home, ".cache")]
    for var in ("XDG_DATA_HOME", "XDG_CACHE_HOME", "XDG_CONFIG_HOME"):
        if os.environ.get(var):
            roots.append(os.environ[var])
    unique: List[str] = []
    for r in roots:
        if r and r not in unique:
            unique.append(r)
    return unique


def login_webview(cookie_string: str = "", note: str = "") -> Dict[str, bool]:
    """Finish a login done in the embedded web view (captcha solved there).

    `cookie_string` is document.cookie from the page (usually without the HttpOnly auth
    cookie); the Gecko profile is searched for `gspkauth` if it is not in there."""
    def run():
        s = _session()
        s.debug_lines = []
        if note:
            s._debug("web view: %s" % note)
        value = webcookies.parse_cookie_header(cookie_string)
        s._debug("document.cookie: %s" % ("gspkauth found" if value else
                                          "no gspkauth (HttpOnly or empty), %d chars" % len(cookie_string or "")))
        if not value:
            value, report = webcookies.find_gspkauth(_webview_roots())
            for line in report:
                s._debug(line)
        if not value:
            s.last_error = "gspkauth cookie not found in the web view"
            return {"status": StatusCode.NO_LOGIN_INFO_STORED.value, "ok": False, "user": None,
                    "member_type": None, "caches_found": -1, "error": s.last_error, "debug": s.debug_report()}
        return _login_result(s.set_auth_cookie(value))
    return _async("login", run)


def restore_login(cookie: str = "", user: str = "") -> Dict[str, bool]:
    """Sign in with a saved session cookie (QML passes the one from dconf). Without arguments the
    auth.json of older versions is used, once: after a successful login the cookie is published to
    dconf and the file is deleted."""
    def run():
        value, legacy = cookie, False
        if not value:
            try:
                with open(_auth_path()) as f:
                    value = json.load(f)["gspkauth"]
                legacy = True
            except (OSError, ValueError, KeyError):
                return {"status": StatusCode.NO_LOGIN_INFO_STORED.value, "ok": False}
        result = _login_result(_session().set_auth_cookie(value))
        result["restored"] = True            # lets the UI say "your session has expired"
        if result["ok"] and legacy:
            try:
                os.remove(_auth_path())
            except OSError:
                pass
        elif result["status"] == StatusCode.WRONG_LOGIN_DATA.value:
            _publish_session(clear=True)     # the server refused it: do not keep a dead cookie
        return result
    return _async("login", run)


def session_check() -> Dict[str, bool]:
    """Is the saved session still valid? Event "session_check": {state: ok | expired | offline}.
    Also keeps the session active (the site renews the cookie on use)."""
    def run():
        from .login import LOGIN_URI
        s = _session()
        page = s.get_text(LOGIN_URI)
        if page is None:
            return {"state": "offline"}
        return {"state": "ok" if s.get_login_status(page) else "expired"}
    return _async("session_check", run)


def logout() -> Dict[str, bool]:
    _session().logout()
    _publish_session(clear=True)
    try:
        os.remove(_auth_path())
    except OSError:
        pass
    return {"ok": True}


def status() -> Dict[str, Any]:
    s = _session()
    return {"logged_in": s.logged_in, "user": s.user_name, "member_type": s.member_type,
            "caches_found": s.caches_found, "date_format": s.gc_custom_date}


# --------------------------------------------------------------- offline queries
def map_caches(lat_min: float, lon_min: float, lat_max: float, lon_max: float,
               filt: Optional[Dict[str, Any]] = None, limit: int = 1000) -> List[Dict[str, Any]]:
    f = filt or {}
    return _db().in_viewport(Viewport(lat_min, lat_max, lon_min, lon_max), limit, f.get("types"),
                             bool(f.get("hide_found")), bool(f.get("hide_disabled")),
                             f.get("hide_archived", True))


def map_view(lat_min: float, lon_min: float, lat_max: float, lon_max: float,
             filt: Optional[Dict[str, Any]] = None, max_markers: int = 250) -> Dict[str, Any]:
    """What the map shows: single caches, or - when there are more than max_markers in the
    visible area - clusters (grid cells with a count; cells with one cache stay normal markers).

    Returns {"total": n, "clustered": bool, "items": [...]}; cluster items have "cluster": true,
    "n", "lat", "lon"."""
    bounds = [lat_min, lon_min, lat_max, lon_max]
    if any(v is None or v != v or abs(v) == float("inf") for v in bounds):   # NaN / inf from an unready map
        return {"total": 0, "clustered": False, "items": [], "error": "invalid viewport", "vp": []}
    vp = Viewport(lat_min, lat_max, lon_min, lon_max)
    f = filt or {}
    args = (f.get("types"), bool(f.get("hide_found")), bool(f.get("hide_disabled")),
            f.get("hide_archived", True))
    db = _db()
    total = db.count_in_viewport(vp, *args)
    if total <= max_markers:
        return {"total": total, "clustered": False, "vp": bounds,
                "items": db.in_viewport(vp, max_markers, *args, center=vp.center)}
    cell = max((lat_max - lat_min) / 8.0, 1e-4)
    items: List[Dict[str, Any]] = []
    singles: List[str] = []
    for c in db.clusters_in_viewport(vp, cell, *args):
        if c["n"] == 1:
            singles.append(c["geocode"])
        else:
            c["cluster"] = True
            items.append(c)
    items += db.summaries(singles)
    return {"total": total, "clustered": True, "items": items, "vp": bounds}


def db_stats() -> Dict[str, Any]:
    """How much is stored and where (diagnostics shown on the map)."""
    return _db().stats()


def nearby(lat: float, lon: float, radius_km: float = 10.0, filt: Optional[Dict[str, Any]] = None,
           limit: int = 200) -> List[Dict[str, Any]]:
    f = filt or {}
    return _db().nearby(Geopoint(lat, lon), radius_km, limit, f.get("types"), bool(f.get("hide_found")),
                        bool(f.get("hide_disabled")), f.get("hide_archived", True))


def search_text(text: str) -> List[Dict[str, Any]]:
    return _db().search_text(text)


def get_cache(geocode: str) -> Optional[Dict[str, Any]]:
    c = _db().get_cache(geocode.upper())
    return cache_to_dict(c) if c else None


def export_listing_html(geocode: str) -> Dict[str, Any]:
    """Write the stored listing (short + long description, hint) to Documents/<GC code>.html, e.g. to look at
    why a listing is displayed badly."""
    c = _db().get_cache(geocode.upper())
    if c is None:
        return {"ok": False}
    path = os.path.join(documents_dir(), "%s.html" % c.geocode)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write('<!-- %s %s -->\n<meta charset="utf-8">\n%s\n<hr>\n%s\n<hr>\n<pre>%s</pre>\n' % (
            c.geocode, c.name, c.short_description, c.description, c.hint))
    return {"ok": True, "path": path}


def delete_caches(geocodes: List[str]) -> Dict[str, bool]:
    _db().delete_caches(geocodes)
    return {"ok": True}


def distance_bearing(lat: float, lon: float, target_lat: float, target_lon: float) -> Dict[str, float]:
    """For the compass page: distance (m) and bearing (degrees) from the user to the target."""
    a, b = Geopoint(lat, lon), Geopoint(target_lat, target_lon)
    return {"distance_m": a.distance_km(b) * 1000.0, "bearing": a.bearing_to(b)}


def format_distance(meters: float, imperial: bool = False) -> str:
    if imperial:
        feet = meters * 3.28084
        return "%d ft" % round(feet) if feet < 1000 else "%.1f mi" % (meters / 1609.344)
    if meters < 1000:
        return "%d m" % round(meters)
    if meters < 10000:
        return "%.1f km" % (meters / 1000.0)
    return "%d km" % round(meters / 1000.0)


# ---------------------------------------------------------------- online (threads)
def search_online_viewport(lat_min: float, lon_min: float, lat_max: float, lon_max: float,
                           filt: Optional[Dict[str, Any]] = None) -> Dict[str, bool]:
    def run():
        res = search_by_viewport(_session(), Viewport(lat_min, lat_max, lon_min, lon_max),
                                 _filter_from_dict(filt))
        _db().save_caches(res.caches)
        return {"kind": "viewport", "count": len(res.caches), "left_to_fetch": max(res.left_to_fetch, 0),
                "partial": res.partial, "error": res.error.value if res.error else None, "detail": res.detail}
    return _async("online_search", run)


def search_online_nearby(lat: float, lon: float, radius_km: float = 10.0,
                         filt: Optional[Dict[str, Any]] = None, already_took: int = 0) -> Dict[str, bool]:
    def run():
        f = _filter_from_dict(filt)
        f.center, f.max_distance_km = Geopoint(lat, lon), radius_km
        res = search_by_filter(_session(), f, "distance", True, already_took, Geopoint(lat, lon))
        _db().save_caches(res.caches)
        return {"count": len(res.caches), "left_to_fetch": max(res.left_to_fetch, 0), "partial": res.partial,
                "error": res.error.value if res.error else None, "detail": res.detail}
    return _async("online_search", run)


def search_online_name(text: str, lat: float, lon: float,
                       filt: Optional[Dict[str, Any]] = None) -> Dict[str, bool]:
    """Search geocaching.com by (whole word) name anywhere in the world, nearest to (lat, lon) first.
    The caches are stored and also returned in the event payload under "results"."""
    def run():
        origin = Geopoint(lat, lon)
        f = _filter_from_dict(filt)
        f.name_contains = text.strip()
        res = search_by_filter(_session(), f, "distance", True, 0, origin)
        _db().save_caches(res.caches)
        rows = []
        for c in res.caches:
            d = cache_to_dict(c, full=False)
            if c.coords is not None:
                d["distance_km"] = origin.distance_km(c.coords)
            rows.append(d)
        return {"kind": "name", "count": len(rows), "left_to_fetch": max(res.left_to_fetch, 0),
                "partial": res.partial, "error": res.error.value if res.error else None, "detail": res.detail,
                "results": rows}
    return _async("online_search", run)


def connection_test() -> Dict[str, bool]:
    """Step by step check of everything the online features need; the report has no secrets."""
    def run():
        import sys
        from .webapi import WebApiSearch, search_caches
        from .login import LOGIN_URI
        s = _session()
        lines = ["app %s, python %s" % (VERSION, sys.version.split()[0])]
        lines.append("cookies: %s" % sorted({c.name for c in s.http._jar}))
        page = s.get_text(LOGIN_URI)
        if page is None:
            lines.append("account page: no answer / HTTP error")
        elif s.get_login_status(page):
            lines.append("account page: signed in as %s" % s.user_name)
        else:
            lines.append("account page: NOT signed in (cookie expired or invalid)")
        token = s.authorization(force=True)
        lines.append("token: ok" if token else "token: FAILED - %s" % s.token_error)
        res = search_caches(s, WebApiSearch(box=Viewport(50.05, 50.10, 14.35, 14.45)).set_page(1, 0))
        if res.error:
            lines.append("search: FAILED (%s) %s" % (res.error.value, res.detail))
        else:
            lines.append("search: ok, %d result(s) returned, %d more available" % (len(res.caches), max(res.left_to_fetch, 0)))
        return {"report": "\n".join(lines)}
    return _async("connection_test", run)


def geocode(query: str) -> Dict[str, bool]:
    """Find a place (city, address) -> event "geocode" {places: [{name, lat, lon, bbox}]}."""
    return _async("geocode", lambda: {"places": _geocode(query)})


def load_gallery(geocode: str) -> Dict[str, bool]:
    """Images of the cache's web gallery (the page behind the "Gallery (N)" link).
    Event "gallery": {geocode, images: [{url, title, description}], error}."""
    geocode = geocode.upper()

    def run():
        cache = _db().get_cache(geocode)
        if cache is None or not cache.guid:
            return {"geocode": geocode, "images": [], "error": "unknown_guid"}
        found = fetch_gallery(_session(), cache.guid)
        if found is None:
            return {"geocode": geocode, "images": [], "error": "communication_error",
                    "detail": _session().last_api_error}
        images, info = found
        return {"geocode": geocode, "error": None, "debug": info,
                "images": [{"url": i.url, "title": i.title or "", "description": i.description or ""} for i in images]}
    return _async("gallery", run)


def load_cache_online(geocode: str) -> Dict[str, bool]:
    geocode = geocode.upper()

    def run():
        st, cache = load_cache(_session(), geocode, progress=lambda step: _send("progress", geocode, step))
        if st == StatusCode.NO_ERROR and cache is not None:
            _db().save_cache(cache)
        elif st == StatusCode.PREMIUM_ONLY and cache is not None:
            _db().save_cache(cache)
        stored = _db().get_cache(geocode)
        return {"geocode": geocode, "status": st.value, "cache": cache_to_dict(stored) if stored else None,
                "detail": _session().last_api_error}
    return _async("cache_loaded", run)


# --------------------------------------------------------------------- GPX import
def import_gpx_file(path: str, list_name: str = "") -> Dict[str, bool]:
    def run():
        list_id = _db().create_list(list_name) if list_name else None
        stats = gpx_import.import_gpx(_db(), path, list_id,
                                      progress=lambda n: _send("progress", "gpx", n))
        stats["list_id"] = list_id
        return stats
    return _async("gpx_imported", run)


# ------------------------------------------------------------------------- lists
def get_lists() -> List[Dict[str, Any]]:
    return _db().get_lists()


def create_list(name: str) -> int:
    return _db().create_list(name)


def rename_list(list_id: int, name: str) -> Dict[str, bool]:
    _db().rename_list(list_id, name)
    return {"ok": True}


def delete_list(list_id: int, delete_caches: bool = False) -> Dict[str, bool]:
    _db().delete_list(list_id, delete_caches)
    return {"ok": True}


def add_to_list(list_id: int, geocodes: List[str]) -> Dict[str, bool]:
    _db().add_to_list(list_id, geocodes)
    return {"ok": True}


def remove_from_list(list_id: int, geocodes: List[str]) -> Dict[str, bool]:
    _db().remove_from_list(list_id, geocodes)
    return {"ok": True}


def list_caches(list_id: int) -> List[Dict[str, Any]]:
    return _db().list_caches(list_id)


# --------------------------------------------------------- waypoints / offline logs
def add_user_waypoint(geocode: str, name: str, lat: float, lon: float, note: str = "") -> int:
    from .models import Waypoint
    return _db().add_waypoint(geocode, Waypoint(name=name, type_id="waypoint", coords=Geopoint(lat, lon),
                                                note=note, user_defined=True))


def delete_waypoint(waypoint_id: int) -> Dict[str, bool]:
    _db().delete_waypoint(waypoint_id)
    return {"ok": True}


def log_types() -> List[str]:
    return list(FIELD_NOTE_TYPES)


def save_offline_log(geocode: str, log_type: str, text: str = "", favorite: bool = False) -> Dict[str, bool]:
    _db().set_offline_log(geocode.upper(), log_type, None, text, favorite)
    return {"ok": True}


def offline_logs() -> List[Dict[str, Any]]:
    return _db().list_offline_logs()


def delete_offline_log(geocode: str) -> Dict[str, bool]:
    _db().delete_offline_log(geocode)
    return {"ok": True}


def export_field_notes(path: str) -> Dict[str, Any]:
    """Write geocache_visits.txt (UTF-16) for upload on geocaching.com."""
    return {"path": path, "count": _db().write_field_notes(path)}
