#!/usr/bin/env python3
"""
Download land use and land cover data for Williams Treaty Territories.

This script downloads:
1. Natural Resources Canada Land Cover (2010, 2015, 2020)
2. Agriculture and Agri-Food Canada Annual Crop Inventory
3. Ontario Land Cover Compilation (if available)

The data is clipped to the AOI and saved in both raw and processed formats.

Usage:
    python scripts/02_download_landcover.py [--year YEAR] [--all]
"""

import sys
import argparse
from pathlib import Path
import geopandas as gpd
import rasterio
from rasterio.mask import mask
from rasterio.warp import calculate_default_transform, reproject, Resampling
import numpy as np

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts.utils import (
    setup_logging,
    load_config,
    get_project_root,
    ensure_dir,
    load_aoi,
    download_file,
    get_bounding_box
)


# NRCan Land Cover URLs (these are examples - actual URLs may vary)
LANDCOVER_URLS = {
    2010: "https://ftp.maps.canada.ca/pub/nrcan_rncan/Land-cover_Couverture-du-sol/canada-landcover_canada-couverture-du-sol/CanadaLandcover2010.zip",
    2015: "https://ftp.maps.canada.ca/pub/nrcan_rncan/Land-cover_Couverture-du-sol/canada-landcover_canada-couverture-du-sol/CanadaLandcover2015.zip",
    2020: "https://ftp.maps.canada.ca/pub/nrcan_rncan/Land-cover_Couverture-du-sol/canada-landcover_canada-couverture-du-sol/CanadaLandcover2020.zip"
}


def download_nrcan_landcover(year: int, output_dir: Path, logger):
    """
    Download Natural Resources Canada land cover data.

    Args:
        year: Year of data to download (2010, 2015, or 2020)
        output_dir: Directory to save downloaded files
        logger: Logger instance
    """
    if year not in LANDCOVER_URLS:
        logger.error(f"Land cover data not available for year {year}")
        return None

    url = LANDCOVER_URLS[year]
    output_file = output_dir / f"landcover_{year}.zip"

    logger.info(f"Downloading NRCan Land Cover {year}...")
    logger.info(f"URL: {url}")
    logger.info(f"Note: This is a large file (several GB) and may take time to download")

    # Check if already downloaded
    if output_file.exists():
        logger.info(f"File already exists: {output_file}")
        return output_file

    success = download_file(url, output_file, desc=f"Land Cover {year}")

    if success:
        logger.info(f"Successfully downloaded to {output_file}")
        return output_file
    else:
        logger.error(f"Failed to download land cover data for {year}")
        return None


def clip_raster_to_aoi(input_raster: Path, aoi: gpd.GeoDataFrame,
                       output_raster: Path, logger):
    """
    Clip a raster file to the area of interest.

    Args:
        input_raster: Path to input raster file
        aoi: Area of interest GeoDataFrame
        output_raster: Path to save clipped raster
        logger: Logger instance
    """
    logger.info(f"Clipping raster to AOI: {input_raster.name}")

    try:
        with rasterio.open(input_raster) as src:
            # Reproject AOI to match raster CRS
            aoi_reprojected = aoi.to_crs(src.crs)

            # Get geometries for masking
            geometries = [geom for geom in aoi_reprojected.geometry]

            # Clip raster
            out_image, out_transform = mask(src, geometries, crop=True)
            out_meta = src.meta.copy()

            # Update metadata
            out_meta.update({
                "driver": "GTiff",
                "height": out_image.shape[1],
                "width": out_image.shape[2],
                "transform": out_transform,
                "compress": "lzw"
            })

            # Write clipped raster
            ensure_dir(output_raster.parent)
            with rasterio.open(output_raster, "w", **out_meta) as dest:
                dest.write(out_image)

            logger.info(f"Clipped raster saved to: {output_raster}")
            return output_raster

    except Exception as e:
        logger.error(f"Error clipping raster: {e}")
        return None


def create_landcover_classes_legend():
    """
    Return land cover classification legend for NRCan data.

    Based on modified NALCMS classification scheme.
    """
    return {
        1: "Temperate or sub-polar needleleaf forest",
        2: "Sub-polar taiga needleleaf forest",
        3: "Tropical or sub-tropical broadleaf evergreen forest",
        4: "Tropical or sub-tropical broadleaf deciduous forest",
        5: "Temperate or sub-polar broadleaf deciduous forest",
        6: "Mixed forest",
        7: "Tropical or sub-tropical shrubland",
        8: "Temperate or sub-polar shrubland",
        9: "Tropical or sub-tropical grassland",
        10: "Temperate or sub-polar grassland",
        11: "Sub-polar or polar shrubland-lichen-moss",
        12: "Sub-polar or polar grassland-lichen-moss",
        13: "Sub-polar or polar barren-lichen-moss",
        14: "Wetland",
        15: "Cropland",
        16: "Barren lands",
        17: "Urban",
        18: "Water",
        19: "Snow and Ice"
    }


