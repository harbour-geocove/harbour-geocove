"""Port of c:geo's GCParser.java (read-only parts).

Ported: cache detail page, waypoints, spoilers, gallery, inventory, log
counts, logbook JSON, live-map JSON, pocket-query map search, bookmark lists.
Not ported yet: trackable page, watchlist/favorites/personal-note/ignore/
modified-coordinate write operations and the pocket-query list (Jsoup table).
Map / filter search lives in search.py + webapi.py.

`session` is a gcconnector.login.GCLogin instance (get_request_logged / get_text /
parse_date / user_name).
"""
import html
import json
import re
from datetime import datetime
from typing import Callable, Dict, List, Optional, Tuple

from . import constants as C
from .enums import cache_type_by_wpt
from .gcutils import gc_like_code_to_gc_like_id, log_id_to_log_code
from .geopoint import Geopoint, GeopointError
from .login import get_caches_count, get_username  # noqa: F401  (re-exported)
from .models import (Geocache, Image, LogEntry, StatusCode, Trackable,
                     Waypoint)
from .webapi import GC_ID_TO_SIZE, get_trackables_of_cache
from .textutils import (decode, get_match, matches, remove_control_characters,
                        replace_whitespace, split_whole, strip_html)

Progress = Optional[Callable[[str], None]]
DateParser = Optional[Callable[[str], datetime]]


def _progress(cb: Progress, step: str) -> None:
    if cb:
        cb(step)


# ------------------------------------------------------------------ live map JSON
def parse_map(page_content: Optional[str], user_name: str = "") -> List[Geocache]:
    if not page_content or not page_content.strip():
        return []
    features = json.loads(page_content)["data"]["layer"]["features"]
    caches = []
    for feature in features:
        props = feature.get("properties")
        if not props:
            continue
        cache = Geocache(
            name=props["name"], geocode=props["key"], type_id=cache_type_by_wpt(str(props["wptid"])).id,
            archived=bool(props["archived"]), disabled=not props["available"],
            coords=Geopoint(float(props["lat"]), float(props["lng"])))
        icon = props.get("icon", "")
        if icon == "MyHide":
            cache.owner_user_id = user_name
        elif icon == "MyFind":
            cache.found = True
        elif icon.startswith("solved"):
            cache.user_modified_coords = True
        caches.append(cache)
    return caches


def search_by_map(session, params: Dict[str, str], context: str) -> List[Geocache]:
    page = session.get_request_logged(C.URL_LIVE_MAP, params)
    if not page or not page.strip():
        return []
    token = get_match(page, C.PATTERN_SESSIONTOKEN, default="")
    if not token:
        return []
    q = dict(params)
    q["st"] = token
    data = session.get_request_logged("https://tiles01.geocaching.com/map." + context, q)
    try:
        caches = parse_map(data, session.user_name or "")
    except (ValueError, KeyError, TypeError):
        return []
    session.get_login_status(page)
    return caches


def search_by_pocket_query(session, short_guid: str, pq_hash: str) -> List[Geocache]:
    if not pq_hash:
        return []
    return search_by_map(session, {"pq": short_guid, "hash": pq_hash}, "pq")


# ---------------------------------------------------------------- cache details page
def _to_float(value: Optional[str], default: float = 0.0) -> float:
    try:
        return float(value.replace("_", ".").replace(",", ".")) if value else default
    except ValueError:
        return default


def _format_event_time(m) -> str:
    """Rough equivalent of Formatter.formatGCEventTime from PATTERN_EVENTTIMES."""
    def one(ampm_a, h, mi, ampm_b):
        h, mi = int(h), int(mi)
        marker = (ampm_a + ampm_b).strip().upper()
        if marker == "PM" and h < 12:
            h += 12
        elif marker == "AM" and h == 12:
            h = 0
        return "%02d:%02d" % (h, mi)
    return "%s - %s" % (one(m.group(1), m.group(2), m.group(3), m.group(4)),
                        one(m.group(5), m.group(6), m.group(7), m.group(8)))


