#!/usr/bin/env python3
"""
Process Indigenous Community Infrastructure Management (ICIM) data
Converts infrastructure project data to GeoJSON format for mapping
"""

import pandas as pd
import geopandas as gpd
from shapely.geometry import Point
import json
from pathlib import Path

def process_icim_data():
    """Process ICIM infrastructure project data"""

    print("Processing ICIM infrastructure data...")

    # Read the CSV file
    # Note: The file has UTF-16 encoding with BOM and tab delimiter
    df = pd.read_csv(
        'data/raw/ICIM_Data_Export_2025-11-13T204227.csv',
        encoding='utf-16',
        sep='\t',
        on_bad_lines='skip'
    )

    print(f"Loaded {len(df)} infrastructure projects")

    # Filter for Ontario projects only
    df_ontario = df[df['Province/Territory'] == 'Ontario'].copy()
    print(f"Found {len(df_ontario)} projects in Ontario")

    # Clean up column names (remove extra spaces)
    df_ontario.columns = df_ontario.columns.str.strip()

    # Convert to numeric, handling errors
    df_ontario['Latitude'] = pd.to_numeric(df_ontario['Latitude'], errors='coerce')
    df_ontario['Longitude'] = pd.to_numeric(df_ontario['Longitude'], errors='coerce')

    # Drop rows without valid coordinates
    df_ontario = df_ontario.dropna(subset=['Latitude', 'Longitude'])
    print(f"Found {len(df_ontario)} projects with valid coordinates")

    # Create geometry
    geometry = [Point(xy) for xy in zip(df_ontario['Longitude'], df_ontario['Latitude'])]

    # Create GeoDataFrame
    gdf = gpd.GeoDataFrame(df_ontario, geometry=geometry, crs='EPSG:4326')

    # Load Williams Treaty boundaries to filter projects
    # Note: We include all Indigenous communities within treaty boundaries,
    # not just the seven original signatories
    treaty = gpd.read_file('data/boundaries/williams_treaty.geojson')
    treaty_reproj = treaty.to_crs('EPSG:4326')

    # Filter to projects within treaty boundaries
    mask = gdf.intersects(treaty_reproj.union_all())
    gdf_filtered = gdf[mask].copy()

    print(f"Found {len(gdf_filtered)} projects within Williams Treaty boundaries")

    if len(gdf_filtered) == 0:
        print("No projects found in Williams Treaty boundaries, saving all Ontario projects instead")
        gdf_filtered = gdf

    # Select and rename columns for the map
    # Note: The CSV has a typo - "Infrastucture" instead of "Infrastructure"
    columns_to_keep = {
        'Community': 'community',
        'Community Number': 'community_number',
        'Infrastucture Category': 'category',  # Note the typo in source data
        'Project Name': 'project_name',
        'Description': 'description',
        'Project Status': 'status',
        'Departmental Investment': 'investment',
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

    # Ensure output directory exists
    output_dir = Path('data/processed/infrastructure')
    output_dir.mkdir(parents=True, exist_ok=True)

    # Save to GeoJSON
    output_file = output_dir / 'infrastructure_projects.geojson'
    gdf_result.to_file(output_file, driver='GeoJSON')

    print(f"✓ Saved {len(gdf_result)} projects to {output_file}")

    # Print summary by category
    if 'category' in gdf_result.columns:
        print("\nProjects by category:")
        print(gdf_result['category'].value_counts().to_string())
    else:
        print(f"\nColumns in output: {list(gdf_result.columns)}")

    return gdf_result

if __name__ == '__main__':
    process_icim_data()
