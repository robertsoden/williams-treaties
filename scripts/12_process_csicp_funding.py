#!/usr/bin/env python3
"""
Process CSICP (Cultural and Social Infrastructure Capital Program) funding data
Matches Indigenous groups to locations and filters to Williams Treaty boundaries
"""

import pandas as pd
import geopandas as gpd
from pathlib import Path

def process_csicp_data():
    """Process CSICP funding data"""

    print("Processing CSICP funding data...")

    # Read CSICP data
    csicp = pd.read_excel('data/raw/CSICP Funding.xlsx')
    print(f"Loaded {len(csicp)} projects")

    # Filter for Ontario
    csicp_ont = csicp[csicp['Province'] == 'Ontario'].copy()
    print(f"Found {len(csicp_ont)} projects in Ontario")

    # Load communities data to match locations
    # Try to load our processed communities first
    communities = gpd.read_file('data/processed/communities/williams_treaty_communities.geojson')

    # Also load CWB First Nations data which has more communities
    cwb_fn = gpd.read_file('data/processed/cwb/community_wellbeing_first_nations.geojson')

    print(f"Loaded {len(communities)} Williams Treaty communities")
    print(f"Loaded {len(cwb_fn)} First Nations from CWB data")

    # Manual matching of CSICP groups to locations
    # We'll match based on the Indigenous Group Name
    location_matches = []

    for _, project in csicp_ont.iterrows():
        group_name = project['Indigenous Group Name']

        # Try to find matching community
        matched = False

        # Check in Williams Treaty communities
        for _, comm in communities.iterrows():
            if group_name.lower() in comm['name'].lower() or comm['name'].lower() in group_name.lower():
                location_matches.append({
                    'group_name': group_name,
                    'project_name': project['Project Name'],
                    'project_type': project['Project Type'],
                    'funding': project['Total Funding'],
                    'matched_community': comm['name'],
                    'geometry': comm['geometry']
                })
                matched = True
                break

        if not matched:
            # Check in CWB First Nations
            for _, comm in cwb_fn.iterrows():
                # Handle variations in names
                comm_name_clean = comm['name'].replace(' First Nation', '').replace(' Indian Reserve', '').replace(' No.', '').replace('79', '').strip()
                group_name_clean = group_name.replace(' First Nation', '').strip()

                # Special case: "Moose Deer Point" should match "Moose Point"
                if 'moose' in group_name.lower() and 'moose' in comm['name'].lower():
                    location_matches.append({
                        'group_name': group_name,
                        'project_name': project['Project Name'],
                        'project_type': project['Project Type'],
                        'funding': project['Total Funding'],
                        'matched_community': comm['name'],
                        'geometry': comm['geometry']
                    })
                    matched = True
                    break
                elif (comm_name_clean.lower() in group_name_clean.lower() or
                      group_name_clean.lower() in comm_name_clean.lower()):
                    location_matches.append({
                        'group_name': group_name,
                        'project_name': project['Project Name'],
                        'project_type': project['Project Type'],
                        'funding': project['Total Funding'],
                        'matched_community': comm['name'],
                        'geometry': comm['geometry']
                    })
                    matched = True
                    break

        if not matched:
            print(f"  No location match for: {group_name}")

    print(f"\nMatched {len(location_matches)} projects to locations")

    if len(location_matches) == 0:
        print("No projects could be matched to locations within Williams Treaty boundaries")
        return None

    # Create GeoDataFrame and convert polygon geometries to centroids
    gdf = gpd.GeoDataFrame(location_matches, crs='EPSG:4326')

    # Convert all geometries to points (centroids)
    gdf['geometry'] = gdf.geometry.centroid

    # Ensure output directory exists
    output_dir = Path('data/processed/csicp')
    output_dir.mkdir(parents=True, exist_ok=True)

    # Save to GeoJSON
    output_file = output_dir / 'csicp_funding.geojson'
    gdf.to_file(output_file, driver='GeoJSON')

    print(f"✓ Saved {len(gdf)} projects to {output_file}")

    # Print summary
    print(f"\nFunding by group:")
    funding_by_group = gdf.groupby('group_name')['funding'].sum().sort_values(ascending=False)
    for group, funding in funding_by_group.items():
        print(f"  {group}: ${funding:,.0f}")

    print(f"\nTotal CSICP funding: ${gdf['funding'].sum():,.0f}")

    return gdf

if __name__ == '__main__':
    process_csicp_data()
