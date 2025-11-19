# Williams Treaty Territories - Interactive Map

An interactive web-based map for visualizing environmental and climate data in the Williams Treaty Territories of Ontario, Canada.

## Overview

This project provides a lightweight, browser-based map interface to explore geospatial datasets relevant to climate adaptation planning in Williams Treaty First Nations territories.

**This repository contains ONLY the visualization application.** All data generation is handled by the [ontario-environmental-data](https://github.com/robertsoden/ontario-environmental-data) repository.

## Architecture

```
ontario-environmental-data    → Data generation (scripts, downloads, processing)
williams-treaties             → Data visualization (web app, map interface)
```

## Williams Treaty Territories

The Williams Treaties (1923) were signed by seven First Nations in south-central Ontario:
- Alderville First Nation
- Curve Lake First Nation
- Hiawatha First Nation
- Mississaugas of Scugog Island First Nation
- Chippewas of Beausoleil First Nation
- Chippewas of Georgina Island First Nation
- Chippewas of Rama First Nation

**Project Scope:** This project encompasses **all Indigenous peoples and communities within the Williams Treaty territory boundaries**, not solely the seven treaty signatories. This includes other First Nations with reserves in the area (such as Moose Deer Point First Nation, Wahta Mohawk Territory, Nipissing First Nation, etc.), Métis communities, and all Indigenous peoples living within these territorial boundaries.

The treaty area encompasses parts of:
- Simcoe County
- Durham Region
- City of Kawartha Lakes
- Northumberland County
- Peterborough County

---

## Quick Start

### Option 1: Use Remote Data (Recommended)

```bash
# Install dependencies
pip install flask flask-cors pyyaml

# Run with remote data from GitHub Pages
export DATA_SOURCE_URL="https://robertsoden.io/ontario-environmental-data"
python web/server.py

# Open browser to http://localhost:8000
```

### Option 2: Use Local Data (Development)

```bash
# Clone data repository
cd ..
git clone https://github.com/robertsoden/ontario-environmental-data.git

# Generate data (see ontario-environmental-data README)
cd ontario-environmental-data
pip install -e ".[geo]"
python scripts/run_all.py

# Link data to williams-treaties
cd ../williams-treaties
ln -s ../ontario-environmental-data/data data

# Run server with local data
python web/server.py

# Open browser to http://localhost:8000
```

---

## Map Layers

The application visualizes 12+ environmental datasets:

### Boundaries & Communities
- Williams Treaty Territories boundary
- First Nations reserve boundaries
- Community locations

### Environmental Data
- **Fire Data**: Historical fire perimeters (1976-2024), fuel type classifications
- **Elevation**: Digital Elevation Model (DEM) at 2m resolution
- **Vegetation**: NDVI vegetation health indices
- **Land Cover**: NRCan land cover classifications

### Community Data
- Environmental organizations and charities
- Drinking water advisories
- Infrastructure projects
- Community Well-Being (CWB) scores
- Cultural infrastructure funding (CSICP)

---

## Configuration

### Data Sources

Configure where the application loads data from:

**`web/config/data_source.yaml`:**
```yaml
data_source:
  mode: local  # local | remote | hybrid
  remote_url: "https://robertsoden.io/ontario-environmental-data"
  fallback_priority: ["local", "remote"]
```

**Environment Variable (Production):**
```bash
export DATA_SOURCE_URL="https://robertsoden.io/ontario-environmental-data"
export DATA_MODE="remote"
```

### Layer Configuration

All map layers are configured in `web/config/layers.yaml`:

```yaml
layers:
  - id: fire
    name: Fire Perimeters
    category: fire
    type: polygon
    data_url: /data/processed/fire/fire_perimeters_1976_2024.geojson

    # Per-layer data source override
    data_source:
      source_info:
        provider: "Canadian Wildland Fire Information System"
        update_frequency: "Annual"

    style:
      fill:
        color: '#d73027'

    popup:
      title_field: fire_name
      fields:
        - label: Year
          field: year
        - label: Area
          field: area_ha
```

See [web/config/README.md](web/config/README.md) for complete layer configuration documentation.

---

## Features

### Interactive Map
- Full-screen map with Mapbox basemaps
- Layer toggle controls with categories
- Custom styling for each layer type
- Data-driven symbology (choropleth, conditional colors)

### Data Visualization
- **Point layers**: Environmental organizations, communities
- **Polygon layers**: Boundaries, fire perimeters, well-being data
- **Raster layers**: Elevation (DEM), vegetation (NDVI), fuel types

### Popups & Legends
- Click features for detailed information
- Custom popup fields per layer
- Dynamic legends for raster and categorical data

### YAML-Based Configuration
- All layers defined in YAML (no code changes needed)
- Per-layer styling, popups, legends
- Per-layer data source overrides
- Easy to add/modify layers

---

## Development

### Project Structure

```
williams-treaties/
├── web/                          # Web application
│   ├── index.html               # Main map interface
│   ├── map.js                   # Map logic
│   ├── styles.css               # Styling
│   ├── layers.html              # Layer info page
│   ├── server.py                # Flask server
│   └── config/
│       ├── data_source.yaml     # Data source config
│       ├── layers.yaml          # Layer definitions
│       └── README.md            # Config documentation
├── data/                         # Data files (symlink or gitignored)
└── README.md                     # This file
```

### Running the Server

```bash
# Basic usage
python web/server.py

# Custom port
python web/server.py --port 3000

# Debug mode
python web/server.py --debug

# With environment variables
export DATA_SOURCE_URL="https://example.com/data"
python web/server.py
```

### API Endpoints

- `GET /` - Main map application
- `GET /layers` - Layer information page
- `GET /api/info` - Application metadata
- `GET /api/data-source` - Current data source configuration
- `GET /api/layer-config` - Layer definitions (from layers.yaml)
- `GET /api/layers` - Available data layers
- `GET /data/<filepath>` - Data files (redirects or serves local)

---

## Data Generation

**All data generation happens in the [ontario-environmental-data](https://github.com/robertsoden/ontario-environmental-data) repository.**

To generate or update data:

```bash
# Clone data repository
git clone https://github.com/robertsoden/ontario-environmental-data.git
cd ontario-environmental-data

# Install dependencies
pip install -e ".[geo]"

# Generate all datasets
python scripts/run_all.py

# Generated files appear in data/
```

See the [ontario-environmental-data README](https://github.com/robertsoden/ontario-environmental-data#readme) for complete data generation documentation.

---

## Deployment

### Render.com

The `render.yaml` file provides one-click deployment:

1. Connect your GitHub repository to Render
2. Render automatically detects `render.yaml`
3. Set environment variable: `DATA_SOURCE_URL=https://robertsoden.io/ontario-environmental-data`
4. Deploy

### Other Platforms

For Heroku, Railway, Fly.io, etc.:

```bash
# Set environment variable
DATA_SOURCE_URL=https://robertsoden.io/ontario-environmental-data

# Install dependencies
pip install -r requirements.txt

# Run server
python web/server.py
```

---

## Cultural Sensitivity

When working with Indigenous data:

✅ Follow OCAP® principles (Ownership, Control, Access, Possession)
✅ Respect data sovereignty
✅ Include proper attribution
✅ Obtain permission for sensitive data
✅ Use respectful terminology

---

## Related Projects

- **ontario-environmental-data**: https://github.com/robertsoden/ontario-environmental-data - Data generation and API library
- **Ontario Nature Watch**: https://github.com/robertsoden/onw - LLM agent for environmental queries

---

## License

MIT License - see LICENSE file for details.

## Contact

- **Issues**: https://github.com/robertsoden/williams-treaties/issues
- **Email**: robertsoden@users.noreply.github.com

---

## Attribution

### Data Sources

- **Natural Resources Canada**: Land cover, DEM, fire data
- **Canadian Wildland Fire Information System (CWFIS)**: Fire perimeters and fuel types
- **Indigenous Services Canada**: Water advisories
- **Infrastructure Canada**: Project data
- **Statistics Canada**: Census data, boundaries, Community Well-Being Index

### Acknowledgments

- Williams Treaty First Nations
- Ontario conservation authorities
- Ontario Ministry of Natural Resources and Forestry
- Environment and Climate Change Canada
