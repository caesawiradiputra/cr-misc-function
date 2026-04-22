"""Application configuration management with multi-source environment loading.

Provides centralized configuration access for all application services using Pydantic schemas.

Configuration sources (priority order):
    1. Vault secrets: /vault/secrets/.env (Docker/Kubernetes deployments)
    2. Local .env file: project root directory
    3. Environment variables and defaults: built-in fallbacks

All configurations are loaded at import time. Use module-level variables (DEBUG, LOGGING_CONFIG,
DATABASE_MSSQL, ODPS, OSS_NEGATIVE_LIST) for direct access to configuration objects.

Usage:
    from app.configs import DEBUG, LOGGING_CONFIG, DATABASE_MSSQL

    if DEBUG:
        logger.setLevel(logging.DEBUG)

    if LOGGING_CONFIG.validate_format():
        console_output = LOGGING_CONFIG.format

Environment Variables:
    DEBUG: Enable debug mode ('true'/'false', default: 'false')
    DATETIME_NOW: ISO format datetime; empty = current time
    LOG_LEVEL, LOG_FORMAT, LOG_DIR, LOG_FILE_PREFIX, etc.
    DATABASE_MSSQL_*, DATABASE_POSTGRES_*, ODPS_*, OSS_*, etc.
    (See config_schemas.py for complete environment variable mappings)

Notes:
    - Configuration is loaded at module import time
    - Changes to environment variables after import are not reflected until reload
    - Validation of required credentials happens at connection time, not config load time
    - Extend schemas in config_schemas.py for new services
"""

import logging
import os

from dotenv import load_dotenv

from app.configs.config_schemas import (
    AppConfig,
    DatabaseConfig,
    LoggingConfig,
    ODPSConfig,
    OSSConfig,
)

# Import logger only if available (allows standalone use without log_config)
try:
    from app.configs.log_config import logger
except ImportError:
    logger = logging.getLogger(__name__)


def load_environment() -> None:
    """Load environment configuration from multiple sources.

    Loads environment variables in priority order:
        1. Vault secrets: /vault/secrets/.env (if present)
        2. Local .env file: project root directory

    The function is idempotent and safe to call multiple times. Both calls use
    override=False to preserve already-set environment variables.

    Side Effects:
        Prints status messages indicating which configuration sources were loaded.
    """
    vault_env = "/vault/secrets/.env"

    if os.path.exists(vault_env):
        load_dotenv(vault_env, override=False)
        print(f"✓ Loaded Vault secrets from {vault_env}")
    else:
        load_dotenv(override=False)
        print("✓ Loaded environment variables from .env (if present)")


# Load configuration from environment
load_environment()

# ============================================================================
# DEBUG AND APPLICATION CONFIGURATION
# ============================================================================
APP_CONFIG: AppConfig = AppConfig(
    debug=os.environ.get("DEBUG", "false").lower() == "true"
)
DEBUG = APP_CONFIG.debug

# ============================================================================
# LOGGING CONFIGURATION (using LoggingConfig schema)
# ============================================================================
LOGGING_CONFIG: LoggingConfig = LoggingConfig(
    level=os.environ.get("LOG_LEVEL", "INFO").upper(),
    format=os.environ.get("LOG_FORMAT", "json").lower(),  # 'json' or 'text'
    dir=os.environ.get("LOG_DIR", "./logs"),
    file_prefix=os.environ.get("LOG_FILE_PREFIX", "misc_function"),
    retention_days=int(os.environ.get("LOG_RETENTION_DAYS", "7")),
    max_files=int(os.environ.get("MAX_LOG_FILES", "50")),
    enable_file_rotation=os.environ.get("ENABLE_LOG_ROTATION", "true").lower() == "true",
    enable_compression=os.environ.get("ENABLE_LOG_COMPRESSION", "true").lower() == "true",
    diagnose=os.environ.get("LOG_DIAGNOSE", "true").lower() == "true",
)

# Timezone configuration (change this for different regions)
DEFAULT_TIMEZONE = "Asia/Jakarta"


# ============================================================================
# DATABASE CONFIGURATION: MSSQL (using DatabaseConfig schema)
# ============================================================================
DATABASE_MSSQL: DatabaseConfig = DatabaseConfig(
    host=os.environ.get("DATABASE_MSSQL_HOST", ""),
    port=os.environ.get("DATABASE_MSSQL_PORT", "1433"),
    user=os.environ.get("DATABASE_MSSQL_USER", ""),
    password=os.environ.get("DATABASE_MSSQL_PASSWORD", ""),
    database=os.environ.get("DATABASE_MSSQL_DATABASE", ""),
    driver=os.environ.get("DATABASE_MSSQL_DRIVER", "ODBC Driver 17 for SQL Server"),
    dialect=os.environ.get("DATABASE_MSSQL_DIALECT", "mssql"),
    library=os.environ.get("DATABASE_MSSQL_LIBRARY", "pyodbc"),
    pool_size=int(os.environ.get("DATABASE_MSSQL_POOL_SIZE", "5")),
    max_overflow=int(os.environ.get("DATABASE_MSSQL_MAX_OVERFLOW", "10")),
    connect_timeout=int(os.environ.get("DATABASE_MSSQL_CONNECT_TIMEOUT", "30")),
    command_timeout=int(os.environ.get("DATABASE_MSSQL_COMMAND_TIMEOUT", "300")),
)

# Database router for accessing multiple database configurations
database_config: dict[str, DatabaseConfig] = {
    "mssql": DATABASE_MSSQL,
    # Add other databases as needed:
    # "postgres": DATABASE_POSTGRES,
    # "mysql": DATABASE_MYSQL,
}


# ============================================================================
# ALIBABA MAXCOMPUTE (ODPS) CONFIGURATION
# ============================================================================
ODPS: ODPSConfig = ODPSConfig(
    access_id=os.environ.get("ODPS_ACCESS_ID", ""),
    secret_access_key=os.environ.get("ODPS_ACCESS_KEY", ""),
    project=os.environ.get("ODPS_PROJECT", ""),
    endpoint=os.environ.get("ODPS_ENDPOINT", ""),
    region=os.environ.get("ODPS_REGION", ""),
)

# ============================================================================
# ALIBABA OBJECT STORAGE SERVICE (OSS) CONFIGURATION
# ============================================================================
OSS_NEGATIVE_LIST: OSSConfig = OSSConfig(
    access_key_id=os.environ.get("OSS_NEGATIVE_LIST_ACCESS_KEY_ID", ""),
    access_key_secret=os.environ.get("OSS_NEGATIVE_LIST_ACCESS_KEY_SECRET", ""),
    bucket_name=os.environ.get("OSS_NEGATIVE_LIST_BUCKET_NAME", ""),
    endpoint=os.environ.get("OSS_NEGATIVE_LIST_ENDPOINT", ""),
    region=os.environ.get("OSS_NEGATIVE_LIST_REGION", ""),
)

# ============================================================================
# PROJECT-SPECIFIC CONFIGURATION (add directly in config.py)
# ============================================================================
# Enable caching of task output files on PVC to skip re-processing
ENABLE_TASK_OUTPUT_CACHE: bool = (
    os.environ.get("ENABLE_TASK_OUTPUT_CACHE", "true").lower() == "true"
)
TASK_OUTPUT_CACHE_HOURS: int = int(os.environ.get("TASK_OUTPUT_CACHE_HOURS", "12"))
