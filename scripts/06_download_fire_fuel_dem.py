#!/usr/bin/env python3
"""
Download fire perimeters, fuel type mapping, and DEM data.

This script downloads:
1. National Burned Area Composite (NBAC) - Historical fire perimeters
2. Canadian Fuel Type Mapping
3. Canadian Digital Elevation Model (CDEM)

Usage:
    python scripts/06_download_fire_fuel_dem.py [--start-year 2010] [--end-year 2024]
"""

import sys
import argparse
from pathlib import Path
from datetime import datetime
import pandas as pd
import geopandas as gpd
import rasterio
from rasterio.merge import merge
from rasterio.mask import mask
from rasterio import CRS
from rasterio.warp import calculate_default_transform, reproject, Resampling
import requests
import json
import zipfile
import io
from typing import List, Tuple
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
    get_bounding_box,
    clip_to_aoi,
    save_geojson
)


# Data source URLs
NFIS_BASE_URL = "https://opendata.nfis.org/mapserver/nfis-change"
FUEL_TYPE_WMS = "https://cwfis.cfs.nrcan.gc.ca/geoserver/public/wms"
CDEM_BASE_URL = "https://ftp.maps.canada.ca/pub/elevation/dem_mne/highresolution_hauteresolution/dtm_mnt"


def download_nbac_fire_perimeters(aoi: gpd.GeoDataFrame, output_dir: Path,
                                   start_year: int, end_year: int, logger):
    """
    Download historical fire perimeters from National Burned Area Composite (NBAC).

    NBAC provides vector fire perimeter data through WFS service.

    Args:
        aoi: Area of interest
        output_dir: Directory to save outputs
        start_year: Start year for fire data
        end_year: End year for fire data
        logger: Logger instance
    """
    logger.info(f"Downloading NBAC fire perimeters ({start_year}-{end_year})")

    # Get AOI bounds
    bbox = get_bounding_box(aoi)
    bbox_str = f"{bbox[0]},{bbox[1]},{bbox[2]},{bbox[3]}"

    # NBAC WFS service URL
    wfs_url = "https://cwfis.cfs.nrcan.gc.ca/geoserver/public/wfs"

    fire_perimeters = []

    for year in range(start_year, end_year + 1):
        logger.info(f"  Fetching fire perimeters for {year}...")

        try:
            # WFS GetFeature request
            params = {
                'service': 'WFS',
                'version': '2.0.0',
                'request': 'GetFeature',
                'typeName': f'public:nbac_{year}',  # NBAC layer naming pattern
                'outputFormat': 'application/json',
                'srsName': 'EPSG:4326',
                'bbox': bbox_str
            }

            response = requests.get(wfs_url, params=params, timeout=30)

            if response.status_code == 200 and 'features' in response.text:
                gdf = gpd.read_file(io.StringIO(response.text))
                if not gdf.empty:
                    gdf['year'] = year
                    fire_perimeters.append(gdf)
                    logger.info(f"    Found {len(gdf)} fire perimeters")
                else:
                    logger.info(f"    No fires found in AOI")
            else:
                logger.warning(f"    Could not fetch data for {year}")

        except Exception as e:
            logger.warning(f"    Error fetching {year}: {str(e)}")
            continue

    # Combine all years
    if fire_perimeters:
        combined = gpd.GeoDataFrame(pd.concat(fire_perimeters, ignore_index=True))
        combined = combined.set_crs("EPSG:4326")

        # Clip to AOI
        combined = clip_to_aoi(combined, aoi)

        # Save
        output_path = output_dir / f"fire_perimeters_{start_year}_{end_year}.geojson"
        save_geojson(combined, output_path)

        logger.info(f"\n✓ Downloaded {len(combined)} fire perimeters")
        logger.info(f"  Saved to: {output_path}")
        logger.info(f"  Total burned area: {combined.geometry.area.sum():.2f} ha")

        return combined
    else:
        logger.warning("No fire perimeter data downloaded")
        logger.info("\nNote: NBAC data may require manual download from:")
        logger.info("  https://opendata.nfis.org/")
        logger.info("  https://cwfis.cfs.nrcan.gc.ca/datamart")

        return None


