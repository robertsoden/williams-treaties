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
from functools import wraps
from flask import Flask, send_from_directory, send_file, jsonify, redirect, request, Response
from flask_cors import CORS
import yaml
import requests
from urllib.parse import urljoin
from copy import deepcopy

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

# Get project root
PROJECT_ROOT = Path(__file__).parent.parent
WEB_DIR = PROJECT_ROOT / 'web'
DATA_DIR = PROJECT_ROOT / 'data'
CONFIG_DIR = WEB_DIR / 'config'

# Basic Authentication Configuration
# Set via environment variable:
#   BASIC_AUTH_PASSWORD - password for authentication (optional, disables auth if not set)
#   Username will be ignored - only password is checked
BASIC_AUTH_ENABLED = bool(os.getenv('BASIC_AUTH_PASSWORD'))
BASIC_AUTH_PASSWORD = os.getenv('BASIC_AUTH_PASSWORD', '')


def check_auth(username, password):
    """Check if password is valid (username is ignored)."""
    return password == BASIC_AUTH_PASSWORD


def authenticate():
    """Send 401 response that enables basic auth."""
    return Response(
        'Password required. Enter any username and the site password.',
        401,
        {'WWW-Authenticate': 'Basic realm="Williams Treaty Map - Password Required"'}
    )


def requires_auth(f):
    """Decorator to require basic authentication for a route."""
    @wraps(f)
    def decorated(*args, **kwargs):
        # Skip auth if not enabled
        if not BASIC_AUTH_ENABLED:
            return f(*args, **kwargs)

        auth = request.authorization
        if not auth or not check_auth(auth.username, auth.password):
            return authenticate()
        return f(*args, **kwargs)
    return decorated


def load_data_source_config():
    """Load global data source configuration from data_source.yaml."""
    config_file = CONFIG_DIR / 'data_source.yaml'

    if not config_file.exists():
        # Default configuration if file doesn't exist
        return {
            'data_source': {
                'mode': 'local',
                'remote_url': '',
                'local_path': 'data',
                'fallback_priority': ['local', 'remote'],
                'on_missing': '404'
            },
            'cache': {
                'enabled': True,
                'ttl_seconds': 3600,
                'directory': '.cache/remote_data'
            },
            'auto_create_directories': True,
            'env_overrides': {
                'enabled': True,
                'variables': {
                    'DATA_SOURCE_URL': 'remote_url',
                    'DATA_MODE': 'mode',
                    'LOCAL_DATA_PATH': 'local_path'
                }
            }
        }

    with open(config_file, 'r') as f:
        return yaml.safe_load(f)


def apply_env_overrides(config):
    """Apply environment variable overrides to configuration."""
    if not config.get('env_overrides', {}).get('enabled', True):
        return config

    variables = config.get('env_overrides', {}).get('variables', {})

    for env_var, config_path in variables.items():
        env_value = os.environ.get(env_var)
        if env_value:
            # Parse the config path (e.g., "data_source.mode" -> ['data_source', 'mode'])
            if '.' in config_path:
                parts = config_path.split('.')
                target = config
                for part in parts[:-1]:
                    if part not in target:
                        target[part] = {}
                    target = target[part]
                target[parts[-1]] = env_value
                print(f"✓ Environment override: {env_var}={env_value}")
            else:
                # Simple config path
                if 'data_source' not in config:
                    config['data_source'] = {}
                config['data_source'][config_path] = env_value
                print(f"✓ Environment override: {env_var}={env_value}")

    return config


def get_data_source_mode():
    """Get the current data source mode after env overrides."""
    config = load_data_source_config()
    config = apply_env_overrides(config)
    return config.get('data_source', {}).get('mode', 'local')


def get_data_remote_url():
    """Get the remote data URL after env overrides."""
    config = load_data_source_config()
    config = apply_env_overrides(config)
    return config.get('data_source', {}).get('remote_url', '')


