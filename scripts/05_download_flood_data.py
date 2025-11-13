#!/usr/bin/env python3
"""
Download flood hazard data for Williams Treaty Territories.

This script downloads:
1. Ontario flood plain mapping
2. Conservation Authority flood data
3. Digital Elevation Model (DEM)
4. Hydrological network data
5. Climate and precipitation data

Usage:
    python scripts/05_download_flood_data.py [--include-dem] [--include-climate]
"""

import sys
import argparse
from pathlib import Path
import geopandas as gpd
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
    save_geojson
)


# Data source URLs
ONTARIO_GEOHUB_URL = "https://geohub.lio.gov.on.ca"
CDEM_URL = "https://ftp.maps.canada.ca/pub/elevation/dem_mne/highresolution_hauteresolution"


def download_ontario_floodplain_data(aoi: gpd.GeoDataFrame, output_dir: Path, logger):
    """
    Download Ontario flood plain mapping data.

    Args:
        aoi: Area of interest
        output_dir: Directory to save outputs
        logger: Logger instance
    """
    logger.info("Ontario Flood Plain Mapping")

    # Ontario flood plain data is distributed through GeoHub
    bbox = get_bounding_box(aoi)

    floodplain_info = {
        "source": "Ontario Ministry of Natural Resources and Forestry",
        "portal": ONTARIO_GEOHUB_URL,
        "datasets": {
            "flood_plain_regulation_limit": {
                "name": "Flood Plain Regulation Limit",
                "description": "Regulatory flood lines (100-year flood)",
                "layer_name": "FLOOD_PLAIN_REGULATION_LIMIT"
            },
            "flood_vulnerable_clusters": {
                "name": "Flood Vulnerable Clusters",
                "description": "Areas vulnerable to flooding",
                "layer_name": "FLOOD_VULNERABLE_CLUSTER"
            }
        },
        "aoi_bbox": {
            "minx": bbox[0],
            "miny": bbox[1],
            "maxx": bbox[2],
            "maxy": bbox[3]
        },
        "access_method": "WFS or manual download from Ontario GeoHub",
        "download_instructions": [
            "1. Visit https://geohub.lio.gov.on.ca/",
            "2. Search for 'flood plain' or 'flood vulnerable'",
            "3. Filter by AOI bounding box",
            "4. Download as shapefile or GeoJSON"
        ]
    }

    info_file = output_dir / "ontario_floodplain_info.json"
    with open(info_file, 'w') as f:
        json.dump(floodplain_info, f, indent=2)

    logger.info(f"Ontario flood plain data info saved to {info_file}")
    logger.info("\nKey datasets:")
    for key, dataset in floodplain_info['datasets'].items():
        logger.info(f"  - {dataset['name']}")


def get_conservation_authority_info(logger):
    """
    Get information about relevant Conservation Authorities.

    Returns dict with CA contact information and data availability.
    """
    logger.info("Relevant Conservation Authorities for Williams Treaty area")

    conservation_authorities = {
        "Kawartha_Conservation": {
            "name": "Kawartha Conservation",
            "website": "https://www.kawarthaconservation.com/",
            "jurisdiction": "Kawartha Lakes watershed",
            "data_types": [
                "Watershed boundaries",
                "Flood mapping",
                "Watercourse data",
                "Wetland inventory"
            ]
        },
        "ORCA": {
            "name": "Otonabee Region Conservation Authority",
            "website": "https://www.otonabee.com/",
            "jurisdiction": "Otonabee watershed, Peterborough area",
            "data_types": [
                "Flood risk mapping",
                "Watershed plans",
                "Stream network"
            ]
        },
        "LSRCA": {
            "name": "Lake Simcoe Region Conservation Authority",
            "website": "https://www.lsrca.on.ca/",
            "jurisdiction": "Lake Simcoe watershed",
            "data_types": [
                "Shoreline flood mapping",
                "Watershed characterization",
                "Subwatershed boundaries"
            ]
        },
        "CLOCA": {
            "name": "Central Lake Ontario Conservation Authority",
            "website": "https://www.cloca.com/",
            "jurisdiction": "Durham Region watersheds",
            "data_types": [
                "Flood plain mapping",
                "Coastal flooding",
                "Watershed plans"
            ]
        },
        "GRCA": {
            "name": "Ganaraska Region Conservation Authority",
            "website": "https://www.grca.on.ca/",
            "jurisdiction": "Ganaraska watershed, Northumberland County",
            "data_types": [
                "Flood risk assessment",
                "Watershed boundaries",
                "Stream data"
            ]
        }
    }

    return conservation_authorities


