#!/usr/bin/env python3
"""
Download and Process New Data Layers for Williams Treaty Map

This script downloads climate adaptation data from federal and provincial sources
that are not yet available in the project. Data is clipped to the Williams Treaty
territory and exported as GeoJSON for use in the web map.

Based on the data pipeline from new/ directory.

Usage:
    python scripts/download_new_layers.py [--list] [--layer LAYER_NAME] [--all]

Examples:
    python scripts/download_new_layers.py --list           # List available layers
    python scripts/download_new_layers.py --layer wetlands # Download one layer
    python scripts/download_new_layers.py --all            # Download all layers
"""

import os
import sys
import json
import argparse
import logging
import zipfile
import tempfile
from pathlib import Path
from datetime import datetime
from urllib.parse import urlencode

import requests
from tqdm import tqdm

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
    ]
)
logger = logging.getLogger(__name__)

# =============================================================================
# CONFIGURATION
# =============================================================================

# Project paths
PROJECT_ROOT = Path(__file__).parent.parent
DATA_DIR = PROJECT_ROOT / "data"
OUTPUT_DIR = DATA_DIR / "datasets"
RAW_DIR = DATA_DIR / "raw"
METADATA_DIR = DATA_DIR / "metadata"

# Williams Treaty Territory Bounds (WGS84)
# Bounding box [minx, miny, maxx, maxy]
WILLIAMS_BBOX = [-80.81, 43.64, -76.92, 46.39]
WILLIAMS_BBOX_BUFFERED = [-80.91, 43.54, -76.82, 46.49]

# Ontario GeoHub ESRI REST base URL
GEOHUB_REST_BASE = "https://ws.lioservices.lrc.gov.on.ca/arcgis2/rest/services"

# =============================================================================
# NEW DATA LAYERS TO DOWNLOAD
# =============================================================================

