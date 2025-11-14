/**
 * Layer Manager
 * Dynamically loads and manages map layers from YAML configuration
 */

class LayerManager {
    constructor(map, config) {
        this.map = map;
        this.config = config;
        this.loadedLayers = new Set();
        this.layerState = {};

        // Initialize layer state
        this.config.layers.forEach(layer => {
            this.layerState[layer.id] = layer.initial_visibility || false;
        });
    }

    /**
     * Generate UI controls from configuration
     */
    generateUI() {
        const controlPanel = document.getElementById('layer-control');

        // Clear existing content except header
        const header = controlPanel.querySelector('.control-header');
        const footer = controlPanel.querySelector('.control-footer');
        controlPanel.innerHTML = '';
        if (header) controlPanel.appendChild(header);

        // Group layers by category
        const categorizedLayers = {};
        this.config.categories.forEach(cat => {
            categorizedLayers[cat.id] = {
                ...cat,
                layers: []
            };
        });

        this.config.layers.forEach(layer => {
            if (categorizedLayers[layer.category]) {
                categorizedLayers[layer.category].layers.push(layer);
            }
        });

        // Sort categories by order
        const sortedCategories = Object.values(categorizedLayers)
            .sort((a, b) => a.order - b.order);

        // Generate UI for each category
        sortedCategories.forEach(category => {
            if (category.layers.length === 0) return;

            const section = document.createElement('div');
            section.className = 'control-section';
            section.innerHTML = `<h3>${category.name}</h3>`;

            category.layers.forEach(layer => {
                const layerGroup = this.createLayerControl(layer);
                section.appendChild(layerGroup);
            });

            controlPanel.appendChild(section);

            // Add legends for this category if needed
            category.layers.forEach(layer => {
                if (layer.legend) {
                    const legend = this.createLegend(layer);
                    controlPanel.appendChild(legend);
                }
            });
        });

        if (footer) controlPanel.appendChild(footer);

        // Attach event listeners
        this.attachEventListeners();
    }

    /**
     * Create UI control for a single layer
     */
    createLayerControl(layer) {
        const layerGroup = document.createElement('div');
        layerGroup.className = 'layer-group';

        const label = document.createElement('label');
        label.className = 'layer-item';

        const checkbox = document.createElement('input');
        checkbox.type = 'checkbox';
        checkbox.id = `layer-${layer.id}`;
        checkbox.checked = layer.initial_visibility || false;

        if (layer.requires_library && typeof parseGeoraster === 'undefined') {
            checkbox.disabled = true;
            label.classList.add('disabled');
        }

        const span = document.createElement('span');
        span.textContent = layer.name;

        const status = document.createElement('span');
        status.className = 'layer-status';
        status.id = `${layer.id}-status`;
        status.textContent = layer.status === 'available' ? '✓' : '⚙';

        label.appendChild(checkbox);
        label.appendChild(span);
        label.appendChild(status);

        layerGroup.appendChild(label);

        // Add info if present
        if (layer.info) {
            const info = document.createElement('div');
            info.className = 'layer-info';
            info.innerHTML = `<small>${layer.info.description}</small>`;
            layerGroup.appendChild(info);
        }

        return layerGroup;
    }

    /**
     * Create legend element for a layer
     */
    createLegend(layer) {
        const legend = document.createElement('div');
        legend.className = 'control-section legend';
        legend.id = `${layer.id}-legend`;
        legend.style.display = 'none';

        legend.innerHTML = `<h3>${layer.legend.title}</h3>`;

        if (layer.legend.type === 'gradient') {
            const gradientDiv = document.createElement('div');
            gradientDiv.className = 'legend-gradient';

            const bar = document.createElement('div');
            bar.className = 'legend-bar';
            bar.style.background = layer.legend.gradient;

            const labels = document.createElement('div');
            labels.className = 'legend-labels';

            layer.legend.stops.forEach(stop => {
                const labelSpan = document.createElement('span');
                labelSpan.innerHTML = `${stop.value}${stop.unit || ''}<br><small>${stop.label}</small>`;
                labels.appendChild(labelSpan);
            });

            gradientDiv.appendChild(bar);
            gradientDiv.appendChild(labels);
            legend.appendChild(gradientDiv);

        } else if (layer.legend.type === 'items') {
            const itemsDiv = document.createElement('div');
            itemsDiv.className = 'legend-items';

            layer.legend.items.forEach(item => {
                const itemDiv = document.createElement('div');
                itemDiv.className = 'legend-item';

                const colorSpan = document.createElement('span');
                colorSpan.className = 'legend-color';
                colorSpan.style.background = item.color;
                if (item.border) colorSpan.style.border = item.border;

                const labelSpan = document.createElement('span');
                labelSpan.textContent = item.label;

                itemDiv.appendChild(colorSpan);
                itemDiv.appendChild(labelSpan);
                itemsDiv.appendChild(itemDiv);
            });

            legend.appendChild(itemsDiv);
        }

        if (layer.legend.description) {
            const desc = document.createElement('p');
            desc.className = 'legend-description';
            desc.textContent = layer.legend.description;
            legend.appendChild(desc);
        }

        return legend;
    }

