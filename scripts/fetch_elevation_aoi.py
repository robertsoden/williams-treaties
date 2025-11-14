#!/usr/bin/env python3
"""
Fetch elevation data directly for the AOI using OpenTopography API.

This downloads only the elevation data needed for the Williams Treaty area,
avoiding the need to download massive CDEM tiles.

Uses OpenTopography's Global DEM API with SRTM data (30m resolution).
"""

import sys
from pathlib import Path
import geopandas as gpd
import rasterio
from rasterio import CRS
from rasterio.warp import calculate_default_transform, reproject, Resampling
import requests
import time

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts.utils import (
    setup_logging,
    load_config,
    get_project_root,
    ensure_dir,
    load_aoi
)


def fetch_elevation_for_aoi(aoi: gpd.GeoDataFrame, output_path: Path, logger):
    """
    Fetch elevation data for AOI using OpenTopography API.

    Args:
        aoi: Area of interest GeoDataFrame
        output_path: Path to save elevation GeoTIFF
        logger: Logger instance
    """
    bounds = aoi.total_bounds  # [minx, miny, maxx, maxy]

    logger.info(f"AOI bounds: {bounds}")
    logger.info(f"  West: {bounds[0]:.4f}°")
    logger.info(f"  South: {bounds[1]:.4f}°")
    logger.info(f"  East: {bounds[2]:.4f}°")
    logger.info(f"  North: {bounds[3]:.4f}°")

    # Calculate approximate area
    width_deg = bounds[2] - bounds[0]
    height_deg = bounds[3] - bounds[1]
    area_km2 = (width_deg * 111) * (height_deg * 111)
    logger.info(f"  Approximate area: {area_km2:.0f} km²")

    logger.info("\nFetching elevation data from OpenTopography...")
    logger.info("  Dataset: SRTM GL1 (Global 30m resolution)")
    logger.info("  This may take 1-2 minutes...")

    # OpenTopography Global DEM API
    url = "https://portal.opentopography.org/API/globaldem"

    params = {
        'demtype': 'SRTMGL1',  # SRTM 30m resolution
        'south': bounds[1],
        'north': bounds[3],
        'west': bounds[0],
        'east': bounds[2],
        'outputFormat': 'GTiff',
        'API_Key': 'demoapikeyot2022'  # Public demo API key
    }

    try:
        logger.info("\n  Sending request to OpenTopography...")
        start_time = time.time()

        response = requests.get(url, params=params, timeout=300)
        response.raise_for_status()

        elapsed = time.time() - start_time
        size_mb = len(response.content) / 1024 / 1024

        logger.info(f"  ✓ Downloaded {size_mb:.1f} MB in {elapsed:.1f} seconds")

        # Save the raw downloaded file
        ensure_dir(output_path.parent)
        temp_path = output_path.parent / "temp_elevation_raw.tif"

        with open(temp_path, 'wb') as f:
            f.write(response.content)

        logger.info(f"\n  Processing elevation data...")

        # Read and verify the data
        with rasterio.open(temp_path) as src:
            logger.info(f"  Downloaded DEM info:")
            logger.info(f"    CRS: {src.crs}")
            logger.info(f"    Dimensions: {src.width}x{src.height}")
            logger.info(f"    Resolution: {src.res[0]:.6f}° ({src.res[0] * 111320:.1f}m)")

            # Check if already in WGS84
            if src.crs == CRS.from_epsg(4326):
                logger.info(f"  Already in WGS84, copying to output...")

                # Just copy the file
                with rasterio.open(output_path, 'w', **src.meta) as dst:
                    dst.write(src.read(1), 1)

            else:
                logger.info(f"  Reprojecting to WGS84...")

                # Reproject to WGS84
                transform, width, height = calculate_default_transform(
                    src.crs, CRS.from_epsg(4326),
                    src.width, src.height,
                    *src.bounds
                )

                kwargs = src.meta.copy()
                kwargs.update({
                    'crs': CRS.from_epsg(4326),
                    'transform': transform,
                    'width': width,
                    'height': height
                })

                with rasterio.open(output_path, 'w', **kwargs) as dst:
                    reproject(
                        source=rasterio.band(src, 1),
                        destination=rasterio.band(dst, 1),
                        src_transform=src.transform,
                        src_crs=src.crs,
                        dst_transform=transform,
                        dst_crs=CRS.from_epsg(4326),
                        resampling=Resampling.bilinear
                    )

        # Clean up temp file
        temp_path.unlink()

        # Report final statistics
        with rasterio.open(output_path) as src:
            data = src.read(1, masked=True)

            logger.info(f"\n✓ Elevation data saved to: {output_path}")
            logger.info(f"  Final dimensions: {src.width}x{src.height}")
            logger.info(f"  Resolution: {src.res[0]:.6f}° ({src.res[0] * 111320:.1f}m)")
            logger.info(f"  Elevation range: {data.min():.1f}m to {data.max():.1f}m")
            logger.info(f"  Mean elevation: {data.mean():.1f}m")
            logger.info(f"  File size: {output_path.stat().st_size / 1024 / 1024:.1f} MB")

        return True

    except requests.exceptions.HTTPError as e:
        logger.error(f"\n✗ HTTP Error: {e}")
        logger.error(f"  Response status: {response.status_code}")

        if response.status_code == 400:
            logger.error("\n  Possible causes:")
            logger.error("    - AOI is too large (try smaller area)")
            logger.error("    - Invalid coordinates")
        elif response.status_code == 401 or response.status_code == 403:
            logger.error("\n  API key issue. You may need to:")
            logger.error("    1. Register at https://opentopography.org/")
            logger.error("    2. Get your own API key")
            logger.error("    3. Update this script with your key")

        return False

    except requests.exceptions.Timeout:
        logger.error("\n✗ Request timed out (> 5 minutes)")
        logger.error("  The AOI may be too large. Try:")
        logger.error("    1. Downloading tiles manually")
        logger.error("    2. Processing a smaller area first")
        return False

    except Exception as e:
        logger.error(f"\n✗ Error fetching elevation data: {e}")
        logger.error(f"  Error type: {type(e).__name__}")
        return False


