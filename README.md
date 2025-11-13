# Williams Treaty Territories - Interactive Map Browser

A lightweight interactive map browser for environmental planning and climate change adaptation in the Williams Treaty Territories.

## Overview

This project provides an interactive web-based map interface to explore environmental datasets relevant to climate adaptation planning in the Williams Treaty First Nations territories in Ontario, Canada.

## Focus Areas

1. **Land Use and Land Cover** - Current and historical land classification
2. **NDVI (Vegetation Health)** - Satellite-derived vegetation indices for monitoring ecosystem health
3. **Fire Hazard** - Wildfire risk assessment and historical fire data
4. **Flood Hazard** - Flood plain mapping and flood risk zones

## Williams Treaty Territories

The Williams Treaties (1923) cover territories of seven First Nations in south-central Ontario:
- Alderville First Nation
- Curve Lake First Nation
- Hiawatha First Nation
- Mississaugas of Scugog Island First Nation
- Chippewas of Beausoleil First Nation
- Chippewas of Georgina Island First Nation
- Chippewas of Rama First Nation

The treaty area encompasses parts of:
- Simcoe County
- Durham Region
- City of Kawartha Lakes
- Northumberland County
- Peterborough County

## Getting Started

### 1. Install Dependencies

```bash
# Create virtual environment (recommended)
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install required packages
pip install -r requirements.txt
```

### 2. Download Data

```bash
# Run complete data pipeline
python scripts/run_all.py --ndvi-example

# Or run individual scripts
python scripts/01_download_aoi.py      # Define study area
python scripts/02_download_landcover.py  # Land cover data
python scripts/03_process_ndvi.py --example  # Vegetation indices
python scripts/04_download_fire_data.py    # Fire hazard data
python scripts/05_download_flood_data.py   # Flood hazard data
```

See [DATA_PIPELINE.md](./DATA_PIPELINE.md) for detailed instructions.

### 3. View Data in Interactive Map

```bash
# Quick start - runs server and opens map
./start_map.sh

# Or manually start the server
python web/server.py

# Then open in browser: http://localhost:8000
```

See [web/README.md](./web/README.md) for detailed web application documentation.

**Features:**
- Full-screen interactive map with Mapbox basemaps
- Layer controls to toggle datasets on/off
- NDVI visualization with color-coded legend
- Study area boundary display
- Responsive design for desktop and mobile

## Datasets

See [DATASETS.md](./DATASETS.md) for comprehensive information about data sources, including:
- Open government data sources (Canada, Ontario)
- Satellite imagery (Landsat, Sentinel-2, MODIS)
- Climate and environmental monitoring data
- Conservation authority datasets

## Project Structure

```
williams-treaties/
├── config.yaml              # Configuration settings
├── requirements.txt         # Python dependencies
├── start_map.sh            # Quick start script for web map
├── scripts/                 # Data download and processing scripts
│   ├── utils/              # Common utilities
│   ├── 01_download_aoi.py
│   ├── 02_download_landcover.py
│   ├── 03_process_ndvi.py
│   ├── 04_download_fire_data.py
│   ├── 05_download_flood_data.py
│   └── run_all.py          # Run complete pipeline
├── web/                     # Interactive map application
│   ├── index.html          # Main map interface
│   ├── css/style.css       # Styling
│   ├── js/map.js           # Map logic
│   ├── server.py           # Flask web server
│   └── README.md           # Web app documentation
├── data/
│   ├── boundaries/         # Study area boundaries
│   ├── raw/               # Downloaded raw data
│   └── processed/         # Processed data ready for mapping
└── docs/
    ├── DATASETS.md        # Dataset documentation
    └── DATA_PIPELINE.md   # Pipeline usage guide
```

## Project Status

✅ **Core Features Complete** - Ready for local use and data exploration

**Completed:**
- ✅ Dataset identification and documentation
- ✅ Data download scripts for all focus areas
- ✅ NDVI processing pipeline
- ✅ AOI boundary definition
- ✅ Configuration and utilities
- ✅ Interactive web map interface
- ✅ Layer controls and visualization
- ✅ Full-screen map browser with Mapbox basemaps

**Next Steps:**
- 🔲 Add time-series analysis tools
- 🔲 Implement additional data layers (land cover, fire, flood)
- 🔲 Add data export functionality
- 🔲 Deploy to web hosting (optional)

## License

Project code: TBD
Data sources: Various open licenses (see DATASETS.md for details)

## Contact

For questions about this project or collaboration opportunities, please open an issue.
