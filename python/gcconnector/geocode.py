"""Place search (geocoding) via OpenStreetMap Nominatim, so the map can jump to Prague, London, ...

Usage policy (https://operations.osmfoundation.org/policies/nominatim/): identify the app,
max. 1 request/second, no search-as-you-type - we only search when the user confirms.
"""
import json
from typing import Any, Dict, List, Optional

from . import httpclient

NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
USER_AGENT = "harbour-geocove/0.1 (Sailfish OS geocaching client)"


def parse_nominatim(text: str) -> List[Dict[str, Any]]:
    out = []
    for item in json.loads(text):
        try:
            lat, lon = float(item["lat"]), float(item["lon"])
        except (KeyError, TypeError, ValueError):
            continue
        name = item.get("display_name") or item.get("name") or ""
        bbox = item.get("boundingbox")
        try:
            bbox = [float(x) for x in bbox] if bbox else None   # south, north, west, east
        except (TypeError, ValueError):
            bbox = None
        out.append({"name": name, "lat": lat, "lon": lon, "bbox": bbox,
                    "kind": item.get("type") or item.get("category") or ""})
    return out


def geocode(query: str, limit: int = 8, lang: str = "cs", url: str = NOMINATIM_URL,
            http: Optional[httpclient.Session] = None) -> List[Dict[str, Any]]:
    """Returns [{name, lat, lon, bbox, kind}, ...]; raises RuntimeError on network problems."""
    query = (query or "").strip()
    if len(query) < 2:
        return []
    http = http or httpclient.Session()
    try:
        resp = http.get(url, params={"q": query, "format": "jsonv2", "limit": str(limit),
                                     "accept-language": lang},
                        headers={"User-Agent": USER_AGENT}, timeout=20)
    except httpclient.RequestException as e:
        raise RuntimeError("geocoding failed: %s" % e)
    if not resp.ok:
        raise RuntimeError("geocoding server answered HTTP %d" % resp.status_code)
    try:
        return parse_nominatim(resp.text)
    except ValueError:
        raise RuntimeError("geocoding server returned invalid data")