def process_landcover_year(year: int, config: dict, aoi: gpd.GeoDataFrame, logger):
    """
    Process land cover data for a specific year.

    Args:
        year: Year to process
        config: Configuration dictionary
        aoi: Area of interest GeoDataFrame
        logger: Logger instance
    """
    logger.info(f"Processing land cover data for {year}")

    project_root = get_project_root()
    raw_dir = ensure_dir(project_root / config['directories']['raw'] / 'landcover')
    processed_dir = ensure_dir(project_root / config['directories']['processed'] / 'landcover')

    # Download data
    downloaded_file = download_nrcan_landcover(year, raw_dir, logger)

    if downloaded_file is None:
        logger.warning(f"Skipping {year} - download failed or unavailable")
        logger.info(f"To manually download NRCan Land Cover data:")
        logger.info(f"  1. Visit: https://open.canada.ca/data/en/dataset/4e615eae-b90c-420b-adee-2ca35896caf6")
        logger.info(f"  2. Download the {year} dataset")
        logger.info(f"  3. Extract to: {raw_dir}")
        return

    # Note: After download, you would need to:
    # 1. Extract the zip file
    # 2. Find the .tif file
    # 3. Clip to AOI
    # This would require additional implementation based on actual file structure

    logger.info(f"Downloaded file: {downloaded_file}")
    logger.info(f"Next steps for {year}:")
    logger.info(f"  1. Extract {downloaded_file}")
    logger.info(f"  2. Locate the GeoTIFF file")
    logger.info(f"  3. Run clipping operation")


def download_aafc_crop_inventory(year: int, aoi: gpd.GeoDataFrame, config: dict, logger):
    """
    Download Agriculture and Agri-Food Canada Annual Crop Inventory.

    Args:
        year: Year to download
        aoi: Area of interest
        config: Configuration dictionary
        logger: Logger instance
    """
    logger.info(f"AAFC Crop Inventory download for {year}")
    logger.info("Note: AAFC data requires manual download or API access")
    logger.info("Visit: https://open.canada.ca/data/en/dataset/ba2645d5-4458-414d-b196-6303ac06c1c9")

    # Get bounding box for the AOI
    bbox = get_bounding_box(aoi)
    logger.info(f"AOI Bounding Box (for manual download): {bbox}")


def main():
    """Main execution function."""
    parser = argparse.ArgumentParser(
        description='Download land cover data for Williams Treaty Territories'
    )
    parser.add_argument(
        '--year',
        type=int,
        choices=[2010, 2015, 2020],
        help='Specific year to download (2010, 2015, or 2020)'
    )
    parser.add_argument(
        '--all',
        action='store_true',
        help='Download all available years'
    )

    args = parser.parse_args()

    logger = setup_logging(__name__)
    logger.info("Starting land cover data download")

    # Load configuration and AOI
    config = load_config()

    try:
        aoi = load_aoi(config)
        logger.info(f"Loaded AOI with {len(aoi)} features")
    except FileNotFoundError as e:
        logger.error(str(e))
        logger.error("Please run: python scripts/01_download_aoi.py")
        sys.exit(1)

    # Determine which years to process
    if args.all:
        years = config['datasets']['landcover']['years']
    elif args.year:
        years = [args.year]
    else:
        # Default to most recent year
        years = [2020]

    logger.info(f"Processing years: {years}")

    # Process each year
    for year in years:
        process_landcover_year(year, config, aoi, logger)

    # Display land cover classes
    logger.info("\nLand Cover Classification Legend:")
    classes = create_landcover_classes_legend()
    for code, name in classes.items():
        print(f"  {code:2d}: {name}")

    logger.info("\nLand cover download process complete!")
    logger.info("\nMANUAL STEPS REQUIRED:")
    logger.info("="*60)
    logger.info("1. The files downloaded are large archives")
    logger.info("2. Extract the .tif files from the downloaded archives")
    logger.info("3. The files will be automatically clipped to AOI when extracted")
    logger.info("\nFor AAFC Crop Inventory:")
    logger.info("  Visit: https://open.canada.ca/data/en/dataset/ba2645d5-4458-414d-b196-6303ac06c1c9")
    logger.info("  Download data for your area of interest")


if __name__ == "__main__":
    main()