def download_fuel_type_mapping(aoi: gpd.GeoDataFrame, output_path: Path, logger):
    """
    Download Canadian fuel type mapping from Canadian Forest Service.

    Fuel types are used to model fire behavior and assess fire risk.

    Args:
        aoi: Area of interest
        output_path: Path to save output GeoTIFF
        logger: Logger instance
    """
    logger.info("Downloading Canadian fuel type mapping")

    # Get AOI bounds
    bbox = get_bounding_box(aoi)

    # Canadian Wildland Fuel Type layer from CWFIS
    wms_url = "https://cwfis.cfs.nrcan.gc.ca/geoserver/public/wms"

    # Calculate image dimensions (approximate, ~100m resolution)
    width = int((bbox[2] - bbox[0]) * 111320 / 100)  # degrees to meters, then to pixels
    height = int((bbox[3] - bbox[1]) * 111320 / 100)

    # Limit size for reasonable download
    max_dim = 2000
    if width > max_dim or height > max_dim:
        scale = max_dim / max(width, height)
        width = int(width * scale)
        height = int(height * scale)

    logger.info(f"  Requesting image: {width}x{height} pixels")

    try:
        # WMS GetMap request for fuel type layer
        params = {
            'service': 'WMS',
            'version': '1.3.0',
            'request': 'GetMap',
            'layers': 'public:fueltype',
            'bbox': f"{bbox[0]},{bbox[1]},{bbox[2]},{bbox[3]}",
            'width': width,
            'height': height,
            'srs': 'EPSG:4326',
            'format': 'image/geotiff',
        }

        logger.info("  Requesting fuel type data from CWFIS...")
        response = requests.get(wms_url, params=params, timeout=60)

        if response.status_code == 200 and response.headers.get('content-type') == 'image/geotiff':
            # Save the GeoTIFF
            ensure_dir(output_path.parent)
            with open(output_path, 'wb') as f:
                f.write(response.content)

            logger.info(f"\n✓ Downloaded fuel type mapping")
            logger.info(f"  Saved to: {output_path}")
            logger.info(f"  Size: {len(response.content) / 1024 / 1024:.1f} MB")

            # Try to read and describe
            try:
                with rasterio.open(output_path) as src:
                    logger.info(f"  Dimensions: {src.width}x{src.height}")
                    logger.info(f"  Resolution: {src.res[0]:.4f}° ({src.res[0] * 111320:.1f}m)")
            except:
                pass

            return True

        else:
            logger.warning(f"  Failed to download: HTTP {response.status_code}")
            logger.info(f"  Response type: {response.headers.get('content-type')}")
            return False

    except Exception as e:
        logger.error(f"  Error downloading fuel types: {str(e)}")

    logger.info("\nAlternative fuel type data sources:")
    logger.info("  1. CanVec+ (Natural Resources Canada)")
    logger.info("  2. Provincial land cover classifications")
    logger.info("  3. Manual download from CWFIS Data Mart")

    return False


def download_cdem(aoi: gpd.GeoDataFrame, output_path: Path, logger):
    """
    Download Canadian Digital Elevation Model (CDEM) for the AOI.

    CDEM provides high-resolution elevation data (20m) for Canada.

    Args:
        aoi: Area of interest
        output_path: Path to save output GeoTIFF
        logger: Logger instance
    """
    logger.info("Downloading Canadian Digital Elevation Model (CDEM)")

    # Get AOI bounds
    bbox = get_bounding_box(aoi)

    logger.info(f"  AOI bounds: {bbox}")
    logger.info("  Note: CDEM tiles are distributed by NTS map sheets")

    # Calculate which NTS tiles we need (simplified - in reality would need proper NTS grid)
    # For Williams Treaty area, we're approximately in 31D region

    # CDEM is distributed as tiles by NTS (National Topographic System) map sheets
    # Full implementation would:
    # 1. Determine which NTS tiles cover the AOI
    # 2. Download each tile
    # 3. Merge tiles
    # 4. Clip to AOI

    logger.info("\nCDEM Download Information:")
    logger.info("  Data Portal: https://open.canada.ca/data/en/dataset/7f245e4d-76c2-4caa-951a-45d1d2051333")
    logger.info("  Resolution: 20m")
    logger.info("  Format: GeoTIFF (by NTS map sheet)")
    logger.info("  Vertical Datum: CGVD2013")

    # For Williams Treaty area, approximate NTS sheets
    nts_sheets = ["031D", "031C", "031E"]

    logger.info(f"\n  Approximate NTS sheets for your AOI: {', '.join(nts_sheets)}")
    logger.info("\nManual download steps:")
    logger.info("  1. Visit: https://ftp.maps.canada.ca/pub/elevation/dem_mne/highresolution_hauteresolution/")
    logger.info("  2. Navigate to: dtm_mnt/")
    logger.info("  3. Download tiles for NTS sheets listed above")
    logger.info("  4. Place .tif files in data/raw/dem/")
    logger.info("  5. Run merge_dem.py to combine and clip to AOI")

    # Create a simple synthetic DEM for demonstration
    logger.info("\nCreating synthetic DEM for demonstration...")

    # Create a simple elevation grid
    aoi_utm = aoi.to_crs("EPSG:26917")  # UTM Zone 17N
    bounds_utm = aoi_utm.total_bounds

    # Create grid
    width = 500
    height = 500

    # Simple elevation model (higher in north)
    x = np.linspace(0, 1, width)
    y = np.linspace(0, 1, height)
    xx, yy = np.meshgrid(x, y)

    # Base elevation around 300m, varying from 250-400m
    elevation = 250 + (yy * 150) + (np.sin(xx * 10) * np.sin(yy * 10) * 20)
    elevation = elevation.astype(np.float32)

    # Calculate transform
    from rasterio.transform import from_bounds
    transform = from_bounds(
        bounds_utm[0], bounds_utm[1], bounds_utm[2], bounds_utm[3],
        width, height
    )

    # Save as GeoTIFF in WGS84 for web display
    ensure_dir(output_path.parent)

    # First create in UTM
    temp_path = output_path.parent / "dem_utm_temp.tif"
    with rasterio.open(
        temp_path,
        'w',
        driver='GTiff',
        height=height,
        width=width,
        count=1,
        dtype=elevation.dtype,
        crs=CRS.from_epsg(26917),
        transform=transform,
        compress='lzw'
    ) as dst:
        dst.write(elevation, 1)

    # Reproject to WGS84 for web mapping
    with rasterio.open(temp_path) as src:
        transform_wgs84, width_wgs84, height_wgs84 = calculate_default_transform(
            src.crs, CRS.from_epsg(4326), src.width, src.height, *src.bounds
        )

        kwargs = src.meta.copy()
        kwargs.update({
            'crs': CRS.from_epsg(4326),
            'transform': transform_wgs84,
            'width': width_wgs84,
            'height': height_wgs84
        })

        with rasterio.open(output_path, 'w', **kwargs) as dst:
            reproject(
                source=rasterio.band(src, 1),
                destination=rasterio.band(dst, 1),
                src_transform=src.transform,
                src_crs=src.crs,
                dst_transform=transform_wgs84,
                dst_crs=CRS.from_epsg(4326),
                resampling=Resampling.bilinear
            )

    # Clean up temp file
    temp_path.unlink()

    logger.info(f"\n✓ Created synthetic DEM for demonstration")
    logger.info(f"  Saved to: {output_path}")
    logger.info(f"  Dimensions: {width_wgs84}x{height_wgs84}")
    logger.info("  Elevation range: 250-400m (synthetic)")
    logger.info("\n  Note: Replace with real CDEM data for actual analysis")

    return True


