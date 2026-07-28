#!/usr/bin/env python3
"""
Build the "At-Risk Species Sightings" layer for the Williams Treaty map.

For each federally SARA-listed species whose critical habitat is mapped in this
project (see the Critical Habitat layer), this pulls recent research-grade
iNaturalist sightings within the treaty area. It complements the Critical Habitat
POLYGONS with actual observation POINTS.

Sensitivity: iNaturalist automatically obscures the coordinates of conservation-
sensitive taxa (rare turtles, snakes, etc.) to a coarse area. Those points are
flagged "Approximate" in location_precision and must not be treated as exact.

Because this layer shows RECENT sightings and many species are only observable in
certain seasons, refresh it seasonally or quarterly. See MANUAL_DOWNLOADS.md.

Input:   data/datasets/biodiversity/critical_habitat_species_at_risk.geojson
Output:  data/datasets/biodiversity/species_at_risk_occurrences.geojson
Layer:   sar_occurrences  (Biodiversity category in web/config/layers.yaml)

Usage:
    python scripts/build_sar_occurrences.py            # build only
    python scripts/build_sar_occurrences.py --upload   # build + upload to S3
"""

import argparse
import subprocess
import time
from pathlib import Path

import geopandas as gpd
import requests
import warnings
warnings.filterwarnings("ignore")

PROJECT_ROOT = Path(__file__).parent.parent
AOI_PATH = PROJECT_ROOT / "data/boundaries/williams_treaty.geojson"
CH_PATH = PROJECT_ROOT / "data/datasets/biodiversity/critical_habitat_species_at_risk.geojson"
OUT_PATH = PROJECT_ROOT / "data/datasets/biodiversity/species_at_risk_occurrences.geojson"
S3_URI = "s3://ontario-environmental-data/datasets/biodiversity/species_at_risk_occurrences.geojson"

MAX_PER_SPECIES = 40  # cap recent observations fetched per species
TAXA_API = "https://api.inaturalist.org/v1/taxa"
OBS_API = "https://api.inaturalist.org/v1/observations"


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--upload", action="store_true", help="Upload result to S3 after building")
    args = ap.parse_args()

    aoi = gpd.read_file(AOI_PATH).to_crs(4326)
    geom = aoi.geometry.union_all()
    minx, miny, maxx, maxy = aoi.total_bounds

    ch = gpd.read_file(CH_PATH)
    species = ch[["scientific_name", "common_name", "sara_status"]].drop_duplicates("scientific_name")
    print(f"SARA species to map: {len(species)}")

    sess = requests.Session()
    feats = []
    for _, row in species.iterrows():
        sci = row["scientific_name"]
        try:
            t = sess.get(TAXA_API, params={"q": sci, "per_page": 1}, timeout=60).json()
            if not t["results"]:
                print(f"  no taxon: {sci}"); time.sleep(0.3); continue
            tid = t["results"][0]["id"]
        except Exception as e:
            print(f"  taxon err {sci}: {e}"); continue
        try:
            o = sess.get(OBS_API, params={
                "taxon_id": tid, "quality_grade": "research", "geo": "true", "geoprivacy": "open",
                "swlat": miny, "swlng": minx, "nelat": maxy, "nelng": maxx,
                "order_by": "observed_on", "per_page": MAX_PER_SPECIES}, timeout=60).json()
        except Exception as e:
            print(f"  obs err {sci}: {e}"); continue

        n = 0
        for ob in o.get("results", []):
            if not ob.get("geojson"):
                continue
            lon, lat = ob["geojson"]["coordinates"]
            obscured = ob.get("obscured", False)
            feats.append({"type": "Feature",
                "geometry": {"type": "Point", "coordinates": [round(lon, 5), round(lat, 5)]},
                "properties": {
                    "common_name": row["common_name"],
                    "scientific_name": sci,
                    "sara_status": row["sara_status"],
                    "taxon": (ob.get("taxon") or {}).get("iconic_taxon_name"),
                    "observed_on": ob.get("observed_on"),
                    "place": ob.get("place_guess"),
                    "location_precision": ("Approximate (sensitive species — obscured by iNaturalist)"
                                           if obscured else "Precise"),
                    "url": ob.get("uri"),
                }})
            n += 1
        print(f"  {row['common_name']}: {n} pts")
        time.sleep(0.4)  # be polite to the iNaturalist API

    g = gpd.GeoDataFrame.from_features(feats, crs=4326)
    # keep points within the treaty area (small buffer since obscured points may sit just outside)
    g = g[g.geometry.within(geom.buffer(0.02))].copy()

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    g.to_file(OUT_PATH, driver="GeoJSON", COORDINATE_PRECISION=5)
    mb = OUT_PATH.stat().st_size / 1024 / 1024
    approx = (g["location_precision"] != "Precise").sum()
    print(f"\nWrote {len(g)} points ({g['common_name'].nunique()} species, "
          f"{int(approx)} approximate) -> {OUT_PATH} ({mb:.2f} MB)")

    if args.upload:
        subprocess.run(["aws", "s3", "cp", str(OUT_PATH), S3_URI,
                        "--content-type", "application/geo+json"], check=True)
        print(f"Uploaded -> {S3_URI}")


if __name__ == "__main__":
    main()
