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
├── scripts/                 # Data download and processing scripts
│   ├── utils/              # Common utilities
│   ├── 01_download_aoi.py
│   ├── 02_download_landcover.py
│   ├── 03_process_ndvi.py
│   ├── 04_download_fire_data.py
│   ├── 05_download_flood_data.py
│   └── run_all.py          # Run complete pipeline
├── data/
│   ├── boundaries/         # Study area boundaries
│   ├── raw/               # Downloaded raw data
│   └── processed/         # Processed data ready for mapping
└── docs/
    ├── DATASETS.md        # Dataset documentation
    └── DATA_PIPELINE.md   # Pipeline usage guide
```

## Project Status

🚧 **In Development** - Data pipeline complete, map interface in progress

**Completed:**
- ✅ Dataset identification and documentation
- ✅ Data download scripts for all focus areas
- ✅ NDVI processing pipeline
- ✅ AOI boundary definition
- ✅ Configuration and utilities

**Next Steps:**
- 🔲 Build interactive map interface
- 🔲 Implement layer controls and visualization
- 🔲 Add time-series analysis tools
- 🔲 Deploy web application

## License

Project code: TBD
Data sources: Various open licenses (see DATASETS.md for details)

## Contact

For questions about this project or collaboration opportunities, please open an issue.