NEW_LAYERS = {
    # WATER / HYDROLOGY
    "wetlands": {
        "name": "Wetlands with Significance",
        "description": "Provincial wetlands with ecological significance ratings",
        "category": "water",
        "rest_url": f"{GEOHUB_REST_BASE}/LIO_OPEN_DATA/LIO_Open01/MapServer/15",
        "output_path": "environmental/wetlands.geojson",
        "source": "Ontario GeoHub - Land Information Ontario",
        "license": "Open Government Licence - Ontario",
    },
    "watercourse": {
        "name": "Watercourses (Rivers/Streams)",
        "description": "Ontario Hydro Network - linear water features (1:10M scale)",
        "category": "water",
        "rest_url": f"{GEOHUB_REST_BASE}/LIO_OPEN_DATA/LIO_Open02/MapServer/15",
        "output_path": "environmental/watercourses.geojson",
        "source": "Ontario GeoHub - Ontario Hydro Network",
        "license": "Open Government Licence - Ontario",
    },
    "waterbody": {
        "name": "Waterbodies (Lakes/Ponds)",
        "description": "Ontario Hydro Network - polygon water features (1:10M scale)",
        "category": "water",
        "rest_url": f"{GEOHUB_REST_BASE}/LIO_OPEN_DATA/LIO_Open02/MapServer/8",
        "output_path": "environmental/waterbodies.geojson",
        "source": "Ontario GeoHub - Ontario Hydro Network",
        "license": "Open Government Licence - Ontario",
    },
    "watershed_tertiary": {
        "name": "Tertiary Watersheds",
        "description": "Ontario Watershed Boundaries - Tertiary level drainage areas",
        "category": "water",
        "rest_url": f"{GEOHUB_REST_BASE}/LIO_OPEN_DATA/LIO_Open04/MapServer/2",
        "output_path": "environmental/watersheds_tertiary.geojson",
        "source": "Ontario GeoHub - Ontario Watershed Boundaries",
        "license": "Open Government Licence - Ontario",
    },
    "watershed_quaternary": {
        "name": "Quaternary Watersheds",
        "description": "Ontario Watershed Boundaries - Quaternary (smallest) drainage areas",
        "category": "water",
        "rest_url": f"{GEOHUB_REST_BASE}/LIO_OPEN_DATA/LIO_Open04/MapServer/1",
        "output_path": "environmental/watersheds_quaternary.geojson",
        "source": "Ontario GeoHub - Ontario Watershed Boundaries",
        "license": "Open Government Licence - Ontario",
    },
    "dams": {
        "name": "Dam Inventory",
        "description": "Ontario Dam Inventory - location and details of dams",
        "category": "water",
        "rest_url": f"{GEOHUB_REST_BASE}/LIO_OPEN_DATA/LIO_Open04/MapServer/0",
        "output_path": "environmental/dams.geojson",
        "source": "Ontario GeoHub",
        "license": "Open Government Licence - Ontario",
    },

    # ECOLOGY / PROTECTED AREAS
    "conservation_reserves": {
        "name": "Conservation Reserves",
        "description": "Ontario Conservation Reserves - regulated protected areas",
        "category": "ecology",
        "rest_url": f"{GEOHUB_REST_BASE}/LIO_OPEN_DATA/LIO_Open03/MapServer/2",
        "output_path": "protected_areas/conservation_reserves.geojson",
        "source": "Ontario GeoHub",
        "license": "Open Government Licence - Ontario",
    },
    "federal_protected": {
        "name": "Federal Protected Areas",
        "description": "Federal protected areas (National Parks, Wildlife Areas)",
        "category": "ecology",
        "rest_url": f"{GEOHUB_REST_BASE}/LIO_OPEN_DATA/LIO_Open03/MapServer/10",
        "output_path": "protected_areas/federal_protected.geojson",
        "source": "Ontario GeoHub",
        "license": "Open Government Licence - Ontario",
    },
    "national_wildlife_area": {
        "name": "National Wildlife Areas",
        "description": "National Wildlife Areas in Ontario",
        "category": "ecology",
        "rest_url": f"{GEOHUB_REST_BASE}/LIO_OPEN_DATA/LIO_Open03/MapServer/9",
        "output_path": "protected_areas/national_wildlife_areas.geojson",
        "source": "Ontario GeoHub",
        "license": "Open Government Licence - Ontario",
    },
    "ecodistrict": {
        "name": "Ecodistricts",
        "description": "Ontario Ecodistricts - ecological classification units",
        "category": "ecology",
        "rest_url": f"{GEOHUB_REST_BASE}/LIO_OPEN_DATA/LIO_Open03/MapServer/15",
        "output_path": "environmental/ecodistricts.geojson",
        "source": "Ontario GeoHub",
        "license": "Open Government Licence - Ontario",
    },
    "ecoregion": {
        "name": "Ecoregions",
        "description": "Ontario Ecoregions - broad ecological classification",
        "category": "ecology",
        "rest_url": f"{GEOHUB_REST_BASE}/LIO_OPEN_DATA/LIO_Open03/MapServer/16",
        "output_path": "environmental/ecoregions.geojson",
        "source": "Ontario GeoHub",
        "license": "Open Government Licence - Ontario",
    },

    # INFRASTRUCTURE
    "trails": {
        "name": "Recreational Trails",
        "description": "Ontario Recreational Trail Network - trail segments",
        "category": "recreation",
        "rest_url": f"{GEOHUB_REST_BASE}/LIO_OPEN_DATA/LIO_Open04/MapServer/19",
        "output_path": "infrastructure/trails.geojson",
        "source": "Ontario GeoHub - Ontario Trail Network",
        "license": "Open Government Licence - Ontario",
    },
    "trail_access": {
        "name": "Trail Access Points",
        "description": "Ontario Trail Network - access points and trailheads",
        "category": "recreation",
        "rest_url": f"{GEOHUB_REST_BASE}/LIO_OPEN_DATA/LIO_Open04/MapServer/20",
        "output_path": "infrastructure/trail_access_points.geojson",
        "source": "Ontario GeoHub - Ontario Trail Network",
        "license": "Open Government Licence - Ontario",
    },

    # TERRAIN
    "contours": {
        "name": "Contour Lines",
        "description": "Topographic contour lines",
        "category": "terrain",
        "rest_url": f"{GEOHUB_REST_BASE}/LIO_OPEN_DATA/LIO_Open01/MapServer/29",
        "output_path": "environmental/contours.geojson",
        "source": "Ontario GeoHub",
        "license": "Open Government Licence - Ontario",
        "notes": "Large dataset - may take time to download",
    },
}

# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================

def get_bbox_esri():
    """Return bbox formatted for ESRI REST queries."""
    minx, miny, maxx, maxy = WILLIAMS_BBOX_BUFFERED
    return f"{minx},{miny},{maxx},{maxy}"


