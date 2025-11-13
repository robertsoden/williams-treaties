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
        treatyBoundary: '/data/boundaries/williams_treaty.geojson',
        ndvi: '/data/processed/ndvi/ndvi_example_2024-06.tif',
        charities: '/data/processed/charities/environmental_organizations.geojson',
        communities: '/data/processed/communities/williams_treaty_communities.geojson',
        elevation: '/data/processed/dem/elevation.tif',
        firePerimeters: '/data/processed/fire/fire_perimeters_2010_2024.geojson',
        fuelType: '/data/processed/fuel/fuel_types.tif'
    },

    // Basemap styles (use mapbox:// protocol for Mapbox GL JS)
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

// Set Mapbox access token
mapboxgl.accessToken = CONFIG.MAPBOX_TOKEN;

// Initialize the map
const map = new mapboxgl.Map({
    container: 'map',
    style: CONFIG.MAPBOX_TOKEN !== 'YOUR_MAPBOX_TOKEN_HERE'
        ? 'mapbox://styles/mapbox/streets-v12'  // Use mapbox:// protocol - Mapbox GL JS handles it
        : FREE_OSM_STYLE,
    center: CONFIG.CENTER,
    zoom: CONFIG.ZOOM
});

// Add navigation controls
map.addControl(new mapboxgl.NavigationControl(), 'top-left');

// Add scale control
map.addControl(new mapboxgl.ScaleControl(), 'bottom-left');

// Log map initialization
console.log('Map object created');
console.log('Map center:', CONFIG.CENTER);
console.log('Map zoom:', CONFIG.ZOOM);

