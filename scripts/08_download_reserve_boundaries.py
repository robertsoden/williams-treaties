#!/usr/bin/env python3
"""
Download and filter First Nations reserve boundaries for Williams Treaty communities.

This script downloads the official First Nations reserve boundaries from
Indigenous Services Canada and filters for the 7 Williams Treaty First Nations.

Data Source:
    https://open.canada.ca/data/en/dataset/522b07b9-78e2-4819-b736-ad9208eb1067

Reserves included:
    - Alderville 35
    - Curve Lake 35
    - Hiawatha 36
    - Scugog Island 34
    - Chimnissing 1 (Beausoleil)
    - Georgina Island 33
    - Rama 32

Usage:
    python scripts/08_download_reserve_boundaries.py
"""

import sys
import argparse
from pathlib import Path
import geopandas as gpd
import pandas as pd
import requests
from io import BytesIO
import zipfile

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts.utils import (
    setup_logging,
    load_config,
    get_project_root,
    ensure_dir,
    save_geojson
)


# Williams Treaty reserve names to filter
WILLIAMS_TREATY_RESERVES = [
    'Alderville 35',
    'Curve Lake 35',
    'Hiawatha 36',
    'Scugog Island 34',
    'Chimnissing 1',
    'Georgina Island 33',
    'Rama 32'
]

# Alternative name patterns to match
RESERVE_PATTERNS = [
    'alderville',
    'curve lake',
    'hiawatha',
    'scugog',
    'chimnissing',
    'beausoleil',
    'georgina island',
    'rama'
]


def try_wfs_download(logger):
    """
    Attempt to download reserve boundaries via WFS service.

    Returns:
        GeoDataFrame or None if failed
    """
    logger.info("Attempting WFS download from Statistics Canada...")

    # Statistics Canada WFS endpoint
    wfs_urls = [
        # Census boundaries WFS
        "https://geoappext.nrcan.gc.ca/arcgis/services/FGP/aboriginal_lands/MapServer/WFSServer",
        # Alternative endpoints
        "https://maps.canada.ca/arcgis/services/StatCan/census_2021_indigenous/MapServer/WFSServer",
    ]

    for wfs_url in wfs_urls:
        try:
            logger.info(f"  Trying: {wfs_url}")

            # Try to get feature types
            params = {
                'service': 'WFS',
                'version': '2.0.0',
                'request': 'GetCapabilities'
            }

            response = requests.get(wfs_url, params=params, timeout=30)

            if response.status_code == 200:
                logger.info("  ✓ WFS endpoint accessible")
                # Try to get reserve data
                # This would require knowing the layer name
                # For now, return None to move to other methods

        except Exception as e:
            logger.debug(f"  Failed: {str(e)}")
            continue

    logger.info("  WFS download not available")
    return None


def try_direct_download(logger):
    """
    Attempt to download reserve boundaries from direct download links.

    Returns:
        GeoDataFrame or None if failed
    """
    logger.info("Attempting direct download from Open Canada portal...")

    # Known direct download URLs for First Nations reserves
    download_urls = [
        # GeoJSON format (if available)
        "https://www.aadnc-aandc.gc.ca/DAM/DAM-INTER-HQ/STAGING/texte-text/irs_1100100016677_eng.json",
        # Shapefile format
        "https://www.aadnc-aandc.gc.ca/DAM/DAM-INTER-HQ/STAGING/texte-text/irs_1100100016677_eng.zip",
    ]

    for url in download_urls:
        try:
            logger.info(f"  Trying: {url}")

            response = requests.get(url, timeout=60)

            if response.status_code == 200:
                logger.info("  ✓ Download successful")

                # Try to read as GeoJSON
                if url.endswith('.json') or url.endswith('.geojson'):
                    try:
                        gdf = gpd.read_file(BytesIO(response.content))
                        return gdf
                    except Exception as e:
                        logger.debug(f"  Failed to parse GeoJSON: {str(e)}")

                # Try to read as Shapefile
                elif url.endswith('.zip'):
                    try:
                        with zipfile.ZipFile(BytesIO(response.content)) as z:
                            # Find .shp file
                            shp_files = [f for f in z.namelist() if f.endswith('.shp')]
                            if shp_files:
                                logger.info(f"  Found shapefile: {shp_files[0]}")
                                gdf = gpd.read_file(f"zip://{BytesIO(response.content)}/{shp_files[0]}")
                                return gdf
                    except Exception as e:
                        logger.debug(f"  Failed to parse Shapefile: {str(e)}")

        except requests.exceptions.RequestException as e:
            logger.debug(f"  Request failed: {str(e)}")
            continue

    logger.info("  Direct download not available")
    return None


