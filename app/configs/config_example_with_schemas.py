"""Application configuration management with Pydantic schemas and multi-source environment loading.

Demonstrates integration of Pydantic configuration schemas with environment variable loading.
Supports three configuration sources (in priority order):
    1. Vault secrets: /vault/secrets/.env (Docker/Kubernetes deployments)
    2. Local .env file: project root directory
    3. Environment variables and defaults: built-in fallbacks

Usage:
    # Import specific schemas or plain variables
    from app.configs.config import DEBUG, LOG_LEVEL, LOGGING, DATABASE, KAFKA, APP
    from app.configs.config import ENABLE_TASK_OUTPUT_CACHE, TASK_OUTPUT_CACHE_HOURS

    # Use Pydantic models
    if LOGGING.is_configured():
        logger.setLevel(LOGGING.level)

    # Or use plain variables for project-specific settings
    if ENABLE_TASK_OUTPUT_CACHE:
        cache.enable(hours=TASK_OUTPUT_CACHE_HOURS)

Environment Variables:
    DEBUG: Set to 'true' to enable debug mode (default: 'false')
    DATETIME_NOW: ISO format datetime; if empty uses current time in configured timezone
    LOG_LEVEL: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL) - default: INFO
    LOG_FORMAT: Console format ('json' for Grafana, 'text' for local) - default: 'json'
    LOG_DIR: Directory for log files - default: ./logs
    LOG_FILE_PREFIX: Prefix for log filenames - default: misc_function
    LOG_RETENTION_DAYS: Keep logs for N days - default: 7
    MAX_LOG_FILES: Keep only N most recent log files - default: 50

    DATABASE_HOST, DATABASE_PORT, DATABASE_USER, DATABASE_PASSWORD, DATABASE_NAME
    KAFKA_BOOTSTRAP_SERVERS, KAFKA_TOPIC, KAFKA_GROUP_ID
    ODPS_ACCESS_ID, ODPS_SECRET_KEY, ODPS_PROJECT, ODPS_ENDPOINT
    OSS_ACCESS_KEY_ID, OSS_ACCESS_KEY_SECRET, OSS_BUCKET_NAME, OSS_ENDPOINT

    ENABLE_TASK_OUTPUT_CACHE: Enable/disable task output caching (default: true)
    TASK_OUTPUT_CACHE_HOURS: Cache retention hours (default: 12)

Notes:
    - Pydantic models provide validation and type safety
    - Plain variables still exist for project-specific settings
    - Configuration is loaded at import time
    - All models use Config.extra = "allow" for extensibility
    - Project-specific schemas can inherit from base schemas

Customization:
    To extend schemas for your project:
    1. Create a new schema in config_schemas.py inheriting from base (e.g., DatabaseConfig)
    2. Or add fields to the imported classes using Config.extra = "allow"
    3. Load environment variables the same way
"""

import os
from datetime import datetime, timedelta
from typing import Any

import pytz
from dotenv import load_dotenv

from app.configs.config_schemas import (
    AppConfig,
    DatabaseConfig,
    LoggingConfig,
)

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
# DEBUG AND DATETIME CONFIGURATION (Plain Variables)
# ============================================================================
DEBUG: bool = os.environ.get("DEBUG", "false").lower() == "true"
DATETIME_NOW: str = os.environ.get("DATETIME_NOW", "").upper()

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
# LOGGING CONFIGURATION (Pydantic Schema)
# ============================================================================
LOGGING: LoggingConfig = LoggingConfig(
    level=os.environ.get("LOG_LEVEL", "INFO").upper(),
    format=os.environ.get("LOG_FORMAT", "json").lower(),  # 'json' for Grafana, 'text' for standard
    dir=os.environ.get("LOG_DIR", "./logs"),
    file_prefix=os.environ.get("LOG_FILE_PREFIX", "misc_function"),
    retention_days=int(os.environ.get("LOG_RETENTION_DAYS", "7")),
    max_files=int(os.environ.get("MAX_LOG_FILES", "50")),
)

# Legacy plain variables for backward compatibility
LOG_LEVEL: str = LOGGING.level
LOG_DIR: str = LOGGING.dir
LOG_FILE_PREFIX: str = LOGGING.file_prefix
LOG_RETENTION_DAYS: int = LOGGING.retention_days
MAX_LOG_FILES: int = LOGGING.max_files
LOG_FORMAT: str = LOGGING.format


# ============================================================================
# APP CONFIGURATION (Pydantic Schema)
# ============================================================================
APP: AppConfig = AppConfig(
    debug=DEBUG,
    environment=os.environ.get("APP_ENV", "production").lower(),
    app_name=os.environ.get("APP_NAME", "misc_function"),
    app_version=os.environ.get("APP_VERSION", "1.0.0"),
    timezone=DEFAULT_TIMEZONE,
)


