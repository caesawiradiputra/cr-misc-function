"""Pydantic configuration schemas for validated service configurations.

Provides reusable, copy-paste ready schemas for databases, logging, Kafka, Elasticsearch, and
cloud services. Designed to integrate with app/configs/config.py while maintaining
backward compatibility with plain Python variables.

Integration Pattern:
- Schemas use Pydantic for type validation and constraints
- Load from environment variables via app/configs/config.py
- All fields default to "" or None (no validation failures on missing env vars)
- Validation happens at connection time, not config load time
- Each schema allows extra fields via Config.extra = "allow" for extensibility

Key Principles:
1. **Copy-Paste Ready**: No project-specific imports or assumptions
2. **Mixable**: Combine Pydantic schemas with plain variables in config.py
3. **Extensible**: Config.extra = "allow" enables project-specific fields
4. **Type Safe**: Pydantic provides runtime validation and IDE support
5. **Backward Compatible**: Works alongside existing config patterns

Usage in config.py:
    from app.configs.config_schemas import DatabaseConfig, LoggingConfig, AppConfig
    import os

    # Simple service configuration
    LOGGING = LoggingConfig(
        level=os.environ.get("LOG_LEVEL", "INFO").upper(),
        format=os.environ.get("LOG_FORMAT", "json").lower(),  # 'json' or 'text'
        dir=os.environ.get("LOG_DIR", "./logs"),
        file_prefix=os.environ.get("LOG_FILE_PREFIX", "misc_function"),
    )

    # Multiple databases as dict
    databases = {
        "mssql": DatabaseConfig(
            host=os.environ.get("DATABASE_MSSQL_HOST", ""),
            port=os.environ.get("DATABASE_MSSQL_PORT", "1433"),
            user=os.environ.get("DATABASE_MSSQL_USER", ""),
            password=os.environ.get("DATABASE_MSSQL_PASSWORD", ""),
            database=os.environ.get("DATABASE_MSSQL_DATABASE", ""),
        ),
        "postgres": DatabaseConfig(
            host=os.environ.get("DATABASE_POSTGRES_HOST", ""),
            port=os.environ.get("DATABASE_POSTGRES_PORT", "5432"),
            ...
        )
    }

    # Check configuration is valid
    if LOGGING.validate_format():
        console_mode = LOGGING.format
    if databases["mssql"].is_configured():
        connect_to_database(databases["mssql"])
"""

from datetime import datetime

import pytz
from pydantic import BaseModel, Field


def _parse_datetime_now(datetime_now_str: str = "", timezone: str = "Asia/Jakarta") -> datetime:
    """Parse datetime string or return current datetime.

    Supports multiple datetime formats:
    - ISO format: 2024-04-10T15:30:45 or 2024-04-10T15:30:45.123456
    - Date only: 2024-04-10 or YYYY-MM-DD
    - Compact: 20240410 or YYYYMMDD
    - Empty string: returns current datetime

    Args:
        datetime_now_str: Datetime string to parse (empty = current time)
        timezone: Timezone for datetime (default: "Asia/Jakarta")

    Returns:
        datetime object with specified timezone. If datetime_now_str empty, returns current time.

    Raises:
        ValueError: If datetime_now_str format is invalid (when non-empty).
    """
    datetime_now_str = datetime_now_str.strip()

    if not datetime_now_str:
        return datetime.now(pytz.timezone(timezone))

    try:
        # Try ISO format first (includes datetime with optional microseconds)
        parsed = datetime.fromisoformat(datetime_now_str)
        return parsed.replace(tzinfo=pytz.timezone(timezone))
    except ValueError:
        pass

    try:
        # Try YYYY-MM-DD format
        if "-" in datetime_now_str and datetime_now_str.count("-") == 2:
            parsed = datetime.strptime(datetime_now_str, "%Y-%m-%d")
            return parsed.replace(tzinfo=pytz.timezone(timezone))
    except ValueError:
        pass

    try:
        # Try YYYYMMDD format (compact)
        if datetime_now_str.isdigit() and len(datetime_now_str) == 8:
            parsed = datetime.strptime(datetime_now_str, "%Y%m%d")
            return parsed.replace(tzinfo=pytz.timezone(timezone))
    except ValueError:
        pass

    raise ValueError(
        f"Invalid DATETIME_NOW format: '{datetime_now_str}'. "
        "Supported formats: ISO (2024-04-10T15:30:45), Date (2024-04-10), Compact (20240410)"
    )


