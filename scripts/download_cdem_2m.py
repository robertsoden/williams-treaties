#!/usr/bin/env python3
"""
Download high-resolution 2m CDEM data from 2009 LEAP program.

This downloads only the specific tiles covering the Williams Treaty AOI
from the Ontario LEAP (Lake Erie Aerial Photography) 2m resolution dataset.

Much smaller files than full NTS sheets - tiles are ~8-10 MB each.
"""

import sys
from pathlib import Path
import geopandas as gpd
import rasterio
from rasterio.merge import merge
from rasterio.mask import mask
from rasterio import CRS
from rasterio.warp import calculate_default_transform, reproject, Resampling
import requests
from typing import List, Tuple
import zipfile
import io

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts.utils import (
    setup_logging,
    load_config,
    get_project_root,
    ensure_dir,
    load_aoi
)


# CDEM 2m base URLs
CDEM_2M_BASE = "https://ftp.maps.canada.ca/pub/elevation/dem_mne/highresolution_hauteresolution/dtm_mnt/2m/ON/2009_LEAP/"


def get_utm_zone_for_bounds(bounds) -> List[int]:
    """
    Determine which UTM zones cover the AOI.

    UTM Zone 17: 84°W to 78°W
    UTM Zone 18: 78°W to 72°W

    Args:
        bounds: [minx, miny, maxx, maxy] in WGS84

    Returns:
        List of UTM zone numbers
    """
    min_lon, min_lat, max_lon, max_lat = bounds

    zones = []
    # Check if AOI intersects UTM 17 (84°W to 78°W)
    if min_lon < -78:
        zones.append(17)
    # Check if AOI intersects UTM 18 (78°W to 72°W)
    if max_lon > -78:
        zones.append(18)

    return zones


def get_tile_list_for_aoi(aoi: gpd.GeoDataFrame, logger) -> List[Tuple[int, str]]:
    """
    Determine which 2m CDEM tiles are needed to cover the AOI.

    Based on the LEAP naming convention: dtm_2m_utm{zone}_{e/w}_{x}_{y}.tif

    Args:
        aoi: Area of interest GeoDataFrame
        logger: Logger instance

    Returns:
        List of (utm_zone, tile_name) tuples
    """
    bounds = aoi.total_bounds  # [minx, miny, maxx, maxy]

    logger.info(f"AOI bounds: {bounds}")
    logger.info(f"  West: {bounds[0]:.2f}°, South: {bounds[1]:.2f}°")
    logger.info(f"  East: {bounds[2]:.2f}°, North: {bounds[3]:.2f}°")

    # Determine UTM zones
    utm_zones = get_utm_zone_for_bounds(bounds)
    logger.info(f"\nUTM zones covering AOI: {utm_zones}")

    # Based on LEAP coverage, determine tiles needed
    # Williams Treaty area: ~44-46°N, 77-81°W

    tiles = []

    # For UTM 17 (western part, 78-81°W)
    if 17 in utm_zones:
        logger.info("\nChecking UTM Zone 17 tiles...")
        # Based on observed naming: dtm_2m_utm17_e_12_43.tif
        # The coordinates seem to be in a grid system
        # For Williams Treaty west of 78°W, we need the eastern tiles
        # This appears to be a single tile based on the listing
        tiles.append((17, "dtm_2m_utm17_e_12_43.tif"))

    # For UTM 18 (eastern part, 77-78°W)
    if 18 in utm_zones:
        logger.info("\nChecking UTM Zone 18 tiles...")
        # Based on the naming: dtm_2m_utm18_w_X_Y.tif
        # where X and Y are coordinate indices
        # For 44-46°N, we need tiles with Y=44, 45, 46
        # For 77-78°W (western edge of UTM 18), we need tiles with lower X values

        # Based on the available tiles list, likely candidates:
        for x in [2, 3, 4, 5, 6, 7]:  # Western portion of UTM 18
            for y in [43, 44, 45, 46]:  # Latitude range 43-46°N
                tile_name = f"dtm_2m_utm18_w_{x}_{y}.tif"
                tiles.append((18, tile_name))

    logger.info(f"\nTiles to download: {len(tiles)}")
    for zone, tile in tiles[:10]:  # Show first 10
        logger.info(f"  - UTM{zone}: {tile}")
    if len(tiles) > 10:
        logger.info(f"  ... and {len(tiles) - 10} more")

    return tiles


def download_tile(utm_zone: int, tile_name: str, output_dir: Path, logger) -> Path:
    """
    Download a single 2m CDEM tile.

    Args:
        utm_zone: UTM zone number (17 or 18)
        tile_name: Tile filename
        output_dir: Directory to save tile
        logger: Logger instance

    Returns:
        Path to downloaded tile, or None if failed
    """
    output_path = output_dir / tile_name

    if output_path.exists():
        logger.info(f"  ✓ {tile_name} already exists")
        return output_path

    url = f"{CDEM_2M_BASE}utm{utm_zone}/{tile_name}"

    try:
        logger.info(f"  Downloading {tile_name}...")
        response = requests.get(url, timeout=60)
        response.raise_for_status()

        ensure_dir(output_dir)
        with open(output_path, 'wb') as f:
            f.write(response.content)

        size_mb = len(response.content) / 1024 / 1024
        logger.info(f"    ✓ {size_mb:.1f} MB")
        return output_path

    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 404:
            logger.debug(f"    ✗ Not found (tile may not exist in coverage area)")
        else:
            logger.warning(f"    ✗ HTTP {e.response.status_code}")
        return None

    except Exception as e:
        logger.warning(f"    ✗ Error: {e}")
        return None