def get_data_local_path():
    """Get the local data path after env overrides."""
    config = load_data_source_config()
    config = apply_env_overrides(config)
    return config.get('data_source', {}).get('local_path', 'data')


def auto_create_directories():
    """Auto-create missing data directories if configured."""
    config = load_data_source_config()

    if not config.get('auto_create_directories', True):
        return

    # Directories to create
    directories = [
        DATA_DIR / 'boundaries',
        DATA_DIR / 'processed',
        DATA_DIR / 'processed' / 'ndvi',
        DATA_DIR / 'processed' / 'dem',
        DATA_DIR / 'processed' / 'fire',
        DATA_DIR / 'processed' / 'fuel',
        DATA_DIR / 'processed' / 'water',
        DATA_DIR / 'processed' / 'cwb',
        DATA_DIR / 'processed' / 'csicp',
        DATA_DIR / 'processed' / 'infrastructure',
        DATA_DIR / 'processed' / 'communities',
        DATA_DIR / 'raw',
    ]

    created = []
    for directory in directories:
        if not directory.exists():
            directory.mkdir(parents=True, exist_ok=True)
            # Create .gitkeep to track empty directories
            gitkeep = directory / '.gitkeep'
            gitkeep.touch()
            created.append(str(directory.relative_to(PROJECT_ROOT)))

    if created:
        print(f"✓ Auto-created {len(created)} missing directories")


# Load configuration at startup
DATA_SOURCE_CONFIG = load_data_source_config()
DATA_SOURCE_CONFIG = apply_env_overrides(DATA_SOURCE_CONFIG)
DATA_MODE = DATA_SOURCE_CONFIG.get('data_source', {}).get('mode', 'local')
DATA_REMOTE_URL = DATA_SOURCE_CONFIG.get('data_source', {}).get('remote_url', '')
DATA_LOCAL_PATH = DATA_SOURCE_CONFIG.get('data_source', {}).get('local_path', 'data')
DATA_FALLBACK_PRIORITY = DATA_SOURCE_CONFIG.get('data_source', {}).get('fallback_priority', ['local', 'remote'])

# Auto-create directories
auto_create_directories()


def merge_data_source_configs(global_config, layer_config):
    """
    Merge global data source config with per-layer config.
    Layer config takes precedence.
    """
    merged = deepcopy(global_config.get('data_source', {}))

    if 'data_source' in layer_config:
        layer_ds = layer_config['data_source']
        # Merge fields, layer config overrides global
        for key, value in layer_ds.items():
            merged[key] = value

    return merged


def is_external_url(url):
    """Check if URL is external (starts with http:// or https://)."""
    return url.startswith('http://') or url.startswith('https://')


@app.route('/')
@requires_auth
def index():
    """Serve the main map application."""
    return send_file(WEB_DIR / 'index.html')


@app.route('/<path:filename>')
@requires_auth
def serve_web_files(filename):
    """Serve static web files (CSS, JS, etc.)."""
    return send_from_directory(WEB_DIR, filename)


@app.route('/data/<path:filepath>')
@requires_auth
def serve_data(filepath):
    """
    Serve data files (GeoJSON, GeoTIFF, etc.).

    This handles serving files based on the configured mode:
    - local: Serve from local /data/ directory
    - remote: Redirect to external URL
    - hybrid: Try based on fallback_priority
    """
    mode = DATA_MODE

    if mode == 'remote':
        # Remote mode: redirect to external URL
        if DATA_REMOTE_URL:
            external_url = urljoin(DATA_REMOTE_URL + '/', filepath)
            print(f"→ Redirecting to remote: {external_url}")
            return redirect(external_url, code=302)
        else:
            return jsonify({'error': 'Remote mode configured but no remote_url set'}), 500

    elif mode == 'hybrid':
        # Hybrid mode: try sources based on priority
        for source in DATA_FALLBACK_PRIORITY:
            if source == 'local':
                file_path = DATA_DIR / filepath
                if file_path.exists():
                    print(f"→ Serving from local: {filepath}")
                    return serve_local_file(file_path)
            elif source == 'remote' and DATA_REMOTE_URL:
                external_url = urljoin(DATA_REMOTE_URL + '/', filepath)
                print(f"→ Trying remote: {external_url}")
                # In hybrid mode, we redirect and let the client handle failures
                return redirect(external_url, code=302)

        # If we get here, file not found in any source
        return jsonify({'error': 'File not found in any configured source'}), 404

    else:
        # Local mode (default): serve from local directory
        file_path = DATA_DIR / filepath

        if not file_path.exists():
            return jsonify({'error': 'File not found'}), 404

        print(f"→ Serving from local: {filepath}")
        return serve_local_file(file_path)


