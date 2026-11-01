"""Port of c:geo's GCWebAPI.java (geocaching.com *web* api, not the official Live API).

All endpoints are below https://www.geocaching.com/api/proxy and use the OAuth
token handled by `GCLogin.api_proxy()` (port of GCAuthAPI.java).

Not available when this was written (so approximated, see the notes):
  * CacheSize.java   -> container-id table below is from memory
  * CacheAttribute   -> attributes are returned as "gcattr<id>_yes|no"
  * Units.generateSmartRoundedAverageDistance -> plain average
"""
import math
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from typing import List, Optional, Sequence, Tuple

from .enums import cache_type_by_wpt, cache_type_by_id
from .geopoint import Geopoint, Viewport
from .models import Geocache, StatusCode, Trackable

MAX_TAKE = 1000

# SortType keywords of the search api (key = GeocacheSort type, value = api keyword)
SORT_KEYWORDS = {
    "name": "geocacheName",
    "distance": "distance",
    "favorites": "favoritePoint",
    "size": "containerSize",
    "difficulty": "difficulty",
    "terrain": "terrain",
    "inventory": "trackableCount",
    "hidden_date": "placeDate",
    "last_found": "foundDate",
}

# CacheSize id <-> geocaching.com container type ids.
# !! from memory - verify against CacheSize.java (getGcIdsForSize / getByGcId) !!
SIZE_TO_GC_IDS = {"not_chosen": [1], "micro": [2], "regular": [3], "large": [4],
                  "virtual": [5], "other": [6], "small": [8]}
GC_ID_TO_SIZE = {gid: size for size, ids in SIZE_TO_GC_IDS.items() for gid in ids}


@dataclass
class SearchResult:
    caches: List[Geocache] = field(default_factory=list)
    left_to_fetch: int = 0
    partial: bool = False
    error: Optional[StatusCode] = None
    detail: str = ""          # technical reason when error is set (HTTP status ...)


def _range_string(p_from: Optional[float], p_to: Optional[float]) -> Optional[str]:
    """'1.0-4.5' style range in 0.5 steps (difficulty / terrain parameters)."""
    if p_from is None and p_to is None:
        return None

    def norm(v, default):
        if v is None:
            return default
        return math.floor(max(1.0, min(5.0, v)) * 2.0 + 0.5) / 2.0   # Java Math.round

    f, t = norm(p_from, 1.0), norm(p_to, 5.0)
    return "%s-%s" % ((t, f) if f > t else (f, t))


def _parse_date(text: Optional[str]) -> Optional[datetime]:
    if not text:
        return None
    try:
        return datetime.fromisoformat(text.rstrip("Z").split(".")[0])
    except ValueError:
        return None