// Layer state
const layerState = {
    treaty: true,
    charities: false,
    communities: false,
    ndvi: false,
    elevation: false,
    fire: false,
    fuelType: false,
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

// Show notification message (better than alert)
function showNotification(message, type = 'info', duration = 5000) {
    // Create notification element if it doesn't exist
    let notification = document.getElementById('notification');
    if (!notification) {
        notification = document.createElement('div');
        notification.id = 'notification';
        notification.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            max-width: 400px;
            padding: 15px 20px;
            border-radius: 4px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.2);
            z-index: 10000;
            display: none;
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
            font-size: 14px;
            line-height: 1.5;
        `;
        document.body.appendChild(notification);
    }

    // Set color based on type
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

    // Auto-hide after duration
    if (duration > 0) {
        setTimeout(() => {
            notification.style.display = 'none';
        }, duration);
    }
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
        const bounds = new mapboxgl.LngLatBounds();
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
            new mapboxgl.Popup()
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

// Load Williams Treaty boundary
async function loadTreatyBoundary() {
    try {
        const response = await fetch(CONFIG.DATA_URLS.treatyBoundary);
        const geojson = await response.json();

        map.addSource('treaty-boundary', {
            type: 'geojson',
            data: geojson
        });

        // Add fill layer for treaty boundary
        map.addLayer({
            id: 'treaty-fill',
            type: 'fill',
            source: 'treaty-boundary',
            paint: {
                'fill-color': '#2c5f2d',
                'fill-opacity': 0.1
            }
        });

        // Add outline layer
        map.addLayer({
            id: 'treaty-outline',
            type: 'line',
            source: 'treaty-boundary',
            paint: {
                'line-color': '#2c5f2d',
                'line-width': 3,
                'line-opacity': 0.8
            }
        });

        // Fit map to treaty bounds
        const bounds = new mapboxgl.LngLatBounds();
        geojson.features.forEach(feature => {
            if (feature.geometry.type === 'MultiPolygon') {
                feature.geometry.coordinates.forEach(polygon => {
                    polygon[0].forEach(coord => {
                        bounds.extend(coord);
                    });
                });
            } else if (feature.geometry.type === 'Polygon') {
                feature.geometry.coordinates[0].forEach(coord => {
                    bounds.extend(coord);
                });
            }
        });
        map.fitBounds(bounds, { padding: 50 });

        // Add click handler
        map.on('click', 'treaty-fill', (e) => {
            const properties = e.features[0].properties;
            new mapboxgl.Popup()
                .setLngLat(e.lngLat)
                .setHTML(`
                    <h4>${properties.ENAME || 'Williams Treaty Territories'}</h4>
                    <p><strong>Treaty Date:</strong> ${properties.DATE_YEAR || '1923'}</p>
                    <p><strong>Category:</strong> ${properties.Category || 'Treaty Land'}</p>
                `)
                .addTo(map);
        });

        // Change cursor on hover
        map.on('mouseenter', 'treaty-fill', () => {
            map.getCanvas().style.cursor = 'pointer';
        });
        map.on('mouseleave', 'treaty-fill', () => {
            map.getCanvas().style.cursor = '';
        });

        console.log('✓ Treaty boundary loaded');
    } catch (error) {
        console.error('Error loading treaty boundary:', error);
    }
}

// Load environmental charities
async function loadCharities() {
    try {
        const response = await fetch(CONFIG.DATA_URLS.charities);
        const geojson = await response.json();

        map.addSource('charities', {
            type: 'geojson',
            data: geojson
        });

        // Add circle markers for charities
        map.addLayer({
            id: 'charities-circles',
            type: 'circle',
            source: 'charities',
            paint: {
                'circle-radius': 6,
                'circle-color': '#3887be',
                'circle-stroke-width': 2,
                'circle-stroke-color': '#ffffff',
                'circle-opacity': 0.8
            }
        });

        // Initially hide the layer
        map.setLayoutProperty('charities-circles', 'visibility', 'none');

        // Add click handler for popups
        map.on('click', 'charities-circles', (e) => {
            const properties = e.features[0].properties;
            const coordinates = e.features[0].geometry.coordinates.slice();

            // Format revenue
            const revenue = properties.revenue ?
                `$${parseInt(properties.revenue).toLocaleString()}` : 'N/A';

            new mapboxgl.Popup()
                .setLngLat(coordinates)
                .setHTML(`
                    <h4>${properties.name}</h4>
                    <p><strong>Location:</strong> ${properties.city}, ${properties.province}</p>
                    <p><strong>Category:</strong> ${properties.category}</p>
                    <p><strong>Revenue:</strong> ${revenue}</p>
                    ${properties.programs ? `<p><strong>Programs:</strong> ${properties.programs}...</p>` : ''}
                    ${properties.website ? `<p><a href="${properties.website}" target="_blank">Website</a></p>` : ''}
                `)
                .addTo(map);
        });

        // Change cursor on hover
        map.on('mouseenter', 'charities-circles', () => {
            map.getCanvas().style.cursor = 'pointer';
        });
        map.on('mouseleave', 'charities-circles', () => {
            map.getCanvas().style.cursor = '';
        });

        console.log(`✓ Loaded ${geojson.features.length} environmental organizations`);
    } catch (error) {
        console.error('Error loading charities:', error);
    }
}

// Load Williams Treaty First Nations communities
async function loadCommunities() {
    try {
        const response = await fetch(CONFIG.DATA_URLS.communities);
        const geojson = await response.json();

        map.addSource('communities', {
            type: 'geojson',
            data: geojson
        });

        // Add circle markers for communities
        map.addLayer({
            id: 'communities-circles',
            type: 'circle',
            source: 'communities',
            paint: {
                'circle-radius': 8,
                'circle-color': '#d73027',
                'circle-stroke-width': 2,
                'circle-stroke-color': '#ffffff',
                'circle-opacity': 0.9
            }
        });

        // Initially hide the layer
        map.setLayoutProperty('communities-circles', 'visibility', 'none');

        // Add click handler for popups
        map.on('click', 'communities-circles', (e) => {
            const properties = e.features[0].properties;
            const coordinates = e.features[0].geometry.coordinates.slice();

            // Format population
            const population = properties.population ?
                `~${parseInt(properties.population).toLocaleString()}` : 'N/A';

            new mapboxgl.Popup()
                .setLngLat(coordinates)
                .setHTML(`
                    <h4>${properties.name}</h4>
                    <p><strong>Reserve:</strong> ${properties.reserve_name}</p>
                    <p><strong>Population:</strong> ${population}</p>
                    <p><strong>Treaty:</strong> ${properties.treaty}</p>
                `)
                .addTo(map);
        });

        // Change cursor on hover
        map.on('mouseenter', 'communities-circles', () => {
            map.getCanvas().style.cursor = 'pointer';
        });
        map.on('mouseleave', 'communities-circles', () => {
            map.getCanvas().style.cursor = '';
        });

        console.log(`✓ Loaded ${geojson.features.length} Williams Treaty First Nations communities`);
    } catch (error) {
        console.error('Error loading communities:', error);
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
    const coordinates = [
        [georaster.xmin, georaster.ymax], // top-left
        [georaster.xmax, georaster.ymax], // top-right
        [georaster.xmax, georaster.ymin], // bottom-right
        [georaster.xmin, georaster.ymin]  // bottom-left
    ];

    map.addSource('ndvi-raster', {
        type: 'image',
        url: canvas.toDataURL(),
        coordinates: coordinates
    });

    map.addLayer({
        id: 'ndvi-layer',
        type: 'raster',
        source: 'ndvi-raster',
        paint: {
            'raster-opacity': 0.7
        }
    }, 'treaty-fill');

    // Initially hide the layer (it starts unchecked)
    map.setLayoutProperty('ndvi-layer', 'visibility', 'none');

    return true;
}

// Load NDVI raster
async function loadNDVI() {
    // Check if GeoRaster parser is available (required for both methods)
    if (typeof parseGeoraster === 'undefined') {
        console.error('GeoRaster library not loaded');
        hideLoading();
        showNotification('NDVI visualization requires GeoRaster library. Please check console for errors.', 'error');
        return false;
    }

    try {
        showLoading();

        const response = await fetch(CONFIG.DATA_URLS.ndvi);
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        const arrayBuffer = await response.arrayBuffer();

        // Parse GeoTIFF
        const georaster = await parseGeoraster(arrayBuffer);

        // Use canvas-based rendering (compatible with Mapbox GL JS)
        await loadNDVIWithCanvas(georaster);
        map.ndviLayerType = 'canvas';
        map.ndviLoaded = true; // Mark as loaded for reload detection

        hideLoading();
        console.log('✓ NDVI raster loaded successfully');

        return true;

    } catch (error) {
        console.error('❌ Error loading NDVI:', error);
        hideLoading();
        showNotification('Could not load NDVI data: ' + error.message, 'error', 7000);
        return false;
    }
}

// Create color scale for elevation (250-400m synthetic range)
function getElevationColor(value) {
    // Elevation colormap: blue (low) -> green -> yellow -> brown -> white (high)
    if (value < 270) return [69, 117, 180, 180];      // Dark blue - lowest
    if (value < 290) return [116, 173, 209, 180];     // Light blue
    if (value < 310) return [171, 217, 233, 180];     // Pale blue
    if (value < 330) return [224, 243, 248, 180];     // Very pale blue
    if (value < 350) return [255, 255, 191, 180];     // Yellow
    if (value < 370) return [254, 224, 144, 180];     // Orange-yellow
    if (value < 390) return [253, 174, 97, 180];      // Orange
    return [215, 48, 39, 200];                         // Red-brown - highest
}

// Canvas renderer for elevation data
async function loadElevationWithCanvas(georaster) {
    console.log('Using custom canvas renderer for elevation');

    const canvas = document.createElement('canvas');
    canvas.width = georaster.width;
    canvas.height = georaster.height;
    const ctx = canvas.getContext('2d');
    const imageData = ctx.createImageData(canvas.width, canvas.height);

    // Render each pixel
    for (let y = 0; y < georaster.height; y++) {
        for (let x = 0; x < georaster.width; x++) {
            const value = georaster.values[0][y][x];
            const color = getElevationColor(value);
            const idx = (y * canvas.width + x) * 4;
            imageData.data[idx] = color[0];     // R
            imageData.data[idx + 1] = color[1]; // G
            imageData.data[idx + 2] = color[2]; // B
            imageData.data[idx + 3] = color[3]; // A
        }
    }

    ctx.putImageData(imageData, 0, 0);

    // Add as image source
    const coordinates = [
        [georaster.xmin, georaster.ymax], // top-left
        [georaster.xmax, georaster.ymax], // top-right
        [georaster.xmax, georaster.ymin], // bottom-right
        [georaster.xmin, georaster.ymin]  // bottom-left
    ];

    map.addSource('elevation-raster', {
        type: 'image',
        url: canvas.toDataURL(),
        coordinates: coordinates
    });

    map.addLayer({
        id: 'elevation-layer',
        type: 'raster',
        source: 'elevation-raster',
        paint: {
            'raster-opacity': 0.6
        }
    }, 'treaty-fill');

    // Initially hide the layer
    map.setLayoutProperty('elevation-layer', 'visibility', 'none');

    return true;
}

// Load elevation raster
async function loadElevation() {
    // Check if GeoRaster parser is available
    if (typeof parseGeoraster === 'undefined') {
        console.error('GeoRaster library not loaded');
        hideLoading();
        showNotification('Elevation visualization requires GeoRaster library.', 'error');
        return false;
    }

    try {
        showLoading();

        const response = await fetch(CONFIG.DATA_URLS.elevation);
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        const arrayBuffer = await response.arrayBuffer();

        // Parse GeoTIFF
        const georaster = await parseGeoraster(arrayBuffer);

        // Use canvas-based rendering
        await loadElevationWithCanvas(georaster);
        map.elevationLayerType = 'canvas';
        map.elevationLoaded = true;

        hideLoading();
        console.log('✓ Elevation raster loaded successfully');

        return true;

    } catch (error) {
        console.error('❌ Error loading elevation:', error);
        hideLoading();
        showNotification('Could not load elevation data: ' + error.message, 'error', 7000);
        return false;
    }
}

// Load fire perimeters (vector data)
async function loadFirePerimeters() {
    try {
        showLoading();

        const response = await fetch(CONFIG.DATA_URLS.firePerimeters);
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        const geojson = await response.json();

        map.addSource('fire-perimeters', {
            type: 'geojson',
            data: geojson
        });

        // Add fill layer for fire perimeters
        map.addLayer({
            id: 'fire-fill',
            type: 'fill',
            source: 'fire-perimeters',
            paint: {
                'fill-color': '#d73027',
                'fill-opacity': 0.4
            }
        }, 'treaty-fill');

        // Add outline layer
        map.addLayer({
            id: 'fire-outline',
            type: 'line',
            source: 'fire-perimeters',
            paint: {
                'line-color': '#a50026',
                'line-width': 1,
                'line-opacity': 0.8
            }
        }, 'treaty-fill');

        // Initially hide the layer
        map.setLayoutProperty('fire-fill', 'visibility', 'none');
        map.setLayoutProperty('fire-outline', 'visibility', 'none');

        // Add click handler for popups
        map.on('click', 'fire-fill', (e) => {
            const properties = e.features[0].properties;
            new mapboxgl.Popup()
                .setLngLat(e.lngLat)
                .setHTML(`
                    <h4>Fire Perimeter</h4>
                    <p><strong>Year:</strong> ${properties.year || properties.YEAR || 'Unknown'}</p>
                    <p><strong>Area:</strong> ${properties.area ? (properties.area / 10000).toFixed(2) + ' ha' : 'N/A'}</p>
                    ${properties.FIRE_ID ? `<p><strong>Fire ID:</strong> ${properties.FIRE_ID}</p>` : ''}
                `)
                .addTo(map);
        });

        // Change cursor on hover
        map.on('mouseenter', 'fire-fill', () => {
            map.getCanvas().style.cursor = 'pointer';
        });
        map.on('mouseleave', 'fire-fill', () => {
            map.getCanvas().style.cursor = '';
        });

        map.fireLoaded = true;

        hideLoading();
        console.log(`✓ Loaded ${geojson.features.length} fire perimeters`);

        return true;

    } catch (error) {
        console.error('❌ Error loading fire perimeters:', error);
        hideLoading();
        showNotification('Could not load fire perimeter data: ' + error.message, 'error', 7000);
        return false;
    }
}

// Create color scale for fuel types
function getFuelTypeColor(value) {
    // Canadian Forest Fire Behavior Prediction (FBP) System fuel types
    // Simplified colormap for demonstration
    if (value === 0 || value === 99) return [200, 200, 200, 100];  // Non-fuel / Water
    if (value >= 1 && value <= 4) return [34, 139, 34, 180];       // Coniferous (C-1 to C-4) - Green
    if (value >= 5 && value <= 7) return [0, 100, 0, 180];         // Coniferous (C-5 to C-7) - Dark green
    if (value >= 11 && value <= 18) return [255, 215, 0, 180];     // Deciduous (D-1, D-2) - Gold
    if (value >= 21 && value <= 25) return [173, 255, 47, 180];    // Mixed wood (M-1, M-2) - Yellow-green
    if (value >= 31 && value <= 32) return [184, 134, 11, 180];    // Slash (S-1, S-2) - Dark gold
    if (value >= 40 && value <= 43) return [255, 255, 153, 180];   // Grass (O-1a, O-1b) - Light yellow
    return [139, 69, 19, 180];  // Other - Brown
}

// Canvas renderer for fuel type data
async function loadFuelTypeWithCanvas(georaster) {
    console.log('Using custom canvas renderer for fuel types');

    const canvas = document.createElement('canvas');
    canvas.width = georaster.width;
    canvas.height = georaster.height;
    const ctx = canvas.getContext('2d');
    const imageData = ctx.createImageData(canvas.width, canvas.height);

    // Render each pixel
    for (let y = 0; y < georaster.height; y++) {
        for (let x = 0; x < georaster.width; x++) {
            const value = georaster.values[0][y][x];
            const color = getFuelTypeColor(value);
            const idx = (y * canvas.width + x) * 4;
            imageData.data[idx] = color[0];     // R
            imageData.data[idx + 1] = color[1]; // G
            imageData.data[idx + 2] = color[2]; // B
            imageData.data[idx + 3] = color[3]; // A
        }
    }

    ctx.putImageData(imageData, 0, 0);

    // Add as image source
    const coordinates = [
        [georaster.xmin, georaster.ymax], // top-left
        [georaster.xmax, georaster.ymax], // top-right
        [georaster.xmax, georaster.ymin], // bottom-right
        [georaster.xmin, georaster.ymin]  // bottom-left
    ];

    map.addSource('fueltype-raster', {
        type: 'image',
        url: canvas.toDataURL(),
        coordinates: coordinates
    });

    map.addLayer({
        id: 'fueltype-layer',
        type: 'raster',
        source: 'fueltype-raster',
        paint: {
            'raster-opacity': 0.6
        }
    }, 'treaty-fill');

    // Initially hide the layer
    map.setLayoutProperty('fueltype-layer', 'visibility', 'none');

    return true;
}

// Load fuel type raster
async function loadFuelType() {
    // Check if GeoRaster parser is available
    if (typeof parseGeoraster === 'undefined') {
        console.error('GeoRaster library not loaded');
        hideLoading();
        showNotification('Fuel type visualization requires GeoRaster library.', 'error');
        return false;
    }

    try {
        showLoading();

        const response = await fetch(CONFIG.DATA_URLS.fuelType);
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        const arrayBuffer = await response.arrayBuffer();

        // Parse GeoTIFF
        const georaster = await parseGeoraster(arrayBuffer);

        // Use canvas-based rendering
        await loadFuelTypeWithCanvas(georaster);
        map.fuelTypeLayerType = 'canvas';
        map.fuelTypeLoaded = true;

        hideLoading();
        console.log('✓ Fuel type raster loaded successfully');

        return true;

    } catch (error) {
        console.error('❌ Error loading fuel type:', error);
        hideLoading();
        showNotification('Could not load fuel type data: ' + error.message, 'error', 7000);
        return false;
    }
}

// Toggle layer visibility
function toggleLayer(layerId, visible) {
    layerState[layerId] = visible;

    switch(layerId) {
        case 'treaty':
            map.setLayoutProperty('treaty-fill', 'visibility', visible ? 'visible' : 'none');
            map.setLayoutProperty('treaty-outline', 'visibility', visible ? 'visible' : 'none');
            break;

        case 'charities':
            if (map.getLayer('charities-circles')) {
                map.setLayoutProperty('charities-circles', 'visibility', visible ? 'visible' : 'none');
            }
            break;

        case 'communities':
            if (map.getLayer('communities-circles')) {
                map.setLayoutProperty('communities-circles', 'visibility', visible ? 'visible' : 'none');
            }
            break;

        case 'ndvi':
            // Canvas-based rendering (only option with Mapbox GL JS)
            if (map.getLayer('ndvi-layer')) {
                map.setLayoutProperty('ndvi-layer', 'visibility', visible ? 'visible' : 'none');
            }
            document.getElementById('ndvi-legend').style.display = visible ? 'block' : 'none';
            break;

        case 'elevation':
            // Canvas-based rendering
            if (map.getLayer('elevation-layer')) {
                map.setLayoutProperty('elevation-layer', 'visibility', visible ? 'visible' : 'none');
            }
            document.getElementById('elevation-legend').style.display = visible ? 'block' : 'none';
            break;

        case 'fire':
            if (map.getLayer('fire-fill')) {
                map.setLayoutProperty('fire-fill', 'visibility', visible ? 'visible' : 'none');
                map.setLayoutProperty('fire-outline', 'visibility', visible ? 'visible' : 'none');
            }
            const fireLegend = document.getElementById('fire-legend');
            if (fireLegend) {
                fireLegend.style.display = visible ? 'block' : 'none';
            }
            break;

        case 'fuelType':
            if (map.getLayer('fueltype-layer')) {
                map.setLayoutProperty('fueltype-layer', 'visibility', visible ? 'visible' : 'none');
            }
            const fuelLegend = document.getElementById('fuel-legend');
            if (fuelLegend) {
                fuelLegend.style.display = visible ? 'block' : 'none';
            }
            break;
    }
}

// Change basemap
function changeBasemap(style) {
    if (CONFIG.MAPBOX_TOKEN === 'YOUR_MAPBOX_TOKEN_HERE') {
        console.warn('Mapbox token not configured. Cannot change basemap.');
        return;
    }

    const styleUrl = CONFIG.BASEMAPS[style];

    // Change style (Mapbox GL JS handles authentication automatically)
    map.setStyle(styleUrl);

    // Restore layers after style loads
    map.once('style.load', () => {
        loadTreatyBoundary();
        if (layerState.ndvi && map.ndviLoaded) {
            loadNDVI();
        }
    });
}

// Initialize map
map.on('load', () => {
    console.log('✓ Map loaded and ready');

    // Load initial layers
    // loadAOI(); // Replaced with actual treaty boundaries
    loadTreatyBoundary();
    loadCharities();
    loadCommunities();

    // Check if NDVI is available (only need parseGeoraster for canvas rendering)
    const ndviAvailable = typeof parseGeoraster !== 'undefined';

    if (ndviAvailable) {
        console.log('✓ GeoRaster loaded - using canvas renderer for NDVI');
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
document.getElementById('layer-treaty').addEventListener('change', (e) => {
    toggleLayer('treaty', e.target.checked);
});

document.getElementById('layer-charities').addEventListener('change', (e) => {
    toggleLayer('charities', e.target.checked);
});

document.getElementById('layer-communities').addEventListener('change', (e) => {
    toggleLayer('communities', e.target.checked);
});

document.getElementById('layer-ndvi').addEventListener('change', async (e) => {
    const checked = e.target.checked;

    // If turning on and not loaded yet, load it first
    if (checked && !map.ndviLoaded) {
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

document.getElementById('layer-elevation').addEventListener('change', async (e) => {
    const checked = e.target.checked;

    // If turning on and not loaded yet, load it first
    if (checked && !map.elevationLoaded) {
        console.log('First time loading elevation...');
        const loaded = await loadElevation();
        if (!loaded) {
            // Loading failed, uncheck the box
            e.target.checked = false;
            return;
        }
    }

    toggleLayer('elevation', checked);
});

document.getElementById('layer-fire').addEventListener('change', async (e) => {
    const checked = e.target.checked;

    // If turning on and not loaded yet, load it first
    if (checked && !map.fireLoaded) {
        console.log('First time loading fire perimeters...');
        const loaded = await loadFirePerimeters();
        if (!loaded) {
            // Loading failed, uncheck the box
            e.target.checked = false;
            return;
        }
    }

    toggleLayer('fire', checked);
});

document.getElementById('layer-fuel').addEventListener('change', async (e) => {
    const checked = e.target.checked;

    // If turning on and not loaded yet, load it first
    if (checked && !map.fuelTypeLoaded) {
        console.log('First time loading fuel types...');
        const loaded = await loadFuelType();
        if (!loaded) {
            // Loading failed, uncheck the box
            e.target.checked = false;
            return;
        }
    }

    toggleLayer('fuelType', checked);
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
