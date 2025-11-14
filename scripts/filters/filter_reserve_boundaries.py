#!/usr/bin/env python3
"""
Filter First Nations reserve boundaries for Williams Treaty communities.

This script takes the Canada-wide First Nations reserve boundaries dataset
and filters it for the 7 Williams Treaty First Nations.

Usage:
    python scripts/filters/filter_reserve_boundaries.py <input_file>

Example:
    python scripts/filters/filter_reserve_boundaries.py data/raw/reserves/reserves_canada.shp
"""

import sys
import argparse
from pathlib import Path
import geopandas as gpd

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from scripts.utils import (
    setup_logging,
    load_config,
    get_project_root,
    ensure_dir,
    save_geojson
)


# Williams Treaty reserve names to filter
WILLIAMS_TREATY_RESERVES = [
    'Alderville 35',
    'Curve Lake 35',
    'Hiawatha 36',
    'Scugog Island 34',
    'Chimnissing 1',
    'Georgina Island 33',
    'Rama 32'
]

# Alternative name patterns for fuzzy matching
RESERVE_PATTERNS = {
    'alderville': 'Alderville 35',
    'curve lake': 'Curve Lake 35',
    'hiawatha': 'Hiawatha 36',
    'scugog': 'Scugog Island 34',
    'chimnissing': 'Chimnissing 1',
    'beausoleil': 'Chimnissing 1',
    'georgina island': 'Georgina Island 33',
    'rama': 'Rama 32'
}


def find_name_field(gdf, logger):
    """
    Find the field containing reserve names.

    Args:
        gdf: GeoDataFrame with reserve data
        logger: Logger instance

    Returns:
        Field name or None
    """
    # Common field names for reserve names
    possible_fields = [
        'RESERVE_NAME', 'ENGLISH_NAME', 'NAME', 'RESNAME',
        'name', 'reserve_name', 'english_name', 'RES_NAME'
    ]

    for field in possible_fields:
        if field in gdf.columns:
            logger.info(f"  Using name field: {field}")
            return field

    logger.warning("  Could not find reserve name field")
    logger.info(f"  Available fields: {list(gdf.columns)}")
    return None


def filter_reserves(gdf, name_field, logger):
    """
    Filter GeoDataFrame for Williams Treaty reserves.

    Args:
        gdf: GeoDataFrame with all reserves
        name_field: Field name containing reserve names
        logger: Logger instance

    Returns:
        Filtered GeoDataFrame
    """
    logger.info("\nFiltering for Williams Treaty reserves...")

    # Try exact match first
    mask = gdf[name_field].isin(WILLIAMS_TREATY_RESERVES)
    filtered = gdf[mask].copy()

    logger.info(f"  Exact matches: {len(filtered)}")

    if len(filtered) > 0:
        for name in filtered[name_field]:
            logger.info(f"    ✓ {name}")

    # If missing reserves, try fuzzy matching
    missing_count = 7 - len(filtered)
    if missing_count > 0:
        logger.info(f"\n  Missing {missing_count} reserves, trying fuzzy matching...")

        for pattern, target_name in RESERVE_PATTERNS.items():
            # Skip if we already have this reserve
            if target_name in filtered[name_field].values:
                continue

            # Try pattern matching
            pattern_mask = gdf[name_field].str.lower().str.contains(pattern, na=False)
            matches = gdf[pattern_mask]

            if len(matches) > 0:
                logger.info(f"  Pattern '{pattern}' matched: {list(matches[name_field])}")
                # Add first match
                for idx, row in matches.head(1).iterrows():
                    if idx not in filtered.index:
                        filtered = gpd.GeoDataFrame(
                            pd.concat([filtered, row.to_frame().T], ignore_index=False)
                        )
                        logger.info(f"    ✓ Added: {row[name_field]}")

    return filtered


