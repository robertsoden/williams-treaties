#!/usr/bin/env python3
"""
Clip fuel type raster to Williams Treaty Territories area.

This script takes a Canada-wide or regional fuel type raster and clips it
to the Williams Treaty Territories study area.

Usage:
    python scripts/filters/clip_fuel_types.py <input_file>

Example:
    python scripts/filters/clip_fuel_types.py data/raw/fuel/canada_fuel_types.tif
"""

import sys
import argparse
from pathlib import Path
import geopandas as gpd
import rasterio
from rasterio.mask import mask
from rasterio.warp import calculate_default_transform, reproject, Resampling
import json

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from scripts.utils import (
    setup_logging,
    load_config,
    get_project_root,
    ensure_dir,
    load_aoi
)


def clip_raster(input_path, aoi, output_path, logger):
    """
    Clip raster to AOI boundary.

    Args:
        input_path: Path to input raster
        aoi: GeoDataFrame with AOI boundary
        output_path: Path to output raster
        logger: Logger instance
    """
    logger.info("\nClipping raster to AOI...")

    with rasterio.open(input_path) as src:
        # Get source info
        logger.info(f"  Input CRS:    {src.crs}")
        logger.info(f"  Input shape:  {src.width} x {src.height}")
        logger.info(f"  Input bounds: {src.bounds}")

        # Reproject AOI to match raster CRS if needed
        aoi_reprojected = aoi.to_crs(src.crs)

        # Get geometries for masking
        geoms = [json.loads(aoi_reprojected.to_json())['features'][0]['geometry']]

        # Clip raster
        try:
            out_image, out_transform = mask(src, geoms, crop=True, filled=True, nodata=src.nodata)
            logger.info(f"  ✓ Clipped")
        except Exception as e:
            logger.error(f"  Failed to clip: {str(e)}")
            raise

        # Update metadata
        out_meta = src.meta.copy()
        out_meta.update({
            "driver": "GTiff",
            "height": out_image.shape[1],
            "width": out_image.shape[2],
            "transform": out_transform,
            "compress": "lzw"
        })

        logger.info(f"  Output shape: {out_image.shape[2]} x {out_image.shape[1]}")

        # Save clipped raster
        with rasterio.open(output_path, 'w', **out_meta) as dest:
            dest.write(out_image)

        logger.info(f"  ✓ Saved clipped raster")


def reproject_to_wgs84(input_path, output_path, logger):
    """
    Reproject raster to WGS84 if needed.

    Args:
        input_path: Path to input raster
        output_path: Path to output raster
        logger: Logger instance

    Returns:
        True if reprojection was done
    """
    with rasterio.open(input_path) as src:
        if src.crs == 'EPSG:4326':
            logger.info("  Already in WGS84, skipping reprojection")
            return False

        logger.info(f"\nReprojecting from {src.crs} to EPSG:4326...")

        # Calculate transform and dimensions for WGS84
        transform, width, height = calculate_default_transform(
            src.crs, 'EPSG:4326', src.width, src.height, *src.bounds
        )

        # Update metadata
        kwargs = src.meta.copy()
        kwargs.update({
            'crs': 'EPSG:4326',
            'transform': transform,
            'width': width,
            'height': height,
            'compress': 'lzw'
        })

        # Reproject
        with rasterio.open(output_path, 'w', **kwargs) as dst:
            for i in range(1, src.count + 1):
                reproject(
                    source=rasterio.band(src, i),
                    destination=rasterio.band(dst, i),
                    src_transform=src.transform,
                    src_crs=src.crs,
                    dst_transform=transform,
                    dst_crs='EPSG:4326',
                    resampling=Resampling.nearest  # Use nearest for categorical data
                )

        logger.info(f"  ✓ Reprojected to WGS84")
        logger.info(f"  Output shape: {width} x {height}")

        return True


def get_fuel_type_stats(raster_path, logger):
    """
    Calculate fuel type statistics.

    Args:
        raster_path: Path to fuel type raster
        logger: Logger instance
    """
    logger.info("\nCalculating fuel type statistics...")

    with rasterio.open(raster_path) as src:
        data = src.read(1)

        # Get unique values and counts
        import numpy as np
        unique, counts = np.unique(data[data != src.nodata], return_counts=True)

        # Fuel type names (simplified)
        fuel_names = {
            0: "Non-fuel/Water",
            1: "Coniferous (C-1)",
            2: "Coniferous (C-2)",
            3: "Coniferous (C-3)",
            4: "Coniferous (C-4)",
            5: "Coniferous (C-5)",
            6: "Coniferous (C-6)",
            7: "Coniferous (C-7)",
            11: "Deciduous (D-1)",
            18: "Deciduous (D-2)",
            21: "Mixedwood (M-1)",
            25: "Mixedwood (M-2)",
            31: "Slash (S-1)",
            32: "Slash (S-2)",
            40: "Grass (O-1a)",
            43: "Grass (O-1b)",
            99: "Non-fuel/Water"
        }

        logger.info(f"\n  Total pixels: {len(data.flatten()):,}")
        logger.info(f"  Valid pixels: {len(data[data != src.nodata]):,}")

        logger.info("\n  Fuel type distribution:")
        total_valid = counts.sum()
        for val, count in sorted(zip(unique, counts), key=lambda x: x[1], reverse=True):
            name = fuel_names.get(int(val), f"Type {int(val)}")
            pct = (count / total_valid) * 100
            logger.info(f"    {name:25s}: {count:8,} pixels ({pct:5.1f}%)")