class DatabaseConfig(BaseModel):
    """General relational database configuration schema for RDBMS systems.

    Supports MSSQL, PostgreSQL, MySQL, Trino, and similar databases.
    Designed to work with app/configs/config.py for multi-database setups.

    Environment Variable Integration:
    When used in config.py, implement the pattern:
        DATABASE_<TYPE>_HOST, DATABASE_<TYPE>_PORT, DATABASE_<TYPE>_USER,
        DATABASE_<TYPE>_PASSWORD, DATABASE_<TYPE>_DATABASE, DATABASE_<TYPE>_DRIVER,
        DATABASE_<TYPE>_DIALECT, DATABASE_<TYPE>_LIBRARY

    For example, for MSSQL:
        DATABASE_MSSQL_HOST, DATABASE_MSSQL_PORT, DATABASE_MSSQL_USER,
        DATABASE_MSSQL_PASSWORD, DATABASE_MSSQL_DATABASE, DATABASE_MSSQL_DRIVER,
        DATABASE_MSSQL_DIALECT, DATABASE_MSSQL_LIBRARY

    Attributes:
        host: Database server hostname or IP address (empty string = not configured)
        port: Database server port (as int or str; defaults empty for flexibility)
        user: Database username for authentication (empty string = not configured)
        password: Database password for authentication (empty string = not configured)
        database: Database name to connect to (empty string = not configured)
        driver: Optional database driver name (e.g., "ODBC Driver 17 for SQL Server")
        dialect: SQLAlchemy dialect name (e.g., "mssql", "postgresql", "mysql")
        library: Python library/driver for SQLAlchemy URL (e.g., "pyodbc", "psycopg2")
        pool_size: Connection pool size for pooling strategies (default: 5)
        max_overflow: Max overflow connections beyond pool_size (default: 10)
        connect_timeout: Connection timeout in seconds (default: 30)
        command_timeout: Command/query timeout in seconds (default: 300)

    Example (MSSQL in config.py):
        DATABASE_MSSQL = DatabaseConfig(
            host=os.environ.get("DATABASE_MSSQL_HOST", ""),
            port=os.environ.get("DATABASE_MSSQL_PORT", "1433"),
            user=os.environ.get("DATABASE_MSSQL_USER", ""),
            password=os.environ.get("DATABASE_MSSQL_PASSWORD", ""),
            database=os.environ.get("DATABASE_MSSQL_DATABASE", ""),
            driver="ODBC Driver 17 for SQL Server",
            dialect="mssql",
            library="pyodbc",
        )
        sqlalchemy_url = DATABASE_MSSQL.get_sqlalchemy_url()
        # Returns: "mssql+pyodbc://user:pass@host:1433/database"

    Example (PostgreSQL in config.py):
        DATABASE_POSTGRES = DatabaseConfig(
            host=os.environ.get("DATABASE_POSTGRES_HOST", ""),
            port=os.environ.get("DATABASE_POSTGRES_PORT", "5432"),
            user=os.environ.get("DATABASE_POSTGRES_USER", ""),
            password=os.environ.get("DATABASE_POSTGRES_PASSWORD", ""),
            database=os.environ.get("DATABASE_POSTGRES_DATABASE", ""),
            dialect="postgresql",
            library="psycopg2",
        )
        sqlalchemy_url = DATABASE_POSTGRES.get_sqlalchemy_url()
        # Returns: "postgresql+psycopg2://user:pass@host:5432/database"

    Example (Multiple Databases):
        databases = {
            "mssql": DATABASE_MSSQL,
            "postgres": DATABASE_POSTGRES,
        }
    """
    host: str = Field(default="", description="Database hostname or IP")
    port: int | str = Field(default="", description="Database port")
    user: str = Field(default="", description="Database username")
    password: str = Field(default="", description="Database password")
    database: str = Field(default="", description="Database name")
    driver: str | None = Field(default=None, description="Database driver name")
    dialect: str = Field(default="", description="SQLAlchemy dialect (e.g., mssql, postgresql)")
    library: str = Field(default="", description="Python library for SQLAlchemy (e.g., pyodbc, psycopg2)")
    pool_size: int = Field(default=5, description="Connection pool size")
    max_overflow: int = Field(default=10, description="Max overflow connections")
    connect_timeout: int = Field(default=30, description="Connection timeout (seconds)")
    command_timeout: int = Field(default=300, description="Command timeout (seconds)")

    class Config:
        extra = "allow"  # Allow project-specific fields like schema, role, etc.

    def is_configured(self) -> bool:
        """Check if minimum required fields are set.

        Returns:
            True if host and port are provided, False otherwise.
        """
        return bool(self.host and self.port)

    def get_sqlalchemy_url(self) -> str:
        """Generate SQLAlchemy connection URL from configuration.

        Builds a SQLAlchemy dialect URL in the format:
            dialect+library://user:password@host:port/database

        Returns:
            SQLAlchemy connection URL string.

        Raises:
            ValueError: If dialect or library is not set, or if required connection fields are missing.

        Examples:
            mssql_config = DatabaseConfig(
                host="localhost", port="1433", user="sa", password="pass",
                database="mydb", dialect="mssql", library="pyodbc"
            )
            url = mssql_config.get_sqlalchemy_url()
            # Returns: "mssql+pyodbc://sa:pass@localhost:1433/mydb"

            postgres_config = DatabaseConfig(
                host="localhost", port="5432", user="postgres", password="pass",
                database="mydb", dialect="postgresql", library="psycopg2"
            )
            url = postgres_config.get_sqlalchemy_url()
            # Returns: "postgresql+psycopg2://postgres:pass@localhost:5432/mydb"
        """
        if not self.dialect:
            raise ValueError("dialect is required for SQLAlchemy URL generation")
        if not self.library:
            raise ValueError("library is required for SQLAlchemy URL generation")
        if not self.host or not self.port or not self.user or not self.database:
            raise ValueError(
                "host, port, user, and database are required for SQLAlchemy URL generation"
            )

        return (
            f"{self.dialect}+{self.library}://{self.user}:{self.password}@"
            f"{self.host}:{self.port}/{self.database}"
        )


