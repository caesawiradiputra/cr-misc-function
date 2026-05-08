"""Integration Guide: Using Pydantic Configuration Schemas

This guide shows best practices for integrating Pydantic configuration schemas
into your project while maintaining backward compatibility with plain variables.

## Key Principles

1. **Copy-Paste Ready Schemas**: All schemas in config_schemas.py are general
   and designed to work in any project
2. **Extensible**: Each schema allows extra fields via Config.extra = "allow"
3. **Mixed Approach**: Use Pydantic schemas for validation + plain variables
   for project-specific settings
4. **Type Safety**: Pydantic provides runtime validation and IDE support
5. **Backward Compatible**: Keep plain variables alongside schemas

## Schema Overview

### DatabaseConfig

- General RDBMS configuration (MSSQL, PostgreSQL, MySQL, etc.)
- Default fields: host, port, user, password, database, driver
- Extensible: schema, role, pool_size, timeout, etc.
- Methods: is_configured() to check if valid

### LoggingConfig

- Unified logging configuration
- Supports JSON (Grafana/ELK) and text (local) formats
- Includes rotation, retention, compression settings
- Methods: validate_level(), validate_format()

### KafkaConfig

- Standard Kafka and Alibaba MQ for Kafka
- SASL/SSL authentication support
- Consumer and producer settings
- Methods: is_configured()

### AppConfig

- High-level application settings
- Feature flags, environment detection
- Cache and timeout settings
- Methods: is_development(), is_production()

### ODPSConfig, OSSConfig

- Alibaba cloud service configurations
- Authentication and connection details
- Methods: is_configured()

## Implementation Patterns

### Pattern 1: Single Service Configuration

```python
from app.configs.config_schemas import DatabaseConfig
import os

# Load from environment
DATABASE = DatabaseConfig(
    host=os.environ.get("DATABASE_HOST", ""),
    port=os.environ.get("DATABASE_PORT", "5432"),
    user=os.environ.get("DATABASE_USER", ""),
    password=os.environ.get("DATABASE_PASSWORD", ""),
    database=os.environ.get("DATABASE_NAME", ""),
)

# Use in your code
if DATABASE.is_configured():
    connection = connect(DATABASE.host, DATABASE.port, DATABASE.user)
```

### Pattern 2: Multiple Database Configurations

```python
from app.configs.config_schemas import DatabaseConfig
import os

# Define each database
DATABASE_MSSQL = DatabaseConfig(
    host=os.environ.get("DATABASE_MSSQL_HOST", ""),
    port=os.environ.get("DATABASE_MSSQL_PORT", "1433"),
    user=os.environ.get("DATABASE_MSSQL_USER", ""),
    password=os.environ.get("DATABASE_MSSQL_PASSWORD", ""),
    database=os.environ.get("DATABASE_MSSQL_NAME", ""),
    driver="ODBC Driver 17 for SQL Server",
)

DATABASE_POSTGRES = DatabaseConfig(
    host=os.environ.get("DATABASE_POSTGRES_HOST", ""),
    port=os.environ.get("DATABASE_POSTGRES_PORT", "5432"),
    user=os.environ.get("DATABASE_POSTGRES_USER", ""),
    password=os.environ.get("DATABASE_POSTGRES_PASSWORD", ""),
    database=os.environ.get("DATABASE_POSTGRES_NAME", ""),
)

# Store in dict for easy routing
databases: dict[str, DatabaseConfig] = {
    "mssql": DATABASE_MSSQL,
    "postgres": DATABASE_POSTGRES,
}

# Use dynamically
db_type = "mssql"  # From app logic
db_config = databases[db_type]
```

### Pattern 3: Extending Schemas for Project-Specific Fields

```python
from app.configs.config_schemas import DatabaseConfig

# Base configuration
db = DatabaseConfig(
    host="localhost",
    port=5432,
    user="admin",
    password="secret",
    database="production",
    # Project-specific fields (allowed via Config.extra = "allow")
    schema="public",
    connection_pool_size=20,
    read_timeout_seconds=60,
)

# Access project fields
print(db.schema)  # "public"
print(db.connection_pool_size)  # 20
print(db.read_timeout_seconds)  # 60
```

### Pattern 4: Creating Project-Specific Schema

```python
# In your project's config_schemas.py (extend the base)
from app.configs.config_schemas import DatabaseConfig

class ProjectDatabaseConfig(DatabaseConfig):
    \"\"\"Project-specific MSSQL configuration with custom fields.\"\"\"

    # Add project-specific fields
    enable_connection_pool: bool = True
    max_pool_size: int = 20
    read_replicas: list[str] = []  # For read-write splitting
    enable_query_cache: bool = False
    cache_ttl_seconds: int = 300

    class Config:
        extra = "allow"  # Still allow dynamic fields

# Use in config.py
DATABASE = ProjectDatabaseConfig(
    host=os.environ.get("DATABASE_HOST", ""),
    port=os.environ.get("DATABASE_PORT", "1433"),
    user=os.environ.get("DATABASE_USER", ""),
    password=os.environ.get("DATABASE_PASSWORD", ""),
    database=os.environ.get("DATABASE_NAME", ""),
    enable_connection_pool=True,
    max_pool_size=int(os.environ.get("DB_POOL_SIZE", "20")),
    read_replicas=os.environ.get("DB_READ_REPLICAS", "").split(","),
)
```

### Pattern 5: Hybrid Approach - Schemas + Plain Variables

```python
from app.configs.config_schemas import AppConfig, LoggingConfig
import os

# Use schemas for validated services
LOGGING = LoggingConfig(
    level=os.environ.get("LOG_LEVEL", "INFO").upper(),
    format=os.environ.get("LOG_FORMAT", "json"),
    dir=os.environ.get("LOG_DIR", "./logs"),
    file_prefix=os.environ.get("LOG_FILE_PREFIX", "app"),
)

APP = AppConfig(
    debug=os.environ.get("DEBUG", "false").lower() == "true",
    environment=os.environ.get("APP_ENV", "production"),
    timezone=os.environ.get("TIMEZONE", "UTC"),
)

# Keep project-specific variables as plain types
ENABLE_CACHE = os.environ.get("ENABLE_CACHE", "true").lower() == "true"
CACHE_TTL_HOURS = int(os.environ.get("CACHE_TTL", "24"))
BATCH_SIZE = int(os.environ.get("BATCH_SIZE", "1000"))

# Use together in your code
if APP.is_development():
    logger.setLevel(LOGGING.level)  # Use schema

if ENABLE_CACHE:  # Use plain variable
    cache.set_ttl(CACHE_TTL_HOURS)
```

## Usage in Application Code

### Reading Configuration

```python
# Import what you need
from app.configs.config import (
    DEBUG,
    DATABASE,
    LOGGING,
    APP,
    ENABLE_TASK_OUTPUT_CACHE,
    TASK_OUTPUT_CACHE_HOURS,
)

# Use schemas for validated data
if DATABASE.is_configured():
    logger.info("Connecting to {} database at {}:{}",
                DATABASE.driver or "default",
                DATABASE.host,
                DATABASE.port)

# Use validation methods
if LOGGING.validate_format():
    console_output = "json" if LOGGING.format == "json" else "text"
    logger.info("Console logging format: {}", console_output)

# Mix with plain variables
if ENABLE_TASK_OUTPUT_CACHE:
    cache.set_ttl_hours(TASK_OUTPUT_CACHE_HOURS)
```

### Conditional Configuration

```python
from app.configs.config import APP, DATABASE, LOGGING

# Development-specific setup
if APP.is_development():
    LOGGING.level = "DEBUG"
    DATABASE.pool_size = 2  # Fewer connections in dev
    enable_hot_reload = True
else:  # Production
    DATABASE.pool_size = 20
    DATABASE.max_overflow = 50
    enable_metrics = True

# Environment-specific behavior
if APP.environment == "staging":
    use_mock_services = True
elif APP.environment == "production":
    enable_alerts = True
```

## .env Example

```bash
# DEBUG AND TIME
DEBUG=false
DATETIME_NOW=
APP_ENV=production
APP_NAME=MyDataApp
APP_VERSION=1.0.0

# LOGGING
LOG_LEVEL=INFO
LOG_FORMAT=json
LOG_DIR=./logs
LOG_FILE_PREFIX=myapp
LOG_RETENTION_DAYS=30
MAX_LOG_FILES=50

# DATABASE
DATABASE_HOST=db.example.com
DATABASE_PORT=1433
DATABASE_USER=sa
DATABASE_PASSWORD=SecurePassword123
DATABASE_NAME=production
DATABASE_DRIVER=ODBC Driver 17 for SQL Server

# PROJECT-SPECIFIC
ENABLE_TASK_OUTPUT_CACHE=true
TASK_OUTPUT_CACHE_HOURS=24
BATCH_SIZE=5000
```

## Migration from Plain Variables

### Before (Only Plain Variables)

```python
DATABASE_HOST = os.environ.get("DATABASE_HOST", "")
DATABASE_PORT = os.environ.get("DATABASE_PORT", "")
DATABASE_USER = os.environ.get("DATABASE_USER", "")
DATABASE_PASSWORD = os.environ.get("DATABASE_PASSWORD", "")
DATABASE_NAME = os.environ.get("DATABASE_NAME", "")

# Validation scattered in code
if not DATABASE_HOST:
    raise ValueError("DATABASE_HOST not configured")
```

### After (With Pydantic Schema)

```python
from app.configs.config_schemas import DatabaseConfig

DATABASE = DatabaseConfig(
    host=os.environ.get("DATABASE_HOST", ""),
    port=os.environ.get("DATABASE_PORT", ""),
    user=os.environ.get("DATABASE_USER", ""),
    password=os.environ.get("DATABASE_PASSWORD", ""),
    database=os.environ.get("DATABASE_NAME", ""),
)

# Validation in one place
if not DATABASE.is_configured():
    raise ValueError("Database not properly configured")
```

## Benefits

1. **Type Safety**: IDE autocomplete, static type checking
2. **Validation**: Pydantic handles type coercion and validation
3. **Documentation**: Schema docstrings describe all fields
4. **Extensibility**: Config.extra = "allow" for project fields
5. **Reusability**: Copy schemas to other projects
6. **Maintainability**: Less scattered validation logic
7. **Consistency**: All projects use same schema structure

## Testing Configuration

```python
def test_database_configuration():
    \"\"\"Test database configuration is valid.\"\"\"
    from app.configs.config import DATABASE

    assert DATABASE.is_configured(), "Database must be configured"
    assert DATABASE.host, "Database host required"
    assert DATABASE.port, "Database port required"

def test_logging_configuration():
    \"\"\"Test logging configuration.\"\"\"
    from app.configs.config import LOGGING

    assert LOGGING.validate_level(), "Invalid logging level"
    assert LOGGING.validate_format(), "Invalid logging format"
    assert LOGGING.dir, "Log directory must be set"
```

## Troubleshooting

**Q: How do I add a new field to a schema?**
A: Use Config.extra = "allow" (already enabled) to pass it dynamically, or create a project-specific schema inheriting from the base.

**Q: Can I validate configuration at startup?**
A: Yes, call is_configured() or validate_*() methods:

```python
if not DATABASE.is_configured():
    raise RuntimeError("Database not configured, cannot start app")
```

**Q: How do I handle multiple environments?**
A: Use AppConfig's is_development(), is_production() methods or check APP.environment directly.

**Q: Should I remove plain variables?**
A: Keep them for project-specific settings. Use Pydantic only for validated service configs.
"""