@dataclass
class WebApiSearch:
    """Search against https://www.geocaching.com/api/proxy/web/search/v2."""
    box: Optional[Viewport] = None
    origin: Optional[Geopoint] = None
    status_own: Optional[bool] = None            # True: only own, False: hide own (premium only)
    status_found: Optional[bool] = None          # True: only found, False: hide found (premium only)
    status_membership: Optional[bool] = None     # True: only basic, False: only premium caches
    status_enabled: Optional[bool] = None        # True: only enabled, False: only disabled
    status_corrected_coordinates: Optional[bool] = None
    show_archived: bool = True
    cache_types: List[str] = field(default_factory=list)       # CacheType ids
    cache_sizes: List[str] = field(default_factory=list)       # CacheSize ids
    cache_attributes: List[int] = field(default_factory=list)  # gc attribute ids (positive only)
    hidden_by: Optional[str] = None
    not_found_by: List[str] = field(default_factory=list)
    found_by: List[str] = field(default_factory=list)
    difficulty: Optional[str] = None
    terrain: Optional[str] = None
    difficulty_terrain_combis: Optional[str] = None
    placed_from: Optional[str] = None
    placed_to: Optional[str] = None
    keywords: Optional[str] = None
    min_favorite_points: int = -1
    sort: Optional[str] = "distance"             # key of SORT_KEYWORDS
    sort_asc: bool = True
    skip: int = 0
    take: int = 500

    # -- setters mirroring the Java builder
    def set_page(self, take: int, skip: int) -> "WebApiSearch":
        self.take, self.skip = take, skip
        return self

    def set_sort(self, sort: Optional[str], asc: bool) -> "WebApiSearch":
        self.sort, self.sort_asc = sort, asc
        return self

    def add_cache_types(self, type_ids: Sequence[str]) -> "WebApiSearch":
        self.cache_types += [t for t in type_ids if t != "all" and t not in self.cache_types]
        return self

    def add_cache_sizes(self, size_ids: Sequence[str]) -> "WebApiSearch":
        self.cache_sizes += [s for s in size_ids if s not in self.cache_sizes]
        return self

    def add_cache_attributes(self, gc_ids: Sequence[int]) -> "WebApiSearch":
        self.cache_attributes += [a for a in gc_ids if a not in self.cache_attributes]
        return self

    def set_difficulty(self, p_from, p_to) -> "WebApiSearch":
        self.difficulty = _range_string(p_from, p_to)
        return self

    def set_terrain(self, p_from, p_to) -> "WebApiSearch":
        self.terrain = _range_string(p_from, p_to)
        return self

    def set_difficulty_terrain_combis(self, combis: Sequence[Tuple[float, float]]) -> "WebApiSearch":
        # example: m=1-4.5,2.5-4.5,3-5
        self.difficulty_terrain_combis = ",".join("%s-%s" % (float(d), float(t)) for d, t in combis)
        return self

    def set_placement_date(self, d_from: Optional[datetime], d_to: Optional[datetime]) -> "WebApiSearch":
        """Day level. gc.com excludes the given day for 'before'/'after', so pad by one day."""
        one = timedelta(days=1)
        fmt = "%Y-%m-%d"
        if d_from is None and d_to is None:
            self.placed_from = self.placed_to = None
        elif d_from is None:
            self.placed_from, self.placed_to = None, (d_to + one).strftime(fmt)
        elif d_to is None:
            self.placed_from, self.placed_to = (d_from - one).strftime(fmt), None
        else:
            lo, hi = (d_from, d_to) if d_from < d_to else (d_to, d_from)
            self.placed_from, self.placed_to = lo.strftime(fmt), hi.strftime(fmt)
        return self

    # -- request
    def build_params(self, current_location: Optional[Geopoint] = None) -> Optional[List[Tuple[str, str]]]:
        """Query parameters as a list of tuples (repeated keys allowed).

        Returns None if the search must not be sent (empty / invalid viewport)."""
        p: List[Tuple[str, str]] = []
        box = self.box
        if box is not None:
            if box.lat_min == box.lat_max and box.lon_min == box.lon_max:
                return None                                   # empty viewport
            if not (-90 <= box.lat_min <= box.lat_max <= 90 and -180 <= box.lon_min <= box.lon_max <= 180):
                return None                                   # invalid coordinate range
            p.append(("box", "%s,%s,%s,%s" % (box.lat_max, box.lon_min, box.lat_min, box.lon_max)))
            p.append(("rad", "16000"))                        # gc.com always sends this with a box
            c = box.center
            p.append(("origin", "%s,%s" % (c.lat, c.lon)))    # overridden below if origin is set
        if self.origin is not None:
            p = [x for x in p if x[0] != "origin"]
            p.append(("origin", "%s,%s" % (self.origin.lat, self.origin.lon)))

        if self.cache_types:
            ids = [cache_type_by_id(t).wpt_type_id for t in self.cache_types]
            p.append(("ct", ",".join(i for i in ids if i)))
        if self.cache_sizes:
            gc_ids = [str(g) for s in self.cache_sizes for g in SIZE_TO_GC_IDS.get(s, [])]
            if gc_ids:
                p.append(("cs", ",".join(gc_ids)))
        if self.cache_attributes:
            p.append(("att", ",".join(str(a) for a in self.cache_attributes)))

        # hide owned / hide found only works for premium members
        if self.status_own is not None:
            p.append(("ho", "0" if self.status_own else "1"))
        if self.status_found is not None:
            p.append(("hf", "0" if self.status_found else "1"))
        if self.status_membership is not None:
            p.append(("sp", "0" if self.status_membership else "1"))
        if self.status_enabled is not None:
            p.append(("sd", "0" if self.status_enabled else "1"))
        if self.show_archived:
            p.append(("sa", "1"))
        if self.status_corrected_coordinates is not None:
            p.append(("cc", "0" if self.status_corrected_coordinates else "1"))

        if self.hidden_by is not None:
            p.append(("hb", self.hidden_by))
        for name in self.not_found_by:
            p.append(("nfb", name))
        for name in self.found_by:
            p.append(("fb", name))
        if self.min_favorite_points > 0:
            p.append(("fp", str(self.min_favorite_points)))
        if self.difficulty is not None:
            p.append(("d", self.difficulty))
        if self.terrain is not None:
            p.append(("t", self.terrain))
        if self.difficulty_terrain_combis is not None:
            p.append(("m", self.difficulty_terrain_combis))

        if self.placed_from is not None or self.placed_to is not None:
            if self.placed_from is None:
                p.append(("pbd", self.placed_to))
            elif self.placed_to is None:
                p.append(("pad", self.placed_from))
            else:
                p.append(("psd", self.placed_from))
                p.append(("ped", self.placed_to))

        if self.keywords is not None:
            p.append(("cn", self.keywords))

        p.append(("properties", "callernote"))   # always set since 6.4.24
        p.append(("take", str(self.take)))
        p.append(("skip", str(self.skip)))

        if self.sort:
            p.append(("sort", SORT_KEYWORDS.get(self.sort, self.sort)))
            if self.sort == "distance" and self.box is None:
                d_origin = self.origin or current_location
                if d_origin is not None:
                    p.append(("dorigin", "%s,%s" % (d_origin.lat, d_origin.lon)))
            p.append(("asc", "true" if self.sort_asc else "false"))

        p.append(("app", "cgeo"))   # identify towards Groundspeak (gentlemen's agreement)
        return p


