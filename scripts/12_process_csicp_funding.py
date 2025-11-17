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

    # Read CSICP data (file has no headers)
    csicp = pd.read_excel('data/raw/CSICP Funding.xlsx', header=None)

    # Set proper column names
    csicp.columns = ['Indigenous Group Name', 'Province', 'Project Name', 'Project Type', 'Funding Amount']
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
                    'funding': project['Funding Amount'],
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
                        'funding': project['Funding Amount'],
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
                        'funding': project['Funding Amount'],
                        'matched_community': comm['name'],
                        'geometry': comm['geometry']
                    })
                    matched = True
                    break

        if not matched:
            print(f"  No location match for: {group_name}")

    # For unmatched organizations, try to geocode headquarters
    print(f"\nGeocoding organization headquarters for unmatched projects...")

    # Manual headquarters locations for known organizations
    org_headquarters = {
        'Metis Nation of Ontario Secretariat': (-79.3832, 43.6532, 'Toronto, ON'),  # Toronto
        'Nishnawbe Aski Nation': (-90.8483, 50.7538, 'Thunder Bay, ON'),  # Thunder Bay
        'Chippewas of the Thames Board of Education': (-81.4991, 42.9697, 'Muncey, ON'),
        'Oneida Nation of the Thames': (-81.4906, 42.9756, 'Southwold, ON'),
        'Temagami First Nation': (-79.7919, 47.0534, 'Temagami, ON'),
        'Biinjitawaabik Zaaging Anishnabek': (-90.0, 49.5, 'Northwestern Ontario'),  # Approximate
        'Bingwi Neyaashi Anishinaabek': (-89.5, 49.0, 'Northwestern Ontario'),  # Approximate
        'Iskatewizaagegan #39 Independent First Nation': (-94.5, 50.5, 'Northwestern Ontario'),  # Approximate
        'MoCreebec Eeyoud': (-80.6489, 51.2328, 'Moose Factory, ON'),
        'Weenusk First Nation': (-84.2500, 54.8833, 'Peawanuck, ON')
    }

    # Add unmatched projects using HQ locations
    for _, project in csicp_ont.iterrows():
        group_name = project['Indigenous Group Name']

        # Check if already matched
        if any(m['group_name'] == group_name for m in location_matches):
            continue

        # Check if we have HQ coordinates
        if group_name in org_headquarters:
            lon, lat, location = org_headquarters[group_name]
            from shapely.geometry import Point

            location_matches.append({
                'group_name': group_name,
                'project_name': project['Project Name'],
                'project_type': project['Project Type'],
                'funding': project['Funding Amount'],
                'matched_community': f'{group_name} HQ ({location})',
                'geometry': Point(lon, lat)
            })
            print(f"  ✓ Geocoded: {group_name} to {location}")

    print(f"\nMatched {len(location_matches)} projects to locations")

    if len(location_matches) == 0:
        print("No projects could be matched to locations within Williams Treaty boundaries")
        return None

    # Create GeoDataFrame
    gdf = gpd.GeoDataFrame(location_matches, crs='EPSG:4326')

    # Convert any polygon geometries to centroids (for First Nations boundaries)
    from shapely.geometry import Point
    def ensure_point(geom):
        if geom.geom_type in ['Polygon', 'MultiPolygon']:
            return geom.centroid
        return geom

    gdf['geometry'] = gdf.geometry.apply(ensure_point)

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
