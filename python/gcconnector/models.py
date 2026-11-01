"""Minimal data models used by the connector.

`type_id` holds the CacheType id ("traditional", "multi", ...; see enums.py).
CacheSize, LogType and WaypointType are kept as raw strings for now.
"""
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional

from .enums import cache_type_by_id
from .geopoint import Geopoint


class StatusCode(Enum):
    NO_ERROR = "no_error"
    UNKNOWN_ERROR = "unknown_error"
    CACHE_NOT_FOUND = "cache_not_found"
    UNPUBLISHED_CACHE = "unpublished_cache"
    PREMIUM_ONLY = "premium_only"
    NO_LOGIN_INFO_STORED = "no_login_info_stored"
    WRONG_LOGIN_DATA = "wrong_login_data"
    LOGIN_CAPTCHA_ERROR = "login_captcha_error"
    UNVALIDATED_ACCOUNT = "unvalidated_account"
    LOGIN_PARSE_ERROR = "login_parse_error"
    CONNECTION_FAILED_GC = "connection_failed_gc"
    COMMUNICATION_ERROR = "communication_error"
    MAINTENANCE = "maintenance"


@dataclass
class Image:
    url: str
    title: str = ""
    description: str = ""
    category: str = "listing"  # listing | log


@dataclass
class Waypoint:
    name: str
    type_id: Optional[str] = None
    prefix: str = ""
    lookup: str = ""
    coords: Optional[Geopoint] = None
    note: str = ""
    original_coords_empty: bool = False
    user_defined: bool = False


@dataclass
class Trackable:
    geocode: Optional[str] = None
    guid: Optional[str] = None
    name: str = ""
    brand: str = "travelbug"
    tracking_code: Optional[str] = None
    icon_url: Optional[str] = None


@dataclass
class LogEntry:
    service_log_id: str = ""
    author: str = ""
    author_guid: str = ""
    date: Optional[datetime] = None
    log_type: str = ""
    log: str = ""
    found_count: int = 0
    friend: bool = False
    favorite: bool = False
    images: List[Image] = field(default_factory=list)


@dataclass
class Geocache:
    geocode: str = ""
    cache_id: str = ""
    guid: str = ""
    name: str = ""
    type_id: str = ""
    size_id: str = ""
    difficulty: float = 0.0
    terrain: float = 0.0
    coords: Optional[Geopoint] = None
    original_coords: Optional[Geopoint] = None
    user_modified_coords: bool = False
    owner_display_name: str = ""
    owner_guid: str = ""
    owner_user_id: str = ""
    hidden: Optional[datetime] = None
    favorite_points: int = 0
    found: bool = False
    dnf: bool = False
    disabled: bool = False
    archived: bool = False
    premium_only: bool = False
    favorite: bool = False
    on_watchlist: bool = False
    watchlist_count: int = -1
    location: str = ""
    hint: str = ""
    personal_note: str = ""
    short_description: str = ""
    description: str = ""
    attributes: List[str] = field(default_factory=list)
    spoilers: List[Image] = field(default_factory=list)
    inventory: List[Trackable] = field(default_factory=list)
    log_counts: Dict[str, int] = field(default_factory=dict)
    waypoints: List[Waypoint] = field(default_factory=list)
    logs: List[LogEntry] = field(default_factory=list)
    visited_date: Optional[datetime] = None
    last_found: Optional[datetime] = None
    inventory_count: int = 0
    distance: Optional[float] = None   # km, only guessed for premium caches
    detailed: bool = True

    def is_event_cache(self) -> bool:
        return cache_type_by_id(self.type_id).is_event

    def add_waypoint(self, wp: Waypoint) -> None:
        self.waypoints.append(wp)

    def create_original_waypoint(self, coords: Geopoint) -> None:
        self.original_coords = coords
        self.waypoints.append(Waypoint(name="Original coordinates", type_id="original",
                                       coords=coords))

    @property
    def is_event(self) -> bool:
        return self.is_event_cache()