def serve_local_file(file_path):
    """Serve a file from the local filesystem with appropriate headers."""
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
@requires_auth
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
@requires_auth
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
        'data_repository': DATA_REMOTE_URL if DATA_REMOTE_URL else 'local'
    })


@app.route('/api/data-source')
@requires_auth
def data_source_info():
    """Return information about the current data source configuration."""
    return jsonify({
        'mode': DATA_MODE,
        'remote_url': DATA_REMOTE_URL if DATA_REMOTE_URL else None,
        'local_path': DATA_LOCAL_PATH,
        'fallback_priority': DATA_FALLBACK_PRIORITY,
        'cache_enabled': DATA_SOURCE_CONFIG.get('cache', {}).get('enabled', False)
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
@requires_auth
def layer_config():
    """
    Return layer configuration from YAML file.
    Merges global data source config with per-layer overrides.
    """
    layers_config_file = CONFIG_DIR / 'layers.yaml'

    if not layers_config_file.exists():
        return jsonify({'error': 'Layer configuration file not found'}), 404

    try:
        # Load layers configuration
        with open(layers_config_file, 'r') as f:
            config = yaml.safe_load(f)

        # Merge global data source config with each layer's config
        if 'layers' in config:
            for layer in config['layers']:
                # Merge data source configuration
                merged_ds = merge_data_source_configs(DATA_SOURCE_CONFIG, layer)

                # Add merged config to layer (for client reference)
                if not layer.get('data_source'):
                    layer['data_source'] = {}

                # Add global defaults if not specified in layer
                if 'mode' not in layer['data_source']:
                    layer['data_source']['mode'] = merged_ds.get('mode', 'local')
                if 'fallback_priority' not in layer['data_source']:
                    layer['data_source']['fallback_priority'] = merged_ds.get('fallback_priority', ['local', 'remote'])

                # Keep layer-specific source_info if it exists
                # (don't override it with global config)

        # Convert all keys to strings for JSON compatibility
        config = convert_keys_to_strings(config)
        return jsonify(config)
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        print(f"Error loading config: {error_details}")
        return jsonify({'error': f'Failed to load configuration: {str(e)}'}), 500


@app.route('/layers')
@requires_auth
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
    print(f'  Mode: {DATA_MODE.upper()}')
    if DATA_MODE == 'remote' or DATA_MODE == 'hybrid':
        if DATA_REMOTE_URL:
            print(f'  Remote URL: {DATA_REMOTE_URL}')
        else:
            print(f'  Remote URL: (not configured)')
    if DATA_MODE == 'local' or DATA_MODE == 'hybrid':
        print(f'  Local Path: {DATA_DIR}')
    if DATA_MODE == 'hybrid':
        print(f'  Fallback Priority: {" → ".join(DATA_FALLBACK_PRIORITY)}')
    print('')
    print('Authentication:')
    if BASIC_AUTH_ENABLED:
        print(f'  Password Protection: ENABLED')
        print(f'  ⚠️  Site requires password (username can be anything)')
    else:
        print(f'  Password Protection: DISABLED (site is public)')
        print(f'  To enable: Set BASIC_AUTH_PASSWORD env var')
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
