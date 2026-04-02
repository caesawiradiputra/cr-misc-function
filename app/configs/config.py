"""Application configuration management with multi-source environment loading.

Supports three configuration sources (in priority order):
    1. Vault secrets: /vault/secrets/.env (Docker/Kubernetes deployments)
    2. Local .env file: project root directory
    3. Environment variables and defaults: built-in fallbacks

Usage:
    from app.configs.config import DEBUG, LOG_LEVEL, DATABASE_MSSQL, now

    # All configuration is loaded at import time
    if DEBUG:
        logger.setLevel(logging.DEBUG)

Environment Variables:
    DEBUG: Set to 'true' to enable debug mode (default: 'false')
    DATETIME_NOW: ISO format datetime; if empty uses current time in configured timezone
    LOG_LEVEL: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL) - default: INFO
    LOG_DIR: Directory for log files - default: ./logs
    LOG_FILE_PREFIX: Prefix for log filenames - default: misc_function
    LOG_RETENTION_DAYS: Keep logs for N days - default: 7
    MAX_LOG_FILES: Maximum number of log files to retain - default: 50
    DATABASE_MSSQL_*: MSSQL connection parameters
    ODPS_*: Alibaba MaxCompute (ODPS) connection parameters
    OSS_*: Alibaba Cloud OSS connection parameters
    ENABLE_TASK_OUTPUT_CACHE: Enable/disable task output caching (default: true)
    TASK_OUTPUT_CACHE_HOURS: Cache retention hours (default: 12)

Notes:
    - This module loads configuration at import time.
    - Changes to environment variables after import won't be reflected until reload.
    - All database and service configurations default to empty strings if env vars are missing.
    - Validation of required credentials happens at connection time, not config load time.

Customization:
    To use in another workspace:
    1. Copy this file to your project's app/configs/directory
    2. Keep the structure and environment variable names consistent
    3. Optionally customize DEFAULT_TIMEZONE for your region
    4. Add new databases/services by extending database_config and oss_config dicts
"""

import os
from datetime import datetime, timedelta
from typing import Any

import pytz
from dotenv import load_dotenv

# Import logger only if available (allows standalone use without log_config)
try:
    from app.configs.log_config import logger
except ImportError:
    import logging
    logger = logging.getLogger(__name__)


