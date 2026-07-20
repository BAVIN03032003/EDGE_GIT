
import json
import os
import sys
import logging
from dotenv import dotenv_values
 
logger = logging.getLogger(__name__)

# Determine base directory for configuration files
if os.environ.get('DOCKER_CONTAINER') == 'true':
    # In Docker, we always want to use /app
    BASE_DIR = '/app'
elif getattr(sys, 'frozen', False):
    # When running as a Nuitka binary, paths are relative to the executable
    BASE_DIR = os.path.dirname(sys.executable)
else:
    # When running as a script, paths are relative to the project root
    BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../'))

logger.info(f"Using BASE_DIR: {BASE_DIR} (sys.executable: {sys.executable})")

CONFIG_PATH = os.path.join(BASE_DIR, 'config.json')
ENV_PATH = os.path.join(BASE_DIR, '.env')
BACKEND_ENV_PATH = os.path.join(BASE_DIR, '.env') # Use root .env for both to avoid missing dirs
 
# Removed DEFAULT_CONFIG from here - we now read from .env
 
 
class Config:

    """Configuration management - Reads from .env file and config.json"""

    _config = None  # Cache for config

    @staticmethod

    def load() -> dict:

        """Load configuration from .env file (environment variables)"""

        # If already cached, return cached version

        if Config._config is not None:

            return Config._config

        try:
            # Read from .env file directly so updates on disk are picked up
            env_source = {}
            logger.info(f"Checking for .env at: {ENV_PATH}")
            if os.path.exists(ENV_PATH):
                env_source = dotenv_values(ENV_PATH)
                logger.info(f"Loaded {len(env_source)} values from {ENV_PATH}")
            elif os.path.exists(BACKEND_ENV_PATH):
                env_source = dotenv_values(BACKEND_ENV_PATH)
                logger.info(f"Loaded {len(env_source)} values from {BACKEND_ENV_PATH}")
            else:
                logger.warning("No .env file found at expected locations!")

            def _get_env(key: str, default=None):
                val = os.getenv(key)
                if val is None or val == "":
                    val = env_source.get(key)
                if val:
                    logger.debug(f"Found config: {key}")
                return val or default

            def _get_int(key: str, default: int) -> int:
                raw = _get_env(key, default)
                try:
                    return int(raw)
                except Exception:
                    return int(default)

            # Build config using .env values (fallback to environment)
            config = {

                # Cloud Configuration (from .env)

                'CLOUD_URL': _get_env('CLOUD_URL', ''),

                'API_KEY': _get_env('API_KEY', ''),
                'SOCKETIO_PATH': _get_env('SOCKETIO_PATH', 'socket.io'),
                'SOCKETIO_NAMESPACE': _get_env('SOCKETIO_NAMESPACE', ''),

                # Edge Configuration (from .env)

                'EDGE_NAME': _get_env('EDGE_NAME', 'My-Edge-Collector'),

                'EDGE_ID': _get_env('EDGE_ID', 'edge_001'),

                'LOCATION': _get_env('LOCATION', 'Unknown'),

                'VERSION': _get_env('VERSION', '1.0.0'),

                # Application Settings (from .env)

                'WEB_UI_HOST': _get_env('WEB_UI_HOST', '0.0.0.0'),

                'WEB_UI_PORT': _get_int('WEB_UI_PORT', 5001),

                'LOG_LEVEL': _get_env('LOG_LEVEL', 'INFO'),

                # Timing Configuration (from .env)

                'MONITORING_INTERVAL': _get_int('MONITORING_INTERVAL', 30),

                'DISCOVERY_INTERVAL': _get_int('DISCOVERY_INTERVAL', 300),

                'COMMAND_CHECK_INTERVAL': _get_int('COMMAND_CHECK_INTERVAL', 5),

                'HEARTBEAT_INTERVAL': _get_int('HEARTBEAT_INTERVAL', 60),
                'IS_MANUAL_UPDATE': _get_int('IS_MANUAL_UPDATE', 0),

                # Local Devices (from config.json - devices stay here)

                'LOCAL_DEVICES': Config._load_devices_from_config()

            }

            # Validate required fields

            if not config['CLOUD_URL']:

                logger.warning("⚠️  CLOUD_URL not set in .env file")

            if not config['API_KEY']:

                logger.warning("⚠️  API_KEY not set in .env file")

            # Cache the config

            Config._config = config

            return config

        except Exception as e:

            logger.error(f"Failed to load configuration: {e}")

            # Return minimal config if error

            return {

                'CLOUD_URL': '',

                'API_KEY': '',

                'EDGE_NAME': 'My-Edge-Collector',

                'LOCATION': 'Unknown',

                'WEB_UI_PORT': 5001,

                'LOCAL_DEVICES': []

            }

    @staticmethod

    def _load_devices_from_config() -> list:

        """Load device list from config.json (devices don't go in .env)"""

        try:

            if os.path.exists(CONFIG_PATH):

                with open(CONFIG_PATH, 'r') as f:

                    config_data = json.load(f)

                    devices = config_data.get('LOCAL_DEVICES', [])

                    logger.info(f"Loaded {len(devices)} devices from config.json")

                    return devices

        except Exception as e:

            logger.warning(f"Could not load devices from config.json: {e}")

        return []

    @staticmethod

    def get(key: str, default=None):

        """Get a configuration value"""

        if Config._config is None:

            Config.load()

        return Config._config.get(key, default)

    @staticmethod

    def save_to_env(updates: dict) -> bool:

        """Save configuration changes to .env file"""

        try:

            # Update in-memory config

            if Config._config is None:

                Config.load()

            Config._config.update(updates)

            # Build .env file content

            env_lines = [

                "# Cloud Configuration",

                f"CLOUD_URL={Config._config.get('CLOUD_URL', '')}",

                f"API_KEY={Config._config.get('API_KEY', '')}",
                f"SOCKETIO_PATH={Config._config.get('SOCKETIO_PATH', 'socket.io')}",
                f"SOCKETIO_NAMESPACE={Config._config.get('SOCKETIO_NAMESPACE', '')}",

                "",

                "# Edge Configuration",

                f"EDGE_NAME={Config._config.get('EDGE_NAME', '')}",

                f"EDGE_ID={Config._config.get('EDGE_ID', '')}",

                f"LOCATION={Config._config.get('LOCATION', '')}",

                "",

                "# Application Settings",

                f"WEB_UI_HOST={Config._config.get('WEB_UI_HOST', '0.0.0.0')}",

                f"WEB_UI_PORT={Config._config.get('WEB_UI_PORT', 5001)}",

                f"LOG_LEVEL={Config._config.get('LOG_LEVEL', 'INFO')}",

                "",

                "# Timing (seconds)",

                f"MONITORING_INTERVAL={Config._config.get('MONITORING_INTERVAL', 30)}",

                f"DISCOVERY_INTERVAL={Config._config.get('DISCOVERY_INTERVAL', 300)}",

                f"COMMAND_CHECK_INTERVAL={Config._config.get('COMMAND_CHECK_INTERVAL', 5)}",

                f"HEARTBEAT_INTERVAL={Config._config.get('HEARTBEAT_INTERVAL', 60)}",
                f"IS_MANUAL_UPDATE={Config._config.get('IS_MANUAL_UPDATE', 0)}",

            ]

            env_content = '\n'.join(env_lines)

            # Write to root .env file and backend/.env for compatibility

            for path in (ENV_PATH, BACKEND_ENV_PATH):

                   with open(path, 'w', encoding='utf-8', newline='\n') as f:

                    f.write(env_content)

            logger.info("Configuration saved to .env file")

            return True

        except Exception as e:

            logger.error(f"Error saving configuration to .env: {e}")

            return False

    @staticmethod

    def reload():

        """Reload configuration from .env file"""

        Config._config = None

        Config.load()

        logger.info("Configuration reloaded from .env file")

    @staticmethod

    def save(data: dict) -> bool:

        """DEPRECATED: Use save_to_env() instead

        Kept for backward compatibility"""

        logger.warning("Config.save() is deprecated, use Config.save_to_env() instead")

        return Config.save_to_env(data)
 
