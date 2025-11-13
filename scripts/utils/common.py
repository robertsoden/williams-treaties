"""
Common utilities for Williams Treaty data processing scripts.
"""

import os
import yaml
import logging
from pathlib import Path
from typing import Dict, Any, Optional
import geopandas as gpd
from shapely.geometry import box
import requests
from tqdm import tqdm


def setup_logging(name: str, level: int = logging.INFO) -> logging.Logger:
    """Set up logging configuration."""
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    return logging.getLogger(name)


def load_config(config_path: str = "config.yaml") -> Dict[str, Any]:
    """Load configuration from YAML file."""
    project_root = Path(__file__).parent.parent.parent
    config_file = project_root / config_path

    with open(config_file, 'r') as f:
        config = yaml.safe_load(f)

    return config


def get_project_root() -> Path:
    """Get the project root directory."""
    return Path(__file__).parent.parent.parent


def ensure_dir(path: Path) -> Path:
    """Ensure directory exists, create if it doesn't."""
    path.mkdir(parents=True, exist_ok=True)
    return path


def download_file(url: str, output_path: Path, chunk_size: int = 8192,
                  timeout: int = 300, desc: Optional[str] = None) -> bool:
    """
    Download a file from URL with progress bar.

    Args:
        url: URL to download from
        output_path: Path to save the file
        chunk_size: Download chunk size in bytes
        timeout: Request timeout in seconds
        desc: Description for progress bar

    Returns:
        True if successful, False otherwise
    """
    try:
        response = requests.get(url, stream=True, timeout=timeout)
        response.raise_for_status()

        total_size = int(response.headers.get('content-length', 0))

        ensure_dir(output_path.parent)

        with open(output_path, 'wb') as f:
            with tqdm(total=total_size, unit='B', unit_scale=True,
                     desc=desc or output_path.name) as pbar:
                for chunk in response.iter_content(chunk_size=chunk_size):
                    if chunk:
                        f.write(chunk)
                        pbar.update(len(chunk))

        return True

    except Exception as e:
        logging.error(f"Error downloading {url}: {e}")
        return False


def clip_to_aoi(gdf: gpd.GeoDataFrame, aoi: gpd.GeoDataFrame,
                buffer_meters: float = 0) -> gpd.GeoDataFrame:
    """
    Clip a GeoDataFrame to the area of interest.

    Args:
        gdf: GeoDataFrame to clip
        aoi: Area of interest GeoDataFrame
        buffer_meters: Buffer distance in meters (assumes projected CRS)

    Returns:
        Clipped GeoDataFrame
    """
    # Ensure same CRS
    if gdf.crs != aoi.crs:
        aoi = aoi.to_crs(gdf.crs)

    # Apply buffer if specified
    if buffer_meters > 0:
        aoi_buffered = aoi.copy()
        aoi_buffered['geometry'] = aoi_buffered.buffer(buffer_meters)
    else:
        aoi_buffered = aoi

    # Clip
    clipped = gpd.clip(gdf, aoi_buffered)

    return clipped


def reproject_gdf(gdf: gpd.GeoDataFrame, target_crs: str) -> gpd.GeoDataFrame:
    """Reproject GeoDataFrame to target CRS."""
    if gdf.crs is None:
        raise ValueError("Input GeoDataFrame has no CRS defined")

    if gdf.crs.to_string() != target_crs:
        return gdf.to_crs(target_crs)

    return gdf


def get_bounding_box(gdf: gpd.GeoDataFrame) -> tuple:
    """
    Get bounding box of a GeoDataFrame.

    Returns:
        Tuple of (minx, miny, maxx, maxy)
    """
    bounds = gdf.total_bounds
    return tuple(bounds)


def save_geojson(gdf: gpd.GeoDataFrame, output_path: Path) -> None:
    """Save GeoDataFrame as GeoJSON."""
    ensure_dir(output_path.parent)
    gdf.to_file(output_path, driver='GeoJSON')


def save_shapefile(gdf: gpd.GeoDataFrame, output_path: Path) -> None:
    """Save GeoDataFrame as Shapefile."""
    ensure_dir(output_path.parent)
    gdf.to_file(output_path, driver='ESRI Shapefile')


def load_aoi(config: Optional[Dict] = None) -> gpd.GeoDataFrame:
    """
    Load Area of Interest (AOI) boundary.

    Args:
        config: Configuration dictionary. If None, will load from config.yaml

    Returns:
        GeoDataFrame with AOI boundary
    """
    if config is None:
        config = load_config()

    project_root = get_project_root()
    aoi_path = project_root / config['directories']['boundaries'] / 'williams_treaty_aoi.geojson'

    if not aoi_path.exists():
        raise FileNotFoundError(
            f"AOI file not found at {aoi_path}. "
            "Please run 'python scripts/01_download_aoi.py' first."
        )

    aoi = gpd.read_file(aoi_path)
    return aoi


def print_gdf_info(gdf: gpd.GeoDataFrame, name: str = "GeoDataFrame") -> None:
    """Print information about a GeoDataFrame."""
    print(f"\n{name} Info:")
    print(f"  Rows: {len(gdf)}")
    print(f"  CRS: {gdf.crs}")
    print(f"  Bounds: {gdf.total_bounds}")
    print(f"  Columns: {list(gdf.columns)}")
    if len(gdf) > 0:
        print(f"  Geometry types: {gdf.geometry.geom_type.unique()}")
