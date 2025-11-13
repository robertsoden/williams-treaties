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

    // Basemap styles
    BASEMAPS: {
        streets: 'mapbox://styles/mapbox/streets-v12',
        satellite: 'mapbox://styles/mapbox/satellite-streets-v12',
        outdoors: 'mapbox://styles/mapbox/outdoors-v12',
        dark: 'mapbox://styles/mapbox/dark-v11'
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
    style: CONFIG.MAPBOX_TOKEN !== 'YOUR_MAPBOX_TOKEN_HERE'
        ? `${CONFIG.BASEMAPS.streets}?access_token=${CONFIG.MAPBOX_TOKEN}`
        : FREE_OSM_STYLE, // Free OpenStreetMap fallback
    center: CONFIG.CENTER,
    zoom: CONFIG.ZOOM,
    transformRequest: (url, resourceType) => {
        // Add Mapbox token to requests if configured
        if (CONFIG.MAPBOX_TOKEN !== 'YOUR_MAPBOX_TOKEN_HERE' && url.includes('mapbox.com')) {
            return {
                url: url.includes('?') ? `${url}&access_token=${CONFIG.MAPBOX_TOKEN}` : `${url}?access_token=${CONFIG.MAPBOX_TOKEN}`
            };
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

// Load NDVI raster
async function loadNDVI() {
    // Check if GeoRaster libraries are available
    if (typeof parseGeoraster === 'undefined' || typeof GeoRasterLayer === 'undefined') {
        console.error('GeoRaster libraries not loaded');
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

        // Create color scale for NDVI (0.2 to 0.8)
        const colorScale = (value) => {
            if (value < 0.2) return [211, 48, 39, 180];      // Red - very low
            if (value < 0.3) return [252, 141, 89, 180];     // Orange-red - low
            if (value < 0.4) return [254, 224, 139, 180];    // Yellow - moderate-low
            if (value < 0.5) return [217, 239, 139, 180];    // Yellow-green - moderate
            if (value < 0.6) return [145, 207, 96, 180];     // Light green - moderate-high
            if (value < 0.7) return [26, 152, 80, 180];      // Green - high
            return [0, 104, 55, 200];                        // Dark green - very high
        };

        // Add NDVI layer
        const layer = new GeoRasterLayer({
            georaster: georaster,
            opacity: 0.7,
            pixelValuesToColorFn: values => colorScale(values[0]),
            resolution: 256
        });

        map.addLayer(layer, 'aoi-fill'); // Add below AOI
        map.ndviLayer = layer;

        // Initially hide the layer
        if (map.ndviLayer) {
            map.ndviLayer.options.opacity = 0;
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
            if (map.ndviLayer) {
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

    const styleUrl = `${CONFIG.BASEMAPS[style]}?access_token=${CONFIG.MAPBOX_TOKEN}`;

    // Save current state
    const center = map.getCenter();
    const zoom = map.getZoom();

    // Change style
    map.setStyle(styleUrl);

    // Restore layers after style loads
    map.once('style.load', () => {
        loadAOI();
        if (layerState.ndvi) {
            loadNDVI();
        }
    });
}

// Initialize map
map.on('load', () => {
    console.log('✓ Map loaded and ready');

    // Load initial layers
    loadAOI();

    // NDVI will be loaded on-demand when user toggles it
    // Enable the checkbox now
    document.getElementById('layer-ndvi').disabled = false;
    const ndviItem = document.querySelector('label[for="layer-ndvi"]');
    if (ndviItem) {
        ndviItem.classList.remove('disabled');
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