class LoggingConfig(BaseModel):
    """Logging configuration schema aligned with app/configs/log_config.py setup.

    Supports dual console output formats:
    - 'json': Structured JSON for log aggregation (Grafana, ELK, Datadog)
    - 'text': Colorized text with loguru markup for local development

    File logging always uses loguru markup format with rotation and compression.
    Integrates with log_config.py which handles loguru initialization via init_logging().

    Environment Variable Integration:
    Load from environment in config.py using:
        LOG_LEVEL, LOG_FORMAT, LOG_DIR, LOG_FILE_PREFIX,
        LOG_RETENTION_DAYS, MAX_LOG_FILES

    Attributes:
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL; default: "INFO")
        format: Console output format - 'json' (Grafana) or 'text' (dev; default: "json")
        dir: Directory path for log files (default: "./logs")
        file_prefix: Prefix for log filenames (default: "app"; e.g., "misc_function")
        retention_days: Days to retain log files before deletion (default: 7)
        max_files: Maximum number of log files to keep (default: 50)
        enable_file_rotation: Enable daily log file rotation (default: True)
        enable_compression: Compress rotated logs as zip files (default: True)
        diagnose: Include full diagnostics traceback in file logs (default: True)

    Example (Production - JSON to Grafana):
        LOGGING = LoggingConfig(
            level=os.environ.get("LOG_LEVEL", "INFO").upper(),
            format="json",  # For Grafana/ELK aggregation
            dir=os.environ.get("LOG_DIR", "./logs"),
            file_prefix=os.environ.get("LOG_FILE_PREFIX", "misc_function"),
            retention_days=int(os.environ.get("LOG_RETENTION_DAYS", "7")),
            max_files=int(os.environ.get("MAX_LOG_FILES", "50")),
        )

    Example (Development - Colorized Text):
        LOGGING = LoggingConfig(
            level="DEBUG",
            format="text",  # For local development
            dir="./logs",
            file_prefix="myapp",
            retention_days=3,
            max_files=20,
        )
    """
    level: str = Field(default="INFO", description="Logging level")
    format: str = Field(default="json", description="Console format: 'json' or 'text'")
    dir: str = Field(default="./logs", description="Log directory path")
    file_prefix: str = Field(default="app", description="Log filename prefix")
    retention_days: int = Field(default=7, description="Log retention days")
    max_files: int = Field(default=50, description="Max log files to keep")
    enable_file_rotation: bool = Field(default=True, description="Enable daily rotation")
    enable_compression: bool = Field(default=True, description="Compress rotated logs")
    diagnose: bool = Field(default=True, description="Full diagnostics in file logs")

    class Config:
        extra = "allow"

    def validate_level(self) -> bool:
        """Check if logging level is valid.

        Returns:
            True if level is one of: DEBUG, INFO, WARNING, ERROR, CRITICAL
        """
        valid_levels = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        return self.level.upper() in valid_levels

    def validate_format(self) -> bool:
        """Check if format is valid.

        Returns:
            True if format is 'json' or 'text'
        """
        return self.format.lower() in {"json", "text"}


