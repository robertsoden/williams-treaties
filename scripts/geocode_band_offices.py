"""Geocode Williams Treaty First Nation band office addresses with Nominatim.

Addresses sourced from each First Nation's official website (or, when blocked,
their official contact page via search). Two communities sit on islands and
have rural-route or postal addresses that don't geocode to the actual community
location -- those use a manual override snapped to the band-office area on the
island.
"""

from __future__ import annotations

import time
from dataclasses import dataclass

from geopy.exc import GeocoderTimedOut
from geopy.geocoders import Nominatim


@dataclass
class Entry:
    first_nation: str
    queries: list[str]              # tried in order; first hit wins
    override: tuple[float, float] | None = None  # (lat, lon)
    override_note: str | None = None


ENTRIES = [
    Entry("Alderville First Nation", [
        "11696 Second Line Road, Roseneath, ON K0K 2X0, Canada",
        "Second Line Road, Roseneath, Ontario, Canada",
        "Alderville First Nation, Ontario, Canada",
        "K0K 2X0, Canada",
    ]),
    Entry("Curve Lake First Nation", [
        "22 Winookeedaa Road, Curve Lake, ON K0L 1R0, Canada",
        "Winookeedaa Road, Curve Lake, Ontario, Canada",
        "Curve Lake First Nation, Ontario, Canada",
        "K0L 1R0, Canada",
    ]),
    Entry("Hiawatha First Nation", [
        "431 Hiawatha Line, Hiawatha, ON K9J 0E6, Canada",
        "Hiawatha Line, Hiawatha, Ontario, Canada",
        "Hiawatha First Nation, Ontario, Canada",
        "K9J 0E6, Canada",
    ]),
    Entry("Mississaugas of Scugog Island First Nation", [
        "22521 Island Road, Port Perry, ON L9L 1B6, Canada",
        "Mississaugas of Scugog Island First Nation, Ontario, Canada",
    ]),
    Entry("Chippewas of Beausoleil First Nation", [],
          override=(44.8420, -80.1232),
          override_note="Christian Island band-office area (ferry-only access)"),
    Entry("Chippewas of Georgina Island First Nation", [],
          override=(44.3733, -79.2967),
          override_note="Georgina Island band-office area (ferry-only access)"),
    Entry("Chippewas of Rama First Nation", [
        "5884 Rama Road, Rama, ON, Canada",
        "Rama Road, Rama, Ontario, Canada",
        "Chippewas of Rama First Nation, Ontario, Canada",
        "L3V 6H6, Canada",
    ]),
]


def geocode_with_fallbacks(geocoder, queries):
    for q in queries:
        for attempt in range(3):
            try:
                loc = geocoder.geocode(q, timeout=10, country_codes="ca")
                break
            except GeocoderTimedOut:
                time.sleep(2 ** attempt)
        else:
            continue
        time.sleep(1.1)
        if loc is not None:
            return loc, q
    return None, None


def main():
    geocoder = Nominatim(user_agent="williams-treaties-static-map/1.0")
    print(f"{'first_nation':45s} {'lat':>9s} {'lon':>10s}  source")
    for entry in ENTRIES:
        if entry.override:
            lat, lon = entry.override
            print(f"{entry.first_nation:45s} {lat:9.5f} {lon:10.5f}  "
                  f"manual: {entry.override_note}")
            continue
        loc, hit = geocode_with_fallbacks(geocoder, entry.queries)
        if loc is None:
            print(f"{entry.first_nation:45s}  -- ALL FALLBACKS FAILED --")
            continue
        print(f"{entry.first_nation:45s} {loc.latitude:9.5f} {loc.longitude:10.5f}  "
              f"query={hit!r}\n{'':45s}     -> {loc.address}")


if __name__ == "__main__":
    main()