def filter_williams_treaty_reserves(gdf, logger):
    """
    Filter GeoDataFrame for Williams Treaty reserves.

    Args:
        gdf: GeoDataFrame with all reserves
        logger: Logger instance

    Returns:
        Filtered GeoDataFrame
    """
    logger.info("\nFiltering for Williams Treaty reserves...")

    # Print available columns for debugging
    logger.info(f"Available columns: {list(gdf.columns)}")

    # Common field names for reserve names
    name_fields = ['RESERVE_NAME', 'ENGLISH_NAME', 'NAME', 'RESNAME', 'name']

    name_field = None
    for field in name_fields:
        if field in gdf.columns:
            name_field = field
            break

    if not name_field:
        logger.error("Could not find reserve name field in dataset")
        logger.info("Please check the dataset structure manually")
        return None

    logger.info(f"Using field: {name_field}")

    # Filter by exact match first
    mask = gdf[name_field].isin(WILLIAMS_TREATY_RESERVES)
    filtered = gdf[mask].copy()

    logger.info(f"Exact matches found: {len(filtered)}")

    # If we didn't get all 7, try pattern matching
    if len(filtered) < 7:
        logger.info("Trying fuzzy matching for missing reserves...")

        for pattern in RESERVE_PATTERNS:
            # Find reserves matching pattern
            pattern_mask = gdf[name_field].str.lower().str.contains(pattern, na=False)
            pattern_matches = gdf[pattern_mask]

            if len(pattern_matches) > 0:
                logger.info(f"  Pattern '{pattern}' matches: {list(pattern_matches[name_field])}")

                # Add to filtered if not already there
                for idx, row in pattern_matches.iterrows():
                    if idx not in filtered.index:
                        filtered = pd.concat([filtered, row.to_frame().T])

    logger.info(f"\nTotal reserves found: {len(filtered)}")

    if len(filtered) > 0:
        logger.info("Reserve names:")
        for name in filtered[name_field]:
            logger.info(f"  - {name}")

    return filtered


def create_dummy_reserves(logger):
    """
    Create approximate reserve boundaries based on known locations.
    This is a fallback when real data is not available.

    Returns:
        GeoDataFrame with approximate boundaries
    """
    logger.info("\nCreating approximate reserve boundaries...")
    logger.info("Note: These are approximate locations only")

    # Approximate boundaries (1km buffer around known locations)
    reserves_data = [
        {
            'name': 'Alderville First Nation',
            'RESERVE_NAME': 'Alderville 35',
            'BAND_NAME': 'Alderville First Nation',
            'lon': -78.086,
            'lat': 44.051,
            'area_sqkm': 12.5
        },
        {
            'name': 'Curve Lake First Nation',
            'RESERVE_NAME': 'Curve Lake 35',
            'BAND_NAME': 'Curve Lake First Nation',
            'lon': -78.279,
            'lat': 44.547,
            'area_sqkm': 16.8
        },
        {
            'name': 'Hiawatha First Nation',
            'RESERVE_NAME': 'Hiawatha 36',
            'BAND_NAME': 'Hiawatha First Nation',
            'lon': -78.272,
            'lat': 44.224,
            'area_sqkm': 2.3
        },
        {
            'name': 'Mississaugas of Scugog Island First Nation',
            'RESERVE_NAME': 'Scugog Island 34',
            'BAND_NAME': 'Mississaugas of Scugog Island First Nation',
            'lon': -78.968,
            'lat': 44.171,
            'area_sqkm': 5.2
        },
        {
            'name': 'Chippewas of Beausoleil First Nation',
            'RESERVE_NAME': 'Chimnissing 1',
            'BAND_NAME': 'Chippewas of Beausoleil First Nation',
            'lon': -79.833,
            'lat': 44.780,
            'area_sqkm': 28.4
        },
        {
            'name': 'Chippewas of Georgina Island First Nation',
            'RESERVE_NAME': 'Georgina Island 33',
            'BAND_NAME': 'Chippewas of Georgina Island First Nation',
            'lon': -79.333,
            'lat': 44.450,
            'area_sqkm': 8.9
        },
        {
            'name': 'Chippewas of Rama First Nation',
            'RESERVE_NAME': 'Rama 32',
            'BAND_NAME': 'Chippewas of Rama First Nation',
            'lon': -79.315,
            'lat': 44.620,
            'area_sqkm': 9.1
        }
    ]

    # Create point geometries and buffer them
    from shapely.geometry import Point
    import numpy as np

    features = []
    for reserve in reserves_data:
        # Create approximate square boundary (~1km on each side)
        center = Point(reserve['lon'], reserve['lat'])
        # Buffer by 0.01 degrees (roughly 1km)
        buffer = center.buffer(0.01)

        features.append({
            'ENGLISH_NAME': reserve['name'],
            'RESERVE_NAME': reserve['RESERVE_NAME'],
            'BAND_NAME': reserve['BAND_NAME'],
            'AREA_SQKM': reserve['area_sqkm'],
            'geometry': buffer,
            'data_source': 'approximate'
        })

    gdf = gpd.GeoDataFrame(features, crs='EPSG:4326')

    logger.info(f"✓ Created {len(gdf)} approximate reserve boundaries")

    return gdf


