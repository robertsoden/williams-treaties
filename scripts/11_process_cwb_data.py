#!/usr/bin/env python3
"""
Process Community Well-Being (CWB) data
Joins CWB data with Census Subdivision boundaries and filters to Williams Treaty area
"""

import pandas as pd
import geopandas as gpd
from pathlib import Path
import requests
import zipfile
import io

def download_csd_boundaries():
    """Download Census Subdivision boundaries from Statistics Canada"""

    print("Downloading Census Subdivision boundaries from Statistics Canada...")

    # 2021 Census boundaries (Cartographic Boundary Files)
    url = "https://www12.statcan.gc.ca/census-recensement/2021/geo/sip-pis/boundary-limites/files-fichiers/lcsd000b21a_e.zip"

    output_dir = Path('data/raw/census')
    output_dir.mkdir(parents=True, exist_ok=True)

    shapefile_path = output_dir / 'lcsd000b21a_e.shp'

    # Check if already downloaded
    if shapefile_path.exists():
        print(f"✓ CSD boundaries already downloaded: {shapefile_path}")
        return gpd.read_file(shapefile_path)

    # Download and extract
    print("Downloading... (this may take a minute)")
    response = requests.get(url, timeout=120)
    response.raise_for_status()

    print("Extracting...")
    with zipfile.ZipFile(io.BytesIO(response.content)) as zip_file:
        zip_file.extractall(output_dir)

    print(f"✓ Downloaded and extracted to {output_dir}")

    # Read the shapefile
    gdf = gpd.read_file(shapefile_path)
    return gdf

def process_cwb_data():
    """Process CWB data and join with CSD boundaries"""

    print("\nProcessing Community Well-Being data...")

    # Read CWB data (note: latin-1 encoding for French characters)
    cwb = pd.read_csv('data/raw/CWB_2021.csv', encoding='latin-1')
    print(f"Loaded {len(cwb)} communities from CWB data")

    # Filter for Ontario only (CSD codes starting with 35)
    cwb_ont = cwb[cwb['CSD Code 2021'].astype(str).str.startswith('35')].copy()
    print(f"Found {len(cwb_ont)} Ontario communities")

    # Download/load CSD boundaries
    csd = download_csd_boundaries()
    print(f"Loaded {len(csd)} CSD boundaries")

    # Filter to Ontario
    csd_ont = csd[csd['PRUID'] == '35'].copy()
    print(f"Found {len(csd_ont)} Ontario CSDs")

    # Prepare for join
    cwb_ont['CSD_CODE'] = cwb_ont['CSD Code 2021'].astype(str)
    csd_ont['CSD_CODE'] = csd_ont['CSDUID'].astype(str)

    # Join CWB data with geometries
    cwb_geo = csd_ont.merge(
        cwb_ont,
        on='CSD_CODE',
        how='inner'
    )

    print(f"Joined {len(cwb_geo)} communities with geometries")

    # Filter to Williams Treaty territory
    treaty = gpd.read_file('data/boundaries/williams_treaty.geojson')
    treaty_reproj = treaty.to_crs(csd_ont.crs)

    cwb_filtered = cwb_geo[cwb_geo.intersects(treaty_reproj.union_all())].copy()
    print(f"Found {len(cwb_filtered)} communities within Williams Treaty boundaries")

    # Select and rename columns
    columns_to_keep = {
        'CSD Name 2021': 'name',
        'CSD Code 2021': 'csd_code',
        'Census Population 2021': 'population',
        'Income 2021': 'income_score',
        'Education 2021': 'education_score',
        'Housing 2021': 'housing_score',
        'Labour Force Activity 2021': 'labour_score',
        'CWB 2021': 'cwb_score',
        'Community Type 2021': 'community_type'
    }

    # Keep only columns that exist
    available_columns = {k: v for k, v in columns_to_keep.items() if k in cwb_filtered.columns}

    # Create result GeoDataFrame
    result_cols = list(available_columns.keys()) + ['geometry']
    gdf_result = gpd.GeoDataFrame(
        cwb_filtered[result_cols].rename(columns=available_columns),
        geometry='geometry',
        crs=cwb_filtered.crs
    )

    # Convert to EPSG:4326 for web mapping
    gdf_result = gdf_result.to_crs('EPSG:4326')

    # Ensure output directory exists
    output_dir = Path('data/processed/cwb')
    output_dir.mkdir(parents=True, exist_ok=True)

    # Save all communities
    output_file = output_dir / 'community_wellbeing.geojson'
    gdf_result.to_file(output_file, driver='GeoJSON')
    print(f"✓ Saved {len(gdf_result)} communities to {output_file}")

    # Save First Nations communities only
    fn_communities = gdf_result[
        gdf_result['community_type'].str.contains('First Nation', case=False, na=False)
    ].copy()

    if len(fn_communities) > 0:
        fn_file = output_dir / 'community_wellbeing_first_nations.geojson'
        fn_communities.to_file(fn_file, driver='GeoJSON')
        print(f"✓ Saved {len(fn_communities)} First Nations to {fn_file}")

        # Print First Nations summary
        print("\nFirst Nations communities:")
        for _, row in fn_communities.iterrows():
            cwb = row.get('cwb_score', 'N/A')
            pop = row.get('population', 'N/A')
            print(f"  {row['name']}: CWB={cwb}, Population={pop}")

    # Print summary statistics
    print(f"\nCWB Score Summary:")
    if 'cwb_score' in gdf_result.columns:
        print(f"  Mean: {gdf_result['cwb_score'].mean():.1f}")
        print(f"  Min: {gdf_result['cwb_score'].min():.1f}")
        print(f"  Max: {gdf_result['cwb_score'].max():.1f}")

    return gdf_result

if __name__ == '__main__':
    process_cwb_data()