class KafkaConfig(BaseModel):
    """General Kafka configuration schema.

    Supports both Kafka brokers (for standard Kafka) and Alibaba Message Queue for Apache Kafka (MQ for Kafka).
    Can be extended with authentication, SSL/TLS, and other options.

    Attributes:
        bootstrap_servers: Comma-separated list of Kafka brokers (e.g., "localhost:9092")
        topic: Default topic name for producers/consumers
        group_id: Consumer group ID for distributed processing
        client_id: Client identifier for Kafka broker
        security_protocol: Security protocol ('PLAINTEXT', 'SSL', 'SASL_SSL')
        sasl_mechanism: SASL mechanism for authentication ('PLAIN', 'SCRAM-SHA-256')
        sasl_username: SASL username
        sasl_password: SASL password
        auto_offset_reset: Auto offset reset policy ('earliest', 'latest', 'none')
        enable_auto_commit: Auto-commit offsets (default: True)
        session_timeout_ms: Session timeout in milliseconds (default: 30000)
        max_poll_records: Max records per poll (default: 500)

    Example:
        # Standard Kafka
        kafka = KafkaConfig(
            bootstrap_servers="kafka1:9092,kafka2:9092,kafka3:9092",
            topic="events",
            group_id="my_consumer_group",
            auto_offset_reset="earliest",
        )

        # Alibaba MQ for Kafka (SASL authentication)
        mq_kafka = KafkaConfig(
            bootstrap_servers="mq-kafka-broker:9092",
            topic="data_stream",
            group_id="processor_group",
            security_protocol="SASL_SSL",
            sasl_mechanism="SCRAM-SHA-256",
            sasl_username=os.environ.get("KAFKA_USER"),
            sasl_password=os.environ.get("KAFKA_PASSWORD"),
        )
    """
    bootstrap_servers: str = Field(default="", description="Kafka broker addresses")
    topic: str = Field(default="", description="Default topic name")
    group_id: str | None = Field(default=None, description="Consumer group ID")
    client_id: str | None = Field(default=None, description="Kafka client ID")
    security_protocol: str = Field(default="PLAINTEXT", description="Security protocol")
    sasl_mechanism: str | None = Field(default=None, description="SASL mechanism")
    sasl_username: str | None = Field(default=None, description="SASL username")
    sasl_password: str | None = Field(default=None, description="SASL password")
    auto_offset_reset: str = Field(default="latest", description="Offset reset policy")
    enable_auto_commit: bool = Field(default=True, description="Auto-commit offsets")
    session_timeout_ms: int = Field(default=30000, description="Session timeout (ms)")
    max_poll_records: int = Field(default=500, description="Max records per poll")

    class Config:
        extra = "allow"

    def is_configured(self) -> bool:
        """Check if minimum required fields are set.

        Returns:
            True if bootstrap_servers and topic are provided
        """
        return bool(self.bootstrap_servers and self.topic)