    /**
     * Attach event listeners to layer controls
     */
    attachEventListeners() {
        this.config.layers.forEach(layer => {
            const checkbox = document.getElementById(`layer-${layer.id}`);
            if (checkbox) {
                checkbox.addEventListener('change', async (e) => {
                    const checked = e.target.checked;

                    // If turning on and not loaded yet, load it first
                    if (checked && layer.lazy_load && !this.loadedLayers.has(layer.id)) {
                        console.log(`First time loading ${layer.name}...`);
                        const loaded = await this.loadLayer(layer);
                        if (!loaded) {
                            e.target.checked = false;
                            return;
                        }
                    }

                    this.toggleLayer(layer.id, checked);
                });
            }
        });
    }

    /**
     * Load a layer based on its configuration
     */
    async loadLayer(layer) {
        try {
            if (layer.type === 'point' || layer.type === 'polygon') {
                return await this.loadVectorLayer(layer);
            } else if (layer.type === 'raster') {
                return await this.loadRasterLayer(layer);
            }
        } catch (error) {
            console.error(`Error loading ${layer.name}:`, error);
            showNotification(`Could not load ${layer.name}: ${error.message}`, 'error', 7000);
            return false;
        }
    }

    /**
     * Load a vector (GeoJSON) layer
     */
    async loadVectorLayer(layer) {
        const response = await fetch(layer.data_url);
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        const geojson = await response.json();

        this.map.addSource(layer.id, {
            type: 'geojson',
            data: geojson
        });

        // Add appropriate layers based on geometry type
        if (layer.type === 'point') {
            this.addPointLayer(layer);
        } else if (layer.type === 'polygon') {
            this.addPolygonLayer(layer);
        }

        // Add click handlers
        this.addPopupHandlers(layer);

        this.loadedLayers.add(layer.id);
        console.log(`✓ Loaded ${geojson.features.length} features for ${layer.name}`);
        return true;
    }

    /**
     * Add a point layer (circles)
     */
    addPointLayer(layer) {
        const paint = {
            'circle-radius': layer.style.circle.radius,
            'circle-opacity': layer.style.circle.opacity,
            'circle-stroke-width': layer.style.circle.stroke_width,
            'circle-stroke-color': layer.style.circle.stroke_color
        };

        // Handle color styling
        if (typeof layer.style.circle.color === 'string') {
            paint['circle-color'] = layer.style.circle.color;
        } else if (layer.style.circle.color.type === 'categorical') {
            const colorExpr = ['match', ['get', layer.style.circle.color.field]];
            Object.entries(layer.style.circle.color.values).forEach(([key, value]) => {
                colorExpr.push(key, value);
            });
            colorExpr.push(layer.style.circle.color.default);
            paint['circle-color'] = colorExpr;
        } else if (layer.style.circle.color.type === 'conditional') {
            const colorExpr = ['case'];
            layer.style.circle.color.conditions.forEach(cond => {
                colorExpr.push(['==', ['get', layer.style.circle.color.field], cond.when]);
                colorExpr.push(cond.value);
            });
            // Add default color
            colorExpr.push(layer.style.circle.color.default || '#999999');
            paint['circle-color'] = colorExpr;
        }

        this.map.addLayer({
            id: `${layer.id}-circles`,
            type: 'circle',
            source: layer.id,
            paint: paint
        });

        // Initially hide if not visible
        if (!layer.initial_visibility) {
            this.map.setLayoutProperty(`${layer.id}-circles`, 'visibility', 'none');
        }
    }

