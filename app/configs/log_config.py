import os
import sys

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from app.configs.config import DEBUG
from loguru import logger

# * Configure log level based on DEBUG environment variable
if DEBUG:
    logger.remove()  # * Remove the default Loguru handler
    logger.add(sys.stdout, level="DEBUG")  # * Set level to DEBUG if DEBUG=True
    logger.debug("Debug mode is enabled.")
else:
    logger.remove()
    logger.add(sys.stdout, level="INFO")  # * Set default log level to INFO
    logger.info("Debug mode is disabled. Default log level is INFO.")
