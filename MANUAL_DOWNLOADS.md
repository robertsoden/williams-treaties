# Manual Download Instructions

Some data layers for the Williams Treaty Territories map require manual download due to access restrictions, file size, or licensing requirements. This document provides step-by-step instructions for each layer.

## Overview

**Layers requiring manual download:**
1. First Nations Reserve Boundaries
2. Fire Perimeters (Historical)
3. Wildland Fuel Type Classification

---

## 1. First Nations Reserve Boundaries

**Required for:** Williams Treaty First Nations reserve boundaries layer

**Data Source:** Indigenous Services Canada
**Portal:** https://open.canada.ca/data/en/dataset/522b07b9-78e2-4819-b736-ad9208eb1067

### Download Steps:

1. Visit the Open Canada portal link above
2. Look for download options (GeoJSON, Shapefile, or GeoPackage format)
3. Download the complete Canada-wide dataset
4. Filter for the 7 Williams Treaty reserves:
   - Alderville 35
   - Curve Lake 35
   - Hiawatha 36
   - Scugog Island 34
   - Chimnissing 1 (Beausoleil)
   - Georgina Island 33
   - Rama 32

### Filtering the Data:

**Option A: Using QGIS**
```
1. Open the downloaded file in QGIS
2. Open the attribute table
3. Use "Select by Expression" with:
   "RESERVE_NAME" IN ('Alderville 35', 'Curve Lake 35', 'Hiawatha 36',
                      'Scugog Island 34', 'Chimnissing 1',
                      'Georgina Island 33', 'Rama 32')
4. Export selected features as GeoJSON
```

**Option B: Using Python/GeoPandas**
```python
import geopandas as gpd

# Load the data
reserves_all = gpd.read_file('path/to/downloaded/file.shp')

# Filter for Williams Treaty reserves
reserve_names = [
    'Alderville 35', 'Curve Lake 35', 'Hiawatha 36',
    'Scugog Island 34', 'Chimnissing 1',
    'Georgina Island 33', 'Rama 32'
]

# Filter (adjust field name as needed - might be RESERVE_NAME, NAME, etc.)
reserves_filtered = reserves_all[reserves_all['RESERVE_NAME'].isin(reserve_names)]

# Ensure WGS84 projection
if reserves_filtered.crs != 'EPSG:4326':
    reserves_filtered = reserves_filtered.to_crs('EPSG:4326')

# Save
reserves_filtered.to_file(
    'data/processed/communities/williams_treaty_reserves.geojson',
    driver='GeoJSON'
)
```

### Save Location:
```
data/processed/communities/williams_treaty_reserves.geojson
```

### Expected Result:
- 7 polygon features
- File size: ~20-50 KB (depending on detail level)
- Projection: WGS84 (EPSG:4326)

---

## 2. Fire Perimeters (Historical)

**Required for:** Historical fire boundaries layer (2010-2024)

**Data Source:** Canadian Wildland Fire Information System (CWFIS)
**Portal:** https://cwfis.cfs.nrcan.gc.ca/datamart

### Download Steps:

1. Visit the CWFIS Data Mart
2. Navigate to: **Historical Fire Data** > **Fire Perimeters**
3. Select years: 2010-2024
4. Download format: **Shapefile** or **GeoJSON**
5. Filter for Ontario or use bounding box for Williams Treaty area

### Alternative Source:
National Burned Area Composite (NBAC)
- Portal: https://open.canada.ca/data/en/dataset/9d8f219c-4df0-4481-926f-8a2a532ca003
- More complete historical dataset
- Includes all provinces/territories

### Filtering for Study Area:

**Bounding Box for Williams Treaty Territories:**
```
West:  -80.0
East:  -78.0
South:  44.0
North:  45.0
```

**Using Python/GeoPandas:**
```python
import geopandas as gpd

# Load fire perimeters
fires = gpd.read_file('path/to/fire_perimeters.shp')

# Filter by bounding box (Williams Treaty area)
bbox = [-80.0, 44.0, -78.0, 45.0]  # [minx, miny, maxx, maxy]
fires_filtered = fires.cx[bbox[0]:bbox[2], bbox[1]:bbox[3]]

# Filter by year range
fires_filtered = fires_filtered[
    (fires_filtered['YEAR'] >= 2010) &
    (fires_filtered['YEAR'] <= 2024)
]

# Ensure WGS84
if fires_filtered.crs != 'EPSG:4326':
    fires_filtered = fires_filtered.to_crs('EPSG:4326')

# Save
fires_filtered.to_file(
    'data/processed/fire/fire_perimeters_2010_2024.geojson',
    driver='GeoJSON'
)
```