def ensure_directories():
    """Create output directories if they don't exist."""
    dirs = [
        OUTPUT_DIR / "environmental",
        OUTPUT_DIR / "protected_areas",
        OUTPUT_DIR / "infrastructure",
        RAW_DIR,
        METADATA_DIR,
    ]
    for d in dirs:
        d.mkdir(parents=True, exist_ok=True)
    logger.info(f"Output directories ready at: {OUTPUT_DIR}")


def query_esri_rest(
    rest_url: str,
    bbox: str = None,
    where: str = "1=1",
    out_fields: str = "*",
    out_sr: int = 4326,
    return_geometry: bool = True,
    max_records: int = 2000,
    output_path: Path = None
) -> dict:
    """
    Query an ESRI REST service and return GeoJSON.
    Handles pagination automatically.

    Args:
        rest_url: Base URL to the REST service layer
        bbox: Bounding box as "minx,miny,maxx,maxy"
        where: SQL where clause
        out_fields: Fields to return
        out_sr: Output spatial reference (default WGS84)
        return_geometry: Whether to return geometries
        max_records: Maximum records per request
        output_path: If provided, save GeoJSON to this path

    Returns:
        GeoJSON dict
    """
    all_features = []
    offset = 0

    while True:
        params = {
            "where": where,
            "outFields": out_fields,
            "outSR": out_sr,
            "returnGeometry": str(return_geometry).lower(),
            "f": "geojson",
            "resultOffset": offset,
            "resultRecordCount": max_records,
        }

        if bbox:
            params["geometry"] = bbox
            params["geometryType"] = "esriGeometryEnvelope"
            params["spatialRel"] = "esriSpatialRelIntersects"
            params["inSR"] = 4326

        query_url = f"{rest_url}/query?{urlencode(params)}"

        if offset == 0:
            logger.info(f"Querying: {rest_url}")

        response = requests.get(query_url, timeout=120)
        response.raise_for_status()
        data = response.json()

        if "features" not in data:
            error_msg = data.get('error', {}).get('message', 'Unknown error')
            logger.warning(f"No features in response: {error_msg}")
            break

        features = data["features"]
        all_features.extend(features)

        logger.info(f"  Retrieved {len(features)} features (total: {len(all_features)})")

        # Check if we've retrieved all features
        if len(features) < max_records:
            break

        offset += max_records

    # Build GeoJSON FeatureCollection
    geojson = {
        "type": "FeatureCollection",
        "features": all_features,
        "crs": {
            "type": "name",
            "properties": {"name": f"EPSG:{out_sr}"}
        }
    }

    if output_path:
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, 'w') as f:
            json.dump(geojson, f)
        logger.info(f"Saved: {output_path} ({len(all_features)} features)")

    return geojson


def validate_geojson(geojson_path: Path) -> bool:
    """Basic validation of a GeoJSON file."""
    try:
        with open(geojson_path) as f:
            data = json.load(f)

        if data.get("type") != "FeatureCollection":
            logger.warning(f"Not a FeatureCollection: {geojson_path}")
            return False

        features = data.get("features", [])
        if not features:
            logger.warning(f"No features in: {geojson_path}")
            return False

        logger.info(f"Valid GeoJSON: {geojson_path.name} ({len(features)} features)")
        return True

    except Exception as e:
        logger.error(f"Invalid GeoJSON {geojson_path}: {e}")
        return False


def save_metadata(layer_id: str, layer_config: dict, feature_count: int):
    """Save metadata JSON for a downloaded layer."""
    metadata = {
        "layer_id": layer_id,
        "name": layer_config["name"],
        "description": layer_config.get("description", ""),
        "category": layer_config.get("category", ""),
        "source": layer_config.get("source", ""),
        "license": layer_config.get("license", ""),
        "download_date": datetime.now().isoformat(),
        "feature_count": feature_count,
        "bounding_box": WILLIAMS_BBOX_BUFFERED,
        "output_path": layer_config["output_path"],
    }

    metadata_path = METADATA_DIR / f"{layer_id}_metadata.json"
    with open(metadata_path, 'w') as f:
        json.dump(metadata, f, indent=2)

    logger.info(f"Saved metadata: {metadata_path.name}")


def get_file_size_mb(path: Path) -> float:
    """Get file size in MB."""
    if path.exists():
        return path.stat().st_size / 1024 / 1024
    return 0


# =============================================================================
# MAIN DOWNLOAD FUNCTIONS
# =============================================================================