class ElasticsearchConfig(BaseModel):
    """Elasticsearch integration configuration schema.

    Supports Elasticsearch clusters (including Alibaba Cloud Elasticsearch).
    Can be extended with additional options like API key auth, SSL/TLS settings, etc.

    Environment Variable Integration:
    Load from environment in config.py using:
        ELASTICSEARCH_ENABLED, ELASTICSEARCH_HOSTS, ELASTICSEARCH_INDEX,
        ELASTICSEARCH_SCHEMA, ELASTICSEARCH_USERNAME, ELASTICSEARCH_PASSWORD

    Attributes:
        enabled: Whether Elasticsearch is enabled (default: False)
        hosts: Comma-separated list of Elasticsearch hosts (e.g., "host1:9200,host2:9200")
            or full URLs (e.g., "https://es.example.com:9200")
        index: Elasticsearch index name for logs (e.g., "log-dev-da-nl")
        connection_schema: Connection schema - 'http' or 'https' (default: "https")
        username: Username for authentication (empty = no auth)
        password: Password for authentication (empty = no auth)
        request_timeout: Request timeout in seconds (default: 30)
        max_retries: Maximum retries for failed requests (default: 3)
        verify_certs: Verify SSL certificates (default: True)

    Example (config.py Integration):
        ELASTICSEARCH = ElasticsearchConfig(
            enabled=os.environ.get("ELASTICSEARCH_ENABLED", "false").lower() == "true",
            hosts=os.environ.get("ELASTICSEARCH_HOSTS", ""),
            index=os.environ.get("ELASTICSEARCH_INDEX", ""),
            connection_schema=os.environ.get("ELASTICSEARCH_SCHEMA", "https"),
            username=os.environ.get("ELASTICSEARCH_USERNAME", ""),
            password=os.environ.get("ELASTICSEARCH_PASSWORD", ""),
        )

    Example (Alibaba Cloud Elasticsearch):
        # Environment variables:
        # ELASTICSEARCH_ENABLED=true
        # ELASTICSEARCH_HOSTS=https://es-sg-6wr29ezb50004pp81.elasticsearch.aliyuncs.com:9200
        # ELASTICSEARCH_INDEX=log-dev-da-nl-sync-lms-consumer
        # ELASTICSEARCH_SCHEMA=https
        # ELASTICSEARCH_USERNAME=elastic
        # ELASTICSEARCH_PASSWORD=pV6wEeJB6PPhD2bW

        ELASTICSEARCH = ElasticsearchConfig(
            enabled=True,
            hosts="https://es-sg-6wr29ezb50004pp81.elasticsearch.aliyuncs.com:9200",
            index="log-dev-da-nl-sync-lms-consumer",
            connection_schema="https",
            username="elastic",
            password="pV6wEeJB6PPhD2bW",
        )
    """
    enabled: bool = Field(default=False, description="Enable Elasticsearch integration")
    hosts: str = Field(default="", description="Elasticsearch host(s) - comma-separated")
    index: str = Field(default="", description="Target index name")
    connection_schema: str = Field(default="https", description="Connection schema: 'http' or 'https'")
    username: str = Field(default="", description="Username for authentication")
    password: str = Field(default="", description="Password for authentication")
    request_timeout: int = Field(default=30, description="Request timeout (seconds)")
    max_retries: int = Field(default=3, description="Max retries for failed requests")
    verify_certs: bool = Field(default=True, description="Verify SSL certificates")

    class Config:
        extra = "allow"

    def is_configured(self) -> bool:
        """Check if minimum required fields are set for enabled Elasticsearch.

        Returns:
            True if enabled and hosts, index, username, password are all provided
        """
        if not self.enabled:
            return False
        return bool(self.hosts and self.index and self.username and self.password)