### Save Location:
```
data/processed/fire/fire_perimeters_2010_2024.geojson
```

### Expected Result:
- Variable number of features (depends on fire activity)
- Projection: WGS84 (EPSG:4326)
- Attributes should include: YEAR, FIRE_ID, AREA (hectares)

---

## 3. Wildland Fuel Type Classification

**Required for:** Fuel type mapping layer (for fire behavior modeling)

**Data Source:** Canadian Forest Service / CWFIS
**Portal:** https://cwfis.cfs.nrcan.gc.ca/datamart

### Download Steps:

1. Visit CWFIS Data Mart
2. Navigate to: **Fuel Type Mapping** or **FBP Fuel Types**
3. Look for Canada-wide fuel type grid
4. Download format: **GeoTIFF** preferred
5. Clip to Williams Treaty area

### Alternative Source:
CanVec+ Land Cover (includes fuel types)
- Portal: https://open.canada.ca/data/en/dataset/8ba2aa2a-7bb9-4448-b4d7-f164409fe056

### Processing for Study Area:

**Using Python/rasterio:**
```python
import rasterio
from rasterio.mask import mask
import geopandas as gpd
import json

# Load AOI
aoi = gpd.read_file('data/boundaries/williams_treaty_aoi.geojson')

# Load fuel type raster
with rasterio.open('path/to/fuel_types.tif') as src:
    # Get AOI geometry
    geoms = [json.loads(aoi.to_json())['features'][0]['geometry']]

    # Clip raster to AOI
    out_image, out_transform = mask(src, geoms, crop=True)
    out_meta = src.meta.copy()

    # Update metadata
    out_meta.update({
        "driver": "GTiff",
        "height": out_image.shape[1],
        "width": out_image.shape[2],
        "transform": out_transform,
        "crs": "EPSG:4326"
    })

    # Save clipped raster
    with rasterio.open(
        'data/processed/fuel/fuel_types.tif',
        'w',
        **out_meta
    ) as dest:
        dest.write(out_image)
```

### Save Location:
```
data/processed/fuel/fuel_types.tif
```

### Expected Result:
- GeoTIFF raster file
- Projection: WGS84 (EPSG:4326)
- Pixel values: FBP fuel type codes (1-99)
- File size: Variable (depends on resolution)

### Fuel Type Code Reference:
```
C-1 to C-7: Coniferous
D-1, D-2:   Deciduous
M-1, M-2:   Mixedwood
S-1, S-2:   Slash
O-1a, O-1b: Grass/Open
99:         Water/Non-fuel
```

---

## Verification

After downloading and processing each layer, verify using the web map:

1. Start the development server:
   ```bash
   python web/server.py
   ```

2. Open in browser: http://localhost:8000

3. Toggle each layer in the sidebar:
   - **First Nations Reserves** - Should show 7 orange polygons
   - **Fire Perimeters** - Should show red fire boundaries
   - **Wildland Fuel Classification** - Should show color-coded fuel types

4. Click on features to verify popup information

---

## Troubleshooting

### File Not Found Errors
- Verify file path matches exactly (case-sensitive)
- Ensure file is in correct directory under `data/processed/`
- Check file extension (.geojson or .tif)

### Projection Issues
- All web map layers must be in WGS84 (EPSG:4326)
- Use QGIS or Python to reproject if needed
- Check CRS with: `gdalinfo file.tif` or in QGIS

### Large File Sizes
- GeoJSON files should be < 10 MB for web performance
- Simplify geometries if needed (using `mapshaper` or QGIS)
- For rasters, reduce resolution if > 50 MB

### Missing Attributes
- Check field names in downloaded data
- Update popup code in `web/js/map.js` if field names differ
- Common variations: RESERVE_NAME vs NAME, YEAR vs FIRE_YEAR

---

## Support

For questions or issues:
1. Check dataset documentation on source portal
2. Review error messages in browser console (F12)
3. Verify file format and projection with QGIS or `ogrinfo`/`gdalinfo`

---

## Quick Reference

| Layer | File Path | Format | Required Fields |
|-------|-----------|--------|-----------------|
| Reserve Boundaries | `data/processed/communities/williams_treaty_reserves.geojson` | GeoJSON | RESERVE_NAME, BAND_NAME, AREA_SQKM |
| Fire Perimeters | `data/processed/fire/fire_perimeters_2010_2024.geojson` | GeoJSON | YEAR, FIRE_ID, area |
| Fuel Types | `data/processed/fuel/fuel_types.tif` | GeoTIFF | Single band with fuel codes |
