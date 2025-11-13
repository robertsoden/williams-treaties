# Williams Treaty Territories - Environmental Datasets

## Project Focus
Interactive map browser for environmental planning and climate change adaptation focused on:
- Land use and land cover
- NDVI (vegetation health monitoring)
- Fire hazard assessment
- Flood hazard mapping

## Geographic Scope
Williams Treaty Territories (1923) - covers parts of:
- Simcoe County
- Durham Region
- City of Kawartha Lakes
- Northumberland County
- Peterborough County

First Nations: Alderville, Curve Lake, Hiawatha, Mississaugas of Scugog Island, Chippewas of Beausoleil, Chippewas of Georgina Island, and Chippewas of Rama

---

## 1. Land Use and Land Cover

### Annual Crop Inventory (AAFC)
- **Source**: Agriculture and Agri-Food Canada
- **URL**: https://open.canada.ca/data/en/dataset/ba2645d5-4458-414d-b196-6303ac06c1c9
- **Format**: GeoTIFF, 30m resolution
- **Coverage**: Annual updates, Canada-wide
- **Use Case**: Agricultural land classification, crop types
- **License**: Open Government License - Canada

### Land Cover of Canada (Natural Resources Canada)
- **Source**: Natural Resources Canada
- **URL**: https://open.canada.ca/data/en/dataset/4e615eae-b90c-420b-adee-2ca35896caf6
- **Format**: GeoTIFF, 30m resolution
- **Years**: 2010, 2015, 2020
- **Classes**: 15 land cover classes (forest, wetland, urban, etc.)
- **License**: Open Government License - Canada

### Ontario Land Cover Compilation (OLCC)
- **Source**: Ontario Ministry of Natural Resources
- **URL**: https://geohub.lio.gov.on.ca/
- **Format**: Vector/Raster
- **Resolution**: Various
- **Use Case**: Provincial land cover baseline
- **License**: Ontario Open Data License

---

## 2. NDVI (Vegetation Health)

### Landsat 8/9 (USGS/NASA)
- **Source**: USGS Earth Explorer / Google Earth Engine
- **URL**: https://earthexplorer.usgs.gov/
- **Resolution**: 30m (multispectral)
- **Frequency**: 16-day revisit
- **Bands**: Band 4 (Red), Band 5 (NIR) for NDVI calculation
- **License**: Public Domain
- **NDVI Formula**: (NIR - Red) / (NIR + Red)

### Sentinel-2 (ESA/Copernicus)
- **Source**: Copernicus Open Access Hub / Google Earth Engine
- **URL**: https://scihub.copernicus.eu/
- **Resolution**: 10m (multispectral)
- **Frequency**: 5-day revisit (2 satellites)
- **Bands**: Band 4 (Red 665nm), Band 8 (NIR 842nm)
- **License**: Free and Open (Copernicus)
- **Advantage**: Higher resolution and frequency than Landsat

### MODIS Vegetation Indices (NASA)
- **Source**: NASA EOSDIS
- **Product**: MOD13Q1 (16-day composite)
- **Resolution**: 250m
- **URL**: https://lpdaac.usgs.gov/products/mod13q1v006/
- **Use Case**: Long-term vegetation trends, seasonal monitoring
- **License**: Public Domain

---

## 3. Fire Hazard Data

### Canadian Wildland Fire Information System (CWFIS)
- **Source**: Natural Resources Canada
- **URL**: https://cwfis.cfs.nrcan.gc.ca/
- **Data Types**:
  - Fire Weather Index (FWI)
  - Daily fire danger ratings
  - Historical fire perimeters
- **Format**: Various (WMS, data downloads)
- **License**: Open Government License - Canada

### Ontario Fire Regions and Historical Fires
- **Source**: Ontario Ministry of Natural Resources and Forestry
- **URL**: https://geohub.lio.gov.on.ca/
- **Datasets**:
  - Fire region boundaries
  - Historical fire occurrence points
  - Fire intensity zones
- **License**: Ontario Open Data License

### National Burned Area Composite (NBAC)
- **Source**: Natural Resources Canada
- **URL**: https://opendata.nfis.org/
- **Coverage**: 1985-present
- **Resolution**: 30m (derived from Landsat)
- **Format**: GeoTIFF
- **Use Case**: Historical fire patterns and severity
- **License**: Open Government License - Canada

### Wildfire Risk Assessment Factors
- **Fuel Type Mapping**: From Canadian Forest Service
- **Topographic Data**: Canadian Digital Elevation Model (CDEM)
- **Climate Data**: Historical temperature, precipitation, drought indices

---

## 4. Flood Hazard Data