def download_conservation_authority_data(aoi: gpd.GeoDataFrame, output_dir: Path, logger):
    """
    Download/document Conservation Authority flood data.

    Args:
        aoi: Area of interest
        output_dir: Directory to save outputs
        logger: Logger instance
    """
    logger.info("Conservation Authority Flood Data")

    ca_info = get_conservation_authority_info(logger)

    # Save CA information
    info_file = output_dir / "conservation_authorities_info.json"
    with open(info_file, 'w') as f:
        json.dump(ca_info, f, indent=2)

    logger.info(f"\nConservation Authority info saved to {info_file}")
    logger.info("\nContact these authorities for flood mapping data:")
    for ca_key, ca_data in ca_info.items():
        logger.info(f"  - {ca_data['name']}")
        logger.info(f"    Website: {ca_data['website']}")


def download_dem_data(aoi: gpd.GeoDataFrame, output_dir: Path, logger):
    """
    Download Canadian Digital Elevation Model (CDEM) data.

    Args:
        aoi: Area of interest
        output_dir: Directory to save outputs
        logger: Logger instance
    """
    logger.info("Canadian Digital Elevation Model (CDEM)")

    bbox = get_bounding_box(aoi)

    dem_info = {
        "name": "Canadian Digital Elevation Model (CDEM)",
        "source": "Natural Resources Canada",
        "resolution": "20m (best available for Ontario)",
        "url": CDEM_URL,
        "format": "GeoTIFF",
        "vertical_datum": "CGVD2013 (Canadian Geodetic Vertical Datum)",
        "horizontal_datum": "NAD83",
        "aoi_bbox": {
            "minx": bbox[0],
            "miny": bbox[1],
            "maxx": bbox[2],
            "maxy": bbox[3]
        },
        "download_instructions": [
            "1. Visit https://open.canada.ca/data/en/dataset/7f245e4d-76c2-4caa-951a-45d1d2051333",
            "2. Download CDEM tiles covering the AOI",
            "3. Tiles are organized by NTS (National Topographic System) map sheets",
            "4. Mosaic tiles and clip to AOI"
        ],
        "use_cases": [
            "Slope analysis for flood modeling",
            "Flow accumulation",
            "Watershed delineation",
            "Elevation-based risk assessment"
        ]
    }

    info_file = output_dir / "dem_info.json"
    with open(info_file, 'w') as f:
        json.dump(dem_info, f, indent=2)

    logger.info(f"DEM data info saved to {info_file}")
    logger.info(f"\nResolution: {dem_info['resolution']}")
    logger.info("Note: DEM files are large. Download only tiles covering your AOI.")


def download_hydrological_network(aoi: gpd.GeoDataFrame, output_dir: Path, logger):
    """
    Download hydrological network data (streams, rivers, lakes).

    Args:
        aoi: Area of interest
        output_dir: Directory to save outputs
        logger: Logger instance
    """
    logger.info("Hydrological Network Data")

    hydro_info = {
        "ontario_hydro_network": {
            "name": "Ontario Hydro Network (OHN)",
            "source": "Ontario Ministry of Natural Resources",
            "portal": ONTARIO_GEOHUB_URL,
            "components": {
                "watercourse": "Streams and rivers",
                "waterbody": "Lakes and ponds",
                "wetland": "Wetland areas"
            },
            "layer_names": [
                "OHN_WATERCOURSE",
                "OHN_WATERBODY",
                "WETLAND"
            ]
        },
        "provincial_stream_network": {
            "name": "Provincial (Stream) Network (PSN)",
            "source": "Ontario Ministry of Natural Resources",
            "description": "Detailed stream network for watershed analysis"
        },
        "national_hydro_network": {
            "name": "National Hydro Network (NHN)",
            "source": "Natural Resources Canada",
            "url": "https://open.canada.ca/data/en/dataset/a4b190fe-e090-4e6d-881e-b87956c07977",
            "format": "Shapefile, GeoPackage",
            "description": "Canada-wide hydrographic network"
        }
    }

    info_file = output_dir / "hydrological_network_info.json"
    with open(info_file, 'w') as f:
        json.dump(hydro_info, f, indent=2)

    logger.info(f"Hydrological network info saved to {info_file}")
    logger.info("\nKey datasets:")
    for key, dataset in hydro_info.items():
        logger.info(f"  - {dataset['name']}")


