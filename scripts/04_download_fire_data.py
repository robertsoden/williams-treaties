#!/usr/bin/env python3
"""
Download fire hazard data for Williams Treaty Territories.

This script downloads:
1. Canadian Wildland Fire Information System (CWFIS) data
2. Ontario historical fire occurrence
3. National Burned Area Composite
4. Fire weather indices

Usage:
    python scripts/04_download_fire_data.py [--historical-years N]
"""

import sys
import argparse
from pathlib import Path
from datetime import datetime, timedelta
import geopandas as gpd
import pandas as pd
import requests
import json

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts.utils import (
    setup_logging,
    load_config,
    get_project_root,
    ensure_dir,
    load_aoi,
    download_file,
    get_bounding_box,
    clip_to_aoi,
    save_geojson
)


# CWFIS WMS/WFS endpoints
CWFIS_BASE_URL = "https://cwfis.cfs.nrcan.gc.ca/geoserver"
NFIS_BASE_URL = "https://opendata.nfis.org"


def download_cwfis_current_fire_danger(aoi: gpd.GeoDataFrame, output_dir: Path, logger):
    """
    Download current fire danger ratings from CWFIS.

    Args:
        aoi: Area of interest
        output_dir: Directory to save outputs
        logger: Logger instance
    """
    logger.info("Downloading current fire danger ratings from CWFIS")

    # CWFIS provides WMS/WFS services
    # This would require WMS/WFS client implementation

    logger.info("Note: CWFIS data is available via WMS/WFS services")
    logger.info("Web services:")
    logger.info(f"  WMS: {CWFIS_BASE_URL}/public/wms")
    logger.info(f"  WFS: {CWFIS_BASE_URL}/public/wfs")
    logger.info("\nAvailable layers include:")
    logger.info("  - Fire Weather Index (FWI)")
    logger.info("  - Initial Spread Index (ISI)")
    logger.info("  - Buildup Index (BUI)")
    logger.info("  - Daily Fire Danger Rating")

    # Example: Save connection info
    wms_info = {
        "service": "WMS",
        "url": f"{CWFIS_BASE_URL}/public/wms",
        "version": "1.1.1",
        "layers": [
            "public:fwi_current",
            "public:fire_danger_rating"
        ]
    }

    info_file = output_dir / "cwfis_wms_info.json"
    with open(info_file, 'w') as f:
        json.dump(wms_info, f, indent=2)

    logger.info(f"WMS connection info saved to {info_file}")


def download_ontario_historical_fires(aoi: gpd.GeoDataFrame, output_dir: Path,
                                      years: int, logger):
    """
    Download Ontario historical fire occurrence data.

    Args:
        aoi: Area of interest
        output_dir: Directory to save outputs
        years: Number of years of historical data
        logger: Logger instance
    """
    logger.info(f"Downloading Ontario historical fires (last {years} years)")

    # Ontario fire data is available through Ontario GeoHub
    # This would typically be downloaded manually or via API

    logger.info("Ontario historical fire data sources:")
    logger.info("  1. Ontario GeoHub: https://geohub.lio.gov.on.ca/")
    logger.info("  2. Search for: 'Fire Regions' and 'Historical Fires'")
    logger.info("\nDatasets to look for:")
    logger.info("  - Fire Region (FIRE_REGION)")
    logger.info("  - Fire Point (historical fire locations)")
    logger.info("  - Fire Perimeter (burned areas)")

    # Create placeholder metadata
    ontario_fire_info = {
        "source": "Ontario Ministry of Natural Resources and Forestry",
        "data_portal": "https://geohub.lio.gov.on.ca/",
        "datasets": {
            "fire_regions": "FIRE_REGION",
            "fire_points": "Fire occurrences point dataset",
            "fire_perimeters": "Fire perimeters polygon dataset"
        },
        "temporal_coverage": f"Last {years} years",
        "access": "Manual download required from Ontario GeoHub"
    }

    info_file = output_dir / "ontario_fire_data_info.json"
    with open(info_file, 'w') as f:
        json.dump(ontario_fire_info, f, indent=2)

    logger.info(f"Ontario fire data info saved to {info_file}")


def download_national_burned_area_composite(aoi: gpd.GeoDataFrame, output_dir: Path,
                                            start_year: int, end_year: int, logger):
    """
    Download National Burned Area Composite (NBAC) data.

    Args:
        aoi: Area of interest
        output_dir: Directory to save outputs
        start_year: Start year
        end_year: End year
        logger: Logger instance
    """
    logger.info(f"National Burned Area Composite ({start_year}-{end_year})")

    # NBAC is available through the National Forest Information System
    logger.info(f"Data available at: {NFIS_BASE_URL}")
    logger.info("\nDataset: National Burned Area Composite")
    logger.info("  Resolution: 30m")
    logger.info("  Source: Landsat-derived")
    logger.info("  Coverage: 1985-present")
    logger.info("  Format: GeoTIFF (annual files)")

    # Get AOI bounding box for reference
    bbox = get_bounding_box(aoi)
    logger.info(f"\nAOI Bounding Box: {bbox}")
    logger.info("Use this bounding box when downloading data")

    nbac_info = {
        "name": "National Burned Area Composite",
        "source": "Natural Resources Canada - Canadian Forest Service",
        "url": NFIS_BASE_URL,
        "resolution": "30m",
        "temporal_range": {
            "start": start_year,
            "end": end_year
        },
        "aoi_bbox": {
            "minx": bbox[0],
            "miny": bbox[1],
            "maxx": bbox[2],
            "maxy": bbox[3]
        },
        "download_instructions": [
            "1. Visit https://opendata.nfis.org/",
            "2. Navigate to 'Burned Areas'",
            "3. Select 'National Burned Area Composite'",
            "4. Download annual files for your date range",
            "5. Clip to AOI bounding box"
        ]
    }

    info_file = output_dir / "nbac_info.json"
    with open(info_file, 'w') as f:
        json.dump(nbac_info, f, indent=2)

    logger.info(f"NBAC data info saved to {info_file}")


