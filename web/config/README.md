# Layer Configuration System

The Williams Treaty map uses a YAML-based configuration system to define all map layers. This makes it easy to add, modify, or remove layers without changing JavaScript code.

## Configuration File

The main configuration file is `layers.yaml` in this directory.

## Structure

### Categories

Categories organize layers in the UI:

```yaml
categories:
  - id: boundaries
    name: Boundaries
    order: 1
```

- `id`: Unique identifier for the category
- `name`: Display name shown in the UI
- `order`: Controls the order categories appear in the control panel

### Layers

Each layer is defined with these properties:

```yaml
layers:
  - id: layer_id              # Unique identifier
    name: Layer Display Name   # Name shown in UI
    category: boundaries       # Category this layer belongs to
    type: point|polygon|raster # Layer geometry type
    data_url: /path/to/data   # URL to the data file
    initial_visibility: false  # Whether layer is visible on load
    status: available          # Status indicator (available, requires_download, etc.)
    active: true              # If false, layer is hidden from UI but config is retained (default: true)
    lazy_load: true           # If true, only load when user enables layer
```

#### Layer Activation

The `active` field controls whether a layer appears in the UI:

- **`active: true`** (default) - Layer appears in the UI and can be loaded by users
- **`active: false`** - Layer configuration is retained but completely hidden from the UI

Use `active: false` to:
- Temporarily disable layers without deleting their configuration
- Keep work-in-progress layer configs
- Maintain seasonal or conditional layers (e.g., snow cover in winter only)
- Test configurations before making them public
- Keep backup layer configs for different data sources

**Example:**
```yaml
- id: snow_cover
  name: Snow Cover (Winter Only)
  active: false  # Disabled until winter season
  category: weather
  type: raster
  data_url: /data/snow_cover.tif
  # ... rest of configuration preserved ...
```

When a layer is inactive:
- It will not appear in the layer control panel
- It will not be loaded, even if `initial_visibility: true`
- The configuration remains in the file for easy re-activation
- Console will show: `⊘ Layer "Name" is inactive, skipping UI generation`

## Layer Types

### Point Layers

Point layers display GeoJSON point features as circles:

```yaml
- id: communities
  type: point
  style:
    circle:
      radius: 8
      color: '#d73027'
      opacity: 0.9
      stroke_width: 2
      stroke_color: '#ffffff'
```

#### Data-Driven Styling

**Categorical colors** based on a property:

```yaml
style:
  circle:
    color:
      type: categorical
      field: category
      values:
        Housing: '#e41a1c'
        Water: '#377eb8'
        Fire Protection: '#ff7f00'
      default: '#999999'
```

**Conditional colors** based on boolean:

```yaml
style:
  circle:
    color:
      type: conditional
      field: is_active
      conditions:
        - when: true
          value: '#d73027'  # Red
        - when: false
          value: '#91cf60'  # Green
```

### Polygon Layers

Polygon layers display GeoJSON polygon features with fill and outline:

```yaml
- id: reserves
  type: polygon
  style:
    fill:
      color: '#fc8d59'
      opacity: 0.3
    outline:
      color: '#d73027'
      width: 2
      opacity: 0.8
    before_layer: treaty-fill  # Optional: layer ordering
```

#### Choropleth Maps

Use interpolated colors for numeric data:

```yaml
style:
  fill:
    color:
      type: interpolate
      field: cwb_score
      stops:
        - [60, '#d73027']  # Low - red
        - [70, '#fee08b']  # Medium - yellow
        - [80, '#91cf60']  # High - green
    opacity: 0.6
```

### Raster Layers

Raster layers display GeoTIFF files rendered with custom color scales:

```yaml
- id: elevation
  type: raster
  requires_library: georaster  # Requires GeoRaster.js
  style:
    opacity: 0.6
    color_scale:
      type: continuous
      steps:
        - [75, [8, 48, 107, 180]]     # value, [R, G, B, A]
        - [150, [33, 113, 181, 180]]
        - [300, [107, 174, 214, 180]]
```

**Categorical rasters** (e.g., fuel types):

```yaml
style:
  color_scale:
    type: categorical
    values:
      0: [200, 200, 200, 100]      # Non-fuel
      1-4: [34, 139, 34, 180]      # Coniferous
      11-18: [255, 215, 0, 180]    # Deciduous
    default: [139, 69, 19, 180]
```

## Popups

Configure what information appears when users click features:

