"""Port of c:geo's GCMap.java: filter -> geocaching.com web-API search.

The HTTP part lives in webapi.py (GCWebAPI.searchCaches / WebApiSearch).
"""
from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional, Tuple

from .geopoint import Geopoint, Viewport
from .webapi import SearchResult, WebApiSearch, search_caches

SEARCH_LOAD_INITIAL = 200
SEARCH_LOAD_NEXTPAGE = 50
VIEWPORT_PAGE_SIZE = 500


@dataclass
class SearchFilter:
    """Simplified GeocacheFilter: an AND chain of the criteria GCMap understands."""
    types: Optional[List[str]] = None               # CacheType ids ("traditional", ...)
    name_contains: Optional[str] = None
    attributes: Optional[List[int]] = None          # required attributes (gc ids 0..99)
    sizes: Optional[List[str]] = None               # CacheSize ids ("micro", "small", ...)
    center: Optional[Geopoint] = None               # distance filter
    max_distance_km: Optional[float] = None
    difficulty: Tuple[Optional[float], Optional[float]] = (None, None)
    terrain: Tuple[Optional[float], Optional[float]] = (None, None)
    dt_combis: Optional[List[Tuple[float, float]]] = None   # 81-matrix filter
    owner: Optional[str] = None
    min_favorites: Optional[int] = None
    status_found: Optional[bool] = None
    status_owned: Optional[bool] = None
    exclude_disabled: bool = False
    exclude_archived: bool = False
    exclude_active: bool = False
    hidden_min: Optional[datetime] = None
    hidden_max: Optional[datetime] = None
    found_by: Optional[str] = None
    not_found_by: Optional[str] = None


def create_search_for_filter(flt: Optional[SearchFilter], take: int = SEARCH_LOAD_INITIAL,
                             skip: int = 0, sort: Optional[str] = "distance",
                             ascending: bool = True) -> WebApiSearch:
    """GCMap.createSearchForFilter + fillForBasicFilter."""
    f = flt or SearchFilter()
    s = WebApiSearch().set_page(take, skip).set_sort(sort, ascending)
    if f.types:
        s.add_cache_types(f.types)
    if f.name_contains:
        s.keywords = f.name_contains
    if f.attributes:
        s.add_cache_attributes([a for a in f.attributes if 0 <= a < 100])
    if f.sizes:
        s.add_cache_sizes(f.sizes)
    if f.center is not None:
        if f.max_distance_km is not None:
            s.box = Viewport.around(f.center, f.max_distance_km)
        else:
            s.origin = f.center
    if f.difficulty != (None, None):
        s.set_difficulty(*f.difficulty)
    if f.terrain != (None, None):
        s.set_terrain(*f.terrain)
    if f.dt_combis:
        s.set_difficulty_terrain_combis(f.dt_combis)
    if f.owner:
        s.hidden_by = f.owner
    if f.min_favorites is not None:
        s.min_favorite_points = int(round(f.min_favorites))
    s.status_found = f.status_found
    s.status_own = f.status_owned
    if f.exclude_disabled and f.exclude_archived:
        s.status_enabled = True
    elif f.exclude_active and f.exclude_archived:
        s.status_enabled = False
    else:
        s.status_enabled = None
    s.show_archived = not f.exclude_archived
    if f.hidden_min is not None or f.hidden_max is not None:
        s.set_placement_date(f.hidden_min, f.hidden_max)
    if f.found_by:
        s.found_by.append(f.found_by)
    if f.not_found_by:
        s.not_found_by.append(f.not_found_by)
    return s


def search_by_viewport(session, viewport: Viewport, flt: Optional[SearchFilter] = None) -> SearchResult:
    """GCMap.searchByViewport: one page of up to 500 caches inside the box."""
    search = create_search_for_filter(flt)
    search.box = viewport
    search.set_page(VIEWPORT_PAGE_SIZE, 0)
    return search_caches(session, search)


def search_by_filter(session, flt: SearchFilter, sort: str = "distance", ascending: bool = True,
                     already_took: int = 0, current_location: Optional[Geopoint] = None) -> SearchResult:
    """GCMap.searchByFilter / searchByNextPage: 200 caches first, then pages of 50."""
    take = SEARCH_LOAD_INITIAL if already_took == 0 else SEARCH_LOAD_NEXTPAGE
    search = create_search_for_filter(flt, take, already_took, sort, ascending)
    return search_caches(session, search, current_location)
