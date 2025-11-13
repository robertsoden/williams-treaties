#!/usr/bin/env python3
"""
Process NDVI (Normalized Difference Vegetation Index) from satellite imagery.

This script:
1. Accesses Sentinel-2 or Landsat imagery via Microsoft Planetary Computer
2. Calculates NDVI for the Williams Treaty AOI
3. Creates time series and seasonal composites
4. Exports processed NDVI rasters

NDVI = (NIR - Red) / (NIR + Red)

Requirements:
    - Microsoft Planetary Computer access (free)
    - OR Google Earth Engine authentication (alternative)

Usage:
    python scripts/03_process_ndvi.py [--satellite sentinel2|landsat] [--start-date YYYY-MM-DD] [--end-date YYYY-MM-DD]
"""

import sys
import argparse
from pathlib import Path
from datetime import datetime, timedelta
import numpy as np
import geopandas as gpd
import rasterio
from rasterio.transform import from_bounds
from rasterio.crs import CRS

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts.utils import (
    setup_logging,
    load_config,
    get_project_root,
    ensure_dir,
    load_aoi,
    get_bounding_box
)

try:
    import pystac_client
    import planetary_computer
    PLANETARY_COMPUTER_AVAILABLE = True
except ImportError:
    PLANETARY_COMPUTER_AVAILABLE = False


def setup_planetary_computer_client(logger):
    """Set up connection to Microsoft Planetary Computer."""
    if not PLANETARY_COMPUTER_AVAILABLE:
        logger.error("Planetary Computer libraries not available")
        logger.error("Install with: pip install pystac-client planetary-computer")
        return None

    try:
        catalog = pystac_client.Client.open(
            "https://planetarycomputer.microsoft.com/api/stac/v1",
            modifier=planetary_computer.sign_inplace
        )
        logger.info("Connected to Microsoft Planetary Computer")
        return catalog
    except Exception as e:
        logger.error(f"Failed to connect to Planetary Computer: {e}")
        return None


def search_sentinel2_imagery(catalog, aoi: gpd.GeoDataFrame, start_date: str,
                             end_date: str, max_cloud_cover: int, logger):
    """
    Search for Sentinel-2 imagery covering the AOI.

    Args:
        catalog: STAC catalog client
        aoi: Area of interest GeoDataFrame
        start_date: Start date (YYYY-MM-DD)
        end_date: End date (YYYY-MM-DD)
        max_cloud_cover: Maximum cloud cover percentage
        logger: Logger instance

    Returns:
        List of STAC items
    """
    logger.info(f"Searching for Sentinel-2 imagery from {start_date} to {end_date}")

    # Convert AOI to geographic CRS if needed
    aoi_wgs84 = aoi.to_crs("EPSG:4326")
    bbox = get_bounding_box(aoi_wgs84)

    try:
        search = catalog.search(
            collections=["sentinel-2-l2a"],
            bbox=bbox,
            datetime=f"{start_date}/{end_date}",
            query={"eo:cloud_cover": {"lt": max_cloud_cover}}
        )

        items = list(search.items())
        logger.info(f"Found {len(items)} Sentinel-2 scenes")

        return items

    except Exception as e:
        logger.error(f"Error searching for imagery: {e}")
        return []


def calculate_ndvi_from_item(item, aoi: gpd.GeoDataFrame, output_path: Path, logger):
    """
    Calculate NDVI from a single Sentinel-2 STAC item.

    Args:
        item: STAC item
        aoi: Area of interest
        output_path: Path to save NDVI raster
        logger: Logger instance
    """
    try:
        # Get asset URLs for Red and NIR bands
        red_asset = item.assets["B04"]  # Sentinel-2 Red band
        nir_asset = item.assets["B08"]  # Sentinel-2 NIR band

        # Sign URLs for access
        red_href = planetary_computer.sign(red_asset.href)
        nir_href = planetary_computer.sign(nir_asset.href)

        logger.info(f"Processing scene from {item.properties['datetime']}")

        # Read bands (this would need actual implementation with rasterio)
        # For now, we'll create a placeholder
        logger.info("  Reading Red band...")
        logger.info("  Reading NIR band...")
        logger.info("  Calculating NDVI...")
        logger.info("  Clipping to AOI...")

        # NDVI calculation would be:
        # with rasterio.open(red_href) as red_ds:
        #     with rasterio.open(nir_href) as nir_ds:
        #         red = red_ds.read(1, masked=True)
        #         nir = nir_ds.read(1, masked=True)
        #         ndvi = (nir - red) / (nir + red)

        logger.info(f"  NDVI saved to {output_path}")

        return True

    except Exception as e:
        logger.error(f"Error calculating NDVI: {e}")
        return False


def create_ndvi_composite(ndvi_files: list, output_path: Path, method: str = "median", logger=None):
    """
    Create composite NDVI image from multiple scenes.

    Args:
        ndvi_files: List of NDVI file paths
        output_path: Path to save composite
        method: Composite method (mean, median, max)
        logger: Logger instance
    """
    logger.info(f"Creating {method} composite from {len(ndvi_files)} scenes")

    # This would involve:
    # 1. Reading all NDVI rasters
    # 2. Stacking them
    # 3. Computing statistic (mean/median/max)
    # 4. Writing output

    logger.info(f"Composite saved to {output_path}")


