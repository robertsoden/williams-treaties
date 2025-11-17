#!/usr/bin/env python3
"""
Simple web server for Williams Treaty Territories map application.

This serves the web application and data files with proper CORS headers
to allow client-side data loading.

Usage:
    python web/server.py [--port PORT]
"""

import os
import sys
import argparse
from pathlib import Path
from flask import Flask, send_from_directory, send_file, jsonify, redirect
from flask_cors import CORS
import yaml
import requests
from urllib.parse import urljoin

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

# Get project root
PROJECT_ROOT = Path(__file__).parent.parent
WEB_DIR = PROJECT_ROOT / 'web'
DATA_DIR = PROJECT_ROOT / 'data'
CONFIG_DIR = WEB_DIR / 'config'


def load_data_source_config():
    """Load data source configuration."""
    config_file = CONFIG_DIR / 'data_source.yaml'

    if not config_file.exists():
        # Default configuration if file doesn't exist
        return {
            'data_source': {
                'base_url': '',
                'fallback_to_local': True
            },
            'use_env_override': True,
            'env_var_name': 'DATA_SOURCE_URL'
        }

    with open(config_file, 'r') as f:
        return yaml.safe_load(f)


def get_data_base_url():
    """Get the base URL for data files, checking environment variables."""
    config = load_data_source_config()

    # Check for environment variable override
    if config.get('use_env_override', True):
        env_var = config.get('env_var_name', 'DATA_SOURCE_URL')
        env_url = os.environ.get(env_var)
        if env_url:
            print(f"Using data source from {env_var}: {env_url}")
            return env_url

    # Use configured base URL
    base_url = config.get('data_source', {}).get('base_url', '')
    return base_url


# Load data source configuration at startup
DATA_BASE_URL = get_data_base_url()
DATA_SOURCE_CONFIG = load_data_source_config()


def is_external_url(url):
    """Check if URL is external (starts with http:// or https://)."""
    return url.startswith('http://') or url.startswith('https://')


@app.route('/')
def index():
    """Serve the main map application."""
    return send_file(WEB_DIR / 'index.html')


@app.route('/<path:filename>')
def serve_web_files(filename):
    """Serve static web files (CSS, JS, etc.)."""
    return send_from_directory(WEB_DIR, filename)


@app.route('/data/<path:filepath>')
def serve_data(filepath):
    """
    Serve data files (GeoJSON, GeoTIFF, etc.).

    This handles serving files from either:
    1. External data repository (redirects to external URL)
    2. Local data directory (serves file directly)
    """
    # If we have a base URL configured, redirect to external source
    if DATA_BASE_URL:
        # Construct external URL
        external_url = urljoin(DATA_BASE_URL + '/', filepath)
        print(f"Redirecting data request to: {external_url}")
        return redirect(external_url, code=302)

    # Otherwise serve from local data directory
    file_path = DATA_DIR / filepath

    if not file_path.exists():
        # If fallback is enabled and we were trying local, could try external here
        fallback = DATA_SOURCE_CONFIG.get('data_source', {}).get('fallback_to_local', False)
        if fallback:
            return jsonify({
                'error': 'File not found locally and no external data source configured'
            }), 404
        return jsonify({'error': 'File not found'}), 404

    # Determine MIME type based on extension
    mime_types = {
        '.geojson': 'application/geo+json',
        '.json': 'application/json',
        '.tif': 'image/tiff',
        '.tiff': 'image/tiff',
        '.png': 'image/png',
        '.jpg': 'image/jpeg',
        '.jpeg': 'image/jpeg'
    }

    file_ext = file_path.suffix.lower()
    mime_type = mime_types.get(file_ext, 'application/octet-stream')

    # Create response
    response = send_file(file_path, mimetype=mime_type)

    # Disable caching for .tif files to ensure elevation updates are reflected
    if file_ext in ['.tif', '.tiff']:
        response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '0'

    return response


@app.route('/api/layers')
def list_layers():
    """Return list of available data layers."""
    layers = {
        'boundaries': [],
        'ndvi': [],
        'fire': [],
    }

    # Check for boundary files
    boundaries_dir = DATA_DIR / 'boundaries'
    if boundaries_dir.exists():
        for file in boundaries_dir.glob('*.geojson'):
            layers['boundaries'].append({
                'name': file.stem,
                'path': f'/data/boundaries/{file.name}',
                'type': 'geojson'
            })

    # Check for NDVI files
    ndvi_dir = DATA_DIR / 'processed' / 'ndvi'
    if ndvi_dir.exists():
        for file in ndvi_dir.glob('*.tif'):
            layers['ndvi'].append({
                'name': file.stem,
                'path': f'/data/processed/ndvi/{file.name}',
                'type': 'geotiff'
            })

    return jsonify(layers)