    /**
     * Add a polygon layer (fill + outline)
     */
    addPolygonLayer(layer) {
        const beforeLayer = layer.style.before_layer || undefined;

        // Fill layer
        const fillPaint = {
            'fill-opacity': layer.style.fill.opacity
        };

        // Handle fill color
        if (typeof layer.style.fill.color === 'string') {
            fillPaint['fill-color'] = layer.style.fill.color;
        } else if (layer.style.fill.color.type === 'interpolate') {
            const interpolateExpr = [
                'interpolate',
                ['linear'],
                ['get', layer.style.fill.color.field]
            ];
            layer.style.fill.color.stops.forEach(([value, color]) => {
                interpolateExpr.push(value, color);
            });
            fillPaint['fill-color'] = interpolateExpr;
        }

        this.map.addLayer({
            id: `${layer.id}-fill`,
            type: 'fill',
            source: layer.id,
            paint: fillPaint
        }, beforeLayer);

        // Outline layer
        this.map.addLayer({
            id: `${layer.id}-outline`,
            type: 'line',
            source: layer.id,
            paint: {
                'line-color': layer.style.outline.color,
                'line-width': layer.style.outline.width,
                'line-opacity': layer.style.outline.opacity
            }
        }, beforeLayer);

        // Initially hide if not visible
        if (!layer.initial_visibility) {
            this.map.setLayoutProperty(`${layer.id}-fill`, 'visibility', 'none');
            this.map.setLayoutProperty(`${layer.id}-outline`, 'visibility', 'none');
        }
    }

    /**
     * Load a raster (GeoTIFF) layer
     */
    async loadRasterLayer(layer) {
        if (typeof parseGeoraster === 'undefined') {
            throw new Error('GeoRaster library not loaded');
        }

        showLoading();

        const response = await fetch(layer.data_url);
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        const arrayBuffer = await response.arrayBuffer();
        const georaster = await parseGeoraster(arrayBuffer);

        await this.renderRasterWithCanvas(layer, georaster);

        this.loadedLayers.add(layer.id);
        hideLoading();
        console.log(`✓ ${layer.name} loaded successfully`);
        return true;
    }

    /**
     * Render raster using canvas
     */
    async renderRasterWithCanvas(layer, georaster) {
        console.log(`Using canvas renderer for ${layer.name}`);

        const canvas = document.createElement('canvas');
        canvas.width = georaster.width;
        canvas.height = georaster.height;
        const ctx = canvas.getContext('2d');
        const imageData = ctx.createImageData(canvas.width, canvas.height);

        // Get color function based on config
        const getColor = this.createColorFunction(layer.style.color_scale);

        // Render each pixel
        for (let y = 0; y < georaster.height; y++) {
            for (let x = 0; x < georaster.width; x++) {
                const value = georaster.values[0][y][x];
                const color = getColor(value);
                const idx = (y * canvas.width + x) * 4;
                imageData.data[idx] = color[0];     // R
                imageData.data[idx + 1] = color[1]; // G
                imageData.data[idx + 2] = color[2]; // B
                imageData.data[idx + 3] = color[3]; // A
            }
        }

        ctx.putImageData(imageData, 0, 0);

        // Handle coordinate swapping if needed
        let xmin = georaster.xmin;
        let xmax = georaster.xmax;
        let ymin = georaster.ymin;
        let ymax = georaster.ymax;

        if (Math.abs(xmin) < 90 && Math.abs(xmax) < 90 &&
            Math.abs(ymin) > 90 && Math.abs(ymax) > 90) {
            console.warn('Detected potential lat/lon swap, swapping coordinates');
            [xmin, ymin] = [ymin, xmin];
            [xmax, ymax] = [ymax, xmax];
        }

        // Special handling for elevation layer alignment
        if (layer.id === 'elevation') {
            const pixelHeight = (ymax - ymin) / georaster.height;
            const latShift = pixelHeight * 45.36;
            ymin -= latShift;
            ymax -= latShift;
        }

        const coordinates = [
            [xmin, ymax], // top-left
            [xmax, ymax], // top-right
            [xmax, ymin], // bottom-right
            [xmin, ymin]  // bottom-left
        ];

        this.map.addSource(`${layer.id}-raster`, {
            type: 'image',
            url: canvas.toDataURL(),
            coordinates: coordinates
        });

        this.map.addLayer({
            id: `${layer.id}-layer`,
            type: 'raster',
            source: `${layer.id}-raster`,
            paint: {
                'raster-opacity': layer.style.opacity
            }
        }, layer.style.before_layer);

        // Initially hide if not visible
        if (!layer.initial_visibility) {
            this.map.setLayoutProperty(`${layer.id}-layer`, 'visibility', 'none');
        }
    }

