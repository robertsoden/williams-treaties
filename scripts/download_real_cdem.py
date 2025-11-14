#!/usr/bin/env python3
"""
Download and process real Canadian Digital Elevation Model (CDEM) data.

This script:
1. Downloads CDEM tiles from Natural Resources Canada
2. Merges tiles covering the AOI
3. Clips to the Williams Treaty area
4. Reprojects to WGS84 for web mapping

CDEM provides 20m resolution elevation data for Canada.
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
from typing import List
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


# CDEM FTP base URL
CDEM_FTP_BASE = "https://ftp.maps.canada.ca/pub/elevation/dem_mne/highresolution_hauteresolution/dtm_mnt/"


def get_nts_tiles_for_aoi(aoi: gpd.GeoDataFrame, logger) -> List[str]:
    """
    Determine which NTS map sheet tiles cover the AOI.

    For the Williams Treaty area, we need approximately:
    - 031D (covers Peterborough/Kawartha Lakes area)
    - 031C (covers part of Lake Ontario shoreline)
    - 031E (covers Haliburton/Algonquin area)

    Args:
        aoi: Area of interest GeoDataFrame
        logger: Logger instance

    Returns:
        List of NTS tile identifiers
    """
    bounds = aoi.total_bounds  # [minx, miny, maxx, maxy]

    logger.info(f"AOI bounds: {bounds}")
    logger.info("  West: {:.2f}°, South: {:.2f}°".format(bounds[0], bounds[1]))
    logger.info("  East: {:.2f}°, North: {:.2f}°".format(bounds[2], bounds[3]))

    # For Williams Treaty area (approx 44-46°N, 77-81°W)
    # These NTS sheets cover the region
    nts_tiles = ["031D", "031C", "031E"]

    logger.info(f"\nNTS map sheets covering AOI: {', '.join(nts_tiles)}")
    logger.info("\nNote: CDEM tiles are organized by NTS 1:50,000 map sheets")
    logger.info("      Each NTS tile may be ~20-30 GB when uncompressed")

    return nts_tiles


def download_cdem_tile(nts_code: str, output_dir: Path, logger) -> Path:
    """
    Download a CDEM tile from Natural Resources Canada FTP.

    Args:
        nts_code: NTS map sheet code (e.g., "031D")
        output_dir: Directory to save downloaded tile
        logger: Logger instance

    Returns:
        Path to downloaded tile
    """
    logger.info(f"\nDownloading CDEM tile: {nts_code}")

    # CDEM tiles are organized as:
    # /dtm_mnt/{nts_code}/{nts_subcode}/
    # e.g., /dtm_mnt/031/031d/031d01/cdem_031d01_...tif

    # For simplicity, we'll try the direct tile approach
    # In reality, NTS sheets are subdivided into 1:50k sheets

    tile_url = f"{CDEM_FTP_BASE}{nts_code[:3]}/{nts_code.lower()}/"

    logger.info(f"  Checking: {tile_url}")
    logger.info("\n  NOTE: CDEM tiles are large (10-30 GB per NTS sheet)")
    logger.info("        Manual download recommended for production use")
    logger.info("\n  Manual download steps:")
    logger.info(f"  1. Visit: {tile_url}")
    logger.info("  2. Download subdirectory tiles (e.g., 031d01, 031d02, etc.)")
    logger.info("  3. Place .tif files in: {output_dir}")

    # For automated download, we'd need to:
    # 1. List the FTP directory to find subdirectories
    # 2. Download each subdirectory tile
    # 3. Extract if zipped
    # This is complex and large, so better done manually

    raise NotImplementedError(
        f"Automatic download of CDEM tiles not implemented due to file size.\n"
        f"Please manually download tiles from: {tile_url}\n"
        f"Place .tif files in: {output_dir}"
    )


def find_downloaded_tiles(tile_dir: Path, logger) -> List[Path]:
    """
    Find all CDEM GeoTIFF tiles in the download directory.

    Args:
        tile_dir: Directory containing downloaded tiles
        logger: Logger instance

    Returns:
        List of paths to GeoTIFF files
    """
    tiles = list(tile_dir.glob("*.tif")) + list(tile_dir.glob("*.tiff"))

    logger.info(f"\nFound {len(tiles)} GeoTIFF files in {tile_dir}")
    for tile in tiles:
        logger.info(f"  - {tile.name}")

    return tiles


def merge_and_clip_tiles(tile_paths: List[Path], aoi: gpd.GeoDataFrame,
                         output_path: Path, logger):
    """
    Merge multiple CDEM tiles and clip to AOI.

    Args:
        tile_paths: List of paths to GeoTIFF tiles
        aoi: Area of interest to clip to
        output_path: Path to save clipped DEM
        logger: Logger instance
    """
    logger.info(f"\nMerging {len(tile_paths)} tiles and clipping to AOI...")

    if not tile_paths:
        raise ValueError("No tiles to merge")

    # Open all tiles
    src_files = [rasterio.open(tile) for tile in tile_paths]

    logger.info("  Merging tiles...")
    # Merge tiles
    mosaic, mosaic_transform = merge(src_files)

    # Get metadata from first tile
    profile = src_files[0].profile.copy()
    profile.update({
        'height': mosaic.shape[1],
        'width': mosaic.shape[2],
        'transform': mosaic_transform
    })

    # Close source files
    for src in src_files:
        src.close()

    logger.info("  Clipping to AOI...")

    # Create temporary merged file
    temp_merged = output_path.parent / "temp_merged.tif"
    ensure_dir(temp_merged.parent)

    with rasterio.open(temp_merged, 'w', **profile) as dst:
        dst.write(mosaic)

    # Clip to AOI
    with rasterio.open(temp_merged) as src:
        # Reproject AOI to same CRS as DEM
        aoi_reprojected = aoi.to_crs(src.crs)

        # Clip
        out_image, out_transform = mask(
            src,
            aoi_reprojected.geometry,
            crop=True,
            all_touched=True
        )

        out_meta = src.meta.copy()
        out_meta.update({
            'height': out_image.shape[1],
            'width': out_image.shape[2],
            'transform': out_transform
        })

        # Check if we need to reproject to WGS84
        if src.crs != CRS.from_epsg(4326):
            logger.info(f"  Reprojecting from {src.crs} to EPSG:4326 (WGS84)...")

            # Calculate transform for WGS84
            transform_wgs84, width_wgs84, height_wgs84 = calculate_default_transform(
                src.crs,
                CRS.from_epsg(4326),
                out_image.shape[2],
                out_image.shape[1],
                *rasterio.transform.array_bounds(
                    out_image.shape[1],
                    out_image.shape[2],
                    out_transform
                )
            )

            # Create output in WGS84
            out_meta.update({
                'crs': CRS.from_epsg(4326),
                'transform': transform_wgs84,
                'width': width_wgs84,
                'height': height_wgs84
            })

            with rasterio.open(output_path, 'w', **out_meta) as dst:
                reproject(
                    source=out_image[0],
                    destination=rasterio.band(dst, 1),
                    src_transform=out_transform,
                    src_crs=src.crs,
                    dst_transform=transform_wgs84,
                    dst_crs=CRS.from_epsg(4326),
                    resampling=Resampling.bilinear
                )
        else:
            # Already in WGS84, just write
            with rasterio.open(output_path, 'w', **out_meta) as dst:
                dst.write(out_image)

    # Clean up temp file
    temp_merged.unlink()

    logger.info(f"✓ Clipped DEM saved to: {output_path}")

    # Report statistics
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
    logger.info("Canadian Digital Elevation Model (CDEM) Download")
    logger.info("=" * 70)

    # Load configuration and AOI
    config = load_config()

    try:
        aoi = load_aoi(config)
        logger.info("✓ Loaded AOI")
    except FileNotFoundError as e:
        logger.error(str(e))
        sys.exit(1)

    # Set up directories
    project_root = get_project_root()
    raw_dem_dir = ensure_dir(project_root / config['directories']['raw'] / 'dem')
    processed_dem_dir = ensure_dir(project_root / config['directories']['processed'] / 'dem')

    # Get NTS tiles needed
    nts_tiles = get_nts_tiles_for_aoi(aoi, logger)

    logger.info("\n" + "=" * 70)
    logger.info("DOWNLOADING TILES")
    logger.info("=" * 70)
    logger.info("\n⚠️  CDEM tiles are very large (10-30 GB per NTS sheet)")
    logger.info("⚠️  Automatic download not implemented due to file size")
    logger.info("\nPlease manually download CDEM tiles:")
    logger.info("\n1. Visit the CDEM portal:")
    logger.info("   https://ftp.maps.canada.ca/pub/elevation/dem_mne/highresolution_hauteresolution/dtm_mnt/")
    logger.info("\n2. Navigate to each NTS sheet directory:")
    for nts in nts_tiles:
        logger.info(f"   - {nts[:3]}/{nts.lower()}/  (download all subdirectory tiles)")
    logger.info(f"\n3. Place all .tif files in: {raw_dem_dir}")
    logger.info("\n4. Re-run this script to merge and process the tiles")

    # Check if tiles already downloaded
    downloaded_tiles = find_downloaded_tiles(raw_dem_dir, logger)

    if not downloaded_tiles:
        logger.info("\n" + "=" * 70)
        logger.info("No tiles found. Please download tiles first.")
        logger.info("=" * 70)
        sys.exit(0)

    # Process downloaded tiles
    logger.info("\n" + "=" * 70)
    logger.info("PROCESSING TILES")
    logger.info("=" * 70)

    output_path = processed_dem_dir / "elevation.tif"
    merge_and_clip_tiles(downloaded_tiles, aoi, output_path, logger)

    logger.info("\n" + "=" * 70)
    logger.info("COMPLETE")
    logger.info("=" * 70)
    logger.info(f"\n✓ Real CDEM elevation data ready for use")
    logger.info(f"  Output: {output_path}")
    logger.info("\nNext steps:")
    logger.info("  1. Refresh your web browser to see real elevation data")
    logger.info("  2. Elevation should now align with water bodies and terrain")


if __name__ == "__main__":
    main()
