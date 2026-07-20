import os
import time
import logging
from datetime import datetime
from pathlib import Path

from flask import Flask, send_from_directory, request, jsonify, current_app

from flask_cors import CORS

from api_edge import get_edges, get_edge, create_edge, regenerate_key, delete_edge

from utils.config import Config
from routes.power_conditioner_routes import pc_bp
 
logger = logging.getLogger(__name__)
 
 
def create_app():

    """

    Flask application factory.

    Creates the app, registers all API routes,

    and serves the React frontend after build.

    """

    # Point Flask to React build folder
    build_folder = os.getenv('FRONTEND_BUILD_DIR')
    if not build_folder:
        build_folder = os.path.abspath(
            os.path.join(os.path.dirname(__file__), '../my-app/build')
        )
    logger.info(f"Serving frontend from: {build_folder}")

    app = Flask(

        __name__,

        static_folder=build_folder,

        template_folder=build_folder

    )

    app.config['SECRET_KEY'] = 'edge-collector-secret-2024'

    app.config['JSON_SORT_KEYS'] = False

    # Allow React dev server (port 3000) to call Flask (port 5001)

    CORS(app, resources={r"/api/*": {"origins": "*"}})

    # Register all API blueprints

    from routes.status_routes import status_bp

    from routes.device_routes import device_bp

    from routes.command_routes import command_bp

    from routes.config_routes import config_bp

    from routes.log_routes import log_bp

    from routes.power_conditioner_routes import pc_bp

    app.register_blueprint(status_bp, url_prefix='/api/status')
    app.register_blueprint(pc_bp, url_prefix='/api/powerconditioner')

    app.register_blueprint(device_bp, url_prefix='/api/devices')

    app.register_blueprint(command_bp, url_prefix='/api/commands')

    app.register_blueprint(config_bp, url_prefix='/api/config')

    app.register_blueprint(log_bp, url_prefix='/api/logs')

    app.add_url_rule('/api/edges/', view_func=get_edges, methods=['GET'])

    app.add_url_rule('/api/edges/', view_func=create_edge, methods=['POST'])

    app.add_url_rule('/api/edges/<int:edge_id>/', view_func=get_edge, methods=['GET'])

    app.add_url_rule('/api/edges/<int:edge_id>/', view_func=delete_edge, methods=['DELETE'])

    app.add_url_rule('/api/edges/<int:edge_id>/regenerate-key/', view_func=regenerate_key, methods=['POST'])

    # ------------------------------------------------------------------

    # Configuration Management Routes

    # ------------------------------------------------------------------

    @app.route('/api/v1/config/update', methods=['POST'])

    def update_config():

        """Update configuration and save to .env file"""

        try:

            data = request.get_json()

            if not data:

                return jsonify({

                    'status': 'error',

                    'message': 'No data provided'

                }), 400

            # Prepare updates dictionary

            updates = {}

            if 'cloud_url' in data and data['cloud_url']:

                updates['CLOUD_URL'] = data['cloud_url']

                logger.info(f"[CONFIG] Updating CLOUD_URL: {data['cloud_url']}")

            if 'api_key' in data and data['api_key']:

                updates['API_KEY'] = data['api_key']

                masked_key = 'sk_' + '*' * (len(data['api_key']) - 7) + data['api_key'][-4:]

                logger.info(f"API Server starting at http://0.0.0.0:{port}")
                logger.info("Edge Application startup complete")

            if 'edge_name' in data and data['edge_name']:

                updates['EDGE_NAME'] = data['edge_name']

                logger.info(f"[CONFIG] Updating EDGE_NAME: {data['edge_name']}")

            if 'location' in data and data['location']:
                updates['LOCATION'] = data['location']
                logger.info(f"[CONFIG] Updating LOCATION: {data['location']}")

            if 'is_manual_update' in data:
                val = 1 if data['is_manual_update'] in [1, '1', True, 'true'] else 0
                updates['IS_MANUAL_UPDATE'] = val
                logger.info(f"[CONFIG] Updating IS_MANUAL_UPDATE: {val}")

            # If no updates provided

            if not updates:

                return jsonify({

                    'status': 'error',

                    'message': 'No valid configuration fields provided'

                }), 400

            # Save to .env file

            success = Config.save_to_env(updates)

            if success:

                logger.info("[CONFIG] Configuration saved to .env file")

                # Reconnect to cloud with new config if cloud_connector exists

                cloud_connector = current_app.config.get('cloud_connector')

                if cloud_connector:

                    logger.info("[CONFIG] Cloud connector found. Reconnecting...")

                    cloud_connector.disconnect()

                    time.sleep(1)

                    # start() loop will automatically reconnect

                    logger.info("[CONFIG] Cloud connector reconnection initiated")

                return jsonify({

                    'status': 'success',

                    'message': 'Configuration saved to .env file'

                }), 200

            else:

                logger.error("[CONFIG] Failed to save configuration to .env")

                return jsonify({

                    'status': 'error',

                    'message': 'Failed to save configuration to .env'

                }), 500

        except Exception as e:

            logger.error(f"[CONFIG] Error updating config: {e}")

            return jsonify({

                'status': 'error',

                'message': str(e)

            }), 500


    @app.route('/api/v1/config/reload', methods=['POST'])

    def reload_config():

        """Reload configuration from .env file"""

        try:

            logger.info("[CONFIG] Reloading configuration from .env")

            Config.reload()

            logger.info("[CONFIG] Configuration reloaded successfully")

            return jsonify({

                'status': 'success',

                'message': 'Configuration reloaded from .env'

            }), 200

        except Exception as e:

            logger.error(f"[CONFIG] Error reloading config: {e}")

            return jsonify({

                'status': 'error',

                'message': str(e)

            }), 500


    @app.route('/api/v1/config', methods=['GET'])

    def get_config():

        """Get current configuration (masks sensitive data)"""

        try:

            config = Config.load()

            # Prepare response with masked sensitive data

            response_config = {

                'cloud_url': config.get('CLOUD_URL', ''),

                'api_key': _mask_api_key(config.get('API_KEY', '')),

                'edge_name': config.get('EDGE_NAME', ''),

                'location': config.get('LOCATION', ''),

                'edge_id': config.get('EDGE_ID', ''),

                'version': config.get('VERSION', ''),

                'web_ui_port': config.get('WEB_UI_PORT', 5001),

                'log_level': config.get('LOG_LEVEL', 'INFO'),
                'is_manual_update': int(config.get('IS_MANUAL_UPDATE', 0))

            }

            return jsonify({

                'status': 'success',

                'config': response_config

            }), 200

        except Exception as e:

            logger.error(f"[CONFIG] Error getting config: {e}")

            return jsonify({

                'status': 'error',

                'message': str(e)

            }), 500

    @app.route('/health', methods=['GET'])
    def health():
        """Health check endpoint for Docker and monitoring"""
        current_version = "dev"
        try:
            VERSION_FILE = Path(__file__).parent / "VERSION"
            if VERSION_FILE.exists():
                current_version = VERSION_FILE.read_text().strip()
        except:
            pass

        return jsonify({
            'status': 'healthy',
            'service': 'edge-application',
            'version': current_version,
            'timestamp': datetime.utcnow().isoformat() + 'Z'
        })

    @app.route('/api/version', methods=['GET'])
    def get_version_info():
        """Get application version information"""
        current_version = "dev"
        try:
            VERSION_FILE = Path(__file__).parent / "VERSION"
            if VERSION_FILE.exists():
                current_version = VERSION_FILE.read_text().strip()
        except:
            pass

        return jsonify({
            'version': current_version,
            'build_date': 'N/A',
            'git_sha': 'N/A'
        })

    # ------------------------------------------------------------------
    # API Only - React is served via Nginx on port 3000
    # ------------------------------------------------------------------
    @app.route('/')
    def root():
        return jsonify({
            'status': 'online',
            'message': 'Edge API is running',
            'ui_url': 'http://localhost:3000'
        })

    return app
 
 
def _mask_api_key(api_key):

    """Mask API key for display (show only last 4 characters)"""
    if not api_key:
        return None

    if len(api_key) <= 4:

        return api_key

    return 'sk_' + '*' * (len(api_key) - 7) + api_key[-4:]
 
