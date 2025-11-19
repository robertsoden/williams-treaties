// Williams Treaty Territories - Map Application (Config-Driven)

// Configuration - First check local config.js, then will check API
let CONFIG = {
    MAPBOX_TOKEN: (window.MAP_CONFIG && window.MAP_CONFIG.MAPBOX_TOKEN) || 'YOUR_MAPBOX_TOKEN_HERE',
    CENTER: (window.MAP_CONFIG && window.MAP_CONFIG.CENTER) || [-79.05, 44.3],
    ZOOM: (window.MAP_CONFIG && window.MAP_CONFIG.ZOOM) || 9,
    BASEMAPS: {
        streets: 'mapbox://styles/mapbox/streets-v12',
        satellite: 'mapbox://styles/mapbox/satellite-streets-v12',
        outdoors: 'mapbox://styles/mapbox/outdoors-v12',
        dark: 'mapbox://styles/mapbox/dark-v11'
    }
};

// Fetch config from API if no local token found
async function loadConfigFromAPI() {
    if (CONFIG.MAPBOX_TOKEN !== 'YOUR_MAPBOX_TOKEN_HERE') {
        // Local config already has a token
        return;
    }

    try {
        const response = await fetch('/api/config');
        const apiConfig = await response.json();

        if (apiConfig.mapbox_token && apiConfig.mapbox_token !== '') {
            CONFIG.MAPBOX_TOKEN = apiConfig.mapbox_token;
            CONFIG.CENTER = apiConfig.center || CONFIG.CENTER;
            CONFIG.ZOOM = apiConfig.zoom || CONFIG.ZOOM;
            console.log('✓ Loaded Mapbox token from server environment');
        }
    } catch (error) {
        console.warn('Could not load config from API:', error.message);
    }
}

// Check if Mapbox token is configured
if (CONFIG.MAPBOX_TOKEN === 'YOUR_MAPBOX_TOKEN_HERE') {
    console.warn('⚠️  Mapbox token not configured locally. Checking server...');
} else {
    console.log('✓ Using Mapbox token from local config.js');
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
    layers: [{
        id: 'osm',
        type: 'raster',
        source: 'osm',
        minzoom: 0,
        maxzoom: 22
    }]
};

// Global variables
let map = null;
let layerManager = null;

// Initialize map after loading config
async function initializeMap() {
    // Load config from API if needed
    await loadConfigFromAPI();

    // Set Mapbox access token
    mapboxgl.accessToken = CONFIG.MAPBOX_TOKEN;

    // Initialize the map
    map = new mapboxgl.Map({
        container: 'map',
        style: CONFIG.MAPBOX_TOKEN !== 'YOUR_MAPBOX_TOKEN_HERE'
            ? 'mapbox://styles/mapbox/streets-v12'
            : FREE_OSM_STYLE,
        center: CONFIG.CENTER,
        zoom: CONFIG.ZOOM
    });

    // Add navigation controls
    map.addControl(new mapboxgl.NavigationControl(), 'top-left');
    map.addControl(new mapboxgl.ScaleControl(), 'bottom-left');

    // Continue with layer initialization when map is ready
    map.on('load', async () => {
        console.log('✓ Map loaded and ready');

        // Check library availability
        if (typeof parseGeoraster !== 'undefined') {
            console.log('✓ GeoRaster loaded - raster layers available');
        } else {
            console.warn('❌ GeoRaster library not loaded - raster layers disabled');
        }

        if (typeof jsyaml !== 'undefined') {
            console.log('✓ js-yaml loaded - configuration system available');
        } else {
            console.error('❌ js-yaml library not loaded - cannot load configuration');
            showNotification('Required library (js-yaml) not loaded. Layer configuration unavailable.', 'error');
            return;
        }

        // Initialize layer system
        await initializeLayers();
    });
}

// Start initialization when page loads
initializeMap();

// Utility functions
function showLoading() {
    document.getElementById('loading').style.display = 'block';
}

function hideLoading() {
    document.getElementById('loading').style.display = 'none';
}