    /**
     * Create color function from color scale configuration
     */
    createColorFunction(colorScale) {
        if (colorScale.type === 'continuous') {
            return (value) => {
                const steps = colorScale.steps;
                for (let i = 0; i < steps.length - 1; i++) {
                    if (value < steps[i][0]) return steps[0][1];
                    if (value >= steps[i][0] && value < steps[i + 1][0]) {
                        return steps[i][1];
                    }
                }
                return steps[steps.length - 1][1];
            };
        } else if (colorScale.type === 'categorical') {
            return (value) => {
                for (const [range, color] of Object.entries(colorScale.values)) {
                    if (range.includes('-')) {
                        const [min, max] = range.split('-').map(Number);
                        if (value >= min && value <= max) return color;
                    } else if (value === parseInt(range)) {
                        return color;
                    }
                }
                return colorScale.default;
            };
        }
    }

    /**
     * Add popup click handlers for a layer
     */
    addPopupHandlers(layer) {
        if (!layer.popup) return;

        const layerId = layer.type === 'point' ? `${layer.id}-circles` : `${layer.id}-fill`;

        this.map.on('click', layerId, (e) => {
            const properties = e.features[0].properties;
            const coordinates = layer.type === 'point'
                ? e.features[0].geometry.coordinates.slice()
                : e.lngLat;

            const html = this.generatePopupHTML(layer, properties);

            new mapboxgl.Popup()
                .setLngLat(coordinates)
                .setHTML(html)
                .addTo(this.map);
        });

        // Change cursor on hover
        this.map.on('mouseenter', layerId, () => {
            this.map.getCanvas().style.cursor = 'pointer';
        });
        this.map.on('mouseleave', layerId, () => {
            this.map.getCanvas().style.cursor = '';
        });
    }

    /**
     * Generate popup HTML from configuration
     */
    generatePopupHTML(layer, properties) {
        let html = '<div class="popup-content">';

        // Title
        let title = layer.popup.title || '';
        if (layer.popup.title_field) {
            title = properties[layer.popup.title_field] || layer.popup.title_default || '';
        } else if (layer.popup.title_fields) {
            for (const field of layer.popup.title_fields) {
                if (properties[field]) {
                    title = properties[field];
                    break;
                }
            }
            if (!title) title = layer.popup.title_default || '';
        }
        html += `<h4>${title}</h4>`;

        // Fields
        layer.popup.fields.forEach(fieldConfig => {
            let value = null;
            let label = fieldConfig.label;

            // Get value from properties
            if (fieldConfig.field) {
                value = properties[fieldConfig.field];
            } else if (fieldConfig.fields) {
                for (const f of fieldConfig.fields) {
                    if (properties[f]) {
                        value = properties[f];
                        break;
                    }
                }
            } else if (fieldConfig.format && fieldConfig.format.includes('{') && !fieldConfig.format.includes('{value')) {
                // Template format like '{city}, {province}'
                value = fieldConfig.format.replace(/\{(\w+)\}/g, (match, key) => {
                    return properties[key] || '';
                });
            }

            // Special handling for is_active field
            if (fieldConfig.field === 'is_active' && (fieldConfig.format_active || fieldConfig.format_inactive)) {
                value = properties[fieldConfig.field]
                    ? fieldConfig.format_active
                    : fieldConfig.format_inactive;
            }

            // Skip if optional and no value
            if (fieldConfig.optional && !value && value !== 0) return;

            // Skip if hide_if condition met
            if (fieldConfig.hide_if && value === fieldConfig.hide_if) return;

            // Calculate hectares from area if specified
            if (fieldConfig.calculate_ha_from && properties[fieldConfig.calculate_ha_from]) {
                const area_m2 = properties[fieldConfig.calculate_ha_from];
                value = (area_m2 / 10000).toFixed(2) + ' ha';
            }

            // Apply formatting
            if (value !== null && value !== undefined && fieldConfig.format) {
                if (fieldConfig.format.includes('{value')) {
                    value = fieldConfig.format.replace(/\{value([^}]*)\}/g, (match, formatSpec) => {
                        let result = value;
                        if (formatSpec.includes(':')) {
                            // Format specifier like :,.0f or :.2f
                            const num = parseFloat(value);
                            if (!isNaN(num)) {
                                if (formatSpec.includes(',')) {
                                    const decimals = formatSpec.match(/\.(\d+)f/);
                                    const decimalPlaces = decimals ? parseInt(decimals[1]) : 0;
                                    result = num.toLocaleString(undefined, {
                                        minimumFractionDigits: decimalPlaces,
                                        maximumFractionDigits: decimalPlaces
                                    });
                                } else {
                                    const decimals = formatSpec.match(/\.(\d+)f/);
                                    if (decimals) {
                                        result = num.toFixed(parseInt(decimals[1]));
                                    }
                                }
                            }
                        }
                        return result;
                    });
                } else if (!fieldConfig.format_active && !fieldConfig.format_inactive) {
                    // Simple format string
                    value = fieldConfig.format.replace('{value}', value);
                }
            }

            // Apply default if no value
            if (!value && value !== 0 && fieldConfig.default) {
                value = fieldConfig.default;
            }

            // Truncate if specified
            if (value && fieldConfig.truncate && typeof value === 'string' && value.length > fieldConfig.truncate) {
                value = value.substring(0, fieldConfig.truncate) + '...';
            }

            // Format as link if specified
            if (fieldConfig.type === 'link' && value) {
                value = `<a href="${value}" target="_blank">Website</a>`;
            }

            if (value || value === 0) {
                html += `<p><strong>${label}:</strong> ${value}</p>`;
            }
        });