def parse_cache_from_text(page_in: Optional[str], date_parser: DateParser = None,
                          progress: Progress = None) -> Tuple[StatusCode, Optional[Geocache]]:
    """Parse a cache detail page. Inline logs are NOT parsed here."""
    _progress(progress, "details")
    if not page_in or not page_in.strip():
        return StatusCode.UNKNOWN_ERROR, None
    if C.STRING_404_FILE_NOT_FOUND in page_in:
        return StatusCode.CACHE_NOT_FOUND, None
    if C.STRING_UNPUBLISHED_OTHER in page_in or C.STRING_UNPUBLISHED_FROM_SEARCH in page_in:
        return StatusCode.UNPUBLISHED_CACHE, None

    if C.STRING_PREMIUMONLY in page_in:
        cache = Geocache(premium_only=True)
        m = C.PATTERN_PREMIUMONLY_CACHETYPE.search(page_in)
        if m:
            cache.type_id = cache_type_by_wpt(m.group(1)).id
            if m.group(2) == "disabled":
                cache.disabled = True
        cache.name = strip_html(get_match(page_in, C.PATTERN_PREMIUMONLY_CACHENAME, True, 1, ""))
        cache.geocode = get_match(page_in, C.PATTERN_PREMIUMONLY_GEOCODE, True, 1, "")
        cache.difficulty = _to_float(get_match(page_in, C.PATTERN_PREMIUMONLY_DIFFICULTY, True, 1, "0"))
        cache.terrain = _to_float(get_match(page_in, C.PATTERN_PREMIUMONLY_TERRAIN, True, 1, "0"))
        cache.size_id = get_match(page_in, C.PATTERN_PREMIUMONLY_SIZE, True, 1, "")
        return StatusCode.PREMIUM_ONLY, cache

    cache_name = strip_html(get_match(page_in, C.PATTERN_NAME, True, 1, ""))
    if C.STRING_UNKNOWN_ERROR.lower() == cache_name.lower():
        return StatusCode.UNKNOWN_ERROR, None

    # personal note first (has meaningful line breaks), then collapse whitespace
    note = ""
    m = C.PATTERN_PERSONALNOTE.search(page_in)
    if m:
        note = html.unescape(m.group(1).strip())

    page = replace_whitespace(page_in)

    cache = Geocache()
    cache.disabled = C.STRING_STATUS_DISABLED in page
    cache.archived = C.STRING_STATUS_ARCHIVED in page or C.STRING_STATUS_LOCKED in page
    cache.premium_only = matches(page, C.PATTERN_PREMIUMMEMBERS)
    cache.favorite = matches(page, C.PATTERN_IS_FAVORITE)
    cache.geocode = get_match(page, C.PATTERN_GEOCODE, True, 1, cache.geocode)
    cache.cache_id = str(gc_like_code_to_gc_like_id(cache.geocode))
    cache.guid = get_match(page, C.PATTERN_GUID, True, 1, cache.guid)
    cache.watchlist_count = get_watchlist_count(page)
    cache.name = cache_name
    cache.owner_user_id = decode(get_match(page, C.PATTERN_OWNER_USERID, True, 1, cache.owner_user_id))
    cache.user_modified_coords = False

    pos = page.find(C.STRING_CACHEDETAILS)
    if pos == -1:
        return StatusCode.UNKNOWN_ERROR, None
    table_inside = page[pos:]

    if table_inside.strip():
        cache.terrain = _to_float(get_match(table_inside, C.PATTERN_TERRAIN, True, 1, None), cache.terrain)
        cache.difficulty = _to_float(get_match(table_inside, C.PATTERN_DIFFICULTY, True, 1, None), cache.difficulty)
        cache.owner_display_name = html.unescape(
            get_match(table_inside, C.PATTERN_OWNER_DISPLAYNAME, True, 1, cache.owner_display_name))
        cache.owner_guid = get_match(table_inside, C.PATTERN_OWNER_GUID, True, 2, cache.owner_guid, False)

        # hidden / event date
        if date_parser:
            for pattern in (C.PATTERN_HIDDEN, C.PATTERN_HIDDENEVENT):
                text = get_match(table_inside, pattern, True, 1, None)
                if text:
                    try:
                        cache.hidden = date_parser(text)
                    except ValueError:
                        cache.hidden = None
                if cache.hidden is not None:
                    break

        try:
            cache.favorite_points = int(get_match(table_inside, C.PATTERN_FAVORITECOUNT, True, 1, "0"))
        except ValueError:
            pass
        cache.size_id = get_match(table_inside, C.PATTERN_SIZE, True, 1, cache.size_id)

    cache.found = matches(page, C.PATTERN_FOUND)
    cache.dnf = matches(page, C.PATTERN_DNF)
    cache.type_id = cache_type_by_wpt(get_match(page, C.PATTERN_TYPE, True, 1, None)).id
    cache.on_watchlist = matches(page, C.PATTERN_WATCHLIST)

    latlon = get_match(page, C.PATTERN_LATLON, True, 1, "")  # only if logged in
    if latlon:
        try:
            cache.coords = Geopoint.parse(latlon)
        except GeopointError:
            pass

    cache.location = get_match(page, C.PATTERN_LOCATION, True, 1, "")

    hint = get_match(page, C.PATTERN_HINT, False, 1, None)
    if hint is not None:
        hint = C.PATTERN_LINEBREAK.sub("\n", hint)
        cache.hint = hint.replace("</p>", "").strip()

    cache.personal_note = note

    # short description
    if cache.is_event_cache():
        short = ""
        m = C.PATTERN_EVENTTIMES.search(table_inside)
        if m and cache.hidden:
            short = "<b>%s, %s</b>" % (cache.hidden.strftime("%d %B %Y"), _format_event_time(m))
    else:
        short = get_match(page, C.PATTERN_SHORTDESC, True, 1, "")
    cache.short_description = short

    # long description
    long_desc = get_match(page, C.PATTERN_DESC, True, 1, "")
    related = get_match(page, C.PATTERN_RELATED_WEB_PAGE, True, 1, "")
    if related:
        related = '<br/><br/><a href="%s"><b>%s</b></a>' % (related, related)
    gallery_link = ""
    gallery_images = get_gallery_count(page)
    if gallery_images > 0:
        gallery_link = '<br/><br/><a href="%s"><b>%s</b></a>' % (
            "https://www.geocaching.com/seek/gallery.aspx?guid=" + cache.guid,
            "Gallery (%d)" % gallery_images)
    gc_checker = "<!--GC checker-->" if C.PATTERN_GC_CHECKER in page else ""
    cache.description = long_desc + related + gallery_link + gc_checker

    # attributes (the last block is the official one)
    try:
        attributes: List[str] = []
        for block in C.PATTERN_ATTRIBUTES.finditer(page):
            pre = block.group(1)
            if pre is None:
                continue
            attributes = []
            for a in C.PATTERN_ATTRIBUTESINSIDE.finditer(pre):
                if a.group(2).lower() == "blank":
                    continue
                attribute = a.group(2).lower()
                image_name = a.group(1).strip()
                if image_name:
                    start, end = image_name.rfind("/"), image_name.rfind(".")
                    if start >= 0 and end >= 0:
                        attribute = image_name[start + 1:end].replace("-", "_").lower()
                attributes.append(attribute)
        cache.attributes = attributes
    except (AttributeError, ValueError):
        pass

    # spoilers + background image
    _progress(progress, "spoilers")
    spoilers = parse_spoilers(page)
    bg = C.PATTERN_BACKGROUND_IMAGE.search(page)
    if bg and all(i.url != bg.group(1) for i in spoilers):
        spoilers.append(Image(url=bg.group(1), title="Listing background",
                              description="Background image of the cache listing"))
    cache.spoilers = spoilers

    inventory = parse_inventory(page)
    if inventory is not None:
        cache.inventory = inventory

    # log counts (keyed by the numeric log type id found in the icon name)
    counts = get_match(page, C.PATTERN_COUNTLOGS, True, 1, None)
    if counts:
        for m in C.PATTERN_COUNTLOG.finditer(counts):
            num = m.group(2).replace(".", "").replace(",", "")
            if m.group(1) and num.isdigit():
                cache.log_counts[m.group(1)] = int(num)

    # waypoints
    cache.waypoints = []
    orig = get_match(page, C.PATTERN_LATLON_ORIG, False, 1, None)
    if orig:
        try:
            cache.create_original_waypoint(Geopoint.parse(orig))
        except GeopointError:
            pass
    if C.WPT_SECTION_START in page:
        _progress(progress, "waypoints")
        parse_waypoints(cache, page)

    if not cache.geocode.strip():
        return StatusCode.UNKNOWN_ERROR, None
    return StatusCode.NO_ERROR, cache


