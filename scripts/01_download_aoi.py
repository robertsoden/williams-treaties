#!/usr/bin/env python3
"""
Download and create Area of Interest (AOI) for Williams Treaty Territories.

This script creates a boundary representing the Williams Treaty area by:
1. Downloading First Nations boundaries from Statistics Canada
2. Filtering for the seven Williams Treaty First Nations
3. Creating a buffered union to define the study area
4. Saving as GeoJSON for use in other scripts

Usage:
    python scripts/01_download_aoi.py
"""

import sys
from pathlib import Path
import geopandas as gpd
from shapely.ops import unary_union

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts.utils import (
    setup_logging,
    load_config,
    get_project_root,
    ensure_dir,
    save_geojson,
    print_gdf_info
)


def create_aoi_from_coordinates(config):
    """
    Create AOI from approximate coordinates of Williams Treaty area.

    This creates a bounding box around the general Williams Treaty region
    in south-central Ontario as a starting point.
    """
    logger = setup_logging(__name__)
    logger.info("Creating AOI from approximate coordinates...")

    # Approximate bounding box for Williams Treaty Territories
    # Covers area from Lake Simcoe to Peterborough/Kawartha Lakes region
    # Coordinates in WGS84 (EPSG:4326)
    minx, miny = -79.8, 43.8   # Southwest corner
    maxx, maxy = -78.3, 44.8   # Northeast corner

    # Create bounding box
    from shapely.geometry import box
    bbox = box(minx, miny, maxx, maxy)

    # Create GeoDataFrame
    aoi = gpd.GeoDataFrame(
        {
            'name': ['Williams Treaty Territories'],
            'description': ['Approximate area covering Williams Treaty First Nations territories'],
            'source': ['Manual bounding box'],
            'buffer_applied': [False]
        },
        geometry=[bbox],
        crs="EPSG:4326"
    )

    # Reproject to UTM for accurate area calculation
    aoi_utm = aoi.to_crs(config['crs']['utm'])

    logger.info(f"Created AOI with area: {aoi_utm.geometry.area[0] / 1e6:.2f} km²")

    return aoi


def download_first_nations_boundaries(config):
    """
    Download First Nations boundaries from open data sources.

    Note: This is a placeholder for actual data download.
    Statistics Canada's First Nations boundaries can be accessed via:
    - Census boundary files
    - Indigenous Services Canada open data
    """
    logger = setup_logging(__name__)
    logger.info("Attempting to download First Nations boundaries...")

    # Statistics Canada 2021 Census - Indigenous geography
    # URL for actual download (this would need to be implemented with proper API)
    url = "https://www12.statcan.gc.ca/census-recensement/2021/geo/sip-pis/boundary-limites/files-fichiers/lfn000b21a_e.zip"

    logger.warning("Direct download not implemented. Using coordinate-based AOI instead.")
    logger.info("To use actual First Nations boundaries, download from:")
    logger.info("  https://www12.statcan.gc.ca/census-recensement/2021/geo/sip-pis/boundary-limites/index-eng.cfm")

    return None


def create_williams_treaty_aoi(config):
    """
    Create the Williams Treaty AOI.

    Priority:
    1. Try to load/filter actual First Nations boundaries
    2. Fall back to coordinate-based bounding box
    """
    logger = setup_logging(__name__)

    # Try to get First Nations boundaries
    fn_boundaries = download_first_nations_boundaries(config)

    if fn_boundaries is not None:
        # Filter for Williams Treaty First Nations
        williams_fn = config['aoi']['first_nations']
        aoi = fn_boundaries[fn_boundaries['name'].isin(williams_fn)]

        # Apply buffer and create union
        buffer_m = config['aoi']['buffer_meters']
        aoi_utm = aoi.to_crs(config['crs']['utm'])
        aoi_buffered = aoi_utm.buffer(buffer_m)
        aoi_union = gpd.GeoDataFrame(
            geometry=[unary_union(aoi_buffered)],
            crs=config['crs']['utm']
        )
        aoi_final = aoi_union.to_crs(config['crs']['geographic'])
    else:
        # Use coordinate-based approach
        aoi_final = create_aoi_from_coordinates(config)

    return aoi_final


def main():
    """Main execution function."""
    logger = setup_logging(__name__)
    logger.info("Starting AOI creation for Williams Treaty Territories")

    # Load configuration
    config = load_config()

    # Get project paths
    project_root = get_project_root()
    boundaries_dir = ensure_dir(project_root / config['directories']['boundaries'])
    output_path = boundaries_dir / 'williams_treaty_aoi.geojson'

    # Create AOI
    aoi = create_williams_treaty_aoi(config)

    # Print information
    print_gdf_info(aoi, "Williams Treaty AOI")

    # Save as GeoJSON
    save_geojson(aoi, output_path)
    logger.info(f"AOI saved to: {output_path}")

    # Also save in UTM projection for analysis
    output_path_utm = boundaries_dir / 'williams_treaty_aoi_utm.geojson'
    aoi_utm = aoi.to_crs(config['crs']['utm'])
    save_geojson(aoi_utm, output_path_utm)
    logger.info(f"AOI (UTM) saved to: {output_path_utm}")

    # Calculate and display area
    area_km2 = aoi_utm.geometry.area[0] / 1e6
    logger.info(f"Total AOI area: {area_km2:.2f} km²")

    logger.info("AOI creation complete!")
    print("\n" + "="*60)
    print("NEXT STEPS:")
    print("="*60)
    print("1. Review the AOI boundary in data/boundaries/")
    print("2. Run land cover download: python scripts/02_download_landcover.py")
    print("3. Run NDVI processing: python scripts/03_process_ndvi.py")
    print("4. Run fire data download: python scripts/04_download_fire_data.py")


if __name__ == "__main__":
    main()