def _coords(d: Optional[dict]) -> Optional[Geopoint]:
    if not d or d.get("latitude") is None or d.get("longitude") is None:
        return None
    return Geopoint(float(d["latitude"]), float(d["longitude"]))


def _geocache_from_result(r: dict) -> Geocache:
    c = Geocache(detailed=False, geocode=r.get("code", ""), name=r.get("name", ""))
    corrected, posted = _coords(r.get("userCorrectedCoordinates")), _coords(r.get("postedCoordinates"))
    if corrected is not None:
        c.coords, c.user_modified_coords = corrected, True
    elif posted is not None:
        c.coords, c.user_modified_coords = posted, False
    else:
        c.coords = None     # premium cache searched by a basic member
    c.type_id = cache_type_by_wpt(str(r.get("geocacheType"))).id
    c.difficulty = float(r.get("difficulty") or 0)
    c.terrain = float(r.get("terrain") or 0)
    c.size_id = GC_ID_TO_SIZE.get(int(r.get("containerType") or 0), "unknown")
    c.premium_only = bool(r.get("premiumOnly"))
    c.hidden = _parse_date(r.get("placedDate"))
    c.last_found = _parse_date(r.get("lastFoundDate"))
    c.inventory_count = int(r.get("trackableCount") or 0)
    c.location = ", ".join(x for x in (r.get("region"), r.get("country")) if x)
    # the map api may lag behind: only ever set found, never un-set it
    if r.get("userFound"):
        c.found = True
    elif r.get("userDidNotFind"):
        c.dnf = True
    c.favorite_points = int(r.get("favoritePoints") or 0)
    status = r.get("cacheStatus")
    c.disabled, c.archived = status == 1, status == 2
    owner = r.get("owner")
    if owner:
        c.owner_display_name = c.owner_user_id = owner.get("username", "")
    c.attributes = ["gcattr%s_%s" % (a.get("id"), "yes" if a.get("isApplicable") else "no")
                    for a in (r.get("attributes") or [])]
    return c