def parse_waypoints(cache: Geocache, page: str) -> None:
    begin = page.find(C.WPT_SECTION_START)
    wp_list = page[begin:]
    if "No additional waypoints to display." in wp_list:
        return
    end = wp_list.find("</table>")
    if end > -1:
        wp_list = wp_list[:end]
    b, e = wp_list.find("<tbody>"), wp_list.find("</tbody>")
    if b >= 0 and e >= 0:
        wp_list = wp_list[b + 7:e]

    items = split_whole(wp_list, "<tr")
    # each waypoint = 2 rows: 1. type/coordinates/..., 2. note
    j = 0
    while j < len(items):
        wp = split_whole(items[j], "<td")
        if len(wp) < 7:
            j += 1
            continue
        name = get_match(wp[5], C.PATTERN_WPNAME, True, 1, "Waypoint", True)
        wp_type = get_match(wp[2], C.PATTERN_WPTYPE, True, 1, None)
        waypoint = Waypoint(name=name, type_id=wp_type)
        waypoint.prefix = get_match(wp[3], C.PATTERN_WPPREFIXORLOOKUPORLATLON, True, 2, waypoint.prefix, False)
        waypoint.lookup = get_match(wp[4], C.PATTERN_WPPREFIXORLOOKUPORLATLON, True, 2, waypoint.lookup, False)
        latlon = strip_html(get_match(wp[6], C.PATTERN_WPPREFIXORLOOKUPORLATLON, False, 2, "", False)).strip()
        if not latlon.startswith("???"):
            try:
                waypoint.coords = Geopoint.parse(latlon)
            except GeopointError:
                waypoint.original_coords_empty = True
        else:
            waypoint.original_coords_empty = True

        j += 1  # second row
        if j >= len(items):
            cache.add_waypoint(waypoint)
            return
        note_cols = split_whole(items[j], "<td")
        if len(note_cols) < 4:
            j += 1
            continue
        note_text = get_match(note_cols[3], C.PATTERN_WPNOTE, True, 1, waypoint.note)
        waypoint.note = note_text if note_text and note_text.strip() else ""
        cache.add_waypoint(waypoint)
        j += 1


