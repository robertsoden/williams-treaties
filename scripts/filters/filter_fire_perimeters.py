#!/usr/bin/env python3
"""
Filter fire perimeters for Williams Treaty Territories area and time range.

This script takes historical fire perimeter data and filters it for:
- Geographic extent: Williams Treaty Territories bounding box
- Time range: 2010-2024 (configurable)

Usage:
    python scripts/filters/filter_fire_perimeters.py <input_file> [--start-year 2010] [--end-year 2024]

Example:
    python scripts/filters/filter_fire_perimeters.py data/raw/fire/nbac_fire_perimeters.shp
    python scripts/filters/filter_fire_perimeters.py data/raw/fire/fires.geojson --start-year 2015
"""

import sys
import argparse
from pathlib import Path
import geopandas as gpd
import pandas as pd

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from scripts.utils import (
    setup_logging,
    load_config,
    get_project_root,
    ensure_dir,
    load_aoi,
    save_geojson
)


# Williams Treaty Territories bounding box (approximate)
BBOX = {
    'west': -80.0,
    'east': -78.0,
    'south': 44.0,
    'north': 45.0
}


def find_year_field(gdf, logger):
    """
    Find the field containing fire year.

    Args:
        gdf: GeoDataFrame with fire data
        logger: Logger instance

    Returns:
        Field name or None
    """
    # Common field names for year
    possible_fields = [
        'YEAR', 'Year', 'year', 'FIRE_YEAR', 'fire_year',
        'FireYear', 'YR', 'yr', 'DATE', 'date'
    ]

    for field in possible_fields:
        if field in gdf.columns:
            logger.info(f"  Using year field: {field}")
            return field

    logger.warning("  Could not find year field")
    logger.info(f"  Available fields: {list(gdf.columns)}")
    return None


def extract_year(value):
    """
    Extract year from various date formats.

    Args:
        value: Date value (int, str, datetime, etc.)

    Returns:
        Year as integer or None
    """
    if pd.isna(value):
        return None

    # If already an integer
    if isinstance(value, (int, float)):
        year = int(value)
        if 1900 <= year <= 2100:
            return year
        return None

    # If string
    if isinstance(value, str):
        # Try to extract 4-digit year
        import re
        match = re.search(r'(19|20)\d{2}', value)
        if match:
            return int(match.group())

    # If datetime
    if hasattr(value, 'year'):
        return value.year

    return None


def filter_fires(gdf, year_field, bbox, start_year, end_year, logger):
    """
    Filter fires by geography and time.

    Args:
        gdf: GeoDataFrame with fire data
        year_field: Field containing year
        bbox: Bounding box dict with west/east/south/north
        start_year: Start year (inclusive)
        end_year: End year (inclusive)
        logger: Logger instance

    Returns:
        Filtered GeoDataFrame
    """
    logger.info("\nFiltering fire perimeters...")

    # Reproject to WGS84 if needed for bbox filtering
    original_crs = gdf.crs
    if gdf.crs != 'EPSG:4326':
        logger.info(f"  Reprojecting from {gdf.crs} to EPSG:4326 for filtering...")
        gdf = gdf.to_crs('EPSG:4326')

    # Filter by bounding box
    logger.info(f"\n  Applying bounding box filter:")
    logger.info(f"    West:  {bbox['west']}")
    logger.info(f"    East:  {bbox['east']}")
    logger.info(f"    South: {bbox['south']}")
    logger.info(f"    North: {bbox['north']}")

    bbox_filtered = gdf.cx[bbox['west']:bbox['east'], bbox['south']:bbox['north']]
    logger.info(f"    ✓ {len(bbox_filtered):,} fires in study area")

    if len(bbox_filtered) == 0:
        logger.warning("    No fires found in bounding box!")
        return bbox_filtered

    # Filter by year if field exists
    if year_field:
        logger.info(f"\n  Applying year filter: {start_year}-{end_year}")

        # Extract years
        years = bbox_filtered[year_field].apply(extract_year)
        bbox_filtered['YEAR'] = years

        # Filter by year range
        year_mask = (years >= start_year) & (years <= end_year)
        filtered = bbox_filtered[year_mask].copy()

        logger.info(f"    ✓ {len(filtered):,} fires in time range")

        # Show year distribution
        if len(filtered) > 0:
            year_counts = filtered['YEAR'].value_counts().sort_index()
            logger.info("\n  Fires by year:")
            for year, count in year_counts.items():
                logger.info(f"    {year}: {count:,} fires")

    else:
        logger.warning("  No year field found - skipping time filter")
        filtered = bbox_filtered.copy()

    return filtered


