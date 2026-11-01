"""CacheType, ported from CacheType.java (without Android resources).

Other c:geo enums (CacheSize, CacheAttribute, LogType) are not ported yet;
see webapi.py for the CacheSize <-> GC container-id table used meanwhile.
"""
from enum import Enum
from typing import Dict, Optional


class CacheType(Enum):
    #            id               pattern                         guid                                   wpt type id
    TRADITIONAL = ("traditional", "Traditional Cache", "32bc9333-5e52-4957-b0f6-5a2c8fc7b257", "2")
    MULTI = ("multi", "Multi-cache", "a5f6d0ad-d2f2-4011-8c14-940a9ebf3c74", "3")
    MYSTERY = ("mystery", "Unknown Cache", "40861821-1835-4e11-b666-8d41064d03fe", "8")
    LETTERBOX = ("letterbox", "Letterbox hybrid", "4bdd8fb2-d7bc-453f-a9c5-968563b15d24", "5")
    EVENT = ("event", "Event Cache", "69eb8534-b718-4b35-ae3c-a856a55b0874", "6")
    MEGA_EVENT = ("mega", "Mega-Event Cache", "69eb8535-b718-4b35-ae3c-a856a55b0874", "453")
    GIGA_EVENT = ("giga", "Giga-Event Cache", "51420629-5739-4945-8bdd-ccfd434c0ead", "7005")
    EARTH = ("earth", "Earthcache", "c66f5cf3-9523-4549-b8dd-759cd2f18db8", "137")
    CITO = ("cito", "Cache In Trash Out Event", "57150806-bc1a-42d6-9cf0-538d171a2d22", "13")
    WEBCAM = ("webcam", "Webcam Cache", "31d2ae3c-c358-4b5f-8dcd-2185bf472d3d", "11")
    VIRTUAL = ("virtual", "Virtual Cache", "294d4360-ac86-4c83-84dd-8113ef678d7e", "4")
    WHERIGO = ("wherigo", "Wherigo Cache", "0544fa55-772d-4e5c-96a9-36a51ebcf5c9", "1858")
    COMMUN_CELEBRATION = ("communceleb", "Community Celebration Event", "3ea6533d-bb52-42fe-b2d2-79a3424d4728", "3653")
    PROJECT_APE = ("ape", "Project Ape Cache", "2555690d-b2bc-4b55-b5ac-0cb704c0b768", "9")
    GCHQ = ("gchq", "Geocaching HQ", "416f2494-dc17-4b6a-9bab-1a29dd292d8c", "3773")
    GCHQ_CELEBRATION = ("gchqceleb", "Geocaching HQ Celebration", "af820035-787a-47af-b52b-becc8b0c0c88", "3774")
    GPS_EXHIBIT = ("gps", "GPS Adventures Exhibit", "72e69af2-7986-4990-afd9-bc16cbbb4ce3", "1304")
    BLOCK_PARTY = ("block", "Geocaching HQ Block Party", "bc2f3df2-1aab-4601-b2ff-b5091f6c02e3", "4738")
    LOCATIONLESS = ("locationless", "Locationless (Reverse) Cache", "8f6dd7bc-ff39-4997-bd2e-225a0d2adf9d", "12")
    ADVLAB = ("advlab", "Lab Cache", "", "")
    USER_DEFINED = ("userdefined", "User defined cache", "", "")
    UNKNOWN = ("unknown", "unknown", "", "")
    ALL = ("all", "display all caches", "9a79e6ce-3344-409c-bbe9-496530baf758", "")  # filter only

    def __init__(self, id_: str, pattern: str, guid: str, wpt_type_id: str):
        self.id = id_
        self.pattern = pattern
        self.guid = guid
        self.wpt_type_id = wpt_type_id

    @property
    def is_event(self) -> bool:
        return self in (CacheType.EVENT, CacheType.MEGA_EVENT, CacheType.CITO, CacheType.GIGA_EVENT,
                        CacheType.COMMUN_CELEBRATION, CacheType.BLOCK_PARTY, CacheType.GPS_EXHIBIT,
                        CacheType.GCHQ_CELEBRATION)

    @property
    def is_virtual(self) -> bool:
        return self in (CacheType.VIRTUAL, CacheType.WEBCAM, CacheType.EARTH, CacheType.LOCATIONLESS)

    @property
    def apply_distance_rule(self) -> bool:
        return self in (CacheType.TRADITIONAL, CacheType.PROJECT_APE, CacheType.GCHQ, CacheType.USER_DEFINED)


_BY_ID: Dict[str, CacheType] = {}
_BY_PATTERN: Dict[str, CacheType] = {}
_BY_GUID: Dict[str, CacheType] = {}
_BY_WPT: Dict[str, CacheType] = {}
for _ct in CacheType:
    _BY_ID[_ct.id] = _ct
    _BY_PATTERN[_ct.pattern.lower()] = _ct
    _BY_GUID[_ct.guid] = _ct
    if _ct.wpt_type_id.strip():
        _BY_WPT[_ct.wpt_type_id] = _ct

for _p, _t in {
    "mystery cache": CacheType.MYSTERY,                   # old mystery type (GPX compatibility)
    "traditional geocache": CacheType.TRADITIONAL,        # briefly used 2014-08
    "groundspeak hq": CacheType.GCHQ,                     # renamings in 2019
    "groundspeak block party": CacheType.BLOCK_PARTY,
    "lost and found event cache": CacheType.COMMUN_CELEBRATION,
    "multistep traditional cache": CacheType.MULTI,       # Geocaching.ru
    "multistep virtual cache": CacheType.MYSTERY,
    "contest": CacheType.EVENT,
    "event": CacheType.EVENT,
    "quiz cache": CacheType.MYSTERY,                      # Opencaching
    "moving cache": CacheType.MYSTERY,
    "podcast cache": CacheType.MYSTERY,
    "own cache": CacheType.MYSTERY,
}.items():
    _BY_PATTERN[_p] = _t


def cache_type_by_id(id_: Optional[str]) -> CacheType:
    return _BY_ID.get(id_.lower().strip(), CacheType.UNKNOWN) if id_ else CacheType.UNKNOWN


def cache_type_by_pattern(pattern: Optional[str]) -> CacheType:
    return _BY_PATTERN.get(pattern.lower().strip(), CacheType.UNKNOWN) if pattern else CacheType.UNKNOWN


def cache_type_by_guid(guid: Optional[str]) -> CacheType:
    return _BY_GUID.get(guid, CacheType.UNKNOWN) if guid else CacheType.UNKNOWN


def cache_type_by_wpt(type_number: Optional[str]) -> CacheType:
    """CacheType.getByWaypointType: numeric id; falls back to the pattern
    (earthcaches use a literal "earthcache" on some result pages)."""
    if type_number is None:
        return CacheType.UNKNOWN
    found = _BY_WPT.get(type_number)
    return found if found is not None else cache_type_by_pattern(type_number)
