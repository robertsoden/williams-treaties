#!/usr/bin/env python3
"""
Download Williams Treaty First Nations community and demographic data.

This script downloads data for the 7 Williams Treaty First Nations:
1. Alderville First Nation
2. Curve Lake First Nation
3. Hiawatha First Nation
4. Mississaugas of Scugog Island First Nation
5. Chippewas of Beausoleil First Nation
6. Chippewas of Georgina Island First Nation
7. Chippewas of Rama First Nation

Data includes:
- Reserve boundaries
- Community locations
- Population and demographics (from Statistics Canada)

Usage:
    python scripts/07_download_williams_treaty_communities.py
"""

import sys
import argparse
from pathlib import Path
import geopandas as gpd
import pandas as pd
from shapely.geometry import Point, Polygon
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
    save_geojson
)


# Williams Treaty First Nations
WILLIAMS_TREATY_NATIONS = [
    {
        'name': 'Alderville First Nation',
        'location': [-78.086, 44.051],  # Approximate coordinates
        'population': 1200,  # Approximate - from public sources
        'reserve_name': 'Alderville 35'
    },
    {
        'name': 'Curve Lake First Nation',
        'location': [-78.279, 44.547],
        'population': 2100,
        'reserve_name': 'Curve Lake 35'
    },
    {
        'name': 'Hiawatha First Nation',
        'location': [-78.272, 44.224],
        'population': 700,
        'reserve_name': 'Hiawatha 36'
    },
    {
        'name': 'Mississaugas of Scugog Island First Nation',
        'location': [-78.968, 44.171],
        'population': 300,
        'reserve_name': 'Scugog Island 34'
    },
    {
        'name': 'Chippewas of Beausoleil First Nation',
        'location': [-79.833, 44.780],
        'population': 1800,
        'reserve_name': 'Chimnissing 1'
    },
    {
        'name': 'Chippewas of Georgina Island First Nation',
        'location': [-79.333, 44.450],
        'population': 900,
        'reserve_name': 'Georgina Island 33'
    },
    {
        'name': 'Chippewas of Rama First Nation',
        'location': [-79.315, 44.620],
        'population': 2000,
        'reserve_name': 'Rama 32'
    }
]


def download_first_nations_reserves(output_path: Path, logger):
    """
    Download First Nations reserve boundaries from Indigenous Services Canada.

    The official source is:
    https://open.canada.ca/data/en/dataset/522b07b9-78e2-4819-b736-ad9208eb1067

    Args:
        output_path: Path to save reserve boundaries
        logger: Logger instance
    """
    logger.info("Downloading First Nations reserve boundaries")

    # ISC Open Data - First Nations Reserves
    isc_url = "https://geo.statcan.gc.ca/geoserver/census-recensement/wfs"

    try:
        # WFS GetFeature request for reserves
        params = {
            'service': 'WFS',
            'version': '2.0.0',
            'request': 'GetFeature',
            'typeName': 'census-recensement:lir_000a21a_e',  # Indigenous reserves layer
            'outputFormat': 'application/json',
            'srsName': 'EPSG:4326'
        }

        logger.info("  Requesting reserve data from Statistics Canada...")
        response = requests.get(isc_url, params=params, timeout=60)

        if response.status_code == 200:
            gdf = gpd.read_file(io.StringIO(response.text))

            # Filter for Williams Treaty reserves only
            reserve_names = [nation['reserve_name'] for nation in WILLIAMS_TREATY_NATIONS]
            filtered = gdf[gdf['IRNAME'].isin(reserve_names)]

            if not filtered.empty:
                filtered = filtered.set_crs("EPSG:4326")
                save_geojson(filtered, output_path)
                logger.info(f"\n✓ Downloaded {len(filtered)} reserve boundaries")
                logger.info(f"  Saved to: {output_path}")
                return filtered
            else:
                logger.warning("  No reserves found matching Williams Treaty nations")

    except Exception as e:
        logger.warning(f"  WFS request failed: {str(e)}")

    logger.info("\nNote: Reserve boundaries may require manual download from:")
    logger.info("  https://open.canada.ca/data/en/dataset/522b07b9-78e2-4819-b736-ad9208eb1067")
    logger.info("  Search for each reserve by name")

    # Create placeholder with approximate boundaries
    logger.info("\nCreating community locations from known coordinates...")
    return None


def create_community_locations(output_path: Path, logger):
    """
    Create point locations for Williams Treaty First Nations communities.

    Args:
        output_path: Path to save community locations
        logger: Logger instance
    """
    logger.info("Creating Williams Treaty First Nations community locations")

    # Create GeoDataFrame from community data
    features = []
    for nation in WILLIAMS_TREATY_NATIONS:
        features.append({
            'geometry': Point(nation['location']),
            'name': nation['name'],
            'reserve_name': nation['reserve_name'],
            'population': nation['population'],
            'type': 'First Nation Community',
            'treaty': 'Williams Treaty (1923)'
        })

    gdf = gpd.GeoDataFrame(features, crs="EPSG:4326")
    save_geojson(gdf, output_path)

    logger.info(f"\n✓ Created {len(gdf)} community locations")
    logger.info(f"  Saved to: {output_path}")

    # Print summary
    logger.info("\nWilliams Treaty First Nations:")
    total_pop = 0
    for _, row in gdf.iterrows():
        logger.info(f"  - {row['name']}: ~{row['population']:,} people")
        total_pop += row['population']
    logger.info(f"\n  Total population: ~{total_pop:,}")

    return gdf