def download_precipitation_data(aoi: gpd.GeoDataFrame, output_dir: Path, logger):
    """
    Download precipitation and climate data.

    Args:
        aoi: Area of interest
        output_dir: Directory to save outputs
        logger: Logger instance
    """
    logger.info("Precipitation and Climate Data")

    bbox = get_bounding_box(aoi)

    climate_info = {
        "environment_canada": {
            "name": "Environment and Climate Change Canada",
            "url": "https://climate.weather.gc.ca/",
            "data_types": [
                "Historical climate data",
                "Climate normals (1981-2010, 1991-2020)",
                "Daily precipitation",
                "Extreme weather events"
            ],
            "access": "Web interface or API"
        },
        "climate_projections": {
            "name": "ClimateData.ca",
            "url": "https://climatedata.ca/",
            "description": "Downscaled climate projections for Canada",
            "variables": [
                "Temperature (mean, max, min)",
                "Precipitation (total, rain, snow)",
                "Drought indices",
                "Extreme precipitation events"
            ],
            "scenarios": ["RCP 2.6", "RCP 4.5", "RCP 8.5"]
        },
        "climate_atlas": {
            "name": "Climate Atlas of Canada",
            "url": "https://climateatlas.ca/",
            "description": "Interactive climate data and projections",
            "use_case": "Future flood risk assessment"
        }
    }

    info_file = output_dir / "precipitation_climate_info.json"
    with open(info_file, 'w') as f:
        json.dump(climate_info, f, indent=2)

    logger.info(f"Climate data info saved to {info_file}")
    logger.info("\nData sources:")
    for key, source in climate_info.items():
        logger.info(f"  - {source['name']}: {source['url']}")


def main():
    """Main execution function."""
    parser = argparse.ArgumentParser(
        description='Download flood hazard data for Williams Treaty Territories'
    )
    parser.add_argument(
        '--include-dem',
        action='store_true',
        help='Include DEM data information'
    )
    parser.add_argument(
        '--include-climate',
        action='store_true',
        help='Include climate/precipitation data information'
    )
    parser.add_argument(
        '--all',
        action='store_true',
        help='Include all datasets'
    )

    args = parser.parse_args()

    logger = setup_logging(__name__)
    logger.info("Starting flood hazard data download")

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
    raw_dir = ensure_dir(project_root / config['directories']['raw'] / 'flood')
    processed_dir = ensure_dir(project_root / config['directories']['processed'] / 'flood')

    # Download/document various flood datasets
    logger.info("\n" + "="*60)
    logger.info("1. ONTARIO FLOOD PLAIN MAPPING")
    logger.info("="*60)
    download_ontario_floodplain_data(aoi, raw_dir, logger)

    logger.info("\n" + "="*60)
    logger.info("2. CONSERVATION AUTHORITY DATA")
    logger.info("="*60)
    download_conservation_authority_data(aoi, raw_dir, logger)

    logger.info("\n" + "="*60)
    logger.info("3. HYDROLOGICAL NETWORK")
    logger.info("="*60)
    download_hydrological_network(aoi, raw_dir, logger)

    if args.include_dem or args.all:
        logger.info("\n" + "="*60)
        logger.info("4. DIGITAL ELEVATION MODEL")
        logger.info("="*60)
        download_dem_data(aoi, raw_dir, logger)

    if args.include_climate or args.all:
        logger.info("\n" + "="*60)
        logger.info("5. PRECIPITATION AND CLIMATE DATA")
        logger.info("="*60)
        download_precipitation_data(aoi, raw_dir, logger)

    logger.info("\n" + "="*60)
    logger.info("FLOOD DATA DOWNLOAD SUMMARY")
    logger.info("="*60)
    logger.info("\nFlood hazard assessment requires multiple data layers:")
    logger.info("  ✓ Regulatory flood plains (100-year flood lines)")
    logger.info("  ✓ Conservation Authority mapping")
    logger.info("  ✓ Hydrological network (streams, rivers, lakes)")
    if args.include_dem or args.all:
        logger.info("  ✓ Digital Elevation Model (for modeling)")
    if args.include_climate or args.all:
        logger.info("  ✓ Climate and precipitation data")

    logger.info("\nData access information saved to:")
    logger.info(f"  {raw_dir}")

    logger.info("\nNext steps:")
    logger.info("  1. Review JSON files with download instructions")
    logger.info("  2. Download datasets from Ontario GeoHub and other sources")
    logger.info("  3. Contact Conservation Authorities for detailed flood mapping")
    logger.info("  4. Place downloaded files in raw/flood directory")
    logger.info("  5. Run processing scripts to clip and analyze data")


if __name__ == "__main__":
    main()
