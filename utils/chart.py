"""
Full natal chart calculation for Fortunata: geocoding a free-text birth
location, resolving its timezone, and computing planetary sign placements
with kerykeion (Swiss Ephemeris under the hood).

Everything synchronous/CPU- or network-bound here is wrapped so cogs can
`await` it without blocking the bot's event loop (`asyncio.to_thread`).
"""
from __future__ import annotations

import asyncio
from dataclasses import dataclass

from geopy.geocoders import Nominatim
from geopy.extra.rate_limiter import RateLimiter
from timezonefinder import TimezoneFinder

from utils.astrology import ZodiacSign, sign_from_kerykeion_code

# Planets Fortunata tracks, in the order they're displayed everywhere.
# (kerykeion attribute name on the AstrologicalSubject, display label, emoji)
PLANETS: list[tuple[str, str, str]] = [
    ("sun", "Sun", "☀️"),
    ("moon", "Moon", "🌙"),
    ("mercury", "Mercury", "☿️"),
    ("venus", "Venus", "♀️"),
    ("mars", "Mars", "♂️"),
    ("jupiter", "Jupiter", "♃"),
    ("saturn", "Saturn", "♄"),
    ("uranus", "Uranus", "♅"),
    ("neptune", "Neptune", "♆"),
    ("pluto", "Pluto", "♇"),
]
ASCENDANT_LABEL = ("Rising", "⬆️")

_geolocator = Nominatim(user_agent="fortunata-discord-bot")
_geocode_sync = RateLimiter(_geolocator.geocode, min_delay_seconds=1.1)

_tf: TimezoneFinder | None = None


def _get_tf() -> TimezoneFinder:
    global _tf
    if _tf is None:
        _tf = TimezoneFinder()
    return _tf


class GeocodeError(RuntimeError):
    """Raised when a free-text birth location can't be resolved."""


class ChartError(RuntimeError):
    """Raised when the natal chart itself can't be computed."""


@dataclass
class GeoResult:
    lat: float
    lon: float
    display_name: str
    tz_str: str


def _geocode_blocking(location: str) -> GeoResult:
    place = _geocode_sync(location, exactly_one=True, timeout=10)
    if place is None:
        raise GeocodeError(
            f"Couldn't find a place called '{location}'. Try adding a "
            f"country, e.g. 'Naples, Italy'."
        )
    tz_str = _get_tf().timezone_at(lat=place.latitude, lng=place.longitude)
    if not tz_str:
        # fall back to the nearest timezone if the exact point is offshore/etc.
        tz_str = _get_tf().closest_timezone_at(
            lat=place.latitude, lng=place.longitude
        )
    if not tz_str:
        raise GeocodeError(
            f"Found '{location}' but couldn't determine its timezone. "
            f"Try a nearby larger city instead."
        )
    return GeoResult(
        lat=place.latitude,
        lon=place.longitude,
        display_name=place.address,
        tz_str=tz_str,
    )


async def geocode_location(location: str) -> GeoResult:
    """Resolve a free-text location string to lat/lon/timezone."""
    try:
        return await asyncio.to_thread(_geocode_blocking, location)
    except GeocodeError:
        raise
    except Exception as exc:  # geopy network/timeout errors, etc.
        raise GeocodeError(
            "The location lookup service didn't respond. Please try again "
            "in a moment."
        ) from exc


@dataclass
class NatalChart:
    placements: dict[str, ZodiacSign]  # key -> ZodiacSign, keys = planet ids + "ascendant"
    lat: float
    lon: float
    tz_str: str
    location_label: str


def _compute_chart_blocking(
    name: str,
    year: int,
    month: int,
    day: int,
    hour: int,
    minute: int,
    lat: float,
    lon: float,
    tz_str: str,
) -> dict[str, ZodiacSign]:
    from kerykeion import AstrologicalSubjectFactory

    subject = AstrologicalSubjectFactory.from_birth_data(
        name,
        year, month, day, hour, minute,
        lng=lon,
        lat=lat,
        tz_str=tz_str,
        online=False,
    )

    placements: dict[str, ZodiacSign] = {}
    for attr, _label, _emoji in PLANETS:
        point = getattr(subject, attr)
        sign = sign_from_kerykeion_code(point.sign)
        if sign is None:
            raise ChartError(f"Unrecognized zodiac code for {attr}: {point.sign!r}")
        placements[attr] = sign

    ascendant_sign = sign_from_kerykeion_code(subject.first_house.sign)
    if ascendant_sign is None:
        raise ChartError(
            f"Unrecognized zodiac code for ascendant: {subject.first_house.sign!r}"
        )
    placements["ascendant"] = ascendant_sign
    return placements


async def compute_natal_chart(
    *,
    name: str,
    year: int,
    month: int,
    day: int,
    hour: int,
    minute: int,
    location: str,
) -> NatalChart:
    """Geocode `location` and compute the full natal chart for the given
    birth date/time. Raises GeocodeError or ChartError on failure."""
    geo = await geocode_location(location)
    try:
        placements = await asyncio.to_thread(
            _compute_chart_blocking,
            name, year, month, day, hour, minute,
            geo.lat, geo.lon, geo.tz_str,
        )
    except ChartError:
        raise
    except Exception as exc:
        raise ChartError(
            "Couldn't calculate a chart from that birth date/time. Double "
            "check the date is valid and try again."
        ) from exc

    return NatalChart(
        placements=placements,
        lat=geo.lat,
        lon=geo.lon,
        tz_str=geo.tz_str,
        location_label=geo.display_name,
    )