def main():
    # Parse arguments
    parser = argparse.ArgumentParser(
        description='Download Williams Treaty First Nations reserve boundaries'
    )
    parser.add_argument(
        '--force-approximate',
        action='store_true',
        help='Skip download attempts and use approximate boundaries'
    )
    args = parser.parse_args()

    # Setup
    logger = setup_logging('download_reserves')
    config = load_config()
    project_root = get_project_root()

    logger.info("=" * 70)
    logger.info("Williams Treaty First Nations - Reserve Boundaries Download")
    logger.info("=" * 70)

    # Create output directory
    output_dir = ensure_dir(
        project_root / config['directories']['processed'] / 'communities'
    )
    output_path = output_dir / 'williams_treaty_reserves.geojson'

    reserves_gdf = None

    if not args.force_approximate:
        # Try to download real data
        logger.info("\nAttempting to download reserve boundaries...")

        # Method 1: Try WFS
        reserves_gdf = try_wfs_download(logger)

        # Method 2: Try direct download
        if reserves_gdf is None:
            reserves_gdf = try_direct_download(logger)

        # Filter for Williams Treaty reserves
        if reserves_gdf is not None:
            reserves_gdf = filter_williams_treaty_reserves(reserves_gdf, logger)

    # Fallback: Create approximate boundaries
    if reserves_gdf is None or len(reserves_gdf) == 0:
        logger.info("\n" + "=" * 70)
        logger.info("MANUAL DOWNLOAD REQUIRED")
        logger.info("=" * 70)
        logger.info("\nAutomatic download not available.")
        logger.info("\nTo get official reserve boundaries:")
        logger.info("  1. Visit: https://open.canada.ca/data/en/dataset/522b07b9-78e2-4819-b736-ad9208eb1067")
        logger.info("  2. Download the dataset (GeoJSON or Shapefile format)")
        logger.info("  3. Filter for these reserves:")
        for reserve in WILLIAMS_TREATY_RESERVES:
            logger.info(f"     - {reserve}")
        logger.info(f"  4. Save as: {output_path}")
        logger.info("\nCreating approximate boundaries for demonstration...")

        reserves_gdf = create_dummy_reserves(logger)

    # Save to file
    logger.info("\nSaving reserve boundaries...")

    # Ensure CRS is WGS84
    if reserves_gdf.crs != 'EPSG:4326':
        logger.info(f"  Reprojecting from {reserves_gdf.crs} to EPSG:4326")
        reserves_gdf = reserves_gdf.to_crs('EPSG:4326')

    # Save as GeoJSON
    save_geojson(reserves_gdf, output_path)
    logger.info(f"  ✓ Saved {len(reserves_gdf)} features")

    logger.info(f"\n✓ Saved to: {output_path}")
    logger.info(f"  File size: {output_path.stat().st_size / 1024:.1f} KB")
    logger.info(f"  Features: {len(reserves_gdf)}")

    # Summary
    logger.info("\n" + "=" * 70)
    logger.info("DOWNLOAD COMPLETE")
    logger.info("=" * 70)
    logger.info(f"\nReserve boundaries: {output_path}")
    logger.info(f"Features: {len(reserves_gdf)}")

    if 'data_source' in reserves_gdf.columns and 'approximate' in reserves_gdf['data_source'].values:
        logger.info("\n⚠️  Using approximate boundaries")
        logger.info("    For official boundaries, download manually from Open Canada")

    logger.info("\nNext steps:")
    logger.info("  1. Review reserve boundaries on the web map")
    logger.info("  2. Toggle 'First Nations Reserves' layer in the UI")
    logger.info("  3. If using approximate data, replace with official boundaries")


if __name__ == '__main__':
    main()