function showNotification(message, type = 'info', duration = 5000) {
    let notification = document.getElementById('notification');
    if (!notification) {
        notification = document.createElement('div');
        notification.id = 'notification';
        notification.style.cssText = `
            position: fixed; top: 20px; right: 20px; max-width: 400px;
            padding: 15px 20px; border-radius: 4px; box-shadow: 0 2px 8px rgba(0,0,0,0.2);
            z-index: 10000; display: none;
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
            font-size: 14px; line-height: 1.5;
        `;
        document.body.appendChild(notification);
    }

    const colors = {
        'info': { bg: '#2196F3', text: '#fff' },
        'success': { bg: '#4CAF50', text: '#fff' },
        'warning': { bg: '#FF9800', text: '#fff' },
        'error': { bg: '#f44336', text: '#fff' }
    };

    const color = colors[type] || colors['info'];
    notification.style.backgroundColor = color.bg;
    notification.style.color = color.text;
    notification.textContent = message;
    notification.style.display = 'block';

    if (duration > 0) {
        setTimeout(() => {
            notification.style.display = 'none';
        }, duration);
    }
}

// Load layer configuration and initialize
async function initializeLayers() {
    try {
        showLoading();
        console.log('Loading layer configuration...');

        // Load YAML configuration
        const response = await fetch('/config/layers.yaml');
        const yamlText = await response.text();
        const layerConfig = jsyaml.load(yamlText);

        console.log('✓ Layer configuration loaded:', layerConfig);

        // Create layer manager
        layerManager = new LayerManager(map, layerConfig);

        // Generate UI from configuration
        layerManager.generateUI();

        // Load initial layers (non-lazy layers that start visible and are active)
        for (const layer of layerConfig.layers) {
            // Skip inactive layers (default to true if not specified)
            if (layer.active === false) continue;

            if (layer.initial_visibility && !layer.lazy_load) {
                console.log(`Loading initial layer: ${layer.name}`);
                await layerManager.loadLayer(layer);
            }
        }

        hideLoading();
        console.log('✓ Layer system initialized');

    } catch (error) {
        console.error('Failed to initialize layers:', error);
        hideLoading();
        showNotification('Failed to load layer configuration: ' + error.message, 'error', 10000);
    }
}

// Change basemap
function changeBasemap(style) {
    if (CONFIG.MAPBOX_TOKEN === 'YOUR_MAPBOX_TOKEN_HERE') {
        console.warn('Mapbox token not configured. Cannot change basemap.');
        return;
    }

    const styleUrl = CONFIG.BASEMAPS[style];
    console.log('Changing basemap to:', style);
    showLoading();

    map.setStyle(styleUrl);

    // Restore all layers after style loads
    map.once('style.load', async () => {
        console.log('Restoring layers after basemap change...');
        if (layerManager) {
            await layerManager.reloadLayers();
        }
        hideLoading();
        console.log('✓ Basemap changed and layers restored');
    });
}

// Basemap switcher event listeners
document.addEventListener('DOMContentLoaded', () => {
    document.querySelectorAll('input[name="basemap"]').forEach(radio => {
        radio.addEventListener('change', (e) => {
            changeBasemap(e.target.value);
        });
    });

    // Toggle control panel
    const toggleBtn = document.getElementById('toggle-control');
    if (toggleBtn) {
        toggleBtn.addEventListener('click', () => {
            const panel = document.getElementById('layer-control');
            panel.classList.toggle('hidden');
        });
    }
});

// Handle map errors
map.on('error', (e) => {
    console.error('❌ Map error:', e);
    if (e.error) console.error('Error details:', e.error);
});

// Debug logging
console.log('🗺️  Williams Treaty Territories Map Application (Config-Driven)');
console.log('📍 Center:', CONFIG.CENTER);
console.log('🔍 Zoom:', CONFIG.ZOOM);
console.log('🔑 Mapbox token configured:', CONFIG.MAPBOX_TOKEN !== 'YOUR_MAPBOX_TOKEN_HERE');
