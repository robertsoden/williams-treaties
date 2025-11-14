#!/usr/bin/env python3
"""
Run complete data download pipeline for Williams Treaty Territories.

This script orchestrates the entire data download and processing workflow:
1. Create Area of Interest (AOI)
2. Download land cover data
3. Process NDVI from satellite imagery
4. Download fire hazard data
5. Download fire perimeters, fuel types, and DEM
6. Download Williams Treaty First Nations communities
7. Process manually downloaded reserve boundaries (if available)
8. Process manually downloaded fire perimeters (if available)
9. Process manually downloaded fuel types (if available)

Note: Steps 8-10 require manual downloads first (see MANUAL_DOWNLOADS.md)

Usage:
    python scripts/run_all.py [--skip-ndvi] [--skip-communities] [--skip-fire-fuel-dem] [--skip-filters]
"""

import sys
import argparse
import subprocess
from pathlib import Path
from datetime import datetime

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts.utils import setup_logging, load_config, get_project_root


def run_script(script_path: Path, args: list = None, logger=None):
    """
    Run a Python script as a subprocess.

    Args:
        script_path: Path to the script to run
        args: Additional command-line arguments
        logger: Logger instance

    Returns:
        True if successful, False otherwise
    """
    if logger:
        logger.info(f"Running: {script_path.name}")

    cmd = [sys.executable, str(script_path)]
    if args:
        cmd.extend(args)

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=True
        )

        if logger and result.stdout:
            print(result.stdout)

        return True

    except subprocess.CalledProcessError as e:
        if logger:
            logger.error(f"Error running {script_path.name}")
            logger.error(f"Return code: {e.returncode}")
            if e.stderr:
                logger.error(f"Error output:\n{e.stderr}")

        return False


