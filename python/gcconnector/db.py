"""SQLite storage: offline caches, waypoints, logs, lists and offline (field note) logs.

Pure standard library (sqlite3), safe to use from several threads
(one connection, guarded by a lock).
"""
import json
import sqlite3
import threading
from datetime import datetime, timedelta, timezone
from typing import Dict, Iterable, List, Optional, Sequence

from .geopoint import Geopoint, Viewport
from .models import Geocache, Image, LogEntry, Trackable, Waypoint

SCHEMA_VERSION = 1

# Field-notes log types accepted by geocaching.com
FIELD_NOTE_TYPES = ("Found it", "Didn't find it", "Write note", "Needs Archived",
                    "Needs Maintenance", "Owner Maintenance", "Will Attend", "Attended",
                    "Webcam Photo Taken")

_SCHEMA = """
CREATE TABLE IF NOT EXISTS caches (
    geocode TEXT PRIMARY KEY,
    cache_id TEXT, guid TEXT, name TEXT, type_id TEXT, size_id TEXT,
    difficulty REAL, terrain REAL,
    lat REAL, lon REAL, user_modified INTEGER DEFAULT 0,
    orig_lat REAL, orig_lon REAL,
    location TEXT, owner_user_id TEXT, owner_display_name TEXT, owner_guid TEXT,
    hidden REAL, last_found REAL, visited REAL,
    favorite_points INTEGER DEFAULT 0, favorite INTEGER DEFAULT 0,
    found INTEGER DEFAULT 0, dnf INTEGER DEFAULT 0, disabled INTEGER DEFAULT 0,
    archived INTEGER DEFAULT 0, premium_only INTEGER DEFAULT 0, on_watchlist INTEGER DEFAULT 0,
    watchlist_count INTEGER DEFAULT -1, inventory_count INTEGER DEFAULT 0,
    hint TEXT, personal_note TEXT, short_description TEXT, description TEXT,
    attributes TEXT, spoilers TEXT, inventory TEXT, log_counts TEXT,
    detailed INTEGER DEFAULT 0, updated REAL
);
CREATE INDEX IF NOT EXISTS idx_caches_pos ON caches(lat, lon);
CREATE INDEX IF NOT EXISTS idx_caches_name ON caches(name);

CREATE TABLE IF NOT EXISTS waypoints (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    geocode TEXT NOT NULL, name TEXT, type_id TEXT, prefix TEXT, lookup TEXT,
    lat REAL, lon REAL, note TEXT, coords_empty INTEGER DEFAULT 0, user_defined INTEGER DEFAULT 0
);
CREATE INDEX IF NOT EXISTS idx_wp_geocode ON waypoints(geocode);

CREATE TABLE IF NOT EXISTS logs (
    geocode TEXT NOT NULL, service_log_id TEXT NOT NULL,
    author TEXT, author_guid TEXT, date REAL, log_type TEXT, log TEXT,
    found_count INTEGER DEFAULT 0, friend INTEGER DEFAULT 0, favorite INTEGER DEFAULT 0,
    images TEXT,
    PRIMARY KEY (geocode, service_log_id)
);

CREATE TABLE IF NOT EXISTS lists (
    id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL UNIQUE
);
CREATE TABLE IF NOT EXISTS list_caches (
    list_id INTEGER NOT NULL, geocode TEXT NOT NULL, PRIMARY KEY (list_id, geocode)
);

CREATE TABLE IF NOT EXISTS offline_logs (
    geocode TEXT PRIMARY KEY, log_type TEXT NOT NULL, date REAL NOT NULL,
    text TEXT, favorite INTEGER DEFAULT 0
);
"""

_SUMMARY_COLS = ("geocode, name, type_id, size_id, difficulty, terrain, lat, lon, found, dnf, "
                 "disabled, archived, premium_only, favorite_points, user_modified, detailed")


# Plain datetime arithmetic: independent of the platform's time_t. On 32-bit systems
# datetime.fromtimestamp() fails outside 1901-2038 (e.g. EarthCaches with a placed date in year 1).
_EPOCH = datetime(1970, 1, 1, tzinfo=timezone.utc)


def _ts(dt: Optional[datetime]) -> Optional[float]:
    if dt is None:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return (dt - _EPOCH).total_seconds()


def _dt(ts: Optional[float]) -> Optional[datetime]:
    if ts is None:
        return None
    try:
        return _EPOCH + timedelta(seconds=ts)
    except (OverflowError, ValueError):
        return None