def main():
    """Main execution function."""
    logger = setup_logging(__name__)
    logger.info("=" * 70)
    logger.info("Fetch Elevation Data for AOI")
    logger.info("=" * 70)

    # Load configuration and AOI
    config = load_config()

    try:
        aoi = load_aoi(config)
        logger.info("✓ Loaded AOI\n")
    except FileNotFoundError as e:
        logger.error(str(e))
        sys.exit(1)

    # Set up output directory
    project_root = get_project_root()
    processed_dem_dir = ensure_dir(project_root / config['directories']['processed'] / 'dem')
    output_path = processed_dem_dir / "elevation.tif"

    # Fetch elevation data
    logger.info("=" * 70)
    logger.info("FETCHING ELEVATION DATA")
    logger.info("=" * 70)
    logger.info("")

    success = fetch_elevation_for_aoi(aoi, output_path, logger)

    if success:
        logger.info("\n" + "=" * 70)
        logger.info("✓ SUCCESS")
        logger.info("=" * 70)
        logger.info("\n🎉 Real elevation data is ready!")
        logger.info(f"\n  Output: {output_path}")
        logger.info("\nNext steps:")
        logger.info("  1. Hard refresh your browser:")
        logger.info("     • Chrome/Firefox: Cmd+Shift+R (Mac) or Ctrl+Shift+R (Windows)")
        logger.info("     • Safari: Cmd+Option+R")
        logger.info("  2. Turn on the Elevation layer")
        logger.info("  3. The elevation should now match real terrain!")
        logger.info("\n  ✓ Water bodies should appear low")
        logger.info("  ✓ Highlands should appear high")
        logger.info("  ✓ Layer should align with satellite imagery")
    else:
        logger.info("\n" + "=" * 70)
        logger.info("✗ FAILED")
        logger.info("=" * 70)
        logger.info("\nTroubleshooting:")
        logger.info("  1. Check your internet connection")
        logger.info("  2. The OpenTopography service may be down - try later")
        logger.info("  3. Alternative: Download CDEM tiles manually")
        logger.info("     Run: python scripts/download_real_cdem.py")
        sys.exit(1)


if __name__ == "__main__":
    main()
