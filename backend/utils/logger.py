import logging
import os
from logging.handlers import RotatingFileHandler

LOG_DIR = os.path.join(
    os.path.dirname(__file__), "../../logs"
)


def setup_logger():
    log_format = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"

    # Console output only by default
    logging.basicConfig(
        level=logging.INFO,
        format=log_format
    )

    # Optional file logging (disabled unless explicitly enabled)
    if os.getenv("LOG_TO_FILE", "").strip().lower() in {"1", "true", "yes"}:
        os.makedirs(LOG_DIR, exist_ok=True)
        # Rotating file -- max 5MB per file, keep last 5 files
        file_handler = RotatingFileHandler(
            os.path.join(LOG_DIR, "edge-collector.log"),
            maxBytes=5 * 1024 * 1024,
            backupCount=5
        )
        file_handler.setFormatter(logging.Formatter(log_format))
        logging.getLogger().addHandler(file_handler)