def _images_json(images: Iterable[Image]) -> str:
    return json.dumps([[i.url, i.title or "", i.description or "", i.category] for i in images])


def _images_load(text: Optional[str]) -> List[Image]:
    try:
        return [Image(url=u, title=t, description=d, category=c) for u, t, d, c in json.loads(text or "[]")]
    except (ValueError, TypeError):
        return []


class Database:
    def __init__(self, path: str = ":memory:"):
        self.conn = sqlite3.connect(path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self.lock = threading.RLock()
        with self.lock:
            self.conn.executescript(_SCHEMA)
            self.conn.execute("PRAGMA user_version = %d" % SCHEMA_VERSION)
            self.conn.commit()

    def close(self) -> None:
        with self.lock:
            self.conn.close()

    # ------------------------------------------------------------------ caches
    def save_cache(self, c: Geocache) -> None:
        """Save a cache. A list-level (not detailed) result never overwrites details."""
        if not c.geocode:
            return
        with self.lock, self.conn:
            row = self.conn.execute("SELECT detailed FROM caches WHERE geocode=?", (c.geocode,)).fetchone()
            if row is not None and row["detailed"] and not c.detailed:
                self._update_summary(c)
                return
            self._upsert_full(c)
            if c.detailed:
                self._replace_waypoints(c.geocode, c.waypoints)
            if c.logs:
                self._save_logs(c.geocode, c.logs, replace=True)

    def save_caches(self, caches: Iterable[Geocache]) -> int:
        n = 0
        with self.lock, self.conn:
            for c in caches:
                self.save_cache(c)
                n += 1
        return n

    def _params(self, c: Geocache) -> Dict:
        return {
            "geocode": c.geocode, "cache_id": c.cache_id, "guid": c.guid, "name": c.name,
            "type_id": c.type_id, "size_id": c.size_id, "difficulty": c.difficulty, "terrain": c.terrain,
            "lat": c.coords.lat if c.coords else None, "lon": c.coords.lon if c.coords else None,
            "user_modified": int(c.user_modified_coords),
            "orig_lat": c.original_coords.lat if c.original_coords else None,
            "orig_lon": c.original_coords.lon if c.original_coords else None,
            "location": c.location, "owner_user_id": c.owner_user_id,
            "owner_display_name": c.owner_display_name, "owner_guid": c.owner_guid,
            "hidden": _ts(c.hidden), "last_found": _ts(c.last_found), "visited": _ts(c.visited_date),
            "favorite_points": c.favorite_points, "favorite": int(c.favorite),
            "found": int(c.found), "dnf": int(c.dnf), "disabled": int(c.disabled),
            "archived": int(c.archived), "premium_only": int(c.premium_only),
            "on_watchlist": int(c.on_watchlist), "watchlist_count": c.watchlist_count,
            "inventory_count": c.inventory_count or len(c.inventory),
            "hint": c.hint, "personal_note": c.personal_note,
            "short_description": c.short_description, "description": c.description,
            "attributes": json.dumps(c.attributes), "spoilers": _images_json(c.spoilers),
            "inventory": json.dumps([[t.geocode, t.guid, t.name, t.tracking_code, t.icon_url] for t in c.inventory]),
            "log_counts": json.dumps(c.log_counts), "detailed": int(c.detailed),
            "updated": datetime.now(timezone.utc).timestamp(),
        }

    def _upsert_full(self, c: Geocache) -> None:
        p = self._params(c)
        cols = list(p)
        updates = ", ".join("%s=excluded.%s" % (k, k) for k in cols if k not in ("geocode", "found", "dnf"))
        # never un-set found / dnf from a (possibly lagging) source
        updates += ", found=MAX(found, excluded.found), dnf=MAX(dnf, excluded.dnf)"
        self.conn.execute(
            "INSERT INTO caches (%s) VALUES (%s) ON CONFLICT(geocode) DO UPDATE SET %s" % (
                ", ".join(cols), ", ".join(":" + k for k in cols), updates), p)

    def _update_summary(self, c: Geocache) -> None:
        p = self._params(c)
        sets = ["name=:name", "type_id=:type_id", "size_id=:size_id", "difficulty=:difficulty",
                "terrain=:terrain", "location=:location", "owner_user_id=:owner_user_id",
                "owner_display_name=:owner_display_name", "favorite_points=:favorite_points",
                "found=MAX(found, :found)", "dnf=MAX(dnf, :dnf)", "disabled=:disabled",
                "archived=:archived", "premium_only=:premium_only", "inventory_count=:inventory_count",
                "updated=:updated"]
        if c.coords is not None:
            sets += ["lat=:lat", "lon=:lon", "user_modified=:user_modified"]
        if c.last_found is not None:
            sets.append("last_found=:last_found")
        if c.hidden is not None:
            sets.append("hidden=:hidden")
        self.conn.execute("UPDATE caches SET %s WHERE geocode=:geocode" % ", ".join(sets), p)

    def _replace_waypoints(self, geocode: str, waypoints: Sequence[Waypoint]) -> None:
        self.conn.execute("DELETE FROM waypoints WHERE geocode=? AND user_defined=0", (geocode,))
        for w in waypoints:
            if w.user_defined:
                continue
            self._insert_waypoint(geocode, w)

    def _insert_waypoint(self, geocode: str, w: Waypoint) -> int:
        cur = self.conn.execute(
            "INSERT INTO waypoints (geocode, name, type_id, prefix, lookup, lat, lon, note, coords_empty, user_defined) "
            "VALUES (?,?,?,?,?,?,?,?,?,?)",
            (geocode, w.name, w.type_id, w.prefix, w.lookup,
             w.coords.lat if w.coords else None, w.coords.lon if w.coords else None,
             w.note, int(w.original_coords_empty), int(w.user_defined)))
        return cur.lastrowid

    def add_waypoint(self, geocode: str, w: Waypoint) -> int:
        """Add one waypoint (e.g. from an additional-waypoints GPX); replaces the same lookup code."""
        with self.lock, self.conn:
            if w.lookup:
                self.conn.execute("DELETE FROM waypoints WHERE geocode=? AND lookup=? AND user_defined=0",
                                  (geocode, w.lookup))
            return self._insert_waypoint(geocode, w)

    def delete_waypoint(self, waypoint_id: int) -> None:
        with self.lock, self.conn:
            self.conn.execute("DELETE FROM waypoints WHERE id=?", (waypoint_id,))

    def has_cache(self, geocode: str) -> bool:
        with self.lock:
            return self.conn.execute("SELECT 1 FROM caches WHERE geocode=?", (geocode,)).fetchone() is not None

    def get_cache(self, geocode: str) -> Optional[Geocache]:
        with self.lock:
            r = self.conn.execute("SELECT * FROM caches WHERE geocode=?", (geocode,)).fetchone()
            if r is None:
                return None
            c = Geocache(
                geocode=r["geocode"], cache_id=r["cache_id"] or "", guid=r["guid"] or "", name=r["name"] or "",
                type_id=r["type_id"] or "", size_id=r["size_id"] or "",
                difficulty=r["difficulty"] or 0.0, terrain=r["terrain"] or 0.0,
                coords=Geopoint(r["lat"], r["lon"]) if r["lat"] is not None else None,
                original_coords=Geopoint(r["orig_lat"], r["orig_lon"]) if r["orig_lat"] is not None else None,
                user_modified_coords=bool(r["user_modified"]), location=r["location"] or "",
                owner_user_id=r["owner_user_id"] or "", owner_display_name=r["owner_display_name"] or "",
                owner_guid=r["owner_guid"] or "", hidden=_dt(r["hidden"]), last_found=_dt(r["last_found"]),
                visited_date=_dt(r["visited"]), favorite_points=r["favorite_points"], favorite=bool(r["favorite"]),
                found=bool(r["found"]), dnf=bool(r["dnf"]), disabled=bool(r["disabled"]),
                archived=bool(r["archived"]), premium_only=bool(r["premium_only"]),
                on_watchlist=bool(r["on_watchlist"]), watchlist_count=r["watchlist_count"],
                inventory_count=r["inventory_count"], hint=r["hint"] or "", personal_note=r["personal_note"] or "",
                short_description=r["short_description"] or "", description=r["description"] or "",
                detailed=bool(r["detailed"]))
            c.attributes = json.loads(r["attributes"] or "[]")
            c.spoilers = _images_load(r["spoilers"])
            c.log_counts = json.loads(r["log_counts"] or "{}")
            c.inventory = [Trackable(geocode=g, guid=gu, name=n or "", tracking_code=tc, icon_url=ic)
                           for g, gu, n, tc, ic in json.loads(r["inventory"] or "[]")]
            c.waypoints = self.get_waypoints(geocode)
            c.logs = self.get_logs(geocode)
            return c

    def get_waypoints(self, geocode: str) -> List[Waypoint]:
        with self.lock:
            rows = self.conn.execute("SELECT * FROM waypoints WHERE geocode=? ORDER BY id", (geocode,)).fetchall()
        out = []
        for r in rows:
            w = Waypoint(name=r["name"] or "", type_id=r["type_id"], prefix=r["prefix"] or "",
                         lookup=r["lookup"] or "",
                         coords=Geopoint(r["lat"], r["lon"]) if r["lat"] is not None else None,
                         note=r["note"] or "", original_coords_empty=bool(r["coords_empty"]),
                         user_defined=bool(r["user_defined"]))
            w.id = r["id"]  # type: ignore[attr-defined]
            out.append(w)
        return out

    def delete_caches(self, geocodes: Sequence[str]) -> None:
        with self.lock, self.conn:
            for g in geocodes:
                for table in ("caches", "waypoints", "logs", "list_caches"):
                    self.conn.execute("DELETE FROM %s WHERE geocode=?" % table, (g,))

    # -------------------------------------------------------------------- logs
    def save_logs(self, geocode: str, logs: Sequence[LogEntry], replace: bool = True) -> None:
        with self.lock, self.conn:
            self._save_logs(geocode, logs, replace)

    def _save_logs(self, geocode: str, logs: Sequence[LogEntry], replace: bool) -> None:
        if replace:
            self.conn.execute("DELETE FROM logs WHERE geocode=?", (geocode,))
        for i, l in enumerate(logs):
            self.conn.execute(
                "INSERT OR REPLACE INTO logs (geocode, service_log_id, author, author_guid, date, log_type, log, "
                "found_count, friend, favorite, images) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                (geocode, l.service_log_id or "local-%d" % i, l.author, l.author_guid, _ts(l.date), l.log_type,
                 l.log, l.found_count, int(l.friend), int(l.favorite), _images_json(l.images)))

    def get_logs(self, geocode: str, limit: int = 500) -> List[LogEntry]:
        with self.lock:
            rows = self.conn.execute("SELECT * FROM logs WHERE geocode=? ORDER BY date DESC LIMIT ?",
                                     (geocode, limit)).fetchall()
        return [LogEntry(service_log_id=r["service_log_id"], author=r["author"] or "",
                         author_guid=r["author_guid"] or "", date=_dt(r["date"]), log_type=r["log_type"] or "",
                         log=r["log"] or "", found_count=r["found_count"], friend=bool(r["friend"]),
                         favorite=bool(r["favorite"]), images=_images_load(r["images"])) for r in rows]

    # ----------------------------------------------------------------- queries
    @staticmethod
    def _filters(types, hide_found, hide_disabled, hide_archived, params) -> str:
        sql = ""
        if types:
            sql += " AND type_id IN (%s)" % ",".join("?" * len(types))
            params.extend(types)
        if hide_found:
            sql += " AND found=0"
        if hide_disabled:
            sql += " AND disabled=0"
        if hide_archived:
            sql += " AND archived=0"
        return sql

    def in_viewport(self, vp: Viewport, limit: int = 1000, types: Optional[Sequence[str]] = None,
                    hide_found: bool = False, hide_disabled: bool = False,
                    hide_archived: bool = True, center: Optional[Geopoint] = None) -> List[Dict]:
        """Light-weight rows for the map; with `center` the nearest to it come first."""
        params: list = [vp.lat_min, vp.lat_max, vp.lon_min, vp.lon_max]
        sql = ("SELECT %s FROM caches WHERE lat BETWEEN ? AND ? AND lon BETWEEN ? AND ?" % _SUMMARY_COLS
               + self._filters(types, hide_found, hide_disabled, hide_archived, params))
        if center is not None:
            sql += " ORDER BY (lat-?)*(lat-?) + (lon-?)*(lon-?)"
            params += [center.lat, center.lat, center.lon, center.lon]
        sql += " LIMIT ?"
        params.append(limit)
        with self.lock:
            return [dict(r) for r in self.conn.execute(sql, params).fetchall()]

    def count_in_viewport(self, vp: Viewport, types: Optional[Sequence[str]] = None,
                          hide_found: bool = False, hide_disabled: bool = False,
                          hide_archived: bool = True) -> int:
        params: list = [vp.lat_min, vp.lat_max, vp.lon_min, vp.lon_max]
        sql = ("SELECT COUNT(*) FROM caches WHERE lat BETWEEN ? AND ? AND lon BETWEEN ? AND ?"
               + self._filters(types, hide_found, hide_disabled, hide_archived, params))
        with self.lock:
            return self.conn.execute(sql, params).fetchone()[0]

    def clusters_in_viewport(self, vp: Viewport, cell_deg: float, types: Optional[Sequence[str]] = None,
                             hide_found: bool = False, hide_disabled: bool = False,
                             hide_archived: bool = True) -> List[Dict]:
        """Caches grouped in a grid of cell_deg degrees: [{n, lat, lon, geocode, found}, ...]."""
        params: list = [vp.lat_min, vp.lat_max, vp.lon_min, vp.lon_max]
        sql = ("SELECT COUNT(*) AS n, AVG(lat) AS lat, AVG(lon) AS lon, MIN(geocode) AS geocode, "
               "SUM(found) AS found FROM caches WHERE lat BETWEEN ? AND ? AND lon BETWEEN ? AND ?"
               + self._filters(types, hide_found, hide_disabled, hide_archived, params)
               + " GROUP BY CAST((lat + 90.0) / ? AS INTEGER), CAST((lon + 180.0) / ? AS INTEGER)")
        params += [cell_deg, cell_deg]
        with self.lock:
            return [dict(r) for r in self.conn.execute(sql, params).fetchall()]

    def summaries(self, geocodes: Sequence[str]) -> List[Dict]:
        if not geocodes:
            return []
        out: List[Dict] = []
        with self.lock:
            for i in range(0, len(geocodes), 500):          # stay below SQLite's variable limit
                chunk = list(geocodes[i:i + 500])
                rows = self.conn.execute("SELECT %s FROM caches WHERE geocode IN (%s)" % (
                    _SUMMARY_COLS, ",".join("?" * len(chunk))), chunk).fetchall()
                out += [dict(r) for r in rows]
        return out

    def nearby(self, center: Geopoint, radius_km: float = 10.0, limit: int = 200,
               types: Optional[Sequence[str]] = None, hide_found: bool = False,
               hide_disabled: bool = False, hide_archived: bool = True) -> List[Dict]:
        """Rows within radius_km, nearest first, with distance_km and bearing."""
        vp = Viewport.around(center, radius_km)
        rows = self.in_viewport(vp, limit=100000, types=types, hide_found=hide_found,
                                hide_disabled=hide_disabled, hide_archived=hide_archived)
        out = []
        for r in rows:
            here = Geopoint(r["lat"], r["lon"])
            d = center.distance_km(here)
            if d <= radius_km:
                r["distance_km"] = d
                r["bearing"] = center.bearing_to(here)
                out.append(r)
        out.sort(key=lambda r: r["distance_km"])
        return out[:limit]

    def search_text(self, text: str, limit: int = 100) -> List[Dict]:
        like = "%" + text.replace("%", r"\%").replace("_", r"\_") + "%"
        with self.lock:
            rows = self.conn.execute(
                "SELECT %s FROM caches WHERE name LIKE ? ESCAPE '\\' OR geocode LIKE ? ESCAPE '\\' "
                "ORDER BY name LIMIT ?" % _SUMMARY_COLS, (like, like, limit)).fetchall()
        return [dict(r) for r in rows]

    def stats(self) -> Dict:
        """Totals and bounding box of everything stored (for diagnostics)."""
        with self.lock:
            r = self.conn.execute("SELECT COUNT(*), COUNT(lat), MIN(lat), MAX(lat), MIN(lon), MAX(lon) FROM caches").fetchone()
        return {"caches": r[0], "with_coords": r[1], "lat_min": r[2], "lat_max": r[3],
                "lon_min": r[4], "lon_max": r[5]}

    def count_caches(self) -> int:
        with self.lock:
            return self.conn.execute("SELECT COUNT(*) FROM caches").fetchone()[0]

    # ------------------------------------------------------------------- lists
    def create_list(self, name: str) -> int:
        with self.lock, self.conn:
            self.conn.execute("INSERT OR IGNORE INTO lists (name) VALUES (?)", (name,))
            return self.conn.execute("SELECT id FROM lists WHERE name=?", (name,)).fetchone()[0]

    def get_lists(self) -> List[Dict]:
        with self.lock:
            rows = self.conn.execute(
                "SELECT l.id, l.name, COUNT(lc.geocode) AS count FROM lists l "
                "LEFT JOIN list_caches lc ON lc.list_id=l.id GROUP BY l.id ORDER BY l.name").fetchall()
        return [dict(r) for r in rows]

    def rename_list(self, list_id: int, name: str) -> None:
        with self.lock, self.conn:
            self.conn.execute("UPDATE lists SET name=? WHERE id=?", (name, list_id))

    def delete_list(self, list_id: int, delete_caches: bool = False) -> None:
        with self.lock, self.conn:
            geocodes = [r[0] for r in self.conn.execute(
                "SELECT geocode FROM list_caches WHERE list_id=?", (list_id,)).fetchall()]
            self.conn.execute("DELETE FROM list_caches WHERE list_id=?", (list_id,))
            self.conn.execute("DELETE FROM lists WHERE id=?", (list_id,))
            if delete_caches:
                for g in geocodes:
                    if not self.conn.execute("SELECT 1 FROM list_caches WHERE geocode=?", (g,)).fetchone():
                        for table in ("caches", "waypoints", "logs"):
                            self.conn.execute("DELETE FROM %s WHERE geocode=?" % table, (g,))

    def add_to_list(self, list_id: int, geocodes: Sequence[str]) -> None:
        with self.lock, self.conn:
            self.conn.executemany("INSERT OR IGNORE INTO list_caches (list_id, geocode) VALUES (?,?)",
                                  [(list_id, g) for g in geocodes])

    def remove_from_list(self, list_id: int, geocodes: Sequence[str]) -> None:
        with self.lock, self.conn:
            self.conn.executemany("DELETE FROM list_caches WHERE list_id=? AND geocode=?",
                                  [(list_id, g) for g in geocodes])

    def list_caches(self, list_id: int) -> List[Dict]:
        with self.lock:
            rows = self.conn.execute(
                "SELECT %s FROM caches WHERE geocode IN (SELECT geocode FROM list_caches WHERE list_id=?) "
                "ORDER BY name" % _SUMMARY_COLS, (list_id,)).fetchall()
        return [dict(r) for r in rows]

    # ------------------------------------------- offline logs / geocaching.com field notes
    def set_offline_log(self, geocode: str, log_type: str, date: Optional[datetime] = None,
                        text: str = "", favorite: bool = False) -> None:
        if log_type not in FIELD_NOTE_TYPES:
            raise ValueError("unknown log type %r" % log_type)
        with self.lock, self.conn:
            self.conn.execute(
                "INSERT OR REPLACE INTO offline_logs (geocode, log_type, date, text, favorite) VALUES (?,?,?,?,?)",
                (geocode, log_type, _ts(date or datetime.now(timezone.utc)), text, int(favorite)))

    def get_offline_log(self, geocode: str) -> Optional[Dict]:
        with self.lock:
            r = self.conn.execute("SELECT * FROM offline_logs WHERE geocode=?", (geocode,)).fetchone()
        return dict(r) if r else None

    def list_offline_logs(self) -> List[Dict]:
        with self.lock:
            rows = self.conn.execute(
                "SELECT o.*, c.name FROM offline_logs o LEFT JOIN caches c ON c.geocode=o.geocode "
                "ORDER BY o.date").fetchall()
        return [dict(r) for r in rows]

    def delete_offline_log(self, geocode: str) -> None:
        with self.lock, self.conn:
            self.conn.execute("DELETE FROM offline_logs WHERE geocode=?", (geocode,))

    def export_field_notes(self, geocodes: Optional[Sequence[str]] = None) -> str:
        """Text for geocache_visits.txt, one line per log:  GC12345,2026-10-05T14:30Z,Found it,"text"

        Upload it on geocaching.com ("Field Notes"). Write the file as UTF-16 (little endian, with BOM)
        - see write_field_notes(). !! format from memory - verify with a test upload !!"""
        lines = []
        for r in self.list_offline_logs():
            if geocodes is not None and r["geocode"] not in geocodes:
                continue
            d = _dt(r["date"]) or _EPOCH
            when = "%04d-%02d-%02dT%02d:%02dZ" % (d.year, d.month, d.day, d.hour, d.minute)
            text = (r["text"] or "").replace('"', "'")
            lines.append('%s,%s,%s,"%s"' % (r["geocode"], when, r["log_type"], text))
        return "\r\n".join(lines) + ("\r\n" if lines else "")

    def write_field_notes(self, path: str, geocodes: Optional[Sequence[str]] = None) -> int:
        text = self.export_field_notes(geocodes)
        with open(path, "wb") as f:
            f.write(b"\xff\xfe" + text.encode("utf-16-le"))
        return text.count("\r\n")