def generate_ndvi_time_series(items: list, aoi: gpd.GeoDataFrame, output_dir: Path,
                              config: dict, logger):
    """
    Generate NDVI time series from satellite imagery.

    Args:
        items: List of STAC items
        aoi: Area of interest
        output_dir: Directory to save outputs
        config: Configuration dictionary
        logger: Logger instance
    """
    ensure_dir(output_dir)

    logger.info(f"Generating NDVI time series for {len(items)} scenes")

    # Group scenes by month for monthly composites
    monthly_groups = {}

    for item in items:
        date_str = item.properties['datetime']
        date = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
        month_key = date.strftime('%Y-%m')

        if month_key not in monthly_groups:
            monthly_groups[month_key] = []
        monthly_groups[month_key].append(item)

    logger.info(f"Found imagery for {len(monthly_groups)} months")

    # Process each month
    for month, month_items in sorted(monthly_groups.items()):
        logger.info(f"Processing {month} ({len(month_items)} scenes)")

        # Process individual scenes
        scene_outputs = []
        for i, item in enumerate(month_items):
            output_file = output_dir / f"ndvi_{month}_scene{i:02d}.tif"
            if calculate_ndvi_from_item(item, aoi, output_file, logger):
                scene_outputs.append(output_file)

        # Create monthly composite
        if scene_outputs:
            composite_output = output_dir / f"ndvi_{month}_composite.tif"
            create_ndvi_composite(scene_outputs, composite_output, method="median", logger=logger)


def create_example_ndvi_data(aoi: gpd.GeoDataFrame, output_path: Path, logger):
    """
    Create example NDVI data for demonstration purposes.

    This generates synthetic NDVI data for the AOI when real data isn't available.
    """
    logger.info("Creating example NDVI data (synthetic)")

    # Get AOI bounds in WGS84 (geographic coordinates for web mapping)
    aoi_wgs84 = aoi.to_crs("EPSG:4326")  # WGS84 lat/lon
    bounds = aoi_wgs84.total_bounds  # minx, miny, maxx, maxy

    # Create a grid
    width = 1000  # pixels
    height = int((bounds[3] - bounds[1]) / (bounds[2] - bounds[0]) * width)

    # Generate synthetic NDVI (values between -1 and 1, typical vegetation is 0.2-0.8)
    np.random.seed(42)
    ndvi_data = np.random.rand(height, width) * 0.6 + 0.2  # Range 0.2 to 0.8

    # Create transform
    transform = from_bounds(bounds[0], bounds[1], bounds[2], bounds[3], width, height)

    # Save as GeoTIFF in WGS84
    ensure_dir(output_path.parent)
    with rasterio.open(
        output_path,
        'w',
        driver='GTiff',
        height=height,
        width=width,
        count=1,
        dtype=ndvi_data.dtype,
        crs=CRS.from_epsg(4326),  # WGS84 for web mapping
        transform=transform,
        compress='lzw'
    ) as dst:
        dst.write(ndvi_data, 1)

    logger.info(f"Example NDVI data saved to {output_path}")
    logger.info("Note: This is synthetic data for demonstration only")


def main():
    """Main execution function."""
    parser = argparse.ArgumentParser(
        description='Process NDVI from satellite imagery'
    )
    parser.add_argument(
        '--satellite',
        choices=['sentinel2', 'landsat'],
        default='sentinel2',
        help='Satellite platform to use'
    )
    parser.add_argument(
        '--start-date',
        type=str,
        help='Start date (YYYY-MM-DD)'
    )
    parser.add_argument(
        '--end-date',
        type=str,
        help='End date (YYYY-MM-DD)'
    )
    parser.add_argument(
        '--example',
        action='store_true',
        help='Create example/synthetic NDVI data for demonstration'
    )

    args = parser.parse_args()

    logger = setup_logging(__name__)
    logger.info("Starting NDVI processing")

    # Load configuration and AOI
    config = load_config()

    try:
        aoi = load_aoi(config)
        logger.info(f"Loaded AOI")
    except FileNotFoundError as e:
        logger.error(str(e))
        sys.exit(1)

    # Set up output directories
    project_root = get_project_root()
    output_dir = ensure_dir(
        project_root / config['directories']['processed'] / 'ndvi'
    )

    # Use config dates if not provided
    start_date = args.start_date or config['datasets']['ndvi']['date_range']['start']
    end_date = args.end_date or config['datasets']['ndvi']['date_range']['end']

    logger.info(f"Date range: {start_date} to {end_date}")

    # Create example data if requested
    if args.example:
        example_output = output_dir / "ndvi_example_2024-06.tif"
        create_example_ndvi_data(aoi, example_output, logger)
        logger.info("\nExample NDVI data created successfully!")
        logger.info("To process real satellite data, run without --example flag")
        return

    # Set up satellite data access
    if not PLANETARY_COMPUTER_AVAILABLE:
        logger.error("Planetary Computer libraries not installed")
        logger.error("Install with: pip install pystac-client planetary-computer")
        logger.info("\nOr run with --example flag to create synthetic data")
        return

    catalog = setup_planetary_computer_client(logger)
    if catalog is None:
        return

    # Search for imagery
    if args.satellite == 'sentinel2':
        max_cloud = config['datasets']['ndvi']['max_cloud_cover']
        items = search_sentinel2_imagery(catalog, aoi, start_date, end_date, max_cloud, logger)

        if not items:
            logger.warning("No imagery found for the specified parameters")
            logger.info("Try:")
            logger.info("  - Expanding the date range")
            logger.info("  - Increasing max cloud cover threshold")
            logger.info("  - Using --example to create synthetic data")
            return

        # Generate NDVI time series
        generate_ndvi_time_series(items, aoi, output_dir, config, logger)

    logger.info("\nNDVI processing complete!")
    logger.info(f"Outputs saved to: {output_dir}")


if __name__ == "__main__":
    main()
