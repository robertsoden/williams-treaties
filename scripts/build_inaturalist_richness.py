#!/usr/bin/env python3
"""
Build the iNaturalist Biodiversity Richness grid for the Williams Treaty map.

Divides the Williams Treaty territory into a ~12 km (0.15 degree) grid and, for
each cell, queries the iNaturalist API for the number of DISTINCT research-grade
species observed there (all taxa). The result is a choropleth of species richness
that highlights biodiversity hotspots.

This is a CUMULATIVE measure (all species ever recorded per cell), so it drifts
very slowly. Recommended refresh cadence: ~once a year. See MANUAL_DOWNLOADS.md.

Output:  data/datasets/biodiversity/inaturalist_species_richness.geojson
Layer:   inat_richness  (Biodiversity category in web/config/layers.yaml)

Usage:
    python scripts/build_inaturalist_richness.py            # build only
    python scripts/build_inaturalist_richness.py --upload   # build + upload to S3
"""

import argparse
import subprocess
import time
from pathlib import Path

import geopandas as gpd
import requests
from shapely.geometry import box
import warnings
warnings.filterwarnings("ignore")

PROJECT_ROOT = Path(__file__).parent.parent
AOI_PATH = PROJECT_ROOT / "data/boundaries/williams_treaty.geojson"
OUT_PATH = PROJECT_ROOT / "data/datasets/biodiversity/inaturalist_species_richness.geojson"
S3_URI = "s3://ontario-environmental-data/datasets/biodiversity/inaturalist_species_richness.geojson"

CELL_DEG = 0.15  # grid cell size in degrees (~12-16 km)
API = "https://api.inaturalist.org/v1/observations/species_counts"


def build_grid(geom, minx, miny, maxx, maxy):
    cells = []
    x = minx
    while x < maxx:
        y = miny
        while y < maxy:
            c = box(x, y, x + CELL_DEG, y + CELL_DEG)
            if c.intersects(geom):
                cells.append(c)
            y += CELL_DEG
        x += CELL_DEG
    return cells


def species_richness(sess, bounds):
    """Distinct research-grade species observed in a bbox (with light retry)."""
    minx, miny, maxx, maxy = bounds
    params = {"quality_grade": "research", "swlng": minx, "swlat": miny,
              "nelng": maxx, "nelat": maxy, "per_page": 0}
    for attempt in range(3):
        try:
            r = sess.get(API, params=params, timeout=60).json()
            return r["total_results"]
        except Exception:
            time.sleep(1.5)
    return None


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--upload", action="store_true", help="Upload result to S3 after building")
    args = ap.parse_args()

    aoi = gpd.read_file(AOI_PATH).to_crs(4326)
    geom = aoi.geometry.union_all()
    minx, miny, maxx, maxy = aoi.total_bounds
    cells = build_grid(geom, minx, miny, maxx, maxy)
    print(f"Grid {CELL_DEG} deg: {len(cells)} cells intersect treaty boundary")

    sess = requests.Session()
    rows = []
    for i, c in enumerate(cells):
        rows.append({"geometry": c, "species_richness": species_richness(sess, c.bounds)})
        if (i + 1) % 25 == 0:
            print(f"  {i + 1}/{len(cells)} cells done", flush=True)
        time.sleep(0.3)  # be polite to the iNaturalist API

    g = gpd.GeoDataFrame(rows, crs=4326)
    g["geometry"] = g.geometry.intersection(geom)  # clip cells to boundary for display
    g = g[~g.geometry.is_empty & g["species_richness"].notna()].copy()
    g["species_richness"] = g["species_richness"].astype(int)

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    g.to_file(OUT_PATH, driver="GeoJSON", COORDINATE_PRECISION=5)
    mb = OUT_PATH.stat().st_size / 1024 / 1024
    print(f"\nWrote {len(g)} cells -> {OUT_PATH} ({mb:.2f} MB)")
    print(f"Richness range: {g['species_richness'].min()}-{g['species_richness'].max()} "
          f"(median {int(g['species_richness'].median())})")

    if args.upload:
        subprocess.run(["aws", "s3", "cp", str(OUT_PATH), S3_URI,
                        "--content-type", "application/geo+json"], check=True)
        print(f"Uploaded -> {S3_URI}")


if __name__ == "__main__":
    main()