def parse_spoilers(page: str) -> List[Image]:
    images = []
    for m in C.PATTERN_SPOILER_IMAGE.finditer(page):
        title = m.group(2) if m.group(2) is not None else "Spoiler image"
        description = "Spoiler image"
        if m.group(3) is not None:
            description += ": " + m.group(3)
        images.append(Image(url=m.group(1), title=title, description=description))
    return images


def parse_inventory(page: str) -> Optional[List[Trackable]]:
    try:
        m = C.PATTERN_INVENTORY.search(page)
        if not m:
            return None
        pre = m.group(0)
        items = []
        if pre.strip():
            for t in C.PATTERN_INVENTORYINSIDE.finditer(pre):
                is_code = t.group(1) == "TB"
                items.append(Trackable(geocode=t.group(2) if is_code else None,
                                       guid=None if is_code else t.group(2),
                                       name=t.group(3)))
        return items
    except (AttributeError, ValueError):
        return None


def parse_gallery_images(page: str, take: Callable[[str], bool] = lambda url: True,
                         dedupe: bool = True) -> List[Image]:
    images = []
    for m in C.PATTERN_GALLERY_IMAGE.finditer(page):
        date, url, title = m.group(1), m.group(2), (m.group(3) or "").strip()
        description = "Gallery image"
        if date and date.strip():
            description += ": " + date
        if take(url):
            images.append(Image(url=url, title=title, description=description))
    return dedupe_images(images) if dedupe else images