def create_fire_risk_zones(aoi: gpd.GeoDataFrame, output_path: Path, logger):
    """
    Create example fire risk zones based on generic risk factors.

    This creates a simplified demonstration of fire risk mapping.
    Real risk assessment would incorporate fuel types, topography, climate, etc.

    Args:
        aoi: Area of interest
        output_path: Path to save output
        logger: Logger instance
    """
    logger.info("Creating example fire risk zones")

    # For demonstration, create simple risk zones
    # In reality, this would be based on:
    # - Fuel type mapping
    # - Topography (slope, aspect)
    # - Historical fire occurrence
    # - Climate data (temperature, precipitation)
    # - Proximity to human activity

    aoi_utm = aoi.to_crs("EPSG:26917")

    # Create buffer zones (simplified risk zones)
    risk_zones = []
    risk_levels = [
        ("High", 1000),   # 1km buffer
        ("Medium", 3000), # 3km buffer
        ("Low", 5000)     # 5km buffer
    ]

    for risk_level, buffer_dist in risk_levels:
        buffered = aoi_utm.copy()
        buffered['geometry'] = buffered.buffer(buffer_dist)
        buffered['risk_level'] = risk_level
        buffered['buffer_m'] = buffer_dist
        risk_zones.append(buffered)

    # Combine into single GeoDataFrame
    risk_gdf = gpd.GeoDataFrame(pd.concat(risk_zones, ignore_index=True))

    # Convert back to geographic CRS
    risk_gdf = risk_gdf.to_crs("EPSG:4326")

    save_geojson(risk_gdf, output_path)
    logger.info(f"Example fire risk zones saved to {output_path}")
    logger.info("Note: These are simplified example zones")


def main():
    """Main execution function."""
    parser = argparse.ArgumentParser(
        description='Download fire hazard data for Williams Treaty Territories'
    )
    parser.add_argument(
        '--historical-years',
        type=int,
        default=30,
        help='Number of years of historical data to retrieve (default: 30)'
    )

    args = parser.parse_args()

    logger = setup_logging(__name__)
    logger.info("Starting fire hazard data download")

    # Load configuration and AOI
    config = load_config()

    try:
        aoi = load_aoi(config)
        logger.info("Loaded AOI")
    except FileNotFoundError as e:
        logger.error(str(e))
        sys.exit(1)

    # Set up output directories
    project_root = get_project_root()
    raw_dir = ensure_dir(project_root / config['directories']['raw'] / 'fire')
    processed_dir = ensure_dir(project_root / config['directories']['processed'] / 'fire')

    # Download/prepare various fire datasets
    logger.info("\n" + "="*60)
    logger.info("1. CURRENT FIRE DANGER")
    logger.info("="*60)
    download_cwfis_current_fire_danger(aoi, raw_dir, logger)

    logger.info("\n" + "="*60)
    logger.info("2. ONTARIO HISTORICAL FIRES")
    logger.info("="*60)
    download_ontario_historical_fires(aoi, raw_dir, args.historical_years, logger)

    logger.info("\n" + "="*60)
    logger.info("3. NATIONAL BURNED AREA COMPOSITE")
    logger.info("="*60)
    current_year = datetime.now().year
    start_year = current_year - args.historical_years
    download_national_burned_area_composite(aoi, raw_dir, start_year, current_year, logger)

    logger.info("\n" + "="*60)
    logger.info("FIRE DATA DOWNLOAD SUMMARY")
    logger.info("="*60)
    logger.info("\nMost fire hazard datasets require manual download or API access.")
    logger.info("Connection information and download instructions have been saved to:")
    logger.info(f"  {raw_dir}")
    logger.info("\nKey data sources:")
    logger.info("  1. CWFIS: Real-time fire weather and danger ratings")
    logger.info("  2. Ontario GeoHub: Historical fire occurrence")
    logger.info("  3. NFIS: National Burned Area Composite (30m resolution)")
    logger.info("\nNext steps:")
    logger.info("  1. Review the JSON files in the raw/fire directory")
    logger.info("  2. Follow download instructions for each dataset")
    logger.info("  3. Place downloaded files in the raw/fire directory")
    logger.info("  4. Run post-processing scripts to clip to AOI")


if __name__ == "__main__":
    # Import pandas here if needed for creating risk zones
    try:
        import pandas as pd
    except ImportError:
        pd = None

    main()