class AppConfig(BaseModel):
    """Application-level configuration schema for cross-cutting concerns.

    High-level app settings independent of specific services (databases, logging, etc.).
    Useful for environment detection, feature flags, and app-wide behavior.

    Project-specific fields can be added manually in config.py using Config.extra = "allow".

    Environment Variable Integration:
    Load from environment in config.py using:
        DEBUG, APP_ENV, APP_NAME, APP_VERSION, TIMEZONE, DATETIME_NOW

    Attributes:
        debug: Enable debug mode (from DEBUG env var; default: False)
        environment: Environment name - 'development', 'staging', 'production'
        app_name: Application name for logging/identification (default: "app")
        app_version: Application semantic version (default: "1.0.0")
        timezone: Application timezone (default: "Asia/Jakarta"; e.g., "UTC", "Asia/Shanghai")
        max_workers: Max concurrent workers/threads (default: 4)
        request_timeout_seconds: Request/API timeout in seconds (default: 30)
        datetime_now: Processing date/reference datetime (default: current time)

    Example (config.py Integration):
        from app.configs.config_schemas import AppConfig, _parse_datetime_now
        from datetime import datetime
        import os
        import pytz

        # Parse DATETIME_NOW env var if provided, otherwise use current time
        datetime_now_str = os.environ.get("DATETIME_NOW", "")
        datetime_now = (_parse_datetime_now(datetime_now_str, "Asia/Jakarta")
                        if datetime_now_str
                        else datetime.now(pytz.timezone("Asia/Jakarta")))

        # Create AppConfig
        APP = AppConfig(
            debug=os.environ.get("DEBUG", "false").lower() == "true",
            environment=os.environ.get("APP_ENV", "production").lower(),
            app_name=os.environ.get("APP_NAME", "misc_function"),
            app_version=os.environ.get("APP_VERSION", "1.0.0"),
            timezone=os.environ.get("TIMEZONE", "Asia/Jakarta"),
            datetime_now=datetime_now,
        )

    Usage in Application Code:
        from app.configs import APP

        if APP.is_development():
            LOGGING.level = "DEBUG"
        if APP.is_production():
            enable_alerts = True

        processing_date = APP.datetime_now.date()
        execution_timestamp = APP.datetime_now.isoformat()
    """
    debug: bool = Field(default=False, description="Debug mode")
    environment: str = Field(default="production", description="Environment name")
    app_name: str = Field(default="app", description="Application name")
    app_version: str = Field(default="1.0.0", description="Application version")
    timezone: str = Field(default="Asia/Jakarta", description="Application timezone")
    max_workers: int = Field(default=4, description="Max concurrent workers")
    request_timeout_seconds: int = Field(default=30, description="Request timeout (seconds)")
    datetime_now: datetime = Field(
        default_factory=lambda: datetime.now(pytz.timezone("Asia/Jakarta")),
        description="Processing date/reference datetime",
    )

    class Config:
        extra = "allow"

    def is_development(self) -> bool:
        """Check if running in development environment.

        Returns:
            True if environment is 'development' or debug is True
        """
        return self.environment.lower() in ("development", "dev") or self.debug

    def is_production(self) -> bool:
        """Check if running in production environment.

        Returns:
            True if environment is 'production'
        """
        return self.environment.lower() in ("production", "prod")


class ODPSConfig(BaseModel):
    """Alibaba MaxCompute (ODPS) data warehouse configuration schema.

    Used for connecting to Alibaba's ODPS/MaxCompute service for data processing.
    Aligns with existing config.py pattern for ODPS_* environment variables.

    Environment Variable Integration:
    Load from environment in config.py using:
        ODPS_ACCESS_ID, ODPS_ACCESS_KEY, ODPS_PROJECT, ODPS_ENDPOINT

    Attributes:
        access_id: Access ID credential (like AWS Access Key ID; empty = unconfigured)
        secret_access_key: Secret key for authentication (empty = unconfigured)
        project: ODPS project name (workspace; empty = unconfigured)
        endpoint: ODPS endpoint URL (e.g., "http://service.odps.aliyun.com/api")
        region: Optional region code (e.g., "cn-shanghai"; not required)

    Example (config.py Integration):
        ODPS = ODPSConfig(
            access_id=os.environ.get("ODPS_ACCESS_ID", ""),
            secret_access_key=os.environ.get("ODPS_ACCESS_KEY", ""),
            project=os.environ.get("ODPS_PROJECT", ""),
            endpoint=os.environ.get("ODPS_ENDPOINT", ""),
            region=os.environ.get("ODPS_REGION", "cn-shanghai"),
        )

    Validation:
        Use is_configured() before connecting to ODPS
    """
    access_id: str = Field(default="", description="ODPS access ID")
    secret_access_key: str = Field(default="", description="ODPS secret key")
    project: str = Field(default="", description="ODPS project name")
    endpoint: str = Field(default="", description="ODPS endpoint URL")
    region: str | None = Field(default=None, description="Region code")

    class Config:
        extra = "allow"

    def is_configured(self) -> bool:
        """Check if minimum required fields are set.

        Returns:
            True if all core credentials are provided
        """
        return bool(
            self.access_id
            and self.secret_access_key
            and self.project
            and self.endpoint
        )