        html += '</div>';
        return html;
    }

    /**
     * Toggle layer visibility
     */
    toggleLayer(layerId, visible) {
        console.log(`toggleLayer: ${layerId} = ${visible}`);
        this.layerState[layerId] = visible;

        const layer = this.config.layers.find(l => l.id === layerId);
        if (!layer) {
            console.warn(`Layer ${layerId} not found in config`);
            return;
        }

        try {
            if (layer.type === 'point') {
                const mapLayerId = `${layerId}-circles`;
                if (this.map.getLayer(mapLayerId)) {
                    this.map.setLayoutProperty(mapLayerId, 'visibility', visible ? 'visible' : 'none');
                    console.log(`✓ ${layer.name} ${visible ? 'shown' : 'hidden'}`);
                }
            } else if (layer.type === 'polygon') {
                if (this.map.getLayer(`${layerId}-fill`)) {
                    this.map.setLayoutProperty(`${layerId}-fill`, 'visibility', visible ? 'visible' : 'none');
                    this.map.setLayoutProperty(`${layerId}-outline`, 'visibility', visible ? 'visible' : 'none');
                    console.log(`✓ ${layer.name} ${visible ? 'shown' : 'hidden'}`);
                }
            } else if (layer.type === 'raster') {
                if (this.map.getLayer(`${layerId}-layer`)) {
                    this.map.setLayoutProperty(`${layerId}-layer`, 'visibility', visible ? 'visible' : 'none');
                    console.log(`✓ ${layer.name} ${visible ? 'shown' : 'hidden'}`);
                }
            }

            // Toggle legend if exists
            if (layer.legend) {
                const legendEl = document.getElementById(`${layerId}-legend`);
                if (legendEl) {
                    legendEl.style.display = visible ? 'block' : 'none';
                }
            }

            // Handle special behaviors
            if (visible && layer.zoom_on_show) {
                this.map.fitBounds(layer.zoom_on_show.bounds, {
                    padding: layer.zoom_on_show.padding,
                    duration: 1000
                });
            }

        } catch (error) {
            console.error(`Error toggling layer ${layerId}:`, error);
            showNotification(`Error toggling ${layer.name}: ${error.message}`, 'error');
        }
    }

    /**
     * Reload layers after basemap change
     */
    async reloadLayers() {
        console.log('Reloading layers after basemap change...');

        for (const layer of this.config.layers) {
            // Skip if never loaded
            if (layer.lazy_load && !this.loadedLayers.has(layer.id)) {
                continue;
            }

            // Reload the layer
            await this.loadLayer(layer);

            // Restore visibility state
            if (this.layerState[layer.id]) {
                this.toggleLayer(layer.id, true);
            }
        }

        console.log('✓ All layers reloaded');
    }
}

// Export for use in other modules
if (typeof module !== 'undefined' && module.exports) {
    module.exports = LayerManager;
}
