#!/usr/bin/env python3
"""
Create demo fire perimeter and fuel type data for testing.

This script generates synthetic data when real data is unavailable.
"""

import sys
from pathlib import Path
import geopandas as gpd
import pandas as pd
from shapely.geometry import Point, Polygon
import numpy as np
import rasterio
from rasterio.transform import from_bounds
from rasterio import CRS

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


def create_demo_fire_perimeters(aoi: gpd.GeoDataFrame, output_path: Path, logger):
    """
    Create demo fire perimeter data for testing.

    Args:
        aoi: Area of interest
        output_path: Path to save fire perimeters
        logger: Logger instance
    """
    logger.info("Creating demo fire perimeter data")

    # Get AOI bounds
    bounds = aoi.total_bounds  # [minx, miny, maxx, maxy]

    # Create 5 random fire perimeters within the AOI
    fires = []
    years = [2015, 2017, 2019, 2021, 2023]

    np.random.seed(42)  # For reproducibility

    for i, year in enumerate(years):
        # Random center point within AOI
        center_x = np.random.uniform(bounds[0], bounds[2])
        center_y = np.random.uniform(bounds[1], bounds[3])

        # Random radius (500-2000 meters in degrees, approximately)
        radius = np.random.uniform(0.005, 0.02)

        # Create roughly circular polygon with some irregularity
        num_points = 20
        angles = np.linspace(0, 2 * np.pi, num_points)

        # Add randomness to radius for irregular shape
        radii = radius * (1 + np.random.uniform(-0.3, 0.3, num_points))

        x = center_x + radii * np.cos(angles)
        y = center_y + radii * np.sin(angles)

        coords = list(zip(x, y))
        polygon = Polygon(coords)

        # Calculate approximate area in hectares
        area_ha = polygon.area * 111320 * 111320 / 10000

        fires.append({
            'geometry': polygon,
            'year': year,
            'YEAR': year,
            'FIRE_ID': f'DEMO_{year}_{i:03d}',
            'area': area_ha,
            'description': f'Demo fire perimeter from {year}'
        })

    # Create GeoDataFrame
    gdf = gpd.GeoDataFrame(fires, crs="EPSG:4326")

    # Save
    ensure_dir(output_path.parent)
    save_geojson(gdf, output_path)

    logger.info(f"✓ Created {len(gdf)} demo fire perimeters")
    logger.info(f"  Saved to: {output_path}")
    logger.info(f"  Years: {', '.join(map(str, years))}")
    logger.info(f"  Total area: {gdf['area'].sum():.2f} ha")

    return gdf


def create_demo_fuel_types(aoi: gpd.GeoDataFrame, output_path: Path, logger):
    """
    Create demo fuel type raster for testing.

    Args:
        aoi: Area of interest
        output_path: Path to save fuel type raster
        logger: Logger instance
    """
    logger.info("Creating demo fuel type raster")

    # Get AOI bounds
    bounds = aoi.total_bounds

    # Create raster dimensions
    width = 800
    height = 600

    # Create synthetic fuel type data
    # Canadian FBP fuel types: C (coniferous), D (deciduous), M (mixed), S (slash), O (open)
    np.random.seed(42)

    # Create base pattern
    fuel_types = np.zeros((height, width), dtype=np.uint8)

    # Add patches of different fuel types
    for i in range(height):
        for j in range(width):
            # Create zones based on position
            x_factor = j / width
            y_factor = i / height

            rand = np.random.random()

            # North: More coniferous
            if y_factor > 0.6:
                if rand < 0.6:
                    fuel_types[i, j] = np.random.choice([1, 2, 3, 4])  # C-1 to C-4
                elif rand < 0.9:
                    fuel_types[i, j] = np.random.choice([5, 6, 7])  # C-5 to C-7
                else:
                    fuel_types[i, j] = np.random.choice([21, 22])  # M-1, M-2

            # Central: Mixed
            elif y_factor > 0.3:
                if rand < 0.4:
                    fuel_types[i, j] = np.random.choice([11, 18])  # D-1, D-2
                elif rand < 0.7:
                    fuel_types[i, j] = np.random.choice([21, 22, 25])  # M-1, M-2
                else:
                    fuel_types[i, j] = np.random.choice([1, 2, 3])  # Coniferous

            # South: More deciduous and open
            else:
                if rand < 0.5:
                    fuel_types[i, j] = np.random.choice([11, 18])  # D-1, D-2
                elif rand < 0.7:
                    fuel_types[i, j] = np.random.choice([40, 41, 42, 43])  # O-1a, O-1b
                else:
                    fuel_types[i, j] = np.random.choice([31, 32])  # S-1, S-2

    # Create transform
    transform = from_bounds(
        bounds[0], bounds[1], bounds[2], bounds[3],
        width, height
    )

    # Save as GeoTIFF
    ensure_dir(output_path.parent)

    with rasterio.open(
        output_path,
        'w',
        driver='GTiff',
        height=height,
        width=width,
        count=1,
        dtype=fuel_types.dtype,
        crs=CRS.from_epsg(4326),
        transform=transform,
        compress='lzw'
    ) as dst:
        dst.write(fuel_types, 1)

    logger.info(f"✓ Created demo fuel type raster")
    logger.info(f"  Saved to: {output_path}")
    logger.info(f"  Dimensions: {width}x{height}")
    logger.info(f"  Fuel types: Synthetic Canadian FBP categories")
    logger.info(f"  Note: Demo data for testing - replace with real data for analysis")

    return True


def main():
    """Main execution function."""
    logger = setup_logging(__name__)
    logger.info("=" * 70)
    logger.info("Creating Demo Fire and Fuel Type Data")
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
    processed_fire_dir = ensure_dir(project_root / config['directories']['processed'] / 'fire')
    processed_fuel_dir = ensure_dir(project_root / config['directories']['processed'] / 'fuel')

    # Create demo datasets
    logger.info("\n" + "=" * 70)
    logger.info("1. FIRE PERIMETERS")
    logger.info("=" * 70)
    fire_output = processed_fire_dir / "fire_perimeters_2010_2024.geojson"
    create_demo_fire_perimeters(aoi, fire_output, logger)

    logger.info("\n" + "=" * 70)
    logger.info("2. FUEL TYPES")
    logger.info("=" * 70)
    fuel_output = processed_fuel_dir / "fuel_types.tif"
    create_demo_fuel_types(aoi, fuel_output, logger)

    logger.info("\n" + "=" * 70)
    logger.info("COMPLETE")
    logger.info("=" * 70)
    logger.info("\nDemo data created successfully!")
    logger.info("These are synthetic datasets for demonstration purposes.")
    logger.info("\nFor production use:")
    logger.info("  1. Obtain real fire perimeter data from CWFIS/NBAC")
    logger.info("  2. Download actual fuel type mapping from Natural Resources Canada")
    logger.info("  3. Replace demo files with real data")


if __name__ == "__main__":
    main()
