// Williams Treaty Territories - Map Application

// Configuration
const CONFIG = {
    // You'll need your own Mapbox access token
    // Get one free at https://account.mapbox.com/
    // Or create web/js/config.js with your token (see config.example.js)
    MAPBOX_TOKEN: (window.MAP_CONFIG && window.MAP_CONFIG.MAPBOX_TOKEN) || 'YOUR_MAPBOX_TOKEN_HERE',

    // Initial map view centered on Williams Treaty area
    CENTER: (window.MAP_CONFIG && window.MAP_CONFIG.CENTER) || [-79.05, 44.3],
    ZOOM: (window.MAP_CONFIG && window.MAP_CONFIG.ZOOM) || 9,

    // Data endpoints (served by local server)
    DATA_URLS: {
        aoi: '/data/boundaries/williams_treaty_aoi.geojson',
        ndvi: '/data/processed/ndvi/ndvi_example_2024-06.tif'
    },

    // Basemap styles (MapLibre requires full HTTPS URLs, not mapbox:// protocol)
    BASEMAPS: {
        streets: 'https://api.mapbox.com/styles/v1/mapbox/streets-v12',
        satellite: 'https://api.mapbox.com/styles/v1/mapbox/satellite-streets-v12',
        outdoors: 'https://api.mapbox.com/styles/v1/mapbox/outdoors-v12',
        dark: 'https://api.mapbox.com/styles/v1/mapbox/dark-v11'
    }
};

// Check if Mapbox token is configured
if (CONFIG.MAPBOX_TOKEN === 'YOUR_MAPBOX_TOKEN_HERE') {
    console.warn('⚠️ Mapbox token not configured. Using free OSM style instead.');
    console.log('To use Mapbox styles, get a free token at https://account.mapbox.com/');
}

// Free OpenStreetMap style (fallback when no Mapbox token)
const FREE_OSM_STYLE = {
    version: 8,
    sources: {
        osm: {
            type: 'raster',
            tiles: ['https://a.tile.openstreetmap.org/{z}/{x}/{y}.png'],
            tileSize: 256,
            attribution: '&copy; OpenStreetMap Contributors',
            maxzoom: 19
        }
    },
    layers: [
        {
            id: 'osm',
            type: 'raster',
            source: 'osm',
            minzoom: 0,
            maxzoom: 22
        }
    ]
};

// Initialize the map
const map = new maplibregl.Map({
    container: 'map',
    // Use Mapbox if token configured, otherwise fallback to OSM
    style: CONFIG.MAPBOX_TOKEN !== 'YOUR_MAPBOX_TOKEN_HERE'
        ? CONFIG.BASEMAPS.streets  // Don't add token here - transformRequest will handle it
        : FREE_OSM_STYLE,
    center: CONFIG.CENTER,
    zoom: CONFIG.ZOOM,
    transformRequest: (url, resourceType) => {
        // Add Mapbox token to all Mapbox API requests if configured
        if (CONFIG.MAPBOX_TOKEN !== 'YOUR_MAPBOX_TOKEN_HERE' && url.includes('mapbox.com')) {
            // Check if token is already in the URL to avoid duplicates
            if (!url.includes('access_token=')) {
                const separator = url.includes('?') ? '&' : '?';
                return {
                    url: `${url}${separator}access_token=${CONFIG.MAPBOX_TOKEN}`
                };
            }
        }
        return { url };
    }
});

// Add navigation controls
map.addControl(new maplibregl.NavigationControl(), 'top-left');

// Add scale control
map.addControl(new maplibregl.ScaleControl(), 'bottom-left');

// Log map initialization
console.log('Map object created');
console.log('Map center:', CONFIG.CENTER);
console.log('Map zoom:', CONFIG.ZOOM);

// Layer state
const layerState = {
    aoi: true,
    ndvi: false,
    fire: false,
    flood: false
};

// Show loading indicator
function showLoading() {
    document.getElementById('loading').style.display = 'block';
}

// Hide loading indicator
function hideLoading() {
    document.getElementById('loading').style.display = 'none';
}

// Load AOI boundary
async function loadAOI() {
    try {
        const response = await fetch(CONFIG.DATA_URLS.aoi);
        const geojson = await response.json();

        map.addSource('aoi', {
            type: 'geojson',
            data: geojson
        });

        // Add fill layer
        map.addLayer({
            id: 'aoi-fill',
            type: 'fill',
            source: 'aoi',
            paint: {
                'fill-color': '#2c5f2d',
                'fill-opacity': 0.1
            }
        });

        // Add outline layer
        map.addLayer({
            id: 'aoi-outline',
            type: 'line',
            source: 'aoi',
            paint: {
                'line-color': '#2c5f2d',
                'line-width': 3,
                'line-opacity': 0.8
            }
        });

        // Fit map to AOI bounds
        const bounds = new maplibregl.LngLatBounds();
        geojson.features.forEach(feature => {
            if (feature.geometry.type === 'Polygon') {
                feature.geometry.coordinates[0].forEach(coord => {
                    bounds.extend(coord);
                });
            }
        });
        map.fitBounds(bounds, { padding: 50 });

        // Add click handler for popup
        map.on('click', 'aoi-fill', (e) => {
            const properties = e.features[0].properties;
            new maplibregl.Popup()
                .setLngLat(e.lngLat)
                .setHTML(`
                    <h4>${properties.name || 'Williams Treaty Territories'}</h4>
                    <p><strong>Description:</strong> ${properties.description || 'Study area for environmental planning and climate adaptation'}</p>
                `)
                .addTo(map);
        });

        // Change cursor on hover
        map.on('mouseenter', 'aoi-fill', () => {
            map.getCanvas().style.cursor = 'pointer';
        });
        map.on('mouseleave', 'aoi-fill', () => {
            map.getCanvas().style.cursor = '';
        });

        console.log('✓ AOI boundary loaded');
    } catch (error) {
        console.error('Error loading AOI:', error);
    }
}

