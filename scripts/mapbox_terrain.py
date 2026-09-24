"""Shadows-only hillshade from the Mapbox Terrain DEM, for static maps.

This reproduces what the web map does. The `hillshade` layer in
web/config/layers.yaml renders a native Mapbox GL hillshade over
mapbox.mapbox-terrain-dem-v1 with transparent highlights and a dark shadow
colour, so relief is added as shadow only -- the basemap underneath keeps its
full strength and flat ground stays untouched.

The naive static equivalent (generic shaded-relief tiles underneath a dimmed
basemap) washes the whole sheet out, because it darkens flat ground too. Here we
fetch the same DEM the site uses, compute the shading ourselves, and composite
only the shadow term over an undimmed basemap.

Requires a Mapbox token: read from web/js/config.js, or the MAPBOX_TOKEN
environment variable.
"""

import io
import math
import os
import re
from pathlib import Path

import numpy as np
import requests
from PIL import Image
from scipy.ndimage import gaussian_filter

PROJECT_ROOT = Path(__file__).resolve().parent.parent
CONFIG_JS = PROJECT_ROOT / "web" / "js" / "config.js"
CACHE_DIR = PROJECT_ROOT / ".cache" / "terrain_dem"

DEM_TILESET = "mapbox.mapbox-terrain-dem-v1"
EARTH_CIRCUMFERENCE = 40_075_016.686
TILE_PX = 256

# Defaults mirror the `hillshade` layer's paint properties in layers.yaml.
ILLUMINATION_DIRECTION = 335
SHADOW_RGB = (45, 40, 30)
SHADOW_OPACITY = 0.75
EXAGGERATION = 1.0
# Mapbox GL does not expose a light altitude; 45 deg matches its look closely.
LIGHT_ALTITUDE = 45


def mapbox_token():
    """Token from the environment, else from the (gitignored) web config."""
    token = os.environ.get("MAPBOX_TOKEN")
    if token:
        return token
    if CONFIG_JS.exists():
        m = re.search(r"MAPBOX_TOKEN:\s*['\"]([^'\"]+)['\"]", CONFIG_JS.read_text())
        if m and not m.group(1).startswith("YOUR_"):
            return m.group(1)
    raise RuntimeError(
        "No Mapbox token found. Set MAPBOX_TOKEN, or add one to web/js/config.js."
    )


def _tile_indices(bounds_3857, zoom):
    """Inclusive tile x/y range covering a Web Mercator bounding box."""
    minx, miny, maxx, maxy = bounds_3857
    n = 2 ** zoom
    origin = EARTH_CIRCUMFERENCE / 2

    def to_tile(x, y):
        tx = int((x + origin) / EARTH_CIRCUMFERENCE * n)
        ty = int((origin - y) / EARTH_CIRCUMFERENCE * n)
        return min(max(tx, 0), n - 1), min(max(ty, 0), n - 1)

    x0, y0 = to_tile(minx, maxy)  # top-left
    x1, y1 = to_tile(maxx, miny)  # bottom-right
    return x0, y0, x1, y1


def _fetch_tile(z, x, y, token, session):
    """One terrain-RGB tile, memoised on disk (tiles are immutable)."""
    cache_path = CACHE_DIR / f"{z}_{x}_{y}.png"
    if cache_path.exists():
        return Image.open(cache_path).convert("RGB")

    url = f"https://api.mapbox.com/v4/{DEM_TILESET}/{z}/{x}/{y}.pngraw"
    for attempt in range(3):
        try:
            r = session.get(url, params={"access_token": token}, timeout=60)
            if r.status_code == 404:
                return None  # no coverage (ocean); treated as flat
            r.raise_for_status()
            cache_path.parent.mkdir(parents=True, exist_ok=True)
            cache_path.write_bytes(r.content)
            return Image.open(io.BytesIO(r.content)).convert("RGB")
        except requests.RequestException:
            if attempt == 2:
                raise
    return None


