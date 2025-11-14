#!/usr/bin/env python3
"""
Process water advisory data for First Nations
Converts water advisory data to GeoJSON format for mapping
"""

import pandas as pd
import geopandas as gpd
from shapely.geometry import Point
from pathlib import Path
from datetime import datetime

def process_water_advisories():
    """Process water advisory data"""

    print("Processing water advisory data...")

    # Read the CSV file
    df = pd.read_csv('data/raw/water_advisory_map_data_2025_11_13 .csv')

    print(f"Loaded {len(df)} water advisories")

    # Filter for Ontario advisories
    df_ontario = df[df['Region'] == 'ONTARIO'].copy()
    print(f"Found {len(df_ontario)} advisories in Ontario")

    # Convert to numeric, handling errors
    df_ontario['Latitude'] = pd.to_numeric(df_ontario['Latitude'], errors='coerce')
    df_ontario['Longitude'] = pd.to_numeric(df_ontario['Longitude'], errors='coerce')

    # Drop rows without valid coordinates
    df_ontario = df_ontario.dropna(subset=['Latitude', 'Longitude'])
    print(f"Found {len(df_ontario)} advisories with valid coordinates")

    # Parse dates
    date_columns = ['Date Advisory Set', 'Long term advisory since', 'Date Advisory Lifted']
    for col in date_columns:
        if col in df_ontario.columns:
            df_ontario[col] = pd.to_datetime(df_ontario[col], errors='coerce')

    # Calculate advisory duration in days for lifted advisories
    if 'Date Advisory Lifted' in df_ontario.columns and 'Date Advisory Set' in df_ontario.columns:
        df_ontario['duration_days'] = (
            df_ontario['Date Advisory Lifted'] - df_ontario['Date Advisory Set']
        ).dt.days

    # Determine if advisory is active (not lifted)
    df_ontario['is_active'] = df_ontario['Date Advisory Lifted'].isna()

    # Create geometry
    geometry = [Point(xy) for xy in zip(df_ontario['Longitude'], df_ontario['Latitude'])]

    # Create GeoDataFrame
    gdf = gpd.GeoDataFrame(df_ontario, geometry=geometry, crs='EPSG:4326')

    # Load Williams Treaty boundaries to filter advisories
    # Note: We include all Indigenous communities within treaty boundaries,
    # not just the seven original signatories
    treaty = gpd.read_file('data/boundaries/williams_treaty.geojson')
    treaty_reproj = treaty.to_crs('EPSG:4326')

    # Filter to advisories within treaty boundaries
    mask = gdf.intersects(treaty_reproj.union_all())
    gdf_filtered = gdf[mask].copy()

    print(f"Found {len(gdf_filtered)} advisories within Williams Treaty boundaries")

    if len(gdf_filtered) == 0:
        print("No advisories found in Williams Treaty boundaries, saving all Ontario advisories instead")
        gdf_filtered = gdf

    # Select and clean columns for the map
    columns_to_keep = {
        'ID': 'id',
        'First Nation': 'first_nation',
        'Water System Name': 'water_system',
        'Type of advisory': 'advisory_type',
        'Date Advisory Set': 'date_set',
        'Long term advisory since': 'long_term_since',
        'Date Advisory Lifted': 'date_lifted',
        'Population': 'population',
        'Corrective Measure': 'corrective_measure',
        'Project Phase': 'project_phase',
        'is_active': 'is_active',
        'duration_days': 'duration_days',
        'Latitude': 'latitude',
        'Longitude': 'longitude'
    }

    # Keep only columns that exist
    available_columns = {k: v for k, v in columns_to_keep.items() if k in gdf_filtered.columns}

    # Preserve geometry column
    gdf_result = gpd.GeoDataFrame(
        gdf_filtered[list(available_columns.keys())].rename(columns=available_columns),
        geometry=gdf_filtered.geometry,
        crs='EPSG:4326'
    )

    # Convert dates to strings for GeoJSON
    for col in ['date_set', 'long_term_since', 'date_lifted']:
        if col in gdf_result.columns:
            gdf_result[col] = gdf_result[col].astype(str).replace('NaT', '')

    # Ensure output directory exists
    output_dir = Path('data/processed/water')
    output_dir.mkdir(parents=True, exist_ok=True)

    # Save all advisories
    output_file = output_dir / 'water_advisories.geojson'
    gdf_result.to_file(output_file, driver='GeoJSON')
    print(f"✓ Saved {len(gdf_result)} advisories to {output_file}")

    # Save active advisories only
    active_advisories = gdf_result[gdf_result['is_active'] == True].copy()
    if len(active_advisories) > 0:
        active_file = output_dir / 'water_advisories_active.geojson'
        gpd.GeoDataFrame(active_advisories, geometry=active_advisories.geometry, crs='EPSG:4326').to_file(active_file, driver='GeoJSON')
        print(f"✓ Saved {len(active_advisories)} active advisories to {active_file}")

    # Print summary
    print(f"\nSummary:")
    print(f"  Total advisories: {len(gdf_result)}")
    print(f"  Active advisories: {gdf_result['is_active'].sum()}")
    print(f"  Lifted advisories: {(~gdf_result['is_active']).sum()}")

    if 'advisory_type' in gdf_result.columns:
        print("\nAdvisories by type:")
        print(gdf_result['advisory_type'].value_counts().to_string())

    return gdf_result

if __name__ == '__main__':
    process_water_advisories()