class OSSConfig(BaseModel):
    """Alibaba Cloud OSS (Object Storage Service) configuration schema.

    Used for storing/retrieving objects from Alibaba's cloud storage.
    Typically one config per bucket/purpose ("negative_list", "data_archive", etc.).
    Aligns with existing config.py pattern for multiple OSS buckets via dict routing.

    Environment Variable Integration:
    For each bucket, define environment variables:
        OSS_<BUCKET>_ACCESS_KEY_ID, OSS_<BUCKET>_ACCESS_KEY_SECRET,
        OSS_<BUCKET>_BUCKET_NAME, OSS_<BUCKET>_ENDPOINT, OSS_<BUCKET>_REGION

    For example, for "negative_list" bucket:
        OSS_NEGATIVE_LIST_ACCESS_KEY_ID, OSS_NEGATIVE_LIST_ACCESS_KEY_SECRET,
        OSS_NEGATIVE_LIST_BUCKET_NAME, OSS_NEGATIVE_LIST_ENDPOINT

    Attributes:
        access_key_id: Access key ID for authentication (empty = unconfigured)
        access_key_secret: Access key secret for authentication (empty = unconfigured)
        bucket_name: OSS bucket name (target storage; empty = unconfigured)
        endpoint: OSS endpoint URL (e.g., "oss-cn-shanghai.aliyuncs.com")
        region: Region name for the bucket (optional; e.g., "cn-shanghai")
        base_path: Optional base path/prefix for all objects (e.g., "negative_lists/")

    Example (Single Bucket in config.py):
        OSS_NEGATIVE_LIST = OSSConfig(
            access_key_id=os.environ.get("OSS_NEGATIVE_LIST_ACCESS_KEY_ID", ""),
            access_key_secret=os.environ.get("OSS_NEGATIVE_LIST_ACCESS_KEY_SECRET", ""),
            bucket_name=os.environ.get("OSS_NEGATIVE_LIST_BUCKET_NAME", ""),
            endpoint=os.environ.get("OSS_NEGATIVE_LIST_ENDPOINT", ""),
            region=os.environ.get("OSS_NEGATIVE_LIST_REGION", ""),
            base_path="negative_lists/",
        )

    Example (Multiple Buckets in config.py Dict):
        oss_buckets = {
            "negative_list": OSS_NEGATIVE_LIST,
            "data_archive": OSSConfig(
                access_key_id=os.environ.get("OSS_DATA_ARCHIVE_ACCESS_KEY_ID", ""),
                ...
            ),
        }
    """
    access_key_id: str = Field(default="", description="OSS access key ID")
    access_key_secret: str = Field(default="", description="OSS access key secret")
    bucket_name: str = Field(default="", description="OSS bucket name")
    endpoint: str = Field(default="", description="OSS endpoint URL")
    region: str | None = Field(default=None, description="Region name")
    base_path: str | None = Field(default=None, description="Base path prefix")

    class Config:
        extra = "allow"

    def is_configured(self) -> bool:
        """Check if minimum required fields are set.

        Returns:
            True if all core credentials and bucket info are provided
        """
        return bool(
            self.access_key_id
            and self.access_key_secret
            and self.bucket_name
            and self.endpoint
        )