@app.route('/api/info')
def app_info():
    """Return application information."""
    return jsonify({
        'name': 'Williams Treaty Territories Environmental Data Browser',
        'version': '1.0.0',
        'description': 'Interactive map for environmental planning and climate change adaptation',
        'data_sources': [
            'Natural Resources Canada',
            'Ontario Ministry of Natural Resources',
            'Conservation Authorities'
        ],
        'data_repository': DATA_BASE_URL if DATA_BASE_URL else 'local'
    })


@app.route('/api/data-source')
def data_source_info():
    """Return information about the current data source configuration."""
    return jsonify({
        'base_url': DATA_BASE_URL if DATA_BASE_URL else 'local',
        'is_external': bool(DATA_BASE_URL),
        'config': {
            'fallback_to_local': DATA_SOURCE_CONFIG.get('data_source', {}).get('fallback_to_local', False),
            'cache_enabled': DATA_SOURCE_CONFIG.get('cache', {}).get('enabled', False)
        }
    })


def convert_keys_to_strings(obj):
    """Recursively convert all dictionary keys to strings for JSON compatibility."""
    if isinstance(obj, dict):
        return {str(k): convert_keys_to_strings(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [convert_keys_to_strings(item) for item in obj]
    else:
        return obj


@app.route('/api/layer-config')
def layer_config():
    """Return layer configuration from YAML file."""
    layers_config_file = CONFIG_DIR / 'layers.yaml'

    if not layers_config_file.exists():
        return jsonify({'error': 'Layer configuration file not found'}), 404

    try:
        with open(layers_config_file, 'r') as f:
            config = yaml.safe_load(f)
        # Convert all keys to strings for JSON compatibility
        config = convert_keys_to_strings(config)
        return jsonify(config)
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        print(f"Error loading config: {error_details}")
        return jsonify({'error': f'Failed to load configuration: {str(e)}'}), 500


@app.route('/layers')
def layers_page():
    """Serve the layers information page."""
    return send_file(WEB_DIR / 'layers.html')


def main():
    """Start the web server."""
    parser = argparse.ArgumentParser(
        description='Williams Treaty Territories Map Server'
    )
    parser.add_argument(
        '--port',
        type=int,
        default=int(os.environ.get('PORT', 8000)),
        help='Port to run the server on (default: 8000, or PORT env var)'
    )
    parser.add_argument(
        '--host',
        type=str,
        default='127.0.0.1',
        help='Host to bind to (default: 127.0.0.1)'
    )
    parser.add_argument(
        '--debug',
        action='store_true',
        help='Run in debug mode'
    )

    args = parser.parse_args()

    print('=' * 70)
    print('Williams Treaty Territories - Map Server')
    print('=' * 70)
    print(f'Server starting on http://{args.host}:{args.port}')
    print(f'Web directory: {WEB_DIR}')
    print(f'Data directory: {DATA_DIR}')
    print('')
    print('Data Source Configuration:')
    if DATA_BASE_URL:
        print(f'  Mode: EXTERNAL')
        print(f'  Base URL: {DATA_BASE_URL}')
        print(f'  Data files will be loaded from the external repository')
    else:
        print(f'  Mode: LOCAL')
        print(f'  Data files will be served from local {DATA_DIR}')
    print('')
    print('Available endpoints:')
    print(f'  Main application: http://{args.host}:{args.port}/')
    print(f'  Layers info:      http://{args.host}:{args.port}/layers')
    print(f'  API info:         http://{args.host}:{args.port}/api/info')
    print(f'  API layers:       http://{args.host}:{args.port}/api/layers')
    print(f'  API layer config: http://{args.host}:{args.port}/api/layer-config')
    print(f'  API data source:  http://{args.host}:{args.port}/api/data-source')
    print('')
    print('Press Ctrl+C to stop the server')
    print('=' * 70)
    print('')

    try:
        app.run(
            host=args.host,
            port=args.port,
            debug=args.debug
        )
    except KeyboardInterrupt:
        print('\nServer stopped')


if __name__ == '__main__':
    # Check if flask and flask-cors are installed
    try:
        import flask
        from flask_cors import CORS
    except ImportError:
        print('Error: Flask and flask-cors are required')
        print('Install with: pip install flask flask-cors')
        sys.exit(1)

    main()