def fetch_dem(bounds_3857, zoom, token=None, verbose=True):
    """Mosaic terrain tiles into an elevation array.

    Returns (elevation_m, extent) where extent is the array's true Web Mercator
    (minx, maxx, miny, maxy) -- tile edges, so slightly larger than the request.
    """
    token = token or mapbox_token()
    x0, y0, x1, y1 = _tile_indices(bounds_3857, zoom)
    nx, ny = x1 - x0 + 1, y1 - y0 + 1
    if verbose:
        print(f"Terrain DEM: {nx}x{ny} = {nx * ny} tiles at zoom {zoom}")

    rgb = np.zeros((ny * TILE_PX, nx * TILE_PX, 3), dtype=np.float64)
    session = requests.Session()
    for j, ty in enumerate(range(y0, y1 + 1)):
        for i, tx in enumerate(range(x0, x1 + 1)):
            tile = _fetch_tile(zoom, tx, ty, token, session)
            if tile is None:
                continue
            rgb[j * TILE_PX:(j + 1) * TILE_PX, i * TILE_PX:(i + 1) * TILE_PX] = tile

    # Terrain-RGB decoding, per Mapbox's published formula.
    elev = -10000 + (rgb[..., 0] * 65536 + rgb[..., 1] * 256 + rgb[..., 2]) * 0.1
    # 404/ocean tiles decode to -10000; flatten them to sea level.
    elev[elev < -1000] = 0.0

    n = 2 ** zoom
    tile_span = EARTH_CIRCUMFERENCE / n
    origin = EARTH_CIRCUMFERENCE / 2
    extent = (
        x0 * tile_span - origin,
        (x1 + 1) * tile_span - origin,
        origin - (y1 + 1) * tile_span,
        origin - y0 * tile_span,
    )
    return elev, extent


def shadows_only(elev, extent, zoom, exaggeration=EXAGGERATION,
                 azimuth=ILLUMINATION_DIRECTION, altitude=LIGHT_ALTITUDE,
                 shadow_rgb=SHADOW_RGB, opacity=SHADOW_OPACITY, smooth=1.0):
    """RGBA overlay that darkens only the shaded side of slopes.

    Flat ground gets alpha 0, so the basemap below shows through untouched --
    the static equivalent of Mapbox's transparent-highlight hillshade.
    """
    # Web Mercator over-measures distance by 1/cos(lat); correct at the centre
    # latitude so slopes are computed against real-world ground distance.
    lat = math.degrees(
        2 * math.atan(math.exp(((extent[2] + extent[3]) / 2) / 6378137.0)) - math.pi / 2
    )
    px_m = (EARTH_CIRCUMFERENCE / (2 ** zoom * TILE_PX)) * math.cos(math.radians(lat))

    if smooth:
        # The DEM is quantised to 0.1 m, which makes gradients blocky at tile
        # resolution; a light blur keeps the shading readable, not stippled.
        elev = gaussian_filter(elev, smooth)

    dzdy, dzdx = np.gradient(elev, px_m)
    slope = np.arctan(exaggeration * np.hypot(dzdx, dzdy))
    aspect = np.arctan2(dzdy, -dzdx)

    zenith = math.radians(90 - altitude)
    az = math.radians(360 - azimuth + 90)  # compass bearing -> math convention
    illum = (np.cos(zenith) * np.cos(slope)
             + np.sin(zenith) * np.sin(slope) * np.cos(az - aspect))

    # Flat ground illuminates at cos(zenith); shade is the shortfall below it.
    flat = math.cos(zenith)
    strength = np.clip((flat - illum) / flat, 0.0, 1.0)

    rgba = np.zeros((*elev.shape, 4), dtype=np.float64)
    rgba[..., 0] = shadow_rgb[0] / 255
    rgba[..., 1] = shadow_rgb[1] / 255
    rgba[..., 2] = shadow_rgb[2] / 255
    rgba[..., 3] = strength * opacity
    return rgba


def add_hillshade(ax, zoom, zorder=3, exaggeration=EXAGGERATION, verbose=True, **kwargs):
    """Draw a shadows-only hillshade over whatever is already on `ax`."""
    x0, x1 = ax.get_xlim()
    y0, y1 = ax.get_ylim()
    elev, extent = fetch_dem((x0, y0, x1, y1), zoom, verbose=verbose)
    rgba = shadows_only(elev, extent, zoom, exaggeration=exaggeration, **kwargs)
    ax.imshow(
        rgba,
        extent=(extent[0], extent[1], extent[2], extent[3]),
        origin="upper", zorder=zorder, interpolation="bilinear",
    )
    ax.set_xlim(x0, x1)
    ax.set_ylim(y0, y1)