// Create color scale for NDVI (0.2 to 0.8)
function getNDVIColor(value) {
    if (value < 0.2) return [211, 48, 39, 180];      // Red - very low
    if (value < 0.3) return [252, 141, 89, 180];     // Orange-red - low
    if (value < 0.4) return [254, 224, 139, 180];    // Yellow - moderate-low
    if (value < 0.5) return [217, 239, 139, 180];    // Yellow-green - moderate
    if (value < 0.6) return [145, 207, 96, 180];     // Light green - moderate-high
    if (value < 0.7) return [26, 152, 80, 180];      // Green - high
    return [0, 104, 55, 200];                        // Dark green - very high
}

// Custom canvas-based renderer as fallback
async function loadNDVIWithCanvas(georaster) {
    console.log('Using custom canvas renderer for NDVI');

    const canvas = document.createElement('canvas');
    canvas.width = georaster.width;
    canvas.height = georaster.height;
    const ctx = canvas.getContext('2d');
    const imageData = ctx.createImageData(canvas.width, canvas.height);

    // Render each pixel
    for (let y = 0; y < georaster.height; y++) {
        for (let x = 0; x < georaster.width; x++) {
            const value = georaster.values[0][y][x];
            const color = getNDVIColor(value);
            const idx = (y * canvas.width + x) * 4;
            imageData.data[idx] = color[0];     // R
            imageData.data[idx + 1] = color[1]; // G
            imageData.data[idx + 2] = color[2]; // B
            imageData.data[idx + 3] = color[3]; // A
        }
    }

    ctx.putImageData(imageData, 0, 0);

    // Get bounds from georaster
    const bounds = [
        [georaster.xmin, georaster.ymin],
        [georaster.xmax, georaster.ymax]
    ];

    // Add as image source
    map.addSource('ndvi-raster', {
        type: 'image',
        url: canvas.toDataURL(),
        coordinates: [
            [georaster.xmin, georaster.ymax], // top-left
            [georaster.xmax, georaster.ymax], // top-right
            [georaster.xmax, georaster.ymin], // bottom-right
            [georaster.xmin, georaster.ymin]  // bottom-left
        ]
    });

    map.addLayer({
        id: 'ndvi-layer',
        type: 'raster',
        source: 'ndvi-raster',
        paint: {
            'raster-opacity': 0.7
        }
    }, 'aoi-fill');

    return true;
}

// Load NDVI raster
async function loadNDVI() {
    // Check if GeoRaster parser is available (required for both methods)
    if (typeof parseGeoraster === 'undefined') {
        console.error('GeoRaster library not loaded');
        hideLoading();
        alert('NDVI visualization requires GeoRaster library. Please check console for errors.');
        return false;
    }

    try {
        showLoading();
        console.log('Loading NDVI data...');

        const response = await fetch(CONFIG.DATA_URLS.ndvi);
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        const arrayBuffer = await response.arrayBuffer();
        console.log('NDVI file loaded, parsing GeoTIFF...');

        // Parse GeoTIFF
        const georaster = await parseGeoraster(arrayBuffer);
        console.log('GeoTIFF parsed successfully');

        // Try to use GeoRasterLayer if available, otherwise use canvas fallback
        if (typeof GeoRasterLayer !== 'undefined') {
            console.log('Using GeoRasterLayer plugin');

            // Add NDVI layer
            const layer = new GeoRasterLayer({
                georaster: georaster,
                opacity: 0.7,
                pixelValuesToColorFn: values => getNDVIColor(values[0]),
                resolution: 256
            });

            map.addLayer(layer, 'aoi-fill'); // Add below AOI
            map.ndviLayer = layer;

            // Initially hide the layer
            if (map.ndviLayer) {
                map.ndviLayer.options.opacity = 0;
            }
        } else {
            console.warn('⚠️ GeoRasterLayer not available, using canvas fallback');
            await loadNDVIWithCanvas(georaster);
            map.ndviLayerType = 'canvas';
        }

        hideLoading();
        console.log('✓ NDVI raster loaded successfully');

        return true;

    } catch (error) {
        console.error('❌ Error loading NDVI:', error);
        hideLoading();
        alert('Could not load NDVI data. Error: ' + error.message);
        return false;
    }
}