def main():
    """Main execution function."""
    parser = argparse.ArgumentParser(
        description='Clip fuel type raster to Williams Treaty Territories'
    )
    parser.add_argument(
        'input_file',
        type=Path,
        help='Path to input raster (GeoTIFF)'
    )
    parser.add_argument(
        '-o', '--output',
        type=Path,
        help='Output file path (default: data/processed/fuel/fuel_types.tif)'
    )
    parser.add_argument(
        '--skip-stats',
        action='store_true',
        help='Skip fuel type statistics calculation'
    )

    args = parser.parse_args()

    # Setup
    logger = setup_logging('clip_fuel_types')
    config = load_config()
    project_root = get_project_root()

    # Set output path
    if args.output:
        output_path = args.output
    else:
        output_dir = ensure_dir(
            project_root / config['directories']['processed'] / 'fuel'
        )
        output_path = output_dir / 'fuel_types.tif'

    logger.info("=" * 70)
    logger.info("CLIP FUEL TYPE RASTER")
    logger.info("=" * 70)
    logger.info(f"\nInput:  {args.input_file}")
    logger.info(f"Output: {output_path}")

    # Check input file exists
    if not args.input_file.exists():
        logger.error(f"\nInput file not found: {args.input_file}")
        logger.error("\nPlease download the dataset first:")
        logger.error("  https://cwfis.cfs.nrcan.gc.ca/datamart")
        sys.exit(1)

    # Load AOI
    logger.info("\nLoading AOI boundary...")
    try:
        aoi = load_aoi()
        logger.info(f"  ✓ Loaded AOI")
        logger.info(f"  AOI CRS:    {aoi.crs}")
        logger.info(f"  AOI bounds: {aoi.total_bounds}")
    except Exception as e:
        logger.error(f"  Failed to load AOI: {str(e)}")
        logger.error("\nMake sure you have run: python scripts/01_download_aoi.py")
        sys.exit(1)

    # Create temporary file for clipped raster
    temp_path = output_path.parent / f"{output_path.stem}_temp.tif"

    try:
        # Clip to AOI
        clip_raster(args.input_file, aoi, temp_path, logger)

        # Reproject to WGS84
        reprojected = reproject_to_wgs84(temp_path, output_path, logger)

        # If not reprojected, move temp to output
        if not reprojected:
            import shutil
            shutil.move(str(temp_path), str(output_path))
            logger.info("  ✓ Saved final raster")

        # Clean up temp file
        if temp_path.exists():
            temp_path.unlink()

        # Get file info
        logger.info(f"\n{'='*70}")
        logger.info("OUTPUT")
        logger.info(f"{'='*70}")
        logger.info(f"File:  {output_path}")
        logger.info(f"Size:  {output_path.stat().st_size / (1024*1024):.1f} MB")

        with rasterio.open(output_path) as src:
            logger.info(f"CRS:   {src.crs}")
            logger.info(f"Shape: {src.width} x {src.height}")
            logger.info(f"Bounds: ({src.bounds.left:.4f}, {src.bounds.bottom:.4f}, {src.bounds.right:.4f}, {src.bounds.top:.4f})")

        # Calculate statistics
        if not args.skip_stats:
            get_fuel_type_stats(output_path, logger)

        # Summary
        logger.info(f"\n{'='*70}")
        logger.info("COMPLETE")
        logger.info(f"{'='*70}")
        logger.info("\nFuel type raster clipped and ready for web map")
        logger.info("\nNext steps:")
        logger.info("  1. View fuel types on the web map")
        logger.info("  2. Toggle 'Wildland Fuel Classification' layer")
        logger.info("  3. Verify coverage and categories")

    except Exception as e:
        logger.error(f"\nError during processing: {str(e)}")
        # Clean up temp file
        if temp_path.exists():
            temp_path.unlink()
        sys.exit(1)


if __name__ == '__main__':
    main()