_GALLERY_IMG = re.compile(r"""(?:https?:)?//img(?:cdn)?\.geocaching\.com/[^\s"'<>()]+?\.(?:jpe?g|png|gif|bmp)""", re.I)
_SIZE_DIR = re.compile(r"/(thumb|display|large|small|medium|original)/")
_SIZE_QUALITY = {"large": 4, "original": 4, "display": 3, "medium": 2, "small": 1, "thumb": 0}


def picture_key(url: str) -> str:
    """Identity of a picture: its file name without extension (a UUID). The same picture appears with different
    hosts, size directories, extension case and query strings, so none of those may be part of the key."""
    name = url.split("?", 1)[0].split("#", 1)[0].rstrip("/").rsplit("/", 1)[-1]
    return re.sub(r"\.(jpe?g|png|gif|bmp)$", "", name, flags=re.I).lower()


def dedupe_images(images: List[Image], report: Optional[list] = None) -> List[Image]:
    """One entry per picture: the gallery page lists pictures more than once. The first entry (in page order)
    is kept; a missing title is taken from a later duplicate. `report` collects (kept url, dropped url) pairs."""
    result: List[Image] = []
    index = {}
    for image in images:
        key = picture_key(image.url)
        if key in index:
            kept = result[index[key]]
            if report is not None:
                report.append((kept.url, image.url))
            if not kept.title and image.title:
                kept.title = image.title
            if not kept.description and image.description:
                kept.description = image.description
            continue
        index[key] = len(result)
        result.append(image)
    return result


def parse_gallery_images_tolerant(html: str) -> List[Image]:
    """Fallback for when the markup of the gallery page differs from what c:geo expects: every picture of
    a cache found anywhere on the page (one entry per picture, the largest size wins)."""
    best = {}      # picture id -> (quality, url)
    order = []
    for m in _GALLERY_IMG.finditer(html or ""):
        url = m.group(0)
        if url.startswith("//"):
            url = "https:" + url
        if "/cache/" not in url:           # avatars, site graphics
            continue
        size = _SIZE_DIR.search(url)
        key = picture_key(url)                 # same picture whatever size / cdn host
        quality = _SIZE_QUALITY.get(size.group(1), 2) if size else 2
        if key not in best:
            order.append(key)
            best[key] = (quality, url)
        elif quality > best[key][0]:
            best[key] = (quality, url)
    return [Image(url=best[k][1], title="", description="Gallery image", category="listing") for k in order]


def fetch_gallery(session, guid: str):
    """First page of the cache gallery (as c:geo's addImagesFromGallery).

    Returns (images, info) or None when the page can't be read; `info` says what was found, so that an empty
    or odd result can be explained. If c:geo's strict parser finds nothing the tolerant one is tried."""
    page = session.get_request_logged("https://www.geocaching.com/seek/gallery.aspx", {"guid": guid})
    if not page:
        return None
    raw = parse_gallery_images(page, lambda url: True, dedupe=False)
    dropped: list = []
    images = dedupe_images(raw, dropped)
    strict = len(images)
    if not images:
        images = parse_gallery_images_tolerant(page)
    title = re.search(r"<title>(.*?)</title>", page, re.S | re.I)
    info = "page %d B, title %r, image urls %d, strict parser %d entries -> %d pictures, tolerant parser %d" % (
        len(page), (title.group(1).strip()[:60] if title else None), len(_GALLERY_IMG.findall(page)),
        len(raw), strict, len(images) if not strict else 0)
    if dropped:
        info += "\nduplicate e.g.: %s | %s" % (dropped[0][0][-70:], dropped[0][1][-70:])
    return images, info


