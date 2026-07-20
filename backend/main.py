import sys
import io
import os
import logging
import threading
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

from dotenv import load_dotenv
load_dotenv()

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from utils.logger import setup_logger
from utils.config import Config
from utils.state import EdgeState
from services.cloud_connector import CloudConnector
from app import create_app

VERSION_FILE = Path(__file__).parent / "VERSION"

def get_version():
    if VERSION_FILE.exists():
        return VERSION_FILE.read_text().strip()
    return "dev"

def main():
    if "--health" in sys.argv:
        # Minimal health check: if we can import the app, we are likely okay
        try:
            import flask
            sys.exit(0)
        except ImportError:
            sys.exit(1)

    setup_logger()
    logger = logging.getLogger(__name__)

    current_version = get_version()

    logger.info("=" * 60)
    logger.info("  Edge Application Starting")
    logger.info("=" * 60)
    logger.info(f"  Version   : {current_version}")
    logger.info("=" * 60)

    config = Config.load()

    edge_name = config.get('EDGE_NAME', 'Unnamed')
    location = config.get('LOCATION', 'Unknown')
    port = config.get('WEB_UI_PORT', 8080)
    cloud_url = config.get('CLOUD_URL')
    api_key = config.get('API_KEY')

    EdgeState.set('edge_name', edge_name)
    EdgeState.set('edge_version', current_version)
    EdgeState.set('cloud_connected', False)
    EdgeState.set('registered', False)
    EdgeState.set('devices', [])

    logger.info(f"Edge Name : {edge_name}")
    logger.info(f"Edge ID   : {config.get('EDGE_ID', 'NOT SET')}")
    logger.info(f"Location  : {location}")
    logger.info(f"Cloud URL : {cloud_url or 'NOT SET'}")

    if api_key:
        masked_key = 'sk_' + '*' * (len(api_key) - 7) + api_key[-4:]
        logger.info(f"API Key   : {masked_key}")
    else:
        logger.warning("API_KEY not set in .env file")

    logger.info(f"Web UI    : http://localhost:3000")
    logger.info(f"API Server: http://localhost:{port}")
    logger.info("=" * 60)

    cloud_connector = CloudConnector(config)
    cloud_thread = threading.Thread(
        target=cloud_connector.start,
        name='CloudConnector',
        daemon=True
    )
    cloud_thread.start()
    logger.info("CloudConnector thread started")

    flask_app = create_app()
    flask_app.config['cloud_connector'] = cloud_connector

    logger.info(f"API Server starting at http://0.0.0.0:{port}")
    logger.info("Edge Application startup complete")

    flask_app.run(
        host='0.0.0.0',
        port=port,
        debug=False,
        use_reloader=False
    )


if __name__ == '__main__':
    main()