def load_environment() -> None:
    """Load environment configuration from multiple sources.

    Priority order:
        1. Vault secrets: /vault/secrets/.env (Docker/Kubernetes) - when present
        2. Local .env file: from project root - always attempted
        3. Environment variables and defaults - built-in fallbacks

    This function is idempotent and safe to call multiple times.
    Both calls use override=False to preserve environment variables already set.

    Side Effects:
        Prints informational messages about which configuration sources were loaded.

    Raises:
        No exceptions are raised; missing files are logged as info.
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
# DEBUG AND DATETIME CONFIGURATION
# ============================================================================
DEBUG: bool = os.environ.get("DEBUG", "false").lower() == "true"
DATETIME_NOW: str = os.environ.get("DATETIME_NOW", "").upper()

# ============================================================================
# LOGGING CONFIGURATION
# ============================================================================
LOG_LEVEL: str = os.environ.get("LOG_LEVEL", "INFO").upper()
LOG_DIR: str = os.environ.get("LOG_DIR", "./logs")
LOG_FILE_PREFIX: str = os.environ.get("LOG_FILE_PREFIX", "misc_function")
LOG_RETENTION_DAYS: int = int(os.environ.get("LOG_RETENTION_DAYS", "7"))
MAX_LOG_FILES: int = int(os.environ.get("MAX_LOG_FILES", "50"))

# Timezone configuration (change this for different regions)
DEFAULT_TIMEZONE = "Asia/Jakarta"  # Customize for your region

try:
    now: datetime = (
        datetime.fromisoformat(DATETIME_NOW).replace(tzinfo=pytz.timezone(DEFAULT_TIMEZONE))
        if DATETIME_NOW != ""
        else datetime.now(pytz.timezone(DEFAULT_TIMEZONE))
    )
except ValueError as e:
    raise ValueError(f"Invalid DATETIME_NOW format (expected ISO format): {DATETIME_NOW}") from e

print(f"✓ Processing time: {now} ({DEFAULT_TIMEZONE})")

# Derived date calculations (typically for daily batch jobs)
start_date: str = (now - timedelta(1)).strftime("%Y-%m-%d")
end_date: str = (now - timedelta(1)).strftime("%Y-%m-%d")

start_month: datetime = now.strptime(start_date, "%Y-%m-%d").replace(day=1)
start_month_partition_no: str = start_month.strftime("%Y%m%d")

date_id: datetime = now.strptime(start_date, "%Y-%m-%d")
date_id_partition_no: str = date_id.strftime("%Y%m%d")


# ============================================================================
# DATABASE CONFIGURATION: MSSQL
# ============================================================================
DATABASE_MSSQL_USER: str = os.environ.get("DATABASE_MSSQL_USER", "")
DATABASE_MSSQL_PASSWORD: str = os.environ.get("DATABASE_MSSQL_PASSWORD", "")
DATABASE_MSSQL_DATABASE: str = os.environ.get("DATABASE_MSSQL_DATABASE", "")
DATABASE_MSSQL_HOST: str = os.environ.get("DATABASE_MSSQL_HOST", "")
DATABASE_MSSQL_PORT: str = os.environ.get("DATABASE_MSSQL_PORT", "1433")  # Default MSSQL port
DATABASE_MSSQL_DRIVER: str = os.environ.get("DATABASE_MSSQL_DRIVER", "ODBC Driver 17 for SQL Server")

DATABASE_MSSQL: dict[str, Any] = {
    "user": DATABASE_MSSQL_USER,
    "password": DATABASE_MSSQL_PASSWORD,
    "database": DATABASE_MSSQL_DATABASE,
    "host": DATABASE_MSSQL_HOST,
    "port": DATABASE_MSSQL_PORT,
    "driver": DATABASE_MSSQL_DRIVER,
}

# Database router (add more databases by extending this dict)
database_config: dict[str, dict[str, Any]] = {
    "mssql": DATABASE_MSSQL,
    # Add other databases as needed:
    # "postgres": DATABASE_POSTGRES,
    # "mysql": DATABASE_MYSQL,
}


# ============================================================================
# ALIBABA MAXCOMPUTE (ODPS) CONFIGURATION
# ============================================================================
ODPS_ACCESS_ID: str = os.environ.get("ODPS_ACCESS_ID", "")
ODPS_ACCESS_KEY: str = os.environ.get("ODPS_ACCESS_KEY", "")
ODPS_PROJECT: str = os.environ.get("ODPS_PROJECT", "")
ODPS_ENDPOINT: str = os.environ.get("ODPS_ENDPOINT", "")

odps_config: dict[str, Any] = {
    "access_id": ODPS_ACCESS_ID,
    "secret_access_key": ODPS_ACCESS_KEY,
    "default_project": ODPS_PROJECT,
    "endpoint": ODPS_ENDPOINT,
}


# ============================================================================
# ALIBABA CLOUD OSS (OBJECT STORAGE SERVICE) CONFIGURATION
# ============================================================================
OSS_NEGATIVE_LIST_ACCESS_KEY_ID: str = os.environ.get("OSS_NEGATIVE_LIST_ACCESS_KEY_ID", "")
OSS_NEGATIVE_LIST_ACCESS_KEY_SECRET: str = os.environ.get("OSS_NEGATIVE_LIST_ACCESS_KEY_SECRET", "")
OSS_NEGATIVE_LIST_BUCKET_NAME: str = os.environ.get("OSS_NEGATIVE_LIST_BUCKET_NAME", "")
OSS_NEGATIVE_LIST_ENDPOINT: str = os.environ.get("OSS_NEGATIVE_LIST_ENDPOINT", "")
OSS_NEGATIVE_LIST_REGION: str = os.environ.get("OSS_NEGATIVE_LIST_REGION", "")

oss_config: dict[str, dict[str, Any]] = {
    "negative_list": {
        "access_key_id": OSS_NEGATIVE_LIST_ACCESS_KEY_ID,
        "access_key_secret": OSS_NEGATIVE_LIST_ACCESS_KEY_SECRET,
        "bucket_name": OSS_NEGATIVE_LIST_BUCKET_NAME,
        "endpoint": OSS_NEGATIVE_LIST_ENDPOINT,
        "region": OSS_NEGATIVE_LIST_REGION,
    },
    # Add more OSS buckets as needed:
    # "other_bucket": { ... }
}

# ============================================================================
# PERSISTENT VOLUME CLAIM (PVC) AND CACHING CONFIGURATION
# ============================================================================
# Enable caching of task output files on PVC to skip re-processing
ENABLE_TASK_OUTPUT_CACHE: bool = os.environ.get("ENABLE_TASK_OUTPUT_CACHE", "true").lower() == "true"
TASK_OUTPUT_CACHE_HOURS: int = int(os.environ.get("TASK_OUTPUT_CACHE_HOURS", "12"))