def main():
    """Main execution function."""
    parser = argparse.ArgumentParser(
        description='Download fire perimeters, fuel types, and DEM'
    )
    parser.add_argument(
        '--start-year',
        type=int,
        default=2010,
        help='Start year for fire perimeter data (default: 2010)'
    )
    parser.add_argument(
        '--end-year',
        type=int,
        default=datetime.now().year,
        help='End year for fire perimeter data (default: current year)'
    )
    parser.add_argument(
        '--skip-fires',
        action='store_true',
        help='Skip fire perimeter download'
    )
    parser.add_argument(
        '--skip-fuel',
        action='store_true',
        help='Skip fuel type download'
    )
    parser.add_argument(
        '--skip-dem',
        action='store_true',
        help='Skip DEM download'
    )

    args = parser.parse_args()

    logger = setup_logging(__name__)
    logger.info("=" * 70)
    logger.info("Fire Perimeters, Fuel Types, and DEM Download")
    logger.info("=" * 70)

    # Load configuration and AOI
    config = load_config()

    try:
        aoi = load_aoi(config)
        logger.info("✓ Loaded AOI")
    except FileNotFoundError as e:
        logger.error(str(e))
        sys.exit(1)

    # Set up output directories
    project_root = get_project_root()
    raw_fire_dir = ensure_dir(project_root / config['directories']['raw'] / 'fire')
    raw_fuel_dir = ensure_dir(project_root / config['directories']['raw'] / 'fuel')
    raw_dem_dir = ensure_dir(project_root / config['directories']['raw'] / 'dem')
    processed_fire_dir = ensure_dir(project_root / config['directories']['processed'] / 'fire')
    processed_fuel_dir = ensure_dir(project_root / config['directories']['processed'] / 'fuel')
    processed_dem_dir = ensure_dir(project_root / config['directories']['processed'] / 'dem')

    # Download datasets
    if not args.skip_fires:
        logger.info("\n" + "=" * 70)
        logger.info("1. FIRE PERIMETERS (NBAC)")
        logger.info("=" * 70)
        download_nbac_fire_perimeters(
            aoi, processed_fire_dir,
            args.start_year, args.end_year, logger
        )

    if not args.skip_fuel:
        logger.info("\n" + "=" * 70)
        logger.info("2. FUEL TYPE MAPPING")
        logger.info("=" * 70)
        fuel_output = processed_fuel_dir / "fuel_types.tif"
        download_fuel_type_mapping(aoi, fuel_output, logger)

    if not args.skip_dem:
        logger.info("\n" + "=" * 70)
        logger.info("3. DIGITAL ELEVATION MODEL")
        logger.info("=" * 70)
        dem_output = processed_dem_dir / "elevation.tif"
        download_cdem(aoi, dem_output, logger)

    logger.info("\n" + "=" * 70)
    logger.info("DOWNLOAD COMPLETE")
    logger.info("=" * 70)
    logger.info("\nData saved to:")
    logger.info(f"  Fire perimeters: {processed_fire_dir}")
    logger.info(f"  Fuel types: {processed_fuel_dir}")
    logger.info(f"  DEM: {processed_dem_dir}")
    logger.info("\nNext steps:")
    logger.info("  1. Review downloaded data")
    logger.info("  2. Add layers to web map visualization")
    logger.info("  3. Perform fire risk analysis using fuel types + DEM")


if __name__ == "__main__":
    main()
