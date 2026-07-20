import time
import logging
from flask import Blueprint, jsonify, request, current_app

from utils.config import Config
 
config_bp = Blueprint('config', __name__)

logger = logging.getLogger(__name__)
 
 
@config_bp.route('/', methods=['GET'])

def get_config():

    """

    Returns current config.

    API Key is masked - never exposed via API.

    """

    config = Config.load()
 
    # Never expose plain API key via HTTP

    safe_config = {k: v for k, v in config.items() if k != 'API_KEY'}

    safe_config['API_KEY'] = '***' if config.get('API_KEY') else ''

    safe_config['api_key_set'] = bool(config.get('API_KEY'))
 
    return jsonify(safe_config)
 
 
@config_bp.route('/', methods=['POST'])

def update_config():

    """

    Saves new config to config.json.

    Called by Settings page when user clicks Save.

    """

    data = request.get_json()
 
    if not data:

        return jsonify({'error': 'No JSON body provided'}), 400
 
    # Don't overwrite API key if user sent masked value

    if data.get('API_KEY') == '***':

        del data['API_KEY']
 
    success = Config.save(data)
 
    if success:
        # If cloud connector is running, force reconnect so new creds take effect.
        cloud_connector = current_app.config.get('cloud_connector')
        if cloud_connector:
            try:
                logger.info("[CONFIG] Cloud connector found. Reconnecting...")
                cloud_connector.disconnect()
                time.sleep(1)
                logger.info("[CONFIG] Cloud connector reconnection initiated")
            except Exception as e:
                logger.error(f"[CONFIG] Failed to reconnect cloud connector: {e}")

        return jsonify({

            'success': True,

            'message': 'Config saved. Cloud connection will restart automatically. Some settings (like Web UI port) still require a full restart.'

        })
 
    return jsonify({'error': 'Failed to save config'}), 500
