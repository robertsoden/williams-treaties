# Data Download and Processing Pipeline

This guide explains how to download and process environmental datasets for the Williams Treaty Territories interactive map.

## Quick Start

### 1. Install Dependencies

```bash
# Create virtual environment (recommended)
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install required packages
pip install -r requirements.txt
```

### 2. Run the Complete Pipeline

```bash
# Run all steps (with example NDVI data)
python scripts/run_all.py --ndvi-example

# Or run individual scripts
python scripts/01_download_aoi.py
python scripts/02_download_landcover.py
python scripts/03_process_ndvi.py --example
python scripts/04_download_fire_data.py
```

---

## Individual Scripts

### Script 1: Define Area of Interest (AOI)

```bash
python scripts/01_download_aoi.py
```

**What it does:**
- Creates a bounding box for the Williams Treaty Territories
- Covers area from Lake Simcoe to Peterborough/Kawartha Lakes region
- Saves boundary as GeoJSON in both geographic (WGS84) and projected (UTM) coordinates

**Output:**
- `data/boundaries/williams_treaty_aoi.geojson` - Geographic coordinates
- `data/boundaries/williams_treaty_aoi_utm.geojson` - UTM Zone 17N

**Note:** This is a starting point. To use actual First Nations boundaries:
1. Download from Statistics Canada: https://www12.statcan.gc.ca/census-recensement/2021/geo/sip-pis/boundary-limites/index-eng.cfm
2. Look for "Indigenous geography" datasets
3. Filter for the seven Williams Treaty First Nations

---

### Script 2: Download Land Cover Data

```bash
# Download most recent year (2020)
python scripts/02_download_landcover.py

# Download specific year
python scripts/02_download_landcover.py --year 2015

# Download all available years
python scripts/02_download_landcover.py --all
```

**What it does:**
- Downloads Natural Resources Canada Land Cover data (2010, 2015, 2020)
- Provides information for Agriculture Canada Annual Crop Inventory
- Clips data to Williams Treaty AOI

**Data Sources:**
- **NRCan Land Cover:** 30m resolution, 15 land cover classes
  - URL: https://open.canada.ca/data/en/dataset/4e615eae-b90c-420b-adee-2ca35896caf6
- **AAFC Crop Inventory:** 30m resolution, annual crop types
  - URL: https://open.canada.ca/data/en/dataset/ba2645d5-4458-414d-b196-6303ac06c1c9

**Output:**
- `data/raw/landcover/landcover_YEAR.zip` - Downloaded archives
- Processing information and instructions

**Manual Steps Required:**
1. Large files (several GB) will be downloaded
2. Extract .tif files from archives
3. Files will be automatically clipped to AOI

---

### Script 3: Process NDVI (Vegetation Indices)

```bash
# Create example NDVI data for testing
python scripts/03_process_ndvi.py --example

# Process real Sentinel-2 imagery (requires Planetary Computer access)
python scripts/03_process_ndvi.py --satellite sentinel2 --start-date 2024-01-01 --end-date 2024-12-31

# Process Landsat imagery
python scripts/03_process_ndvi.py --satellite landsat --start-date 2020-01-01
```

**What it does:**
- Accesses satellite imagery (Sentinel-2 or Landsat)
- Calculates NDVI: (NIR - Red) / (NIR + Red)
- Creates monthly composites
- Filters by cloud cover (<20% by default)
- Clips to AOI

**Data Sources:**
- **Sentinel-2:** 10m resolution, 5-day revisit (recommended)
- **Landsat 8/9:** 30m resolution, 16-day revisit
- Access via Microsoft Planetary Computer (free)

**Output:**
- `data/processed/ndvi/ndvi_YYYY-MM_composite.tif` - Monthly NDVI composites
- Individual scene files
- Example/synthetic data for testing

**Requirements:**
```bash
pip install pystac-client planetary-computer
```

**NDVI Interpretation:**
- < 0: Water, snow, clouds
- 0-0.2: Bare soil, rock, sand
- 0.2-0.4: Sparse vegetation, stressed vegetation
- 0.4-0.6: Moderate vegetation
- 0.6-0.8: Dense vegetation, healthy forests
- > 0.8: Very dense vegetation

---

### Script 4: Download Fire Hazard Data

