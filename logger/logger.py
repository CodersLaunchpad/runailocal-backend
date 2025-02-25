import logging
import sys

# Configure a single application logger
log_format = '%(asctime)s - %(levelname)s - %(message)s'
logging.basicConfig(
    level=logging.INFO,
    format=log_format,
    handlers=[logging.StreamHandler(sys.stdout)]
)

# Get a single logger for the entire application
logger = logging.getLogger("app")

# Export only the logger instance
__all__ = ["logger"]