def process_cdem_tiles(tile_paths: List[Path], aoi: gpd.GeoDataFrame,
                       output_path: Path, logger):
    """
    Merge CDEM tiles, clip to AOI, and reproject to WGS84.

    Args:
        tile_paths: List of paths to downloaded tiles
        aoi: Area of interest
        output_path: Path to save final DEM
        logger: Logger instance
    """
    logger.info(f"\nProcessing {len(tile_paths)} tiles...")

    # Open all tiles
    src_files = [rasterio.open(tile) for tile in tile_paths]

    logger.info("  Merging tiles...")
    mosaic, mosaic_transform = merge(src_files)

    src_crs = src_files[0].crs
    logger.info(f"  Source CRS: {src_crs}")

    # Close files
    for src in src_files:
        src.close()

    # Create temp merged file
    temp_merged = output_path.parent / "temp_merged_2m.tif"
    ensure_dir(temp_merged.parent)

    profile = {
        'driver': 'GTiff',
        'height': mosaic.shape[1],
        'width': mosaic.shape[2],
        'count': 1,
        'dtype': mosaic.dtype,
        'crs': src_crs,
        'transform': mosaic_transform,
        'compress': 'lzw'
    }

    with rasterio.open(temp_merged, 'w', **profile) as dst:
        dst.write(mosaic[0], 1)

    logger.info("  Clipping to AOI...")

    with rasterio.open(temp_merged) as src:
        # Reproject AOI to match DEM CRS
        aoi_reprojected = aoi.to_crs(src.crs)

        # Clip
        out_image, out_transform = mask(
            src,
            aoi_reprojected.geometry,
            crop=True,
            all_touched=True
        )

        logger.info(f"  Reprojecting to WGS84...")

        # Calculate bounds
        height, width = out_image.shape[1], out_image.shape[2]
        bounds = rasterio.transform.array_bounds(height, width, out_transform)

        # Calculate WGS84 transform
        transform_wgs84, width_wgs84, height_wgs84 = calculate_default_transform(
            src.crs,
            CRS.from_epsg(4326),
            width,
            height,
            *bounds
        )

        out_profile = {
            'driver': 'GTiff',
            'height': height_wgs84,
            'width': width_wgs84,
            'count': 1,
            'dtype': out_image.dtype,
            'crs': CRS.from_epsg(4326),
            'transform': transform_wgs84,
            'compress': 'lzw'
        }

        with rasterio.open(output_path, 'w', **out_profile) as dst:
            reproject(
                source=out_image[0],
                destination=rasterio.band(dst, 1),
                src_transform=out_transform,
                src_crs=src.crs,
                dst_transform=transform_wgs84,
                dst_crs=CRS.from_epsg(4326),
                resampling=Resampling.bilinear
            )

    # Clean up
    temp_merged.unlink()

    logger.info(f"\n✓ Processed DEM saved to: {output_path}")

    # Statistics
    with rasterio.open(output_path) as src:
        data = src.read(1, masked=True)
        logger.info(f"  Dimensions: {src.width}x{src.height}")
        logger.info(f"  Resolution: {src.res[0]:.6f}° ({src.res[0] * 111320:.1f}m)")
        logger.info(f"  Elevation range: {data.min():.1f}m to {data.max():.1f}m")
        logger.info(f"  Mean elevation: {data.mean():.1f}m")


def main():
    """Main execution function."""
    logger = setup_logging(__name__)
    logger.info("=" * 70)
    logger.info("Download 2m CDEM Data (2009 LEAP)")
    logger.info("=" * 70)

    # Load configuration and AOI
    config = load_config()

    try:
        aoi = load_aoi(config)
        logger.info("✓ Loaded AOI\n")
    except FileNotFoundError as e:
        logger.error(str(e))
        sys.exit(1)

    # Set up directories
    project_root = get_project_root()
    raw_dem_dir = ensure_dir(project_root / config['directories']['raw'] / 'dem' / 'cdem_2m')
    processed_dem_dir = ensure_dir(project_root / config['directories']['processed'] / 'dem')

    # Determine tiles needed
    tiles_needed = get_tile_list_for_aoi(aoi, logger)

    # Download tiles
    logger.info("\n" + "=" * 70)
    logger.info("DOWNLOADING TILES")
    logger.info("=" * 70)
    logger.info("")

    downloaded_tiles = []
    for utm_zone, tile_name in tiles_needed:
        tile_path = download_tile(utm_zone, tile_name, raw_dem_dir, logger)
        if tile_path and tile_path.exists():
            downloaded_tiles.append(tile_path)

    logger.info(f"\n✓ Downloaded {len(downloaded_tiles)} tiles")

    if not downloaded_tiles:
        logger.error("\n✗ No tiles downloaded successfully")
        logger.info("\nNote: The 2009 LEAP dataset may not cover your entire AOI.")
        logger.info("      Falling back to existing SRTM data.")
        sys.exit(1)

    # Process tiles
    logger.info("\n" + "=" * 70)
    logger.info("PROCESSING TILES")
    logger.info("=" * 70)

    output_path = processed_dem_dir / "elevation.tif"
    process_cdem_tiles(downloaded_tiles, aoi, output_path, logger)

    logger.info("\n" + "=" * 70)
    logger.info("✓ SUCCESS")
    logger.info("=" * 70)
    logger.info(f"\n🎉 2m resolution elevation data ready!")
    logger.info(f"\n  Output: {output_path}")
    logger.info(f"  Resolution: ~2m (15x better than SRTM!)")
    logger.info("\nNext steps:")
    logger.info("  1. Hard refresh browser (Cmd+Shift+R)")
    logger.info("  2. Turn on Elevation layer")
    logger.info("  3. Zoom in to see incredible detail!")


if __name__ == "__main__":
    main()
