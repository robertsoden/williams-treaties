#!/usr/bin/env python3
"""
Run complete data download pipeline for Williams Treaty Territories.

This script orchestrates the entire data download and processing workflow:
1. Create Area of Interest (AOI)
2. Download land cover data
3. Process NDVI from satellite imagery
4. Download fire hazard data
5. Download flood hazard data
6. Download fire perimeters, fuel types, and DEM
7. Download Williams Treaty First Nations communities
8. Download First Nations reserve boundaries

Usage:
    python scripts/run_all.py [--skip-ndvi] [--skip-communities] [--skip-fire-fuel-dem] [--skip-reserves]
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
        '--skip-flood',
        action='store_true',
        help='Skip flood data download'
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
        '--skip-reserves',
        action='store_true',
        help='Skip First Nations reserve boundaries download'
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

    # 5. Download flood data
    if not args.skip_flood and results['aoi']:
        print("\n" + "="*70)
        print("STEP 5: DOWNLOAD FLOOD HAZARD DATA")
        print("="*70)
        flood_script = scripts_dir / "05_download_flood_data.py"
        flood_args = ['--all']
        results['flood'] = run_script(flood_script, args=flood_args, logger=logger)
    else:
        if args.skip_flood:
            logger.info("Skipping flood data download")
        results['flood'] = None

    # 6. Download fire perimeters, fuel types, and DEM
    if not args.skip_fire_fuel_dem and results['aoi']:
        print("\n" + "="*70)
        print("STEP 6: DOWNLOAD FIRE PERIMETERS, FUEL TYPES, AND DEM")
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

    # 8. Download First Nations reserve boundaries
    if not args.skip_reserves and results['aoi']:
        print("\n" + "="*70)
        print("STEP 8: DOWNLOAD FIRST NATIONS RESERVE BOUNDARIES")
        print("="*70)
        reserves_script = scripts_dir / "08_download_reserve_boundaries.py"
        results['reserves'] = run_script(reserves_script, logger=logger)
    else:
        if args.skip_reserves:
            logger.info("Skipping First Nations reserve boundaries download")
        results['reserves'] = None

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
    print("2. Follow manual download instructions in raw/*/info.json files")
    print("3. Place manually downloaded data in appropriate directories")
    print("4. Proceed to building the interactive map interface")
    print("="*70)


if __name__ == "__main__":
    main()