def main():
    """Main execution function."""
    parser = argparse.ArgumentParser(
        description='Run complete data pipeline for Williams Treaty Territories'
    )
    parser.add_argument(
        '--skip-aoi',
        action='store_true',
        help='Skip AOI creation (if already exists)'
    )
    parser.add_argument(
        '--skip-landcover',
        action='store_true',
        help='Skip land cover download'
    )
    parser.add_argument(
        '--skip-ndvi',
        action='store_true',
        help='Skip NDVI processing'
    )
    parser.add_argument(
        '--skip-fire',
        action='store_true',
        help='Skip fire data download'
    )
    parser.add_argument(
    )
    parser.add_argument(
        '--skip-fire-fuel-dem',
        action='store_true',
        help='Skip fire perimeters, fuel types, and DEM download'
    )
    parser.add_argument(
        '--skip-communities',
        action='store_true',
        help='Skip Williams Treaty communities download'
    )
    parser.add_argument(
        '--skip-filters',
        action='store_true',
        help='Skip processing of manually downloaded data (reserves, fires, fuel types)'
    )
    parser.add_argument(
        '--ndvi-example',
        action='store_true',
        help='Create example NDVI data instead of downloading satellite imagery'
    )

    args = parser.parse_args()

    logger = setup_logging(__name__)

    print("="*70)
    print("WILLIAMS TREATY TERRITORIES - DATA PIPELINE")
    print("="*70)
    print(f"Start time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*70)

    # Get scripts directory
    scripts_dir = Path(__file__).parent

    # Track results
    results = {}

    # 1. Create AOI
    if not args.skip_aoi:
        print("\n" + "="*70)
        print("STEP 1: CREATE AREA OF INTEREST")
        print("="*70)
        aoi_script = scripts_dir / "01_download_aoi.py"
        results['aoi'] = run_script(aoi_script, logger=logger)
    else:
        logger.info("Skipping AOI creation")
        results['aoi'] = True

    # 2. Download land cover
    if not args.skip_landcover and results['aoi']:
        print("\n" + "="*70)
        print("STEP 2: DOWNLOAD LAND COVER DATA")
        print("="*70)
        landcover_script = scripts_dir / "02_download_landcover.py"
        results['landcover'] = run_script(landcover_script, logger=logger)
    else:
        if args.skip_landcover:
            logger.info("Skipping land cover download")
        results['landcover'] = None

    # 3. Process NDVI
    if not args.skip_ndvi and results['aoi']:
        print("\n" + "="*70)
        print("STEP 3: PROCESS NDVI")
        print("="*70)
        ndvi_script = scripts_dir / "03_process_ndvi.py"
        ndvi_args = ['--example'] if args.ndvi_example else []
        results['ndvi'] = run_script(ndvi_script, args=ndvi_args, logger=logger)
    else:
        if args.skip_ndvi:
            logger.info("Skipping NDVI processing")
        results['ndvi'] = None

    # 4. Download fire data
    if not args.skip_fire and results['aoi']:
        print("\n" + "="*70)
        print("STEP 4: DOWNLOAD FIRE HAZARD DATA")
        print("="*70)
        fire_script = scripts_dir / "04_download_fire_data.py"
        results['fire'] = run_script(fire_script, logger=logger)
    else:
        if args.skip_fire:
            logger.info("Skipping fire data download")
        results['fire'] = None

    # 5. Download fire perimeters, fuel types, and DEM
    if not args.skip_fire_fuel_dem and results['aoi']:
        print("\n" + "="*70)
        print("STEP 5: DOWNLOAD FIRE PERIMETERS, FUEL TYPES, AND DEM")
        print("="*70)
        fire_fuel_dem_script = scripts_dir / "06_download_fire_fuel_dem.py"
        # Use --skip-fires and --skip-fuel for faster setup, as they may require manual download
        fire_fuel_dem_args = ['--skip-fires', '--skip-fuel']
        results['fire_fuel_dem'] = run_script(fire_fuel_dem_script, args=fire_fuel_dem_args, logger=logger)
    else:
        if args.skip_fire_fuel_dem:
            logger.info("Skipping fire perimeters, fuel types, and DEM download")
        results['fire_fuel_dem'] = None

    # 7. Download Williams Treaty communities
    if not args.skip_communities and results['aoi']:
        print("\n" + "="*70)
        print("STEP 7: DOWNLOAD WILLIAMS TREATY FIRST NATIONS COMMUNITIES")
        print("="*70)
        communities_script = scripts_dir / "07_download_williams_treaty_communities.py"
        results['communities'] = run_script(communities_script, logger=logger)
    else:
        if args.skip_communities:
            logger.info("Skipping Williams Treaty communities download")
        results['communities'] = None

    # Process manually downloaded data (if available)
    if not args.skip_filters:
        # Get project root and config
        config = load_config()
        project_root = get_project_root()

        # 8. Filter reserve boundaries (if raw data exists)
        print("\n" + "="*70)
        print("STEP 8: PROCESS RESERVE BOUNDARIES (if manually downloaded)")
        print("="*70)

        raw_reserves_dir = project_root / config['directories']['raw'] / 'reserves'
        if raw_reserves_dir.exists():
            # Look for common file formats
            reserve_files = (
                list(raw_reserves_dir.glob('*.shp')) +
                list(raw_reserves_dir.glob('*.geojson')) +
                list(raw_reserves_dir.glob('*.gpkg'))
            )

            if reserve_files:
                filter_reserves_script = scripts_dir / "filters" / "filter_reserve_boundaries.py"
                filter_args = [str(reserve_files[0])]
                logger.info(f"Found raw reserves data: {reserve_files[0].name}")
                results['filter_reserves'] = run_script(filter_reserves_script, args=filter_args, logger=logger)
            else:
                logger.info("No raw reserves data found - skipping")
                logger.info("  Download from: https://open.canada.ca/data/en/dataset/522b07b9-78e2-4819-b736-ad9208eb1067")
                results['filter_reserves'] = None
        else:
            logger.info("data/raw/reserves/ directory not found - skipping")
            logger.info("  Create directory and download reserves data to process")
            results['filter_reserves'] = None

        # 9. Filter fire perimeters (if raw data exists)
        print("\n" + "="*70)
        print("STEP 9: PROCESS FIRE PERIMETERS (if manually downloaded)")
        print("="*70)

        raw_fire_dir = project_root / config['directories']['raw'] / 'fire'
        if raw_fire_dir.exists():
            # Look for common file formats
            fire_files = (
                list(raw_fire_dir.glob('*.shp')) +
                list(raw_fire_dir.glob('*.geojson')) +
                list(raw_fire_dir.glob('*.gpkg'))
            )

            if fire_files:
                filter_fires_script = scripts_dir / "filters" / "filter_fire_perimeters.py"
                filter_args = [str(fire_files[0])]
                logger.info(f"Found raw fire data: {fire_files[0].name}")
                results['filter_fires'] = run_script(filter_fires_script, args=filter_args, logger=logger)
            else:
                logger.info("No raw fire data found - skipping")
                logger.info("  Download from: https://cwfis.cfs.nrcan.gc.ca/datamart")
                results['filter_fires'] = None
        else:
            logger.info("data/raw/fire/ directory not found - skipping")
            logger.info("  Create directory and download fire data to process")
            results['filter_fires'] = None

        # 10. Clip fuel types (if raw data exists)
        print("\n" + "="*70)
        print("STEP 10: PROCESS FUEL TYPES (if manually downloaded)")
        print("="*70)

        raw_fuel_dir = project_root / config['directories']['raw'] / 'fuel'
        if raw_fuel_dir.exists():
            # Look for GeoTIFF files
            fuel_files = list(raw_fuel_dir.glob('*.tif')) + list(raw_fuel_dir.glob('*.tiff'))

            if fuel_files:
                clip_fuel_script = scripts_dir / "filters" / "clip_fuel_types.py"
                filter_args = [str(fuel_files[0])]
                logger.info(f"Found raw fuel type data: {fuel_files[0].name}")
                results['clip_fuel'] = run_script(clip_fuel_script, args=filter_args, logger=logger)
            else:
                logger.info("No raw fuel type data found - skipping")
                logger.info("  Download from: https://cwfis.cfs.nrcan.gc.ca/datamart")
                results['clip_fuel'] = None
        else:
            logger.info("data/raw/fuel/ directory not found - skipping")
            logger.info("  Create directory and download fuel type data to process")
            results['clip_fuel'] = None
    else:
        logger.info("Skipping filter/clip processing of manually downloaded data")
        results['filter_reserves'] = None
        results['filter_fires'] = None
        results['clip_fuel'] = None

    # Print summary
    print("\n" + "="*70)
    print("PIPELINE SUMMARY")
    print("="*70)
    print(f"End time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("\nResults:")

    for step, result in results.items():
        if result is None:
            status = "SKIPPED"
        elif result:
            status = "✓ SUCCESS"
        else:
            status = "✗ FAILED"
        print(f"  {step.upper():15s}: {status}")

    print("\n" + "="*70)
    print("NEXT STEPS")
    print("="*70)
    print("1. Review downloaded/generated data in data/ directory")

    # Check if any filter steps were skipped due to missing data
    if not args.skip_filters:
        needs_manual = []
        if results.get('filter_reserves') is None:
            needs_manual.append("reserve boundaries")
        if results.get('filter_fires') is None:
            needs_manual.append("fire perimeters")
        if results.get('clip_fuel') is None:
            needs_manual.append("fuel types")

        if needs_manual:
            print("\n2. Manual downloads required for:")
            for layer in needs_manual:
                print(f"   - {layer}")
            print("   See MANUAL_DOWNLOADS.md for instructions")
            print("   Then re-run: python scripts/run_all.py")
    else:
        print("\n2. To process manually downloaded data:")
        print("   See MANUAL_DOWNLOADS.md for download instructions")
        print("   Then re-run without --skip-filters")

    print("\n3. Start the web map:")
    print("   python web/server.py")
    print("   Open http://localhost:8000 in your browser")
    print("="*70)


if __name__ == "__main__":
    main()