def _count(page: Optional[str], pattern, group: int = 1) -> int:
    value = get_match(page, pattern, True, group, "notFound", False)
    if value == "notFound":
        return -1
    try:
        return int(value)
    except ValueError:
        return -1


def get_watchlist_count(page: Optional[str]) -> int:
    return _count(page, C.PATTERN_WATCHLIST_COUNT)


def get_gallery_count(page: Optional[str]) -> int:
    return _count(page, C.PATTERN_GALLERY_COUNT)


# ------------------------------------------------------------------------- requests
def request_html_page(session, geocode: Optional[str] = None, guid: Optional[str] = None) -> Optional[str]:
    if geocode:
        return session.get_request_logged("https://www.geocaching.com/geocache/" + geocode,
                                          {"decrypt": "y"}, remove_whitespace=False)
    if guid:
        return session.get_request_logged("https://www.geocaching.com/seek/cache_details.aspx",
                                          {"decrypt": "y", "guid": guid})
    return None


def parse_user_token(page: Optional[str]) -> str:
    return get_match(page, C.PATTERN_USERTOKEN, True, 1, "")


def parse_request_verification_token(page: Optional[str]) -> str:
    return get_match(page, C.PATTERN_REQUESTVERIFICATIONTOKEN, True, 1, "")


# ------------------------------------------------------------------------------ logs
LOG_FILTERS = {"all": None, "friends": "sf", "own": "sp", "owner": "showOwnerOnly"}

_FOUND_TYPES = {"found it", "attended", "webcam photo taken"}
_DNF_TYPE = "didn't find it"


def parse_logs_json(text: str, date_parser: Callable[[str], datetime],
                    mark_as_friends: bool = False) -> List[LogEntry]:
    try:
        resp = json.loads(text)
    except ValueError:
        return []
    if resp.get("status") != "success":
        return []
    logs = []
    for entry in resp.get("data") or []:
        try:
            date = date_parser(entry["Visited"])
        except (KeyError, ValueError, TypeError):
            continue
        lat_lon = entry.get("LatLonString") or ""
        log_text = (lat_lon + "<br/><br/>" if lat_lon else "") + remove_control_characters(entry.get("LogText", ""))
        log = LogEntry(
            service_log_id=log_id_to_log_code(int(entry.get("LogID") or 0)),
            author=remove_control_characters(entry.get("UserName", "")),
            author_guid=entry.get("AccountGuid", ""),
            date=date, log_type=entry.get("LogType", ""), log=log_text,
            found_count=int(entry.get("GeocacheFindCount") or 0),
            friend=mark_as_friends, favorite=bool(entry.get("FavoritePointUsed")))
        for img in entry.get("Images") or []:
            description = img.get("Descr") or ""
            if "Geocaching®" in description and len(description) < 60:
                description = ""
            log.images.append(Image(
                url="https://imgcdn.geocaching.com/cache/log/large/" + img.get("FileName", ""),
                title=remove_control_characters(img.get("Name", "")),
                description=description, category="log"))
        logs.append(log)
    return logs


def get_logs(session, user_token: str, which: str = "all",
             take: int = C.NUMBER_OF_LOGS) -> List[LogEntry]:
    if not user_token:
        return []
    params = {"tkn": user_token, "idx": "1", "num": str(take), "decrypt": "false"}
    flt = LOG_FILTERS[which]
    if flt:
        params[flt] = "true"
    text = session.get_text("https://www.geocaching.com/seek/geocache.logbook", params)
    if not text:
        return []
    return parse_logs_json(text, session.parse_date, which != "all")


def _merge_modified_logs(merged: List[LogEntry], to_merge: List[LogEntry]) -> None:
    by_id = {l.service_log_id: i for i, l in enumerate(merged)}
    for log in to_merge:
        idx = by_id.get(log.service_log_id)
        if idx is None:
            merged.append(log)
        else:  # keep the favorite flag, which is only in the listing logs
            log.favorite = merged[idx].favorite
            merged[idx] = log