def _guess_missing_distances(caches: List[Geocache], search: WebApiSearch) -> None:
    """Basic members get no coordinates for premium caches: guess distances from the sort order."""
    if not caches or search.origin is None or search.sort != "distance":
        return
    loop = caches if search.sort_asc else list(reversed(caches))
    last = 0.0
    empty: List[Geocache] = []
    for c in loop:
        if c.coords is not None:
            new = search.origin.distance_km(c.coords)
            for e in empty:
                e.distance = (new + last) / 2.0   # c:geo: Units.generateSmartRoundedAverageDistance
            empty.clear()
            last = new
        else:
            empty.append(c)
    for e in empty:
        e.distance = 1.0 if last == 0 else last + 1


def search_caches(session, search: WebApiSearch,
                  current_location: Optional[Geopoint] = None) -> SearchResult:
    """GCWebAPI.searchCaches."""
    result = SearchResult()
    params = search.build_params(current_location)
    if params is None:
        return result
    data = session.api_proxy("GET", "/web/search/v2", params=params)
    if data is None:
        result.error = StatusCode.COMMUNICATION_ERROR
        result.detail = getattr(session, "last_api_error", "") or ""
        return result
    try:
        rows = data.get("results") or []
        result.left_to_fetch = int(data.get("total", 0)) - search.take - search.skip
        result.partial = search.take > 0 and len(rows) == search.take
        caches = [_geocache_from_result(r) for r in rows]
        _guess_missing_distances(caches, search)
        result.caches = caches
    except (AttributeError, TypeError, ValueError):
        result.error = StatusCode.COMMUNICATION_ERROR
    return result


# --------------------------------------------------------------------- other endpoints
def _trackable_from_entry(e: dict) -> Trackable:
    return Trackable(geocode=e.get("referenceCode"), name=e.get("name") or "",
                     tracking_code=e.get("trackingNumber"), icon_url=e.get("iconUrl"))


def get_trackables_of_cache(session, geocode: str) -> List[Trackable]:
    """/web/v1/trackables/geocache/<GC>: trackables currently in the cache."""
    result: List[Trackable] = []
    skip = 0
    while True:
        data = session.api_proxy("GET", "/web/v1/trackables/geocache/" + geocode,
                                 params={"take": str(MAX_TAKE), "skip": str(skip)})
        rows = (data or {}).get("data") if isinstance(data, dict) else None
        if not rows:
            break
        result += [_trackable_from_entry(e) for e in rows]
        skip += MAX_TAKE
        if len(rows) != MAX_TAKE:
            break
    return result


def get_trackable_inventory(session, total_trackables: int) -> List[Trackable]:
    """/trackables?inCollection=false&inInventory=true: the user's own inventory."""
    result: List[Trackable] = []
    skip = 0
    while True:
        rows = session.api_proxy("GET", "/trackables", params={
            "inCollection": "false", "inInventory": "true", "take": str(MAX_TAKE), "skip": str(skip)})
        if not isinstance(rows, list):
            break
        result += [_trackable_from_entry(e) for e in rows]
        skip += MAX_TAKE
        if not rows or len(result) >= total_trackables:
            break
    return result


def get_available_favorite_points(session, profile: str) -> Optional[int]:
    """/web/v1/users/<PR...>/availablefavoritepoints"""
    data = session.api_proxy("GET", "/web/v1/users/%s/availablefavoritepoints" % profile)
    return data if isinstance(data, int) else None


def get_needed_difficulty_terrain_combis_for_81_matrix(session) -> List[Tuple[float, float]]:
    """/web/v1/statistics/difficultyterrainmatrix/needed -> [(difficulty, terrain), ...]"""
    raw = session.api_proxy("GET", "/web/v1/statistics/difficultyterrainmatrix/needed")
    combis: List[Tuple[float, float]] = []
    if not isinstance(raw, list):
        return combis
    try:
        for item in raw:
            d, t = str(item).split("-")
            combis.append((float(d), float(t)))
    except ValueError:
        return []
    return combis
