"""Application configuration module with validated schemas and environment loading.

Provides easy access to all configuration classes and utilities from a single import point.

Quick Start:
    from app.configs import (
        LOGGING, DATABASE_MSSQL, ODPS, OSS_NEGATIVE_LIST, DEBUG, now,
        LoggingConfig, DatabaseConfig, ODPSConfig, OSSConfig,
    )

All Main Objects:
    - DEBUG: Debug mode flag
    - LOGGING: LoggingConfig instance with all logging settings
    - DATABASE_MSSQL: DatabaseConfig for MSSQL database
    - ODPS: ODPSConfig for Alibaba MaxCompute
    - OSS_NEGATIVE_LIST: OSSConfig for Alibaba OSS bucket configuration
    - now: Current datetime in configured timezone
    - load_environment(): Function to reload environment variables

All Schema Classes:
    - DatabaseConfig: RDBMS database configuration schema
    - LoggingConfig: Logging settings schema
    - KafkaConfig: Kafka/MQ configuration schema
    - AppConfig: Application-level configuration schema
    - ODPSConfig: Alibaba MaxCompute configuration schema
    - OSSConfig: Alibaba OSS bucket configuration schema
"""

from app.configs.config import (
    DATABASE_MSSQL,
    DEBUG,
    LOGGING_CONFIG,
    ODPS,
    OSS_NEGATIVE_LIST,
    load_environment,
)
from app.configs.config_schemas import (
    AppConfig,
    DatabaseConfig,
    KafkaConfig,
    LoggingConfig,
    ODPSConfig,
    OSSConfig,
)

__all__ = [
    # Configuration instances
    "DEBUG",
    "LOGGING_CONFIG",
    "DATABASE_MSSQL",
    "ODPS",
    "OSS_NEGATIVE_LIST",
    "load_environment",
    # Configuration schemas
    "DatabaseConfig",
    "LoggingConfig",
    "KafkaConfig",
    "AppConfig",
    "ODPSConfig",
    "OSSConfig",
]