def fetch_logs(session, geocode: str, friend_logs: bool = False) -> Tuple[List[LogEntry], List[LogEntry]]:
    """Returns (merged logs, own logs)."""
    page = session.get_request_logged("https://www.geocaching.com/seek/geocache_logs.aspx", {"code": geocode})
    token = parse_user_token(page)
    logs = get_logs(session, token, "all")
    own = get_logs(session, token, "own")
    friends = get_logs(session, token, "friends") if friend_logs else []
    owner = get_logs(session, token, "owner")

    special, seen = [], set()
    for log in friends + own + owner:
        if log.service_log_id and log.service_log_id in seen:
            continue
        seen.add(log.service_log_id)
        log.friend = True
        special.append(log)
    if special:
        _merge_modified_logs(logs, special)
    logs.sort(key=lambda l: l.date or datetime.min, reverse=True)
    return logs, own


# ------------------------------------------------------------------- high level API
def load_cache(session, geocode: str, friend_logs: bool = False,
               progress: Progress = None) -> Tuple[StatusCode, Optional[Geocache]]:
    """Fetch and parse a full cache (details, logs). Equivalent of GCParser.parseCache
    + getExtraOnlineInfo (without the offline-log merge)."""
    page = request_html_page(session, geocode=geocode)
    status, cache = parse_cache_from_text(page, session.parse_date, progress)
    if status != StatusCode.NO_ERROR:
        return status, cache
    _progress(progress, "logs")
    cache.logs, own = fetch_logs(session, cache.geocode, friend_logs)
    inventory = get_trackables_of_cache(session, cache.geocode)   # web api: includes tracking codes
    if inventory:
        cache.inventory = inventory
    if cache.found or cache.dnf:
        for log in own:
            lt = log.log_type.lower()
            if lt in _FOUND_TYPES or (not cache.found and cache.dnf and lt == _DNF_TYPE):
                cache.visited_date = log.date
                break
    return StatusCode.NO_ERROR, cache


# ---------------------------------------------------------------------- bookmark lists
def search_bookmark_lists(session) -> Optional[List[dict]]:
    text = session.get_request_logged("https://www.geocaching.com/api/proxy/web/v1/lists",
                                      {"skip": "0", "take": "100", "type": "bm"})
    if not text or not text.strip():
        return None
    try:
        rows = json.loads(text)["data"]
        result = []
        for row in rows:
            stamp = row["lastUpdateUtc"].rstrip("Z")
            result.append({"guid": row["referenceCode"], "name": row["name"],
                           "count": int(row["count"]),
                           "last_update": datetime.fromisoformat(stamp)})
        return result
    except (ValueError, KeyError, TypeError):
        return None


def search_by_bookmark_list(session, bm_guid: str, already_taken: int = 0) -> Optional[Tuple[List[Geocache], int]]:
    """Returns (caches, left_to_fetch)."""
    url = "https://www.geocaching.com/api/proxy/web/v1/lists/%s/geocaches" % bm_guid
    text = session.get_request_logged(url, {"skip": str(already_taken), "take": "1000"})
    if not text or not text.strip():
        return None
    try:
        data = json.loads(text)
        caches = []
        for row in data["data"]:
            state = row["state"]
            caches.append(Geocache(
                name=row["name"], geocode=row["referenceCode"], owner_display_name=row["owner"],
                difficulty=float(row["difficulty"]), terrain=float(row["terrain"]),
                size_id=GC_ID_TO_SIZE.get(int(row["containerType"]), "unknown"), type_id=cache_type_by_wpt(str(row["geocacheType"])).id,
                archived=bool(state["isArchived"]), disabled=not state["isAvailable"],
                premium_only=bool(state["isPremiumOnly"])))
        left = int(data["total"]) - (already_taken + len(caches))
        return caches, left
    except (ValueError, KeyError, TypeError):
        return None