def main():
    """Main execution function."""
    parser = argparse.ArgumentParser(
        description='Filter First Nations reserves for Williams Treaty communities'
    )
    parser.add_argument(
        'input_file',
        type=Path,
        help='Path to input file (Shapefile, GeoJSON, or GeoPackage)'
    )
    parser.add_argument(
        '-o', '--output',
        type=Path,
        help='Output file path (default: data/processed/communities/williams_treaty_reserves.geojson)'
    )
    parser.add_argument(
        '--list-fields',
        action='store_true',
        help='List all fields in the input file and exit'
    )

    args = parser.parse_args()

    # Setup
    logger = setup_logging('filter_reserves')
    config = load_config()
    project_root = get_project_root()

    # Set output path
    if args.output:
        output_path = args.output
    else:
        output_dir = ensure_dir(
            project_root / config['directories']['processed'] / 'communities'
        )
        output_path = output_dir / 'williams_treaty_reserves.geojson'

    logger.info("=" * 70)
    logger.info("FILTER FIRST NATIONS RESERVE BOUNDARIES")
    logger.info("=" * 70)
    logger.info(f"\nInput:  {args.input_file}")
    logger.info(f"Output: {output_path}")

    # Check input file exists
    if not args.input_file.exists():
        logger.error(f"\nInput file not found: {args.input_file}")
        logger.error("\nPlease download the dataset first:")
        logger.error("  https://open.canada.ca/data/en/dataset/522b07b9-78e2-4819-b736-ad9208eb1067")
        sys.exit(1)

    # Load data
    logger.info("\nLoading reserve boundaries...")
    try:
        gdf = gpd.read_file(args.input_file)
        logger.info(f"  ✓ Loaded {len(gdf):,} reserves")
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

    # Find name field
    name_field = find_name_field(gdf, logger)
    if not name_field:
        logger.error("\nCould not automatically determine reserve name field.")
        logger.error("Run with --list-fields to see available fields.")
        logger.error("Then update the WILLIAMS_TREATY_RESERVES list with exact names.")
        sys.exit(1)

    # Filter for Williams Treaty reserves
    filtered = filter_reserves(gdf, name_field, logger)

    # Check results
    logger.info(f"\n{'='*70}")
    logger.info(f"FILTERING RESULTS")
    logger.info(f"{'='*70}")
    logger.info(f"Total reserves found: {len(filtered)} / 7")

    if len(filtered) == 0:
        logger.error("\nNo reserves found!")
        logger.error("This might mean:")
        logger.error("  1. Field names don't match expected patterns")
        logger.error("  2. Reserve names are different in the dataset")
        logger.error("\nRun with --list-fields to inspect the data.")
        sys.exit(1)

    if len(filtered) < 7:
        logger.warning(f"\nOnly found {len(filtered)} of 7 reserves")
        logger.warning("Missing reserves - you may need to:")
        logger.warning("  1. Check exact spelling in the dataset")
        logger.warning("  2. Update WILLIAMS_TREATY_RESERVES in this script")
        logger.warning("  3. Add more patterns to RESERVE_PATTERNS")

    # Standardize field names
    logger.info("\nStandardizing field names...")
    field_mapping = {}

    # Map to standard names
    for old_field in filtered.columns:
        old_lower = old_field.lower()
        if 'english' in old_lower and 'name' in old_lower:
            field_mapping[old_field] = 'ENGLISH_NAME'
        elif old_field == name_field or 'reserve' in old_lower:
            field_mapping[old_field] = 'RESERVE_NAME'
        elif 'band' in old_lower and 'name' in old_lower:
            field_mapping[old_field] = 'BAND_NAME'
        elif 'area' in old_lower and 'sq' in old_lower:
            field_mapping[old_field] = 'AREA_SQKM'

    if field_mapping:
        filtered = filtered.rename(columns=field_mapping)
        logger.info(f"  Renamed {len(field_mapping)} fields")

    # Reproject to WGS84 if needed
    if filtered.crs != 'EPSG:4326':
        logger.info(f"\nReprojecting from {filtered.crs} to EPSG:4326...")
        filtered = filtered.to_crs('EPSG:4326')
        logger.info("  ✓ Reprojected")

    # Save output
    logger.info("\nSaving filtered reserves...")
    save_geojson(filtered, output_path)
    logger.info(f"  ✓ Saved to: {output_path}")
    logger.info(f"  File size: {output_path.stat().st_size / 1024:.1f} KB")

    # Summary
    logger.info(f"\n{'='*70}")
    logger.info("COMPLETE")
    logger.info(f"{'='*70}")
    logger.info(f"\nFiltered {len(filtered)} Williams Treaty reserves")
    logger.info("\nReserves included:")

    if 'RESERVE_NAME' in filtered.columns:
        for name in sorted(filtered['RESERVE_NAME']):
            logger.info(f"  ✓ {name}")
    elif name_field in filtered.columns:
        for name in sorted(filtered[name_field]):
            logger.info(f"  ✓ {name}")

    logger.info("\nNext steps:")
    logger.info("  1. View reserves on the web map")
    logger.info("  2. Toggle 'First Nations Reserves' layer")
    logger.info("  3. Verify all 7 reserves are present")

    if len(filtered) < 7:
        logger.info("\n⚠️  Missing reserves - may need manual adjustment")


if __name__ == '__main__':
    import pandas as pd
    main()