def get_demographics_info(logger):
    """
    Get information about accessing detailed demographics from Statistics Canada.

    Args:
        logger: Logger instance
    """
    logger.info("\nStatistics Canada Indigenous Demographics")
    logger.info("=" * 70)

    logger.info("\nData available from Census 2021:")
    logger.info("  - Population by age and sex")
    logger.info("  - Indigenous identity")
    logger.info("  - Language spoken at home")
    logger.info("  - Housing and dwelling characteristics")
    logger.info("  - Income and employment")
    logger.info("  - Education levels")

    logger.info("\nAccess methods:")
    logger.info("  1. Census Profile: https://www12.statcan.gc.ca/census-recensement/2021/dp-pd/prof/")
    logger.info("  2. Aboriginal Population Profile: https://www12.statcan.gc.ca/census-recensement/2021/dp-pd/abpopprof/")
    logger.info("  3. Data Download: https://www12.statcan.gc.ca/census-recensement/2021/dp-pd/dt-td/")

    logger.info("\nSearch by reserve name or First Nation name to get detailed demographics")

    demographics_info = {
        "source": "Statistics Canada - Census 2021",
        "url": "https://www12.statcan.gc.ca/census-recensement/2021/",
        "communities": WILLIAMS_TREATY_NATIONS,
        "data_types": [
            "Population and demographics",
            "Indigenous identity",
            "Language",
            "Housing",
            "Income and employment",
            "Education"
        ],
        "note": "Detailed demographics require manual lookup for each community"
    }

    return demographics_info


def create_demographics_summary(communities_gdf: gpd.GeoDataFrame, output_path: Path, logger):
    """
    Create a summary demographics file with basic population data.

    Args:
        communities_gdf: GeoDataFrame with community locations
        output_path: Path to save demographics summary
        logger: Logger instance
    """
    logger.info("\nCreating demographics summary")

    # Create demographics summary
    demographics = []
    for _, community in communities_gdf.iterrows():
        demographics.append({
            'name': community['name'],
            'population': community['population'],
            'population_source': 'Approximate from public sources',
            'census_year': '2021 (approximate)',
            'reserve': community['reserve_name'],
            'treaty': community['treaty']
        })

    df = pd.DataFrame(demographics)

    # Save as JSON
    ensure_dir(output_path.parent)
    with open(output_path, 'w') as f:
        json.dump(demographics, f, indent=2)

    logger.info(f"  Saved to: {output_path}")

    return df


def main():
    """Main execution function."""
    parser = argparse.ArgumentParser(
        description='Download Williams Treaty First Nations community and demographic data'
    )

    args = parser.parse_args()

    logger = setup_logging(__name__)
    logger.info("=" * 70)
    logger.info("Williams Treaty First Nations - Community Data Download")
    logger.info("=" * 70)

    # Load configuration
    config = load_config()
    project_root = get_project_root()

    # Set up output directories
    boundaries_dir = ensure_dir(project_root / config['directories']['boundaries'])
    processed_dir = ensure_dir(project_root / config['directories']['processed'] / 'communities')

    # Download/create datasets
    logger.info("\n" + "=" * 70)
    logger.info("1. FIRST NATIONS RESERVE BOUNDARIES")
    logger.info("=" * 70)
    reserves_path = boundaries_dir / "williams_treaty_reserves.geojson"
    reserves = download_first_nations_reserves(reserves_path, logger)

    logger.info("\n" + "=" * 70)
    logger.info("2. COMMUNITY LOCATIONS")
    logger.info("=" * 70)
    communities_path = processed_dir / "williams_treaty_communities.geojson"
    communities = create_community_locations(communities_path, logger)

    logger.info("\n" + "=" * 70)
    logger.info("3. DEMOGRAPHICS INFORMATION")
    logger.info("=" * 70)
    demographics_info = get_demographics_info(logger)

    # Save demographics info
    demographics_info_path = processed_dir / "demographics_info.json"
    with open(demographics_info_path, 'w') as f:
        json.dump(demographics_info, f, indent=2)
    logger.info(f"\n  Demographics info saved to: {demographics_info_path}")

    # Create demographics summary
    demographics_summary_path = processed_dir / "demographics_summary.json"
    create_demographics_summary(communities, demographics_summary_path, logger)

    logger.info("\n" + "=" * 70)
    logger.info("DOWNLOAD COMPLETE")
    logger.info("=" * 70)
    logger.info("\nData saved to:")
    logger.info(f"  Community locations: {communities_path}")
    logger.info(f"  Demographics summary: {demographics_summary_path}")
    logger.info(f"  Demographics info: {demographics_info_path}")

    if reserves:
        logger.info(f"  Reserve boundaries: {reserves_path}")

    logger.info("\nNext steps:")
    logger.info("  1. Review community locations on the web map")
    logger.info("  2. Visit Statistics Canada for detailed demographics")
    logger.info("  3. Add community layer to map visualization")


if __name__ == "__main__":
    try:
        import io
    except ImportError:
        print("Error: io module required")
        sys.exit(1)

    main()