```bash
# Download with 30 years of historical data (default)
python scripts/04_download_fire_data.py

# Specify different time period
python scripts/04_download_fire_data.py --historical-years 20
```

**What it does:**
- Provides access information for Canadian Wildland Fire Information System (CWFIS)
- Documents Ontario historical fire occurrence data sources
- Provides National Burned Area Composite (NBAC) download instructions
- Saves WMS/WFS connection details for real-time fire danger

**Data Sources:**

1. **CWFIS (Real-time Fire Danger)**
   - URL: https://cwfis.cfs.nrcan.gc.ca/
   - WMS/WFS services available
   - Daily fire weather indices (FWI, ISI, BUI)

2. **Ontario Historical Fires**
   - Source: Ontario Ministry of Natural Resources
   - Portal: https://geohub.lio.gov.on.ca/
   - Datasets: Fire regions, fire points, fire perimeters

3. **National Burned Area Composite**
   - URL: https://opendata.nfis.org/
   - 30m resolution, Landsat-derived
   - Coverage: 1985-present

**Output:**
- `data/raw/fire/cwfis_wms_info.json` - WMS connection details
- `data/raw/fire/ontario_fire_data_info.json` - Ontario data sources
- `data/raw/fire/nbac_info.json` - NBAC download instructions

**Manual Steps Required:**
1. Visit Ontario GeoHub and download historical fire data
2. Download NBAC annual files for your time period
3. Place files in `data/raw/fire/`

---

## Data Directory Structure

After running all scripts, your data directory will look like this:

```
data/
├── boundaries/
│   ├── williams_treaty_aoi.geojson
│   └── williams_treaty_aoi_utm.geojson
├── raw/
│   ├── landcover/
│   │   └── landcover_YYYY.zip
│   ├── fire/
│   │   ├── cwfis_wms_info.json
│   │   ├── ontario_fire_data_info.json
│   │   └── nbac_info.json
│       ├── conservation_authorities_info.json
│       ├── hydrological_network_info.json
│       ├── dem_info.json
│       └── precipitation_climate_info.json
└── processed/
    ├── landcover/
    ├── ndvi/
    │   └── ndvi_YYYY-MM_composite.tif
    ├── fire/
```

---

## Configuration

Edit `config.yaml` to customize:

- **Coordinate systems:** UTM zone, geographic CRS
- **AOI buffer distance:** Expand study area beyond First Nations boundaries
- **NDVI parameters:** Date range, cloud cover threshold, satellite preference
- **Processing settings:** Number of workers, tile size

Example:
```yaml
datasets:
  ndvi:
    date_range:
      start: "2020-01-01"
      end: "2024-12-31"
    max_cloud_cover: 20  # Increase if no imagery found
```

---

## Troubleshooting

### No NDVI imagery found
- Increase cloud cover threshold in `config.yaml`
- Expand date range
- Use `--example` flag to create synthetic data for testing

### Large downloads timing out
- Download files manually and place in appropriate directories
- Increase timeout in `config.yaml`
- Download during off-peak hours

### Missing Python packages
```bash
pip install -r requirements.txt
```

### AOI not found error
Run the AOI creation script first:
```bash
python scripts/01_download_aoi.py
```

---

## Data Licenses

All data sources use open licenses:

- **Federal data:** Open Government License - Canada
- **Ontario data:** Ontario Open Data License
- **Satellite imagery:** Public domain (Landsat) or Free and Open (Sentinel-2)
- **Climate data:** Various open licenses

See [DATASETS.md](./DATASETS.md) for specific license information for each dataset.

---

## Next Steps

After downloading and processing data:

1. **Verify Data:**
   ```bash
   ls -lh data/boundaries/
   ls -lh data/processed/ndvi/
   ```

2. **Build Map Interface:**
   - Create web-based interactive map
   - Add layer controls for each dataset
   - Implement time-series visualization
   - Add analysis tools

3. **Future Enhancements:**
   - Automated updates (cron jobs for CWFIS)
   - Time-series analysis
   - Risk composite indices
   - Community data integration

---

## Support

For issues with:
- **Scripts:** Check error messages, review documentation
- **Data access:** Visit source URLs, contact data providers
- **Satellite imagery:** Check Microsoft Planetary Computer status

See [DATASETS.md](./DATASETS.md) for complete dataset information and URLs.
