#!/usr/bin/env python3
"""
Build the Critical Habitat richness surface for the Williams Treaty map.

The published critical-habitat dataset stores one dissolved polygon per species.
Within the treaty territory those 29 polygons overlap almost completely -- their
union covers 100% of the territory and they stack 4 species deep on average, with
Blanding's Turtle alone covering 96.7% -- so drawing them as stacked translucent
fills produces an opaque wash that shows nothing.

This script converts that pile into a choropleth of how MANY species have critical
habitat at each location:

  1. Polygonize the union of all species-polygon boundaries. That yields atomic
     regions whose species count is constant throughout -- an exact planar overlay,
     not a grid approximation, so small habitats survive intact.
  2. Count the species covering each region (tested at a representative point,
     which is guaranteed to lie inside the region).
  3. Dissolve regions by that count, so the output is one multipolygon per
     richness level rather than thousands of slivers.

Output:  data/datasets/biodiversity/critical_habitat_richness.geojson
Layer:   critical_habitat  (Biodiversity category in web/config/layers.yaml)

Usage:
    python scripts/build_critical_habitat_richness.py            # build only
    python scripts/build_critical_habitat_richness.py --upload   # build + upload to S3
"""

import argparse
import subprocess
import warnings
from pathlib import Path

import geopandas as gpd
from shapely.ops import polygonize, unary_union

warnings.filterwarnings("ignore")

PROJECT_ROOT = Path(__file__).parent.parent
AOI_PATH = PROJECT_ROOT / "data/boundaries/williams_treaty.geojson"
SRC_PATH = PROJECT_ROOT / "data/datasets/biodiversity/critical_habitat_species_at_risk.geojson"
OUT_PATH = PROJECT_ROOT / "data/datasets/biodiversity/critical_habitat_richness.geojson"
S3_URI = "s3://ontario-environmental-data/datasets/biodiversity/critical_habitat_richness.geojson"

ONT_LAMBERT = 3161  # metric CRS, so areas come out in real hectares


def atomic_regions(species):
    """Split the overlapping species polygons into non-overlapping regions.

    Polygonizing the union of every boundary gives regions that are either wholly
    inside or wholly outside each species polygon, so a single point test per
    region resolves its species count exactly.
    """
    boundaries = unary_union([geom.boundary for geom in species.geometry])
    regions = gpd.GeoDataFrame(geometry=list(polygonize(boundaries)), crs=species.crs)
    return regions[~regions.geometry.is_empty].reset_index(drop=True)


def count_species(regions, species):
    """Species count per region, plus the contributing species names."""
    probes = gpd.GeoDataFrame(geometry=regions.representative_point(), crs=regions.crs)
    hits = gpd.sjoin(
        probes, species[["common_name", "geometry"]], predicate="within", how="left"
    )
    grouped = hits.groupby(hits.index)["common_name"]

    out = regions.copy()
    out["species_count"] = grouped.count().reindex(out.index).fillna(0).astype(int)
    # Regions outside every species polygon are holes in the overlay, not habitat.
    return out[out["species_count"] > 0].copy()


def dissolve_by_count(regions, aoi_geom):
    """One multipolygon per richness level, clipped to the treaty boundary."""
    merged = regions.dissolve(by="species_count", as_index=False)[
        ["species_count", "geometry"]
    ]
    merged["geometry"] = merged.geometry.intersection(aoi_geom)
    merged = merged[~merged.geometry.is_empty].copy()
    merged["area_ha"] = (merged.area / 10_000).round(1)
    return merged.sort_values("species_count").reset_index(drop=True)


def main():
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument("--upload", action="store_true",
                    help="Upload result to S3 after building")
    args = ap.parse_args()

    species = gpd.read_file(SRC_PATH).to_crs(ONT_LAMBERT)
    aoi_geom = gpd.read_file(AOI_PATH).to_crs(ONT_LAMBERT).geometry.union_all()
    print(f"Source: {len(species)} species polygons")

    regions = atomic_regions(species)
    print(f"Planar overlay: {len(regions)} atomic regions")

    counted = count_species(regions, species)
    merged = dissolve_by_count(counted, aoi_geom)

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    merged.to_crs(4326).to_file(OUT_PATH, driver="GeoJSON", COORDINATE_PRECISION=5)

    mb = OUT_PATH.stat().st_size / 1024 / 1024
    print(f"\nWrote {len(merged)} richness levels -> {OUT_PATH} ({mb:.2f} MB)")
    print(f"{'species':>8}  {'hectares':>14}")
    for _, r in merged.iterrows():
        print(f"{int(r.species_count):>8}  {r.area_ha:>14,.0f}")

    if args.upload:
        subprocess.run(["aws", "s3", "cp", str(OUT_PATH), S3_URI,
                        "--content-type", "application/geo+json"], check=True)
        print(f"Uploaded -> {S3_URI}")


if __name__ == "__main__":
    main()