// Toggle layer visibility
function toggleLayer(layerId, visible) {
    layerState[layerId] = visible;

    switch(layerId) {
        case 'aoi':
            map.setLayoutProperty('aoi-fill', 'visibility', visible ? 'visible' : 'none');
            map.setLayoutProperty('aoi-outline', 'visibility', visible ? 'visible' : 'none');
            break;

        case 'ndvi':
            // Handle both GeoRasterLayer plugin and canvas-based rendering
            if (map.ndviLayerType === 'canvas') {
                // Canvas-based layer
                if (map.getLayer('ndvi-layer')) {
                    map.setLayoutProperty('ndvi-layer', 'visibility', visible ? 'visible' : 'none');
                }
            } else if (map.ndviLayer) {
                // GeoRasterLayer plugin
                map.ndviLayer.options.opacity = visible ? 0.7 : 0;
            }
            document.getElementById('ndvi-legend').style.display = visible ? 'block' : 'none';
            break;
    }
}

// Change basemap
function changeBasemap(style) {
    if (CONFIG.MAPBOX_TOKEN === 'YOUR_MAPBOX_TOKEN_HERE') {
        console.warn('Mapbox token not configured. Cannot change basemap.');
        return;
    }

    // Don't add token here - transformRequest will handle it
    const styleUrl = CONFIG.BASEMAPS[style];

    // Save current state
    const center = map.getCenter();
    const zoom = map.getZoom();

    // Change style
    map.setStyle(styleUrl);

    // Restore layers after style loads
    map.once('style.load', () => {
        loadAOI();
        if (layerState.ndvi && map.ndviLayer) {
            loadNDVI();
        }
    });
}

// Initialize map
map.on('load', () => {
    console.log('✓ Map loaded and ready');

    // Load initial layers
    loadAOI();

    // Check if NDVI is available (only need parseGeoraster, can use fallback renderer)
    const ndviAvailable = typeof parseGeoraster !== 'undefined';
    const hasGeoRasterLayer = typeof GeoRasterLayer !== 'undefined';

    if (ndviAvailable) {
        if (hasGeoRasterLayer) {
            console.log('✓ NDVI libraries loaded - using GeoRasterLayer plugin');
        } else {
            console.log('✓ GeoRaster loaded - using canvas fallback renderer');
        }
        // Enable the checkbox
        document.getElementById('layer-ndvi').disabled = false;
        const ndviItem = document.querySelector('label[for="layer-ndvi"]');
        if (ndviItem) {
            ndviItem.classList.remove('disabled');
        }
        document.getElementById('ndvi-status').textContent = '✓';
        document.getElementById('ndvi-info').textContent = 'June 2024 composite (example data)';
    } else {
        console.error('❌ GeoRaster library not loaded - NDVI layer disabled');
        // Keep checkbox disabled
        document.getElementById('layer-ndvi').disabled = true;
        document.getElementById('ndvi-status').textContent = '✗';
        document.getElementById('ndvi-info').innerHTML = '<strong>GeoRaster library not loaded</strong><br>NDVI visualization unavailable';
    }
});

// Layer control event listeners
document.getElementById('layer-aoi').addEventListener('change', (e) => {
    toggleLayer('aoi', e.target.checked);
});

document.getElementById('layer-ndvi').addEventListener('change', async (e) => {
    const checked = e.target.checked;

    // If turning on and not loaded yet, load it first
    if (checked && !map.ndviLayer) {
        console.log('First time loading NDVI...');
        const loaded = await loadNDVI();
        if (!loaded) {
            // Loading failed, uncheck the box
            e.target.checked = false;
            return;
        }
    }

    toggleLayer('ndvi', checked);
});

// Basemap switcher
document.querySelectorAll('input[name="basemap"]').forEach(radio => {
    radio.addEventListener('change', (e) => {
        changeBasemap(e.target.value);
    });
});

// Toggle control panel
document.getElementById('toggle-control')?.addEventListener('click', () => {
    const panel = document.getElementById('layer-control');
    panel.classList.toggle('hidden');
});

// Handle map errors
map.on('error', (e) => {
    console.error('❌ Map error:', e);
    console.error('Error details:', e.error);
});

// Log when map is loading
console.log('🗺️  Williams Treaty Territories Map Application');
console.log('📍 Center:', CONFIG.CENTER);
console.log('🔍 Zoom:', CONFIG.ZOOM);
console.log('🔑 Mapbox token configured:', CONFIG.MAPBOX_TOKEN !== 'YOUR_MAPBOX_TOKEN_HERE');

// Add more event listeners for debugging
map.on('style.load', () => {
    console.log('✓ Map style loaded successfully');
});

map.on('data', (e) => {
    if (e.isSourceLoaded) {
        console.log('✓ Data source loaded:', e.sourceId);
    }
});

map.on('sourcedata', (e) => {
    if (e.isSourceLoaded) {
        console.log('✓ Source data loaded:', e.sourceId);
    }
});

map.on('render', () => {
    console.log('🎨 Map rendering...');
}, { once: true });

// Log when map is ready
map.on('idle', () => {
    console.log('✓ Map is idle and ready');
}, { once: true });
