"""Minimal Geopoint (replacement for cgeo.geocaching.location.Geopoint)."""
import html
import math
import re
from dataclasses import dataclass


class GeopointError(ValueError):
    pass


_DM = re.compile(
    r"([NSns])\s*(\d{1,2})\s*[°º\s]\s*(\d{1,2}(?:[.,]\d+)?)\s*['′]?\s*[,;]?\s*"
    r"([EWOewo])\s*(\d{1,3})\s*[°º\s]\s*(\d{1,2}(?:[.,]\d+)?)")
_DEC = re.compile(
    r"([NSns])?\s*(-?\d{1,2}[.,]\d+)\s*°?\s*[,;]?\s*([EWOewo])?\s*(-?\d{1,3}[.,]\d+)\s*°?")


def _f(s: str) -> float:
    return float(s.replace(",", "."))


@dataclass(frozen=True)
class Geopoint:
    lat: float
    lon: float

    @classmethod
    def parse(cls, text: str) -> "Geopoint":
        """Parse 'N 49° 12.345 E 016° 12.345' or decimal degrees."""
        if not text:
            raise GeopointError("empty coordinates")
        t = html.unescape(text).replace("\xa0", " ").strip()
        m = _DM.search(t)
        if m:
            lat = int(m.group(2)) + _f(m.group(3)) / 60.0
            lon = int(m.group(5)) + _f(m.group(6)) / 60.0
            if m.group(1).upper() == "S":
                lat = -lat
            if m.group(4).upper() == "W":
                lon = -lon
            return cls(lat, lon)
        m = _DEC.search(t)
        if m:
            lat, lon = _f(m.group(2)), _f(m.group(4))
            if m.group(1) and m.group(1).upper() == "S":
                lat = -abs(lat)
            if m.group(3) and m.group(3).upper() == "W":
                lon = -abs(lon)
            return cls(lat, lon)
        raise GeopointError("cannot parse coordinates: %r" % text)

    def distance_km(self, other: "Geopoint") -> float:
        r = 6371.0088
        p1, p2 = math.radians(self.lat), math.radians(other.lat)
        dphi = p2 - p1
        dl = math.radians(other.lon - self.lon)
        a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
        return 2 * r * math.asin(math.sqrt(a))

    def bearing_to(self, other: "Geopoint") -> float:
        p1, p2 = math.radians(self.lat), math.radians(other.lat)
        dl = math.radians(other.lon - self.lon)
        y = math.sin(dl) * math.cos(p2)
        x = math.cos(p1) * math.sin(p2) - math.sin(p1) * math.cos(p2) * math.cos(dl)
        return (math.degrees(math.atan2(y, x)) + 360.0) % 360.0


@dataclass(frozen=True)
class Viewport:
    """Lat/lon bounding box (replacement for cgeo.geocaching.location.Viewport)."""
    lat_min: float
    lat_max: float
    lon_min: float
    lon_max: float

    @classmethod
    def around(cls, center: Geopoint, half_side_km: float) -> "Viewport":
        # !! Viewport(Geopoint, double) from c:geo not available - assumed
        # to be a box of +-distance km around the centre; verify !!
        dlat = half_side_km / 111.32
        dlon = half_side_km / (111.32 * max(0.01, math.cos(math.radians(center.lat))))
        return cls(center.lat - dlat, center.lat + dlat, center.lon - dlon, center.lon + dlon)

    @property
    def center(self) -> Geopoint:
        return Geopoint((self.lat_min + self.lat_max) / 2, (self.lon_min + self.lon_max) / 2)