# ============================================================================
# DATABASE CONFIGURATION (Pydantic Schemas in Dict)
# ============================================================================
# Example: Single MSSQL database
DATABASE: DatabaseConfig = DatabaseConfig(
    host=os.environ.get("DATABASE_HOST", ""),
    port=os.environ.get("DATABASE_PORT", "1433"),
    user=os.environ.get("DATABASE_USER", ""),
    password=os.environ.get("DATABASE_PASSWORD", ""),
    database=os.environ.get("DATABASE_NAME", ""),
    driver=os.environ.get("DATABASE_DRIVER", "ODBC Driver 17 for SQL Server"),
)

# Example: Multiple databases as dict of schemas
# Uncomment and customize for your project
# DATABASE_MSSQL: DatabaseConfig = DatabaseConfig(
#     host=os.environ.get("DATABASE_MSSQL_HOST", ""),
#     port=os.environ.get("DATABASE_MSSQL_PORT", "1433"),
#     user=os.environ.get("DATABASE_MSSQL_USER", ""),
#     password=os.environ.get("DATABASE_MSSQL_PASSWORD", ""),
#     database=os.environ.get("DATABASE_MSSQL_NAME", ""),
#     driver="ODBC Driver 17 for SQL Server",
# )
#
# DATABASE_POSTGRES: DatabaseConfig = DatabaseConfig(
#     host=os.environ.get("DATABASE_POSTGRES_HOST", ""),
#     port=os.environ.get("DATABASE_POSTGRES_PORT", "5432"),
#     user=os.environ.get("DATABASE_POSTGRES_USER", ""),
#     password=os.environ.get("DATABASE_POSTGRES_PASSWORD", ""),
#     database=os.environ.get("DATABASE_POSTGRES_NAME", ""),
# )
#
# databases: dict[str, DatabaseConfig] = {
#     "mssql": DATABASE_MSSQL,
#     "postgres": DATABASE_POSTGRES,
# }


# ============================================================================
# KAFKA CONFIGURATION (Pydantic Schema - Optional)
# ============================================================================
# Uncomment if your project uses Kafka
# KAFKA: KafkaConfig = KafkaConfig(
#     bootstrap_servers=os.environ.get("KAFKA_BOOTSTRAP_SERVERS", ""),
#     topic=os.environ.get("KAFKA_TOPIC", ""),
#     group_id=os.environ.get("KAFKA_GROUP_ID", ""),
#     security_protocol=os.environ.get("KAFKA_SECURITY_PROTOCOL", "PLAINTEXT"),
#     sasl_mechanism=os.environ.get("KAFKA_SASL_MECHANISM"),
#     sasl_username=os.environ.get("KAFKA_SASL_USERNAME"),
#     sasl_password=os.environ.get("KAFKA_SASL_PASSWORD"),
# )


# ============================================================================
# ALIBABA MAXCOMPUTE (ODPS) CONFIGURATION (Pydantic Schema - Optional)
# ============================================================================
# Uncomment if your project uses ODPS
# ODPS: ODPSConfig = ODPSConfig(
#     access_id=os.environ.get("ODPS_ACCESS_ID", ""),
#     secret_access_key=os.environ.get("ODPS_SECRET_KEY", ""),
#     project=os.environ.get("ODPS_PROJECT", ""),
#     endpoint=os.environ.get("ODPS_ENDPOINT", ""),
# )


# ============================================================================
# ALIBABA CLOUD OSS CONFIGURATION (Pydantic Schemas in Dict - Optional)
# ============================================================================
# Uncomment and customize for your project
# OSS_NEGATIVE_LIST: OSSConfig = OSSConfig(
#     access_key_id=os.environ.get("OSS_NEGATIVE_LIST_ACCESS_KEY_ID", ""),
#     access_key_secret=os.environ.get("OSS_NEGATIVE_LIST_ACCESS_KEY_SECRET", ""),
#     bucket_name=os.environ.get("OSS_NEGATIVE_LIST_BUCKET_NAME", ""),
#     endpoint=os.environ.get("OSS_NEGATIVE_LIST_ENDPOINT", ""),
#     region=os.environ.get("OSS_NEGATIVE_LIST_REGION", ""),
# )
#
# oss_buckets: dict[str, OSSConfig] = {
#     "negative_list": OSS_NEGATIVE_LIST,
#     # Add more buckets as needed
# }


# ============================================================================
# PROJECT-SPECIFIC PLAIN VARIABLES (Keep These!)
# ============================================================================
# These are project-specific settings that don't fit standard schemas
# They can be added to the AppConfig schema or kept separate as needed

ENABLE_TASK_OUTPUT_CACHE: bool = os.environ.get("ENABLE_TASK_OUTPUT_CACHE", "true").lower() == "true"
TASK_OUTPUT_CACHE_HOURS: int = int(os.environ.get("TASK_OUTPUT_CACHE_HOURS", "12"))

# Legacy database router (alternative to using dict of schemas)
# Kept for backward compatibility with existing code
legacy_database_config: dict[str, dict[str, Any]] = {
    "mssql": {
        "host": DATABASE.host,
        "port": DATABASE.port,
        "user": DATABASE.user,
        "password": DATABASE.password,
        "database": DATABASE.database,
        "driver": DATABASE.driver,
    },
}
