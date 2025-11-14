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
        reserves: '/data/processed/communities/williams_treaty_reserves.geojson',
        ndvi: '/data/processed/ndvi/ndvi_example_2024-06.tif',
        charities: '/data/processed/charities/environmental_organizations.geojson',
        communities: '/data/processed/communities/williams_treaty_communities.geojson',
        elevation: '/data/processed/dem/elevation.tif',
        firePerimeters: '/data/processed/fire/fire_perimeters_1976_2024.geojson',
        fuelType: '/data/processed/fuel/fuel_types.tif',
        infrastructure: '/data/processed/infrastructure/infrastructure_projects.geojson',
        waterAdvisories: '/data/processed/water/water_advisories.geojson',
        cwb: '/data/processed/cwb/community_wellbeing.geojson',
        cwbFirstNations: '/data/processed/cwb/community_wellbeing_first_nations.geojson',
        csicpFunding: '/data/processed/csicp/csicp_funding.geojson'
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
    reserves: false,
    charities: false,
    communities: false,
    ndvi: false,
    elevation: false,
    fire: false,
    fuelType: false,
    infrastructure: false,
    waterAdvisories: false,
    cwb: false,
    csicpFunding: false
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

        // Log treaty boundary for comparison
        console.log('Treaty boundary loaded, features:', geojson.features.length);

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

