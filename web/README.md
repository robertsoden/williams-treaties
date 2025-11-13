# Williams Treaty Territories - Web Map Application

A lightweight, full-screen interactive map browser for exploring environmental data in the Williams Treaty Territories.

## Features

- 🗺️ **Full-screen map interface** with MapLibre GL JS
- 🎨 **Multiple basemaps** - Streets, Satellite, Outdoors, Dark (Mapbox styles)
- 🔄 **Layer controls** - Toggle layers on/off
- 📊 **NDVI visualization** - Vegetation health with color-coded legend
- 🎯 **Study area boundary** - Williams Treaty Territories AOI
- 📱 **Responsive design** - Works on desktop and mobile

## Quick Start

### 1. Install Dependencies

```bash
# Install Flask and CORS support
pip install flask flask-cors
```

### 2. Configure Mapbox Token (Optional but Recommended)

The map works without a Mapbox token (using free OpenStreetMap tiles), but for the best experience with Mapbox basemaps:

1. Get a free Mapbox access token at https://account.mapbox.com/
2. Open `web/js/map.js`
3. Replace `YOUR_MAPBOX_TOKEN_HERE` with your token:

```javascript
const CONFIG = {
    MAPBOX_TOKEN: 'pk.your_actual_token_here',
    // ... rest of config
};
```

### 3. Start the Server

```bash
# From the project root
python web/server.py

# Or specify a custom port
python web/server.py --port 8080
```

### 4. Open in Browser

Navigate to: **http://localhost:8000**

## Available Data Layers

### ✅ Currently Available

- **Study Area (AOI)** - Williams Treaty Territories boundary
- **NDVI** - Vegetation health index (example data: June 2024)

### 🔲 Requires Manual Download

- **Fire Risk Zones** - See `data/raw/fire/*.json` for download instructions
- **Flood Plains** - See `data/raw/flood/*.json` for download instructions

## Map Controls

### Layer Panel (Right Side)

- **Base Layers**: Switch between Streets, Satellite, Outdoors, and Dark basemaps
- **Boundaries**: Toggle study area boundary
- **Vegetation**: Toggle NDVI layer and view legend
- **Fire Hazard**: (Disabled until data is downloaded)
- **Flood Hazard**: (Disabled until data is downloaded)

### Map Navigation

- **Zoom**: Mouse wheel, +/- buttons, or pinch gesture
- **Pan**: Click and drag
- **Rotate**: Right-click and drag (or Ctrl+drag)
- **Tilt**: Ctrl+drag

## API Endpoints

The server provides REST API endpoints for programmatic access:

- `GET /` - Main application
- `GET /api/info` - Application information
- `GET /api/layers` - List of available data layers
- `GET /data/{filepath}` - Access data files (GeoJSON, GeoTIFF, etc.)

## File Structure

```
web/
├── index.html          # Main HTML file
├── css/
│   └── style.css       # Styles and layout
├── js/
│   └── map.js          # Map initialization and controls
├── server.py           # Flask web server
└── README.md           # This file
```

## Adding More Data Layers

### To add a GeoJSON layer:

1. Place your GeoJSON file in `data/` directory
2. Update `map.js` to load and display the layer
3. Add a checkbox to the layer control panel in `index.html`

### To add a GeoTIFF layer:

1. Place your GeoTIFF file in `data/processed/` directory
2. Use the GeoRaster library (already included) to load it
3. Define a color scale function for visualization
4. Add a checkbox and legend to the layer control panel

## Customization

### Change Map Center/Zoom

Edit `web/js/map.js`:

```javascript
const CONFIG = {
    CENTER: [-79.05, 44.3],  // [longitude, latitude]
    ZOOM: 9,                  // Initial zoom level
    // ...
};
```

### Modify Color Schemes

For NDVI or other rasters, edit the `colorScale` function in `map.js`:

```javascript
const colorScale = (value) => {
    if (value < 0.3) return [255, 0, 0, 180];     // Red
    if (value < 0.5) return [255, 255, 0, 180];   // Yellow
    return [0, 255, 0, 180];                      // Green
};
```

### Styling

All visual styles are in `web/css/style.css`. Key sections:

- `#map` - Map container
- `#layer-control` - Side panel
- `.layer-item` - Individual layer controls
- `.legend-bar` - Color gradient for NDVI

## Troubleshooting

### Map doesn't load

- Check browser console for errors (F12)
- Ensure server is running: `python web/server.py`
- Verify port is not in use by another application

### Basemaps not working

- Make sure you've set a valid Mapbox token in `map.js`
- Or accept using the free OpenStreetMap basemap

### NDVI layer not visible

- Check that `data/processed/ndvi/ndvi_example_2024-06.tif` exists
- Run the NDVI processing script: `python scripts/03_process_ndvi.py --example`
- Check browser console for loading errors

### Data not loading

- Verify the data files exist in the `data/` directory
- Check file permissions
- Look for CORS errors in browser console

## Browser Support

- Chrome/Edge: ✅ Full support
- Firefox: ✅ Full support
- Safari: ✅ Full support
- Mobile browsers: ✅ Full support

## Performance Tips

- Large GeoTIFF files may take time to load - consider creating tiles for better performance
- Use appropriate zoom levels for raster data
- Reduce layer opacity for better visualization of overlapping data

## License

See main project LICENSE file.

## Support

For issues or questions:
1. Check browser console for errors
2. Review the main project documentation
3. Ensure all dependencies are installed
4. Verify data files exist and are accessible
