# Data Setup Guide

This application has been refactored to use the `ontario-environmental-data` repository as its data source. This separates the application code from the data files, making deployment easier and more flexible.

## Architecture

```
williams-treaties/          # This repository (application)
├── web/                    # Web application
│   ├── config/
│   │   ├── layers.yaml            # Layer configuration
│   │   ├── data_source.yaml       # Data source config (development)
│   │   └── data_source.production.yaml  # Production config
│   └── server.py           # Flask server
└── data/                   # Local data (development only)

ontario-environmental-data/ # Separate data repository
├── boundaries/
├── processed/
└── ...                     # All geospatial data files
```

## Setup Instructions

### For Development (Local Data)

1. **Clone the data repository** (if you want local data):
   ```bash
   # Clone the data repository into a sibling directory
   cd ..
   git clone https://github.com/robertsoden/ontario-environmental-data.git
   cd williams-treaties

   # Create symlink to data (or copy files)
   ln -s ../ontario-environmental-data data
   ```

2. **Or use local data** without cloning:
   - The `data/` directory is already set up with some files
   - By default, `data_source.yaml` has `base_url: ""` (local mode)
   - Server will serve files from local `data/` directory

3. **Run the server**:
   ```bash
   python web/server.py
   ```

### For Production (External Data)

#### Option 1: Environment Variable (Recommended)

Set the `DATA_SOURCE_URL` environment variable:

```bash
# Render.com, Railway, etc.
export DATA_SOURCE_URL="https://robertsoden.github.io/ontario-environmental-data"
python web/server.py
```

#### Option 2: Configuration File

Update `web/config/data_source.yaml`:

```yaml
data_source:
  base_url: "https://robertsoden.github.io/ontario-environmental-data"
```

Or copy the production config:

```bash
cp web/config/data_source.production.yaml web/config/data_source.yaml
```

## Data Source Options

### GitHub Pages (Recommended for Production)

**URL:** `https://robertsoden.github.io/ontario-environmental-data`

**Pros:**
- Free CDN delivery
- Fast and reliable
- Automatic HTTPS

**Setup:**
1. Enable GitHub Pages on the `ontario-environmental-data` repository
2. Go to Settings → Pages
3. Set source to "main" branch and "/ (root)"
4. Wait 1-2 minutes for deployment

### raw.githubusercontent.com

**URL:** `https://raw.githubusercontent.com/robertsoden/ontario-environmental-data/main`

**Pros:**
- No setup required
- Works immediately

**Cons:**
- Rate limited (60 requests/hour for unauthenticated)
- Slower than GitHub Pages
- No CDN

**Use for:** Quick testing only

### Local Development

**URL:** `""` (empty string)

**Pros:**
- No network required
- Fast
- Easy debugging

**Cons:**
- Requires cloning data repository
- Data files not automatically updated

## Configuration Reference

### data_source.yaml

```yaml
data_source:
  base_url: ""  # URL or empty for local
  fallback_to_local: true  # Fallback if external fails

cache:
  enabled: true
  max_age_seconds: 3600

use_env_override: true  # Allow ENV var to override
env_var_name: "DATA_SOURCE_URL"
```

### Environment Variables

- `DATA_SOURCE_URL` - Overrides `base_url` in config file
- Set this on your hosting platform (Render, Railway, etc.)

## Testing Different Data Sources

### Test with local data:
```bash
python web/server.py
# Visit http://localhost:8000/api/data-source
```

### Test with GitHub Pages:
```bash
export DATA_SOURCE_URL="https://robertsoden.github.io/ontario-environmental-data"
python web/server.py
```

### Test with raw.githubusercontent:
```bash
export DATA_SOURCE_URL="https://raw.githubusercontent.com/robertsoden/ontario-environmental-data/main"
python web/server.py
```

## Deployment Checklist

### For Render.com/Railway/Similar

1. ✅ Set environment variable `DATA_SOURCE_URL`
2. ✅ Ensure ontario-environmental-data has GitHub Pages enabled
3. ✅ Remove `/data` directory from deployment (it's gitignored)
4. ✅ Deploy and test `/api/data-source` endpoint

### For Static Hosting (Netlify/Vercel)

1. ✅ Build as static site
2. ✅ Data automatically loaded from external repository
3. ✅ Set `DATA_SOURCE_URL` in build environment
4. ✅ No server needed - direct client-side data loading

## Troubleshooting

### "File not found" errors

1. Check data source config:
   ```bash
   curl http://localhost:8000/api/data-source
   ```

2. Verify external URL is accessible:
   ```bash
   curl https://robertsoden.github.io/ontario-environmental-data/boundaries/williams_treaty.geojson
   ```

3. Check server logs for redirect URLs

### CORS errors

- GitHub Pages supports CORS by default
- raw.githubusercontent.com has CORS restrictions
- Use GitHub Pages for production

### Data not updating

1. GitHub Pages cache: Wait 1-2 minutes after pushing
2. Browser cache: Hard refresh (Ctrl+Shift+R)
3. Check `max_age_seconds` in config

## File Structure in ontario-environmental-data

Expected structure:
```
ontario-environmental-data/
├── boundaries/
│   ├── williams_treaty.geojson
│   └── ...
├── processed/
│   ├── communities/
│   ├── fire/
│   ├── ndvi/
│   └── ...
└── README.md
```

Files are referenced in `web/config/layers.yaml` using paths like:
- `/data/boundaries/williams_treaty.geojson`
- `/data/processed/fire/fire_perimeters_1976_2024.geojson`

The server automatically redirects these to the external repository when `base_url` is set.