def download_layer(layer_id: str) -> bool:
    """Download a single layer by ID."""
    if layer_id not in NEW_LAYERS:
        logger.error(f"Unknown layer: {layer_id}")
        logger.info(f"Available layers: {', '.join(NEW_LAYERS.keys())}")
        return False

    layer = NEW_LAYERS[layer_id]
    output_path = OUTPUT_DIR / layer["output_path"]

    logger.info("=" * 60)
    logger.info(f"Downloading: {layer['name']}")
    logger.info(f"Description: {layer.get('description', 'N/A')}")
    logger.info("=" * 60)

    try:
        # Download from ESRI REST service
        geojson = query_esri_rest(
            rest_url=layer["rest_url"],
            bbox=get_bbox_esri(),
            output_path=output_path
        )

        feature_count = len(geojson.get("features", []))

        if feature_count == 0:
            logger.warning(f"No features found for {layer['name']} in Williams Treaty area")
            return False

        # Validate
        if validate_geojson(output_path):
            # Save metadata
            save_metadata(layer_id, layer, feature_count)

            file_size = get_file_size_mb(output_path)
            logger.info(f"SUCCESS: {layer['name']} - {feature_count} features, {file_size:.2f} MB")
            return True
        else:
            return False

    except Exception as e:
        logger.error(f"Failed to download {layer['name']}: {e}")
        return False


def download_all_layers() -> dict:
    """Download all new layers."""
    results = {}

    logger.info("=" * 60)
    logger.info("DOWNLOADING ALL NEW LAYERS")
    logger.info(f"Total layers: {len(NEW_LAYERS)}")
    logger.info("=" * 60)

    for layer_id in NEW_LAYERS:
        results[layer_id] = download_layer(layer_id)

    return results


def list_layers():
    """List all available layers to download."""
    print("\n" + "=" * 70)
    print("AVAILABLE NEW DATA LAYERS")
    print("=" * 70)

    # Group by category
    categories = {}
    for layer_id, layer in NEW_LAYERS.items():
        cat = layer.get("category", "other")
        if cat not in categories:
            categories[cat] = []
        categories[cat].append((layer_id, layer))

    for category, layers in sorted(categories.items()):
        print(f"\n{category.upper()}")
        print("-" * 40)
        for layer_id, layer in layers:
            output_path = OUTPUT_DIR / layer["output_path"]
            exists = "✓" if output_path.exists() else " "
            print(f"  [{exists}] {layer_id}")
            print(f"      {layer['name']}")
            print(f"      {layer.get('description', '')[:60]}")

    print("\n" + "=" * 70)
    print("Usage:")
    print("  python scripts/download_new_layers.py --layer wetlands")
    print("  python scripts/download_new_layers.py --all")
    print("=" * 70 + "\n")


def print_summary(results: dict):
    """Print download summary."""
    print("\n" + "=" * 60)
    print("DOWNLOAD SUMMARY")
    print("=" * 60)

    success = sum(1 for v in results.values() if v)
    total = len(results)

    for layer_id, status in results.items():
        status_str = "✓" if status else "✗"
        layer_name = NEW_LAYERS[layer_id]["name"]
        print(f"  {status_str} {layer_name}")

    print(f"\nCompleted: {success}/{total} layers")

    if success < total:
        print("\nSome downloads failed. Check logs for details.")
    else:
        print("\nAll downloads complete!")

    print("\nNext steps:")
    print("  1. Update web/config/layers.yaml to add new layers")
    print("  2. Upload to S3: aws s3 sync data/datasets/ s3://your-bucket/datasets/")
    print("=" * 60 + "\n")


# =============================================================================
# MAIN
# =============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="Download new data layers for Williams Treaty Map",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --list              List available layers
  %(prog)s --layer wetlands    Download wetlands layer
  %(prog)s --layer flood_plain Download flood plains
  %(prog)s --all               Download all layers
        """
    )

    parser.add_argument(
        "--list", "-l",
        action="store_true",
        help="List available layers"
    )
    parser.add_argument(
        "--layer",
        type=str,
        help="Download a specific layer by ID"
    )
    parser.add_argument(
        "--all", "-a",
        action="store_true",
        help="Download all new layers"
    )

    args = parser.parse_args()

    # Default to list if no arguments
    if not any([args.list, args.layer, args.all]):
        args.list = True

    if args.list:
        list_layers()
        return 0

    # Ensure directories exist
    ensure_directories()

    if args.layer:
        success = download_layer(args.layer)
        return 0 if success else 1

    if args.all:
        results = download_all_layers()
        print_summary(results)
        success_count = sum(1 for v in results.values() if v)
        return 0 if success_count == len(results) else 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