// Load First Nations reserve boundaries
async function loadReserves() {
    try {
        const response = await fetch(CONFIG.DATA_URLS.reserves);
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        const geojson = await response.json();

        map.addSource('reserves', {
            type: 'geojson',
            data: geojson
        });

        // Add fill layer for reserves
        map.addLayer({
            id: 'reserves-fill',
            type: 'fill',
            source: 'reserves',
            paint: {
                'fill-color': '#fc8d59',
                'fill-opacity': 0.3
            }
        }, 'treaty-fill');

        // Add outline layer
        map.addLayer({
            id: 'reserves-outline',
            type: 'line',
            source: 'reserves',
            paint: {
                'line-color': '#d73027',
                'line-width': 2,
                'line-opacity': 0.8
            }
        }, 'treaty-fill');

        // Initially hide the layer
        map.setLayoutProperty('reserves-fill', 'visibility', 'none');
        map.setLayoutProperty('reserves-outline', 'visibility', 'none');

        // Add click handler for popups
        map.on('click', 'reserves-fill', (e) => {
            const properties = e.features[0].properties;
            new mapboxgl.Popup()
                .setLngLat(e.lngLat)
                .setHTML(`
                    <h4>${properties.ENGLISH_NAME || properties.name || 'First Nation Reserve'}</h4>
                    <p><strong>Reserve:</strong> ${properties.RESERVE_NAME || properties.reserve_name || 'N/A'}</p>
                    <p><strong>Band:</strong> ${properties.BAND_NAME || properties.band_name || 'N/A'}</p>
                    ${properties.AREA_SQKM ? `<p><strong>Area:</strong> ${parseFloat(properties.AREA_SQKM).toFixed(2)} km²</p>` : ''}
                `)
                .addTo(map);
        });

        // Change cursor on hover
        map.on('mouseenter', 'reserves-fill', () => {
            map.getCanvas().style.cursor = 'pointer';
        });
        map.on('mouseleave', 'reserves-fill', () => {
            map.getCanvas().style.cursor = '';
        });

        map.reservesLoaded = true;

        console.log(`✓ Loaded ${geojson.features.length} First Nations reserve boundaries`);
        return true;

    } catch (error) {
        console.error('❌ Error loading reserve boundaries:', error);
        alert('Could not load reserve boundaries. Error: ' + error.message);
        return false;
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
    console.log('NDVI georaster bounds:', {
        xmin: georaster.xmin,
        xmax: georaster.xmax,
        ymin: georaster.ymin,
        ymax: georaster.ymax,
        width: georaster.width,
        height: georaster.height,
        projection: georaster.projection
    });

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

    // Add as image source
    // Mapbox GL JS expects coordinates in [longitude, latitude] order
    // Order: top-left, top-right, bottom-right, bottom-left

    // Check if georaster has lat/lon swapped (common with EPSG:4326 GeoTIFFs)
    let xmin = georaster.xmin;
    let xmax = georaster.xmax;
    let ymin = georaster.ymin;
    let ymax = georaster.ymax;

    // Detect potential lat/lon swap
    if (Math.abs(xmin) < 90 && Math.abs(xmax) < 90 &&
        Math.abs(ymin) > 90 && Math.abs(ymax) > 90) {
        console.warn('Detected potential lat/lon swap in NDVI georaster, swapping coordinates');
        [xmin, ymin] = [ymin, xmin];
        [xmax, ymax] = [ymax, xmax];
    }

    const coordinates = [
        [xmin, ymax], // top-left
        [xmax, ymax], // top-right
        [xmax, ymin], // bottom-right
        [xmin, ymin]  // bottom-left
    ];

    console.log('NDVI layer coordinates (after swap check):', coordinates);

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

// Create color scale for elevation (7-582m SRTM range)
function getElevationColor(value) {
    // Elevation colormap: blue (low/water) -> green -> yellow -> orange -> red (high)
    // Based on actual SRTM data: 7m (Lake Ontario) to 582m (highlands)
    if (value < 75) return [8, 48, 107, 180];         // Dark blue - water/lake level
    if (value < 150) return [33, 113, 181, 180];      // Medium blue - lowlands
    if (value < 225) return [66, 146, 198, 180];      // Light blue - low elevation
    if (value < 300) return [107, 174, 214, 180];     // Pale blue - moderate
    if (value < 350) return [158, 202, 225, 180];     // Very pale blue/cyan
    if (value < 400) return [198, 219, 239, 180];     // Almost white-blue
    if (value < 450) return [253, 208, 162, 180];     // Light orange - highlands
    if (value < 500) return [253, 174, 107, 180];     // Orange - high elevation
    if (value < 550) return [241, 105, 19, 180];      // Dark orange - mountains
    return [217, 72, 1, 200];                          // Red-orange - highest peaks
}

// Canvas renderer for elevation data
async function loadElevationWithCanvas(georaster) {
    console.log('Using custom canvas renderer for elevation');
    console.log('Elevation georaster bounds:', {
        xmin: georaster.xmin,
        xmax: georaster.xmax,
        ymin: georaster.ymin,
        ymax: georaster.ymax,
        width: georaster.width,
        height: georaster.height,
        projection: georaster.projection
    });

    const canvas = document.createElement('canvas');
    canvas.width = georaster.width;
    canvas.height = georaster.height;
    const ctx = canvas.getContext('2d');
    const imageData = ctx.createImageData(canvas.width, canvas.height);

    // Render each pixel
    // Georaster y=0 corresponds to north (ymax), which matches canvas top
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

    // Log sample values from corners to verify orientation
    console.log('Elevation corner samples:');
    console.log('  Top-left (NW):', georaster.values[0][0][0], 'm');
    console.log('  Top-right (NE):', georaster.values[0][0][georaster.width - 1], 'm');
    console.log('  Bottom-left (SW):', georaster.values[0][georaster.height - 1][0], 'm');
    console.log('  Bottom-right (SE):', georaster.values[0][georaster.height - 1][georaster.width - 1], 'm');

    // Add as image source
    // Mapbox GL JS expects coordinates in [longitude, latitude] order
    // Order: top-left, top-right, bottom-right, bottom-left

    // Check if georaster has lat/lon swapped (common with EPSG:4326 GeoTIFFs)
    // EPSG:4326 officially uses (lat, lon) axis order but web mapping uses (lon, lat)
    // If xmin > xmax or ymin > ymax, coordinates might be swapped
    let xmin = georaster.xmin;
    let xmax = georaster.xmax;
    let ymin = georaster.ymin;
    let ymax = georaster.ymax;

    // Detect potential lat/lon swap - if "x" values look like latitudes
    if (Math.abs(xmin) < 90 && Math.abs(xmax) < 90 &&
        Math.abs(ymin) > 90 && Math.abs(ymax) > 90) {
        console.warn('Detected potential lat/lon swap in georaster, swapping coordinates');
        [xmin, ymin] = [ymin, xmin];
        [xmax, ymax] = [ymax, xmax];
    }

    // Calculate pixel size
    const pixelWidth = (xmax - xmin) / georaster.width;
    const pixelHeight = (ymax - ymin) / georaster.height;

    console.log('Pixel size:', { pixelWidth, pixelHeight });
    console.log('Original bounds:', { xmin, xmax, ymin, ymax });

    // Shift entire image south to correct alignment
    // 1.4km ≈ 0.0126 degrees of latitude, which is about 45.36 pixels at this resolution
    const latShift = pixelHeight * 45.36;
    ymin -= latShift;
    ymax -= latShift;

    console.log('Adjusted bounds (shifted south by ~1.4km):', { xmin, xmax, ymin, ymax, shift_km: latShift * 111 });

    const coordinates = [
        [xmin, ymax], // top-left
        [xmax, ymax], // top-right
        [xmax, ymin], // bottom-right
        [xmin, ymin]  // bottom-left
    ];

    console.log('Elevation layer coordinates (after swap check):', coordinates);
    console.log('  Top-left (NW corner):', coordinates[0]);
    console.log('  Top-right (NE corner):', coordinates[1]);
    console.log('  Bottom-right (SE corner):', coordinates[2]);
    console.log('  Bottom-left (SW corner):', coordinates[3]);

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
        console.log('Loading fire perimeters from:', CONFIG.DATA_URLS.firePerimeters);

        const response = await fetch(CONFIG.DATA_URLS.firePerimeters);
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        const geojson = await response.json();
        console.log(`Fire perimeters GeoJSON loaded: ${geojson.features.length} features`);

        map.addSource('fire-perimeters', {
            type: 'geojson',
            data: geojson
        });

        // Add fill layer for fire perimeters (add on top, not before treaty-fill)
        map.addLayer({
            id: 'fire-fill',
            type: 'fill',
            source: 'fire-perimeters',
            paint: {
                'fill-color': '#d73027',
                'fill-opacity': 0.4
            }
        });

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
        });

        console.log('Fire layers added to map');

        // Initially hide the layer
        map.setLayoutProperty('fire-fill', 'visibility', 'none');
        map.setLayoutProperty('fire-outline', 'visibility', 'none');
        console.log('Fire layers set to hidden initially');

        // Add click handler for popups
        map.on('click', 'fire-fill', (e) => {
            const properties = e.features[0].properties;
            const year = properties.year || properties.YEAR || properties.EXERCICE || properties.AN_ORIGINE || 'Unknown';
            const area_ha = properties.area ? (properties.area / 10000).toFixed(2) :
                           properties.SUPERFICIE ? properties.SUPERFICIE.toFixed(2) : 'N/A';

            new mapboxgl.Popup()
                .setLngLat(e.lngLat)
                .setHTML(`
                    <h4>Fire Perimeter</h4>
                    <p><strong>Year:</strong> ${year}</p>
                    <p><strong>Area:</strong> ${area_ha} ha</p>
                    ${properties.FIRE_ID ? `<p><strong>Fire ID:</strong> ${properties.FIRE_ID}</p>` : ''}
                    ${properties.ORIGINE ? `<p><strong>Origin:</strong> ${properties.ORIGINE}</p>` : ''}
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

        // Store bounds for zooming to fires later
        map.firePerimetersBounds = [
            [-78.7073861, 45.805734],   // southwest
            [-76.91731653, 46.38118623]  // northeast
        ];

        map.fireLoaded = true;

        hideLoading();
        console.log(`✓ Loaded ${geojson.features.length} fire perimeters`);
        console.log(`Fire perimeters bounds: SW(-78.71, 45.81) to NE(-76.92, 46.38)`);

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
    console.log('Fuel type georaster bounds:', {
        xmin: georaster.xmin,
        xmax: georaster.xmax,
        ymin: georaster.ymin,
        ymax: georaster.ymax,
        width: georaster.width,
        height: georaster.height,
        projection: georaster.projection
    });

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
    // Mapbox GL JS expects coordinates in [longitude, latitude] order
    // Order: top-left, top-right, bottom-right, bottom-left

    // Check if georaster has lat/lon swapped (common with EPSG:4326 GeoTIFFs)
    let xmin = georaster.xmin;
    let xmax = georaster.xmax;
    let ymin = georaster.ymin;
    let ymax = georaster.ymax;

    // Detect potential lat/lon swap
    if (Math.abs(xmin) < 90 && Math.abs(xmax) < 90 &&
        Math.abs(ymin) > 90 && Math.abs(ymax) > 90) {
        console.warn('Detected potential lat/lon swap in fuel type georaster, swapping coordinates');
        [xmin, ymin] = [ymin, xmin];
        [xmax, ymax] = [ymax, xmax];
    }

    const coordinates = [
        [xmin, ymax], // top-left
        [xmax, ymax], // top-right
        [xmax, ymin], // bottom-right
        [xmin, ymin]  // bottom-left
    ];

    console.log('Fuel type layer coordinates (after swap check):', coordinates);

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

// Load infrastructure projects
async function loadInfrastructure() {
    try {
        const response = await fetch(CONFIG.DATA_URLS.infrastructure);
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        const geojson = await response.json();

        map.addSource('infrastructure', {
            type: 'geojson',
            data: geojson
        });

        // Add circle markers for infrastructure projects
        map.addLayer({
            id: 'infrastructure-circles',
            type: 'circle',
            source: 'infrastructure',
            paint: {
                'circle-radius': 5,
                'circle-color': [
                    'match',
                    ['get', 'category'],
                    'Housing', '#e41a1c',
                    'Water and Wastewater', '#377eb8',
                    'Solid Waste Management', '#4daf4a',
                    'Fire Protection', '#ff7f00',
                    'Health', '#984ea3',
                    '#999999' // default
                ],
                'circle-stroke-width': 1,
                'circle-stroke-color': '#ffffff',
                'circle-opacity': 0.8
            }
        });

        // Initially hide the layer
        map.setLayoutProperty('infrastructure-circles', 'visibility', 'none');

        // Add click handler
        map.on('click', 'infrastructure-circles', (e) => {
            const properties = e.features[0].properties;
            const coordinates = e.features[0].geometry.coordinates.slice();

            new mapboxgl.Popup()
                .setLngLat(coordinates)
                .setHTML(`
                    <h4>${properties.project_name || 'Infrastructure Project'}</h4>
                    <p><strong>Community:</strong> ${properties.community}</p>
                    <p><strong>Category:</strong> ${properties.category || 'N/A'}</p>
                    <p><strong>Status:</strong> ${properties.status || 'N/A'}</p>
                    ${properties.description ? `<p><strong>Description:</strong> ${properties.description.substring(0, 200)}...</p>` : ''}
                    ${properties.investment && properties.investment !== 'Not Available' ? `<p><strong>Investment:</strong> ${properties.investment}</p>` : ''}
                `)
                .addTo(map);
        });

        // Change cursor on hover
        map.on('mouseenter', 'infrastructure-circles', () => {
            map.getCanvas().style.cursor = 'pointer';
        });
        map.on('mouseleave', 'infrastructure-circles', () => {
            map.getCanvas().style.cursor = '';
        });

        map.infrastructureLoaded = true;
        console.log(`✓ Loaded ${geojson.features.length} infrastructure projects`);
        return true;

    } catch (error) {
        console.error('❌ Error loading infrastructure:', error);
        showNotification('Could not load infrastructure data: ' + error.message, 'error', 7000);
        return false;
    }
}

// Load water advisories
async function loadWaterAdvisories() {
    try {
        const response = await fetch(CONFIG.DATA_URLS.waterAdvisories);
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        const geojson = await response.json();

        map.addSource('water-advisories', {
            type: 'geojson',
            data: geojson
        });

        // Add circle markers for water advisories
        map.addLayer({
            id: 'water-advisories-circles',
            type: 'circle',
            source: 'water-advisories',
            paint: {
                'circle-radius': 7,
                'circle-color': [
                    'case',
                    ['get', 'is_active'], '#d73027',  // Red for active
                    '#91cf60'  // Green for lifted
                ],
                'circle-stroke-width': 2,
                'circle-stroke-color': '#ffffff',
                'circle-opacity': 0.9
            }
        });

        // Initially hide the layer
        map.setLayoutProperty('water-advisories-circles', 'visibility', 'none');

        // Add click handler
        map.on('click', 'water-advisories-circles', (e) => {
            const properties = e.features[0].properties;
            const coordinates = e.features[0].geometry.coordinates.slice();

            const status = properties.is_active ? 'ACTIVE' : 'Lifted';
            const statusColor = properties.is_active ? '#d73027' : '#91cf60';

            new mapboxgl.Popup()
                .setLngLat(coordinates)
                .setHTML(`
                    <h4>${properties.water_system || 'Water System'}</h4>
                    <p><strong>First Nation:</strong> ${properties.first_nation}</p>
                    <p><strong>Status:</strong> <span style="color:${statusColor};font-weight:bold">${status}</span></p>
                    <p><strong>Type:</strong> ${properties.advisory_type}</p>
                    <p><strong>Date Set:</strong> ${properties.date_set || 'N/A'}</p>
                    ${properties.date_lifted ? `<p><strong>Date Lifted:</strong> ${properties.date_lifted}</p>` : ''}
                    ${properties.duration_days ? `<p><strong>Duration:</strong> ${properties.duration_days} days</p>` : ''}
                    ${properties.corrective_measure ? `<p><strong>Corrective Measure:</strong> ${properties.corrective_measure}</p>` : ''}
                `)
                .addTo(map);
        });

        // Change cursor on hover
        map.on('mouseenter', 'water-advisories-circles', () => {
            map.getCanvas().style.cursor = 'pointer';
        });
        map.on('mouseleave', 'water-advisories-circles', () => {
            map.getCanvas().style.cursor = '';
        });

        map.waterAdvisoriesLoaded = true;
        console.log(`✓ Loaded ${geojson.features.length} water advisories`);
        return true;

    } catch (error) {
        console.error('❌ Error loading water advisories:', error);
        showNotification('Could not load water advisory data: ' + error.message, 'error', 7000);
        return false;
    }
}

// Load Community Well-Being data
async function loadCWB() {
    try {
        const response = await fetch(CONFIG.DATA_URLS.cwb);
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        const geojson = await response.json();

        map.addSource('cwb', {
            type: 'geojson',
            data: geojson
        });

        // Add fill layer for CWB polygons with choropleth coloring
        map.addLayer({
            id: 'cwb-fill',
            type: 'fill',
            source: 'cwb',
            paint: {
                'fill-color': [
                    'interpolate',
                    ['linear'],
                    ['get', 'cwb_score'],
                    60, '#d73027',  // Low CWB - red
                    70, '#fee08b',  // Medium - yellow
                    80, '#91cf60'   // High CWB - green
                ],
                'fill-opacity': 0.6
            }
        }, 'treaty-fill');

        // Add outline layer
        map.addLayer({
            id: 'cwb-outline',
            type: 'line',
            source: 'cwb',
            paint: {
                'line-color': '#333',
                'line-width': 1.5,
                'line-opacity': 0.8
            }
        }, 'treaty-fill');

        // Initially hide the layers
        map.setLayoutProperty('cwb-fill', 'visibility', 'none');
        map.setLayoutProperty('cwb-outline', 'visibility', 'none');

        // Add click handler
        map.on('click', 'cwb-fill', (e) => {
            const properties = e.features[0].properties;
            new mapboxgl.Popup()
                .setLngLat(e.lngLat)
                .setHTML(`
                    <h4>${properties.name}</h4>
                    <p><strong>Community Well-Being Score:</strong> ${properties.cwb_score || 'N/A'}</p>
                    <p><strong>Population:</strong> ${properties.population || 'N/A'}</p>
                    ${properties.income_score ? `<p>Income: ${properties.income_score}</p>` : ''}
                    ${properties.education_score ? `<p>Education: ${properties.education_score}</p>` : ''}
                    ${properties.housing_score ? `<p>Housing: ${properties.housing_score}</p>` : ''}
                    ${properties.labour_score ? `<p>Labour: ${properties.labour_score}</p>` : ''}
                `)
                .addTo(map);
        });

        // Change cursor on hover
        map.on('mouseenter', 'cwb-fill', () => {
            map.getCanvas().style.cursor = 'pointer';
        });
        map.on('mouseleave', 'cwb-fill', () => {
            map.getCanvas().style.cursor = '';
        });

        map.cwbLoaded = true;
        console.log(`✓ Loaded ${geojson.features.length} communities with CWB data`);
        return true;

    } catch (error) {
        console.error('❌ Error loading CWB data:', error);
        showNotification('Could not load Community Well-Being data: ' + error.message, 'error', 7000);
        return false;
    }
}

// Load CSICP funding data
async function loadCSICPFunding() {
    try {
        const response = await fetch(CONFIG.DATA_URLS.csicpFunding);
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        const geojson = await response.json();

        map.addSource('csicp', {
            type: 'geojson',
            data: geojson
        });

        // Add circle markers for CSICP projects
        map.addLayer({
            id: 'csicp-circles',
            type: 'circle',
            source: 'csicp',
            paint: {
                'circle-radius': 8,
                'circle-color': '#9e0142',
                'circle-stroke-width': 2,
                'circle-stroke-color': '#ffffff',
                'circle-opacity': 0.9
            }
        });

        // Initially hide the layer
        map.setLayoutProperty('csicp-circles', 'visibility', 'none');

        // Add click handler
        map.on('click', 'csicp-circles', (e) => {
            const properties = e.features[0].properties;
            const coordinates = e.features[0].geometry.coordinates.slice();

            new mapboxgl.Popup()
                .setLngLat(coordinates)
                .setHTML(`
                    <h4>${properties.project_name}</h4>
                    <p><strong>Group:</strong> ${properties.group_name}</p>
                    <p><strong>Community:</strong> ${properties.matched_community}</p>
                    <p><strong>Type:</strong> ${properties.project_type}</p>
                    <p><strong>Funding:</strong> $${parseInt(properties.funding).toLocaleString()}</p>
                `)
                .addTo(map);
        });

        // Change cursor on hover
        map.on('mouseenter', 'csicp-circles', () => {
            map.getCanvas().style.cursor = 'pointer';
        });
        map.on('mouseleave', 'csicp-circles', () => {
            map.getCanvas().style.cursor = '';
        });

        map.csicpLoaded = true;
        console.log(`✓ Loaded ${geojson.features.length} CSICP funding projects`);
        return true;

    } catch (error) {
        console.error('❌ Error loading CSICP funding:', error);
        showNotification('Could not load CSICP funding data: ' + error.message, 'error', 7000);
        return false;
    }
}

// Toggle layer visibility
function toggleLayer(layerId, visible) {
    console.log(`toggleLayer called: ${layerId} = ${visible}`);
    layerState[layerId] = visible;

    try {
        switch(layerId) {
            case 'treaty':
                if (map.getLayer('treaty-fill') && map.getLayer('treaty-outline')) {
                    map.setLayoutProperty('treaty-fill', 'visibility', visible ? 'visible' : 'none');
                    map.setLayoutProperty('treaty-outline', 'visibility', visible ? 'visible' : 'none');
                    console.log(`✓ Treaty boundary ${visible ? 'shown' : 'hidden'}`);
                } else {
                    console.warn('Treaty layers not found');
                }
                break;

            case 'reserves':
                if (map.getLayer('reserves-fill')) {
                    map.setLayoutProperty('reserves-fill', 'visibility', visible ? 'visible' : 'none');
                    map.setLayoutProperty('reserves-outline', 'visibility', visible ? 'visible' : 'none');
                    console.log(`✓ Reserves ${visible ? 'shown' : 'hidden'}`);
                } else {
                    console.warn('Reserves layers not found');
                }
                break;

            case 'charities':
                if (map.getLayer('charities-circles')) {
                    map.setLayoutProperty('charities-circles', 'visibility', visible ? 'visible' : 'none');
                    console.log(`✓ Charities ${visible ? 'shown' : 'hidden'}`);
                } else {
                    console.warn('Charities layer not found');
                }
                break;

            case 'communities':
                if (map.getLayer('communities-circles')) {
                    map.setLayoutProperty('communities-circles', 'visibility', visible ? 'visible' : 'none');
                    console.log(`✓ Communities ${visible ? 'shown' : 'hidden'}`);
                } else {
                    console.warn('Communities layer not found');
                }
                break;

            case 'ndvi':
                // Canvas-based rendering (only option with Mapbox GL JS)
                if (map.getLayer('ndvi-layer')) {
                    map.setLayoutProperty('ndvi-layer', 'visibility', visible ? 'visible' : 'none');
                    console.log(`✓ NDVI ${visible ? 'shown' : 'hidden'}`);
                } else {
                    console.warn('NDVI layer not found');
                }
                const ndviLegend = document.getElementById('ndvi-legend');
                if (ndviLegend) {
                    ndviLegend.style.display = visible ? 'block' : 'none';
                }
                break;

            case 'elevation':
                // Canvas-based rendering
                if (map.getLayer('elevation-layer')) {
                    map.setLayoutProperty('elevation-layer', 'visibility', visible ? 'visible' : 'none');
                    console.log(`✓ Elevation ${visible ? 'shown' : 'hidden'}`);
                } else {
                    console.warn('Elevation layer not found');
                }
                const elevLegend = document.getElementById('elevation-legend');
                if (elevLegend) {
                    elevLegend.style.display = visible ? 'block' : 'none';
                }
                break;

            case 'fire':
                if (map.getLayer('fire-fill') && map.getLayer('fire-outline')) {
                    map.setLayoutProperty('fire-fill', 'visibility', visible ? 'visible' : 'none');
                    map.setLayoutProperty('fire-outline', 'visibility', visible ? 'visible' : 'none');
                    console.log(`✓ Fire perimeters ${visible ? 'shown' : 'hidden'}`);

                    // Zoom to fire perimeters when shown
                    if (visible && map.firePerimetersBounds) {
                        map.fitBounds(map.firePerimetersBounds, {
                            padding: 50,
                            duration: 1000
                        });
                        console.log('Zooming to fire perimeters extent');
                    }
                } else {
                    console.warn('Fire layers not found');
                }
                const fireLegend = document.getElementById('fire-legend');
                if (fireLegend) {
                    fireLegend.style.display = visible ? 'block' : 'none';
                }
                break;

            case 'fuelType':
                if (map.getLayer('fueltype-layer')) {
                    map.setLayoutProperty('fueltype-layer', 'visibility', visible ? 'visible' : 'none');
                    console.log(`✓ Fuel types ${visible ? 'shown' : 'hidden'}`);
                } else {
                    console.warn('Fuel type layer not found');
                }
                const fuelLegend = document.getElementById('fuel-legend');
                if (fuelLegend) {
                    fuelLegend.style.display = visible ? 'block' : 'none';
                }
                break;

            case 'infrastructure':
                if (map.getLayer('infrastructure-circles')) {
                    map.setLayoutProperty('infrastructure-circles', 'visibility', visible ? 'visible' : 'none');
                    console.log(`✓ Infrastructure ${visible ? 'shown' : 'hidden'}`);
                } else {
                    console.warn('Infrastructure layer not found');
                }
                break;

            case 'waterAdvisories':
                if (map.getLayer('water-advisories-circles')) {
                    map.setLayoutProperty('water-advisories-circles', 'visibility', visible ? 'visible' : 'none');
                    console.log(`✓ Water advisories ${visible ? 'shown' : 'hidden'}`);
                } else {
                    console.warn('Water advisories layer not found');
                }
                break;

            case 'cwb':
                if (map.getLayer('cwb-fill') && map.getLayer('cwb-outline')) {
                    map.setLayoutProperty('cwb-fill', 'visibility', visible ? 'visible' : 'none');
                    map.setLayoutProperty('cwb-outline', 'visibility', visible ? 'visible' : 'none');
                    console.log(`✓ Community Well-Being ${visible ? 'shown' : 'hidden'}`);
                } else {
                    console.warn('CWB layers not found');
                }
                break;

            case 'csicpFunding':
                if (map.getLayer('csicp-circles')) {
                    map.setLayoutProperty('csicp-circles', 'visibility', visible ? 'visible' : 'none');
                    console.log(`✓ CSICP funding ${visible ? 'shown' : 'hidden'}`);
                } else {
                    console.warn('CSICP funding layer not found');
                }
                break;
        }
    } catch (error) {
        console.error(`Error toggling layer ${layerId}:`, error);
        showNotification(`Error toggling ${layerId} layer: ${error.message}`, 'error');
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

    // Change style (Mapbox GL JS handles authentication automatically)
    map.setStyle(styleUrl);

    // Restore all layers after style loads
    map.once('style.load', () => {
        console.log('Restoring layers after basemap change...');

        // Always reload treaty boundary (usually visible by default)
        loadTreatyBoundary().then(() => {
            if (!layerState.treaty) {
                toggleLayer('treaty', false);
            }
        });

        // Reload charities (always loaded on map init)
        loadCharities().then(() => {
            if (layerState.charities) {
                toggleLayer('charities', true);
            }
        });

        // Reload communities (always loaded on map init)
        loadCommunities().then(() => {
            if (layerState.communities) {
                toggleLayer('communities', true);
            }
        });

        // Reload NDVI if it was loaded before
        if (map.ndviLoaded) {
            loadNDVI().then(() => {
                if (layerState.ndvi) {
                    toggleLayer('ndvi', true);
                }
            });
        }

        // Reload elevation if it was loaded before
        if (map.elevationLoaded) {
            loadElevation().then(() => {
                if (layerState.elevation) {
                    toggleLayer('elevation', true);
                }
            });
        }

        // Reload fire perimeters if they were loaded before
        if (map.fireLoaded) {
            loadFirePerimeters().then(() => {
                if (layerState.fire) {
                    toggleLayer('fire', true);
                }
            });
        }

        // Reload fuel types if they were loaded before
        if (map.fuelTypeLoaded) {
            loadFuelType().then(() => {
                if (layerState.fuelType) {
                    toggleLayer('fuelType', true);
                }
            });
        }

        // Reload infrastructure if it was loaded before
        if (map.infrastructureLoaded) {
            loadInfrastructure().then(() => {
                if (layerState.infrastructure) {
                    toggleLayer('infrastructure', true);
                }
            });
        }

        // Reload water advisories if they were loaded before
        if (map.waterAdvisoriesLoaded) {
            loadWaterAdvisories().then(() => {
                if (layerState.waterAdvisories) {
                    toggleLayer('waterAdvisories', true);
                }
            });
        }

        // Reload CWB if it was loaded before
        if (map.cwbLoaded) {
            loadCWB().then(() => {
                if (layerState.cwb) {
                    toggleLayer('cwb', true);
                }
            });
        }

        // Reload CSICP funding if it was loaded before
        if (map.csicpLoaded) {
            loadCSICPFunding().then(() => {
                if (layerState.csicpFunding) {
                    toggleLayer('csicpFunding', true);
                }
            });
        }

        hideLoading();
        console.log('✓ All layers restored after basemap change');
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
    console.log('Treaty checkbox changed:', e.target.checked);
    toggleLayer('treaty', e.target.checked);
});

document.getElementById('layer-reserves').addEventListener('change', async (e) => {
    const checked = e.target.checked;

    // If turning on and not loaded yet, load it first
    if (checked && !map.reservesLoaded) {
        console.log('First time loading reserve boundaries...');
        const loaded = await loadReserves();
        if (!loaded) {
            // Loading failed, uncheck the box
            e.target.checked = false;
            return;
        }
    }

    toggleLayer('reserves', checked);
});

document.getElementById('layer-charities').addEventListener('change', (e) => {
    console.log('Charities checkbox changed:', e.target.checked);
    toggleLayer('charities', e.target.checked);
});

document.getElementById('layer-communities').addEventListener('change', (e) => {
    console.log('Communities checkbox changed:', e.target.checked);
    toggleLayer('communities', e.target.checked);
});

document.getElementById('layer-ndvi').addEventListener('change', async (e) => {
    const checked = e.target.checked;
    console.log('NDVI checkbox changed:', checked, 'Already loaded:', map.ndviLoaded);

    // If turning on and not loaded yet, load it first
    if (checked && !map.ndviLoaded) {
        console.log('First time loading NDVI...');
        const loaded = await loadNDVI();
        if (!loaded) {
            // Loading failed, uncheck the box
            console.error('NDVI loading failed, unchecking box');
            e.target.checked = false;
            return;
        }
    }

    toggleLayer('ndvi', checked);
});

document.getElementById('layer-elevation').addEventListener('change', async (e) => {
    const checked = e.target.checked;
    console.log('Elevation checkbox changed:', checked, 'Already loaded:', map.elevationLoaded);

    // If turning on and not loaded yet, load it first
    if (checked && !map.elevationLoaded) {
        console.log('First time loading elevation...');
        const loaded = await loadElevation();
        if (!loaded) {
            // Loading failed, uncheck the box
            console.error('Elevation loading failed, unchecking box');
            e.target.checked = false;
            return;
        }
    }

    toggleLayer('elevation', checked);
});

document.getElementById('layer-fire').addEventListener('change', async (e) => {
    const checked = e.target.checked;
    console.log('Fire checkbox changed:', checked, 'Already loaded:', map.fireLoaded);

    // If turning on and not loaded yet, load it first
    if (checked && !map.fireLoaded) {
        console.log('First time loading fire perimeters...');
        const loaded = await loadFirePerimeters();
        if (!loaded) {
            // Loading failed, uncheck the box
            console.error('Fire loading failed, unchecking box');
            e.target.checked = false;
            return;
        }
    }

    toggleLayer('fire', checked);
});

document.getElementById('layer-fuel').addEventListener('change', async (e) => {
    const checked = e.target.checked;
    console.log('Fuel type checkbox changed:', checked, 'Already loaded:', map.fuelTypeLoaded);

    // If turning on and not loaded yet, load it first
    if (checked && !map.fuelTypeLoaded) {
        console.log('First time loading fuel types...');
        const loaded = await loadFuelType();
        if (!loaded) {
            // Loading failed, uncheck the box
            console.error('Fuel type loading failed, unchecking box');
            e.target.checked = false;
            return;
        }
    }

    toggleLayer('fuelType', checked);
});

document.getElementById('layer-infrastructure').addEventListener('change', async (e) => {
    const checked = e.target.checked;

    if (checked && !map.infrastructureLoaded) {
        console.log('First time loading infrastructure...');
        const loaded = await loadInfrastructure();
        if (!loaded) {
            e.target.checked = false;
            return;
        }
    }

    toggleLayer('infrastructure', checked);
});

document.getElementById('layer-water-advisories').addEventListener('change', async (e) => {
    const checked = e.target.checked;

    if (checked && !map.waterAdvisoriesLoaded) {
        console.log('First time loading water advisories...');
        const loaded = await loadWaterAdvisories();
        if (!loaded) {
            e.target.checked = false;
            return;
        }
    }

    toggleLayer('waterAdvisories', checked);
});

document.getElementById('layer-cwb').addEventListener('change', async (e) => {
    const checked = e.target.checked;

    if (checked && !map.cwbLoaded) {
        console.log('First time loading Community Well-Being data...');
        const loaded = await loadCWB();
        if (!loaded) {
            e.target.checked = false;
            return;
        }
    }

    toggleLayer('cwb', checked);
});

document.getElementById('layer-csicp').addEventListener('change', async (e) => {
    const checked = e.target.checked;

    if (checked && !map.csicpLoaded) {
        console.log('First time loading CSICP funding...');
        const loaded = await loadCSICPFunding();
        if (!loaded) {
            e.target.checked = false;
            return;
        }
    }

    toggleLayer('csicpFunding', checked);
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