def main():
    """Main execution function."""
    parser = argparse.ArgumentParser(
        description='Filter fire perimeters for Williams Treaty Territories'
    )
    parser.add_argument(
        'input_file',
        type=Path,
        help='Path to input file (Shapefile, GeoJSON, or GeoPackage)'
    )
    parser.add_argument(
        '-o', '--output',
        type=Path,
        help='Output file path (default: data/processed/fire/fire_perimeters_YYYY_YYYY.geojson)'
    )
    parser.add_argument(
        '--start-year',
        type=int,
        default=2010,
        help='Start year (inclusive, default: 2010)'
    )
    parser.add_argument(
        '--end-year',
        type=int,
        default=2024,
        help='End year (inclusive, default: 2024)'
    )
    parser.add_argument(
        '--list-fields',
        action='store_true',
        help='List all fields in the input file and exit'
    )
    parser.add_argument(
        '--use-aoi',
        action='store_true',
        help='Use AOI boundary instead of bounding box for filtering'
    )

    args = parser.parse_args()

    # Setup
    logger = setup_logging('filter_fires')
    config = load_config()
    project_root = get_project_root()

    # Set output path
    if args.output:
        output_path = args.output
    else:
        output_dir = ensure_dir(
            project_root / config['directories']['processed'] / 'fire'
        )
        output_path = output_dir / f'fire_perimeters_{args.start_year}_{args.end_year}.geojson'

    logger.info("=" * 70)
    logger.info("FILTER FIRE PERIMETERS")
    logger.info("=" * 70)
    logger.info(f"\nInput:      {args.input_file}")
    logger.info(f"Output:     {output_path}")
    logger.info(f"Time range: {args.start_year}-{args.end_year}")

    # Check input file exists
    if not args.input_file.exists():
        logger.error(f"\nInput file not found: {args.input_file}")
        logger.error("\nPlease download the dataset first:")
        logger.error("  CWFIS: https://cwfis.cfs.nrcan.gc.ca/datamart")
        logger.error("  NBAC:  https://open.canada.ca/data/en/dataset/9d8f219c-4df0-4481-926f-8a2a532ca003")
        sys.exit(1)

    # Load data
    logger.info("\nLoading fire perimeters...")
    try:
        gdf = gpd.read_file(args.input_file)
        logger.info(f"  ✓ Loaded {len(gdf):,} fire perimeters")
        logger.info(f"  CRS: {gdf.crs}")
    except Exception as e:
        logger.error(f"  Failed to load file: {str(e)}")
        sys.exit(1)

    # List fields if requested
    if args.list_fields:
        logger.info("\nAvailable fields:")
        for i, col in enumerate(gdf.columns, 1):
            logger.info(f"  {i:2d}. {col}")
        logger.info("\nSample values from first record:")
        for col in gdf.columns:
            if col != 'geometry':
                logger.info(f"  {col}: {gdf[col].iloc[0]}")
        sys.exit(0)

    # Find year field
    year_field = find_year_field(gdf, logger)

    # Use AOI or bounding box
    bbox = BBOX
    if args.use_aoi:
        logger.info("\nLoading AOI boundary...")
        try:
            aoi = load_aoi()
            # Get bounding box from AOI
            bounds = aoi.total_bounds
            bbox = {
                'west': bounds[0],
                'south': bounds[1],
                'east': bounds[2],
                'north': bounds[3]
            }
            logger.info("  ✓ Using AOI bounds")
        except Exception as e:
            logger.warning(f"  Could not load AOI: {str(e)}")
            logger.info("  Using default bounding box instead")

    # Filter fires
    filtered = filter_fires(gdf, year_field, bbox, args.start_year, args.end_year, logger)

    # Check results
    logger.info(f"\n{'='*70}")
    logger.info(f"FILTERING RESULTS")
    logger.info(f"{'='*70}")
    logger.info(f"Input fires:    {len(gdf):,}")
    logger.info(f"Filtered fires: {len(filtered):,}")
    logger.info(f"Reduction:      {(1 - len(filtered)/len(gdf))*100:.1f}%")

    if len(filtered) == 0:
        logger.warning("\nNo fires found in study area!")
        logger.warning("This might mean:")
        logger.warning("  1. No fires occurred in this area during the time period")
        logger.warning("  2. Bounding box doesn't match your study area")
        logger.warning("  3. Data is in unexpected format/projection")
        logger.info("\nTry:")
        logger.info("  - Adjusting time range with --start-year and --end-year")
        logger.info("  - Using --use-aoi to filter by actual AOI boundary")
        logger.info("  - Running with --list-fields to inspect the data")
        sys.exit(0)

    # Standardize field names
    logger.info("\nStandardizing field names...")
    field_mapping = {}

    for old_field in filtered.columns:
        old_lower = old_field.lower()
        if 'fire' in old_lower and 'id' in old_lower:
            field_mapping[old_field] = 'FIRE_ID'
        elif 'area' in old_lower or 'size' in old_lower:
            if 'ha' in old_lower or 'hectare' in old_lower:
                field_mapping[old_field] = 'area'

    if field_mapping:
        filtered = filtered.rename(columns=field_mapping)
        logger.info(f"  Renamed {len(field_mapping)} fields")

    # Ensure YEAR field exists
    if 'YEAR' not in filtered.columns and year_field:
        filtered['YEAR'] = filtered[year_field].apply(extract_year)
        logger.info("  Added YEAR field")

    # Calculate area in hectares if geometry is polygon
    if 'area' not in filtered.columns and filtered.geometry.type.iloc[0] in ['Polygon', 'MultiPolygon']:
        logger.info("\nCalculating fire areas...")
        # Project to equal area projection for area calculation
        area_crs = 'EPSG:3347'  # Statistics Canada Lambert
        filtered_proj = filtered.to_crs(area_crs)
        filtered['area'] = filtered_proj.geometry.area / 10000  # Convert m² to hectares
        logger.info(f"  ✓ Calculated areas in hectares")

    # Reproject to WGS84 for web
    if filtered.crs != 'EPSG:4326':
        logger.info(f"\nReprojecting to EPSG:4326...")
        filtered = filtered.to_crs('EPSG:4326')
        logger.info("  ✓ Reprojected")

    # Save output
    logger.info("\nSaving filtered fire perimeters...")
    save_geojson(filtered, output_path)
    logger.info(f"  ✓ Saved to: {output_path}")
    logger.info(f"  File size: {output_path.stat().st_size / 1024:.1f} KB")

    # Summary statistics
    if len(filtered) > 0:
        logger.info(f"\n{'='*70}")
        logger.info("STATISTICS")
        logger.info(f"{'='*70}")

        if 'area' in filtered.columns:
            total_area = filtered['area'].sum()
            avg_area = filtered['area'].mean()
            logger.info(f"\nTotal burned area:   {total_area:,.0f} hectares")
            logger.info(f"Average fire size:   {avg_area:,.0f} hectares")
            logger.info(f"Largest fire:        {filtered['area'].max():,.0f} hectares")

        if 'YEAR' in filtered.columns:
            logger.info(f"\nTime range:          {filtered['YEAR'].min():.0f} - {filtered['YEAR'].max():.0f}")

    # Summary
    logger.info(f"\n{'='*70}")
    logger.info("COMPLETE")
    logger.info(f"{'='*70}")
    logger.info(f"\nFiltered {len(filtered):,} fire perimeters for Williams Treaty area")
    logger.info("\nNext steps:")
    logger.info("  1. View fire perimeters on the web map")
    logger.info("  2. Toggle 'Fire Perimeters' layer")
    logger.info("  3. Click on fires to see details")


if __name__ == '__main__':
    main()