```yaml
popup:
  title_field: name                    # Field to use as popup title
  title_default: Default Title         # Fallback if field is empty
  fields:
    - label: Population
      field: population
      format: '~{value:,.0f}'         # Number formatting

    - label: Location
      format: '{city}, {province}'     # Template string

    - label: Website
      field: website
      type: link                       # Render as hyperlink

    - label: Description
      field: description
      truncate: 200                    # Truncate long text
      optional: true                   # Hide if no value
```

### Field Configuration

- `label`: Label shown in popup
- `field`: Property name to display
- `fields`: Array of field names (uses first non-empty)
- `format`: Format string with placeholders
- `default`: Default value if field is empty
- `optional`: Skip field if value is empty
- `truncate`: Max character length
- `type`: Special rendering (e.g., "link")

### Format Specifiers

- `{value}` - Simple substitution
- `{value:,.0f}` - Number with thousand separators, 0 decimals
- `{value:.2f}` - Number with 2 decimal places
- `{city}, {province}` - Template with multiple fields

### Special Formatting

**Conditional formatting** (for boolean fields):

```yaml
- label: Status
  field: is_active
  format_active: '<span style="color:#d73027;font-weight:bold">ACTIVE</span>'
  format_inactive: '<span style="color:#91cf60;font-weight:bold">Lifted</span>'
```

**Calculated values**:

```yaml
- label: Area
  field: area
  calculate_ha_from: area  # Convert m² to hectares
```

## Legends

Add legends for layers that need visual guides:

### Gradient Legend

For continuous data (NDVI, elevation):

```yaml
legend:
  type: gradient
  title: Elevation Legend
  gradient: linear-gradient(to right, #08306b, #2171b5, #c6dbef, #fdd0a2)
  stops:
    - value: 7
      label: Water
      unit: m
    - value: 150
      label: Lowlands
      unit: m
  description: SRTM 30m elevation data
```

### Items Legend

For categorical data (fuel types, fire boundaries):

```yaml
legend:
  type: items
  title: Fuel Type Legend
  items:
    - color: rgba(34, 139, 34, 0.7)
      label: Coniferous (C-1 to C-4)
    - color: rgba(255, 215, 0, 0.7)
      label: Deciduous (D-1, D-2)
  description: Canadian FBP System fuel types
```

## Layer Info

Add descriptive text shown in the layer control:

```yaml
info:
  description: 186 environmental organizations
```

## Special Behaviors

### Zoom on Show

Automatically zoom to layer extent when enabled:

```yaml
zoom_on_show:
  bounds: [[-78.71, 45.81], [-76.92, 46.38]]  # [[west, south], [east, north]]
  padding: 50
```

### Lazy Loading

Defer loading until user enables the layer:

```yaml
lazy_load: true
```

### Required Libraries

Specify JavaScript libraries needed:

```yaml
requires_library: georaster  # For raster layers
```

## Adding a New Layer

1. **Prepare your data file** in GeoJSON or GeoTIFF format
2. **Add to `layers.yaml`** under the `layers` section
3. **Choose appropriate category** or create a new one
4. **Define styling** based on layer type
5. **Configure popup** to show relevant information
6. **Add legend** if the layer needs visual explanation
7. **Test** by opening the map in a browser

The layer will automatically appear in the UI and be fully functional!

## Example: Adding a New Point Layer

```yaml
- id: schools
  name: Schools
  category: communities
  type: point
  data_url: /data/schools.geojson
  initial_visibility: false
  status: available
  lazy_load: true

  style:
    circle:
      radius: 6
      color: '#4daf4a'
      opacity: 0.8
      stroke_width: 2
      stroke_color: '#ffffff'

  popup:
    title_field: name
    title_default: School
    fields:
      - label: Type
        field: school_type
      - label: Students
        field: enrollment
        format: '{value:,.0f}'
      - label: Address
        field: address

  info:
    description: Educational facilities in treaty area
```

## Troubleshooting

### Layer Not Appearing

- **Check the `active` field** - Ensure `active` is not set to `false` (or omit it, defaults to `true`)
- Check that `status: available` is set
- Verify `data_url` path is correct
- Check browser console for error messages
  - Inactive layers will show: `⊘ Layer "Name" is inactive, skipping UI generation`
- Ensure data file is valid GeoJSON/GeoTIFF

### Styling Not Applied

- Verify field names match your data properties
- Check color format (hex strings or RGBA arrays)
- For data-driven styles, ensure the field exists in all features

### Popup Not Showing

- Verify `popup` section is defined
- Check that field names match data properties
- Ensure click handlers are working (check console)

### Raster Layer Not Loading

- Ensure GeoRaster library is loaded (check console)
- Verify GeoTIFF file is valid
- Check that `requires_library: georaster` is set
- Color scale must match data value range
