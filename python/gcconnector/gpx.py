"""Import of geocaching.com GPX files (Pocket Queries, single-cache GPX, additional waypoints).

Streaming (iterparse), so large pocket queries do not need much memory.
This is the fully legitimate offline path: download a Pocket Query on the website
and import it - no scraping involved.
"""
import re
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from typing import Callable, Dict, Iterator, List, Optional, Tuple

from .enums import cache_type_by_pattern
from .gcutils import gc_like_code_to_gc_like_id, log_id_to_log_code
from .geopoint import Geopoint
from .models import Geocache, LogEntry, Waypoint

_SIZE_BY_NAME = {"micro": "micro", "small": "small", "regular": "regular", "large": "large",
                 "not chosen": "not_chosen", "virtual": "virtual", "other": "other",
                 "nano": "nano", "unknown": "unknown"}


def _ln(tag: str) -> str:
    """Local name without namespace."""
    return tag.rsplit("}", 1)[-1] if "}" in tag else tag


def _text(el: Optional[ET.Element]) -> str:
    return (el.text or "").strip() if el is not None else ""


def _child(el: ET.Element, name: str) -> Optional[ET.Element]:
    for ch in el:
        if _ln(ch.tag) == name:
            return ch
    return None


def _parse_iso(text: str) -> Optional[datetime]:
    t = (text or "").strip().rstrip("Z")
    if not t:
        return None
    t = re.sub(r"\.\d+", "", t)
    for fmt in ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M", "%Y-%m-%d"):
        try:
            return datetime.strptime(t, fmt).replace(tzinfo=timezone.utc)
        except ValueError:
            continue
    return None


def _bool(value: Optional[str]) -> bool:
    return (value or "").strip().lower() == "true"


def _parse_log(el: ET.Element) -> LogEntry:
    raw_id = el.get("id", "")
    finder = _child(el, "finder")
    return LogEntry(
        service_log_id=log_id_to_log_code(int(raw_id)) if raw_id.isdigit() else raw_id,
        author=_text(finder), author_guid=finder.get("id", "") if finder is not None else "",
        date=_parse_iso(_text(_child(el, "date"))), log_type=_text(_child(el, "type")),
        log=_text(_child(el, "text")))


def _parse_cache(wpt: ET.Element, cache_el: ET.Element) -> Optional[Geocache]:
    code = _text(_child(wpt, "name")).upper()
    if not code:
        return None
    c = Geocache(geocode=code, detailed=True)
    try:
        c.coords = Geopoint(float(wpt.get("lat")), float(wpt.get("lon")))
    except (TypeError, ValueError):
        c.coords = None
    c.hidden = _parse_iso(_text(_child(wpt, "time")))
    c.found = "found" in _text(_child(wpt, "sym")).lower()

    cid = cache_el.get("id", "")
    c.cache_id = cid if cid.isdigit() else str(gc_like_code_to_gc_like_id(code))
    c.archived = _bool(cache_el.get("archived"))
    c.disabled = not _bool(cache_el.get("available") or "True")

    owner_name = ""
    country = state = ""
    attrs: List[str] = []
    for ch in cache_el:
        n, t = _ln(ch.tag), _text(ch)
        if n == "name":
            c.name = t
        elif n == "placed_by":
            owner_name = owner_name or t
        elif n == "owner":
            c.owner_display_name = c.owner_user_id = t
            c.owner_guid = ch.get("id", "")
        elif n == "type":
            c.type_id = cache_type_by_pattern(t).id
        elif n == "container":
            c.size_id = _SIZE_BY_NAME.get(t.lower(), "unknown")
        elif n == "difficulty":
            c.difficulty = _to_float(t)
        elif n == "terrain":
            c.terrain = _to_float(t)
        elif n == "country":
            country = t
        elif n == "state":
            state = t
        elif n == "short_description":
            c.short_description = t
        elif n == "long_description":
            c.description = t
        elif n == "encoded_hints":
            c.hint = t
        elif n == "attributes":
            for a in ch:
                aid = a.get("id")
                if aid and aid.isdigit():
                    attrs.append("gcattr%s_%s" % (aid, "yes" if a.get("inc", "1") == "1" else "no"))
        elif n == "logs":
            c.logs = [_parse_log(l) for l in ch if _ln(l.tag) == "log"]
        elif n == "travelbugs":
            pass  # inventory is refreshed online
    if not c.owner_display_name:
        c.owner_display_name = c.owner_user_id = owner_name
    c.attributes = attrs
    c.location = ", ".join(x for x in (state, country) if x)
    return c


def _to_float(text: str) -> float:
    try:
        return float(text.replace(",", "."))
    except ValueError:
        return 0.0


def _parse_additional_waypoint(wpt: ET.Element) -> Optional[Tuple[str, Waypoint]]:
    """Additional waypoint: name like 'PK12345' belongs to cache 'GC12345'."""
    name = _text(_child(wpt, "name")).upper()
    if len(name) < 3:
        return None
    w = Waypoint(name=_text(_child(wpt, "desc")) or name,
                 type_id=_text(_child(wpt, "sym")) or None, prefix=name[:2], lookup=name,
                 note=_text(_child(wpt, "cmt")))
    try:
        w.coords = Geopoint(float(wpt.get("lat")), float(wpt.get("lon")))
    except (TypeError, ValueError):
        w.original_coords_empty = True
    return "GC" + name[2:], w


def iter_gpx(path: str) -> Iterator[Tuple[str, object]]:
    """Yields ('cache', Geocache) or ('waypoint', (geocode, Waypoint))."""
    for _, el in ET.iterparse(path, events=("end",)):
        if _ln(el.tag) != "wpt":
            continue
        cache_el = next((ch for ch in el if _ln(ch.tag) == "cache"), None)
        if cache_el is not None:
            c = _parse_cache(el, cache_el)
            if c is not None:
                yield "cache", c
        else:
            wp = _parse_additional_waypoint(el)
            if wp is not None:
                yield "waypoint", wp
        el.clear()


def import_gpx(db, path: str, list_id: Optional[int] = None,
               progress: Optional[Callable[[int], None]] = None) -> Dict[str, int]:
    """Import a GPX file into the database; optionally add all caches to a list."""
    stats = {"caches": 0, "waypoints": 0, "skipped_waypoints": 0}
    geocodes: List[str] = []
    for kind, item in iter_gpx(path):
        if kind == "cache":
            db.save_cache(item)
            geocodes.append(item.geocode)
            stats["caches"] += 1
            if progress and stats["caches"] % 25 == 0:
                progress(stats["caches"])
        else:
            geocode, wp = item
            if db.has_cache(geocode):
                db.add_waypoint(geocode, wp)
                stats["waypoints"] += 1
            else:
                stats["skipped_waypoints"] += 1
    if list_id is not None and geocodes:
        db.add_to_list(list_id, geocodes)
    return stats