### Ontario Flood Plain Mapping
- **Source**: Ontario Ministry of Natural Resources and Forestry
- **URL**: https://geohub.lio.gov.on.ca/
- **Coverage**: Various Conservation Authorities
- **Data Types**:
  - 100-year flood lines
  - Regulatory flood plains
  - Flood vulnerable areas
- **License**: Ontario Open Data License

### Conservation Authority Data
Relevant authorities for Williams Treaty area:
- **Kawartha Conservation**: Flood mapping, watershed boundaries
- **Otonabee Region Conservation Authority**: Flood risk areas
- **Lake Simcoe Region Conservation Authority**: Flood plains
- **Central Lake Ontario Conservation Authority**: Coastal flooding
- **Ganaraska Region Conservation Authority**: Watershed data

### Digital Elevation Model (DEM)
- **Source**: Natural Resources Canada
- **Product**: Canadian Digital Elevation Model (CDEM)
- **URL**: https://open.canada.ca/data/en/dataset/7f245e4d-76c2-4caa-951a-45d1d2051333
- **Resolution**: 20m (best available for Ontario)
- **Use Case**: Slope analysis, flow accumulation, flood modeling
- **License**: Open Government License - Canada

### Provincial (Stream) Network (PSN)
- **Source**: Ontario Ministry of Natural Resources
- **URL**: https://geohub.lio.gov.on.ca/
- **Format**: Vector (lines)
- **Use Case**: Stream networks, watershed delineation
- **License**: Ontario Open Data License

### Climate Normals and Precipitation Data
- **Source**: Environment and Climate Change Canada
- **URL**: https://climate.weather.gc.ca/
- **Data Types**:
  - Historical precipitation
  - Climate normals (1981-2010, 1991-2020)
  - Extreme weather events
- **Use Case**: Flood risk modeling, climate trends
- **License**: Environment Canada Data License

---

## 5. Supporting Base Layers

### First Nations Boundaries
- **Source**: Indigenous Services Canada / Statistics Canada
- **URL**: https://open.canada.ca/data/en/dataset/b6567c5c-8339-4055-99fa-63f92114d9e4
- **Format**: Vector (polygons)
- **License**: Open Government License - Canada

### Administrative Boundaries
- **Source**: Statistics Canada
- **Products**:
  - Census boundaries (provinces, municipalities)
  - Census subdivisions
- **URL**: https://www12.statcan.gc.ca/census-recensement/2021/geo/sip-pis/boundary-limites/index-eng.cfm
- **License**: Statistics Canada Open License

### Ontario Hydro Network (OHN)
- **Source**: Ontario Ministry of Natural Resources
- **URL**: https://geohub.lio.gov.on.ca/
- **Coverage**: Lakes, rivers, watercourses
- **License**: Ontario Open Data License

---

## 6. Climate Change Projections

### Climate Atlas of Canada
- **Source**: Prairie Climate Centre
- **URL**: https://climateatlas.ca/
- **Data Types**:
  - Temperature projections
  - Precipitation changes
  - Growing season length
  - Climate indices
- **Scenarios**: RCP 4.5, RCP 8.5
- **License**: Creative Commons

### ClimateData.ca
- **Source**: Environment and Climate Change Canada
- **URL**: https://climatedata.ca/
- **Data**: Downscaled climate projections for Canada
- **Variables**: Temperature, precipitation, drought indices
- **License**: Government of Canada Open License

---

## Data Access Methods

### Priority Approach:
1. **Google Earth Engine (GEE)**: For NDVI and satellite imagery processing
2. **Ontario GeoHub**: Direct download for provincial datasets
3. **Open Canada Portal**: Federal datasets
4. **WMS/WFS Services**: For real-time or frequently updated data

### Technical Stack Considerations:
- **Frontend**: Leaflet or MapLibre GL JS for interactive mapping
- **Backend**: Python (GeoPandas, Rasterio) or Node.js for data processing
- **Tile Server**: For serving raster data efficiently
- **Data Storage**: GeoTIFF for rasters, GeoJSON/PostGIS for vectors

---

## Next Steps

1. Set up data download and preprocessing pipeline
2. Define area of interest (Williams Treaty boundaries)
3. Create base map with administrative boundaries
4. Add layered datasets with interactive controls
5. Implement basic analysis tools (NDVI time series, risk overlays)

---

## Notes

- Most datasets require clipping to Williams Treaty area
- NDVI calculation requires preprocessing of satellite imagery
- Fire and flood risk may need composite indicators from multiple datasets
- Consider temporal resolution for time-series analysis
- Coordinate system: NAD83 / UTM Zone 17N (EPSG:26917) typical for this region
