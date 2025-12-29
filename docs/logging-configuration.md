# Logging Configuration Guide

## Overview

`app/configs/log_config.py` provides a **simple, plug-and-play logging system** built on [loguru](https://loguru.readthedocs.io/) that supports:

- **Dual output formats**: JSON (console/Grafana) + structured text (file)
- **Automatic cleanup**: Age-based and count-based log file retention
- **Thread-safe operations**: Queue-based logging for concurrent environments
- **Standalone ready**: Works in any Python project with minimal setup
- **Zero magic**: No frame inspection, no implicit initialization—explicit and predictable

---

## Configuration

### Environment Variables

Configuration is loaded from `app/configs/config.py`:

| Variable | Purpose | Default |
| ---------- | --------- | --------- |
| `LOG_LEVEL` | Logging level (DEBUG, INFO, WARNING, ERROR) | `INFO` |
| `LOG_DIR` | Directory for log files | `logs/` |
| `LOG_FILE_PREFIX` | Prefix for log filenames | `app_execution` |
| `LOG_RETENTION_DAYS` | Keep logs for this many days before deletion | `7` |
| `MAX_LOG_FILES` | Maximum number of log files to keep | `50` |
| `DEBUG` | Enable DEBUG level and verbose output | `False` |

#### Log Retention Behavior

The logging system automatically cleans up old log files on initialization:

- **Age-based deletion**: Removes log files older than `LOG_RETENTION_DAYS` (default: 7 days)
- **Count-based deletion**: Keeps maximum `MAX_LOG_FILES` most recent files (default: 50 files)
- **Automatic execution**: Cleanup runs automatically when `init_logging()` is called (can be disabled)
- **Silent operation**: Cleanup failures are caught and ignored to not interrupt application startup

### Setting Environment Variables

#### Via `.env` File

Create a `.env` file in the project root with your custom values:

```env
# Logging Configuration
LOG_LEVEL=DEBUG
LOG_DIR=./logs
LOG_FILE_PREFIX=my_app

# Log Retention (optional, defaults shown)
LOG_RETENTION_DAYS=7
MAX_LOG_FILES=50
```

**Loading mechanism:**

- `app/configs/config.py` loads variables from `.env` using `python-dotenv`
- Environment variables take precedence over `.env` values
- In Kubernetes/Docker, set environment variables via ConfigMap or Secrets

#### Via Environment Variables

```bash
# Unix/Linux/Mac
export LOG_LEVEL=DEBUG
export LOG_RETENTION_DAYS=14
export MAX_LOG_FILES=100

# Windows PowerShell
$env:LOG_LEVEL="DEBUG"
$env:LOG_RETENTION_DAYS="14"
$env:MAX_LOG_FILES="100"
```

#### Via Docker

```dockerfile
FROM python:3.11
ENV LOG_LEVEL=INFO
ENV LOG_DIR=/app/logs
ENV LOG_RETENTION_DAYS=7
ENV MAX_LOG_FILES=50
```

#### Typical Configuration Scenarios

**Development (verbose, keep more logs):**

```env
LOG_LEVEL=DEBUG
LOG_RETENTION_DAYS=30
MAX_LOG_FILES=100
```

**Production (minimal logs, aggressive cleanup):**

```env
LOG_LEVEL=INFO
LOG_RETENTION_DAYS=3
MAX_LOG_FILES=25
```

**Testing (no file logs, memory only):**

```env
LOG_LEVEL=DEBUG
LOG_DIR=/tmp/test_logs
LOG_RETENTION_DAYS=0
```

---

## Quick Start

### One-Time Setup (Main Script)

```python
# main.py or any entry point script
if __name__ == "__main__":
    from app.configs.log_config import init_logging, logger
    
    init_logging("my_app")  # Call this ONCE at startup
    logger.info("Application started")
    # ... rest of your application
```

### Use in Any Module

After initialization in your main script, import the logger in any other module:

```python
# any_module.py
from app.configs.log_config import logger

def process_data(data):
    logger.info(f"Processing {len(data)} items")
    # ... your code
    logger.error("Something went wrong", exc_info=True)
```

---

## Core Function

### `init_logging(script_name: str = "app", cleanup: bool = True) -> None`

Initialize logging for your application. **Call this exactly once** at the start of your main script.

**Parameters:**

- `script_name` (str): Name of your script—used in log filenames. Default: `"app"`
- `cleanup` (bool): Whether to delete old log files on startup. Default: `True`

**What it does:**

1. Loads configuration from `app/configs/config.py` (or environment variables if standalone)
2. Cleans up old log files (if `cleanup=True`)
3. Removes any default loguru handlers
4. Adds console handler with custom minimal JSON sink (no sensitive paths)
5. Adds file handler with structured text format, full diagnostics, and backtrace
6. Enables thread-safe queue-based logging via `enqueue=True`

**Returns:** None (logger is ready to use globally)

**Key Features:**

- **Minimal console output**: Custom JSON sink outputs only essential fields (timestamp, level, logger, function, line, message)
- **No sensitive data in console**: File paths and system info excluded from JSON output
- **Full diagnostics in files**: File logs include complete backtraces and diagnostic information
- **Context support**: Use `logger.bind()` to add context fields that appear in JSON console output

**Example:**

```python
from app.configs.log_config import init_logging, logger

if __name__ == "__main__":
    # Initialize once at the start
    init_logging("batch_processor")
    
    try:
        logger.info("Processing started")
        # ... do work ...
        logger.info("Processing completed successfully")
    except Exception as e:
        logger.error(f"Processing failed: {e}", exc_info=True)
        raise
```

---

## Usage Patterns

### Pattern 1: Standard Script (Recommended)

```python
# main.py
from app.configs.log_config import init_logging, logger

def main():
    logger.info("Main function running")
    result = process_data()
    logger.info(f"Result: {result}")
    return result

if __name__ == "__main__":
    init_logging("main")
    main()
```

### Pattern 2: Module with Logging

```python
# data_processor.py
from app.configs.log_config import logger

class DataProcessor:
    def process(self, data):
        logger.info(f"Processing {len(data)} records")
        try:
            result = self._internal_process(data)
            logger.info(f"Successfully processed {len(result)} records")
            return result
        except Exception as e:
            logger.error(f"Processing failed: {e}", exc_info=True)
            raise
    
    def _internal_process(self, data):
        logger.debug(f"Internal processing of {type(data)}")
        # ... implementation
```

### Pattern 3: Disable Cleanup

```python
# If you want to keep more logs and disable automatic cleanup
if __name__ == "__main__":
    init_logging("my_app", cleanup=False)
    logger.info("Started without cleanup")
```

### Pattern 4: Adding Context to Logs

```python
# Add context fields that appear in all subsequent logs
from app.configs.log_config import logger

# Bind context (appears in JSON console output under "context")
logger_with_context = logger.bind(user_id=123, request_id="abc-123")
logger_with_context.info("User action")
# JSON: {"timestamp": "...", "level": "INFO", ..., "message": "User action", "context": {"user_id": 123, "request_id": "abc-123"}}

# Or use temporary context
with logger.contextualize(transaction_id="tx-456"):
    logger.info("Transaction started")
    # Context only applies within this block
```

---

## Log Output Formats

### File Format (Structured Text)

```text
2025-12-26 14:30:45.123 | INFO     | module:function:42 | Processing started
2025-12-26 14:30:45.456 | INFO     | module:function:50 | Processing completed
2025-12-26 14:30:45.789 | ERROR    | module:function:55 | Processing failed: Timeout
```

**Format breakdown:**

- `YYYY-MM-DD HH:mm:ss.SSS` - ISO timestamp with milliseconds
- `LEVEL` - Log level (INFO, DEBUG, ERROR, WARNING)
- `module:function:line` - File/module, function name, line number
- `message` - Your log message

#### Console Format (Minimal JSON for Grafana)

```json
{"timestamp": "2025-12-29T14:30:45.123456+08:00", "level": "INFO", "logger": "module", "function": "process", "line": 42, "message": "Processing started"}
```

With optional context:

```json
{"timestamp": "2025-12-29T14:30:45.456789+08:00", "level": "ERROR", "logger": "module", "function": "process", "line": 55, "message": "Processing failed", "exception": "Timeout", "context": {"user_id": 123}}
```

**Why minimal JSON on console?**

- Clean, parseable output for Grafana dashboards
- No sensitive file paths or system information
- Includes only essential fields: timestamp, level, logger, function, line, message
- Optional fields added only when present: exception, context (from `logger.bind()`)
- Thread-safe and efficient for high-throughput applications

---

## Plug-and-Play Usage

### For Existing Projects

To add this logging to an existing project:

1. **Copy `log_config.py`** to your project's config directory
2. **Add to your main script:**

   ```python
   from app.configs.log_config import init_logging, logger
   
   if __name__ == "__main__":
       init_logging("my_app")
       logger.info("Starting...")
   ```

3. **In any module, import and use:**

   ```python
   from app.configs.log_config import logger
   logger.info("Doing work...")
   ```

### For Standalone Projects (No `app.configs.config`)

If you're using this in a project without `app.configs.config`, it automatically falls back to environment variables:

```bash
export LOG_LEVEL=DEBUG
export LOG_DIR=./logs
export LOG_FILE_PREFIX=myapp
export LOG_RETENTION_DAYS=7
export MAX_LOG_FILES=50

python my_script.py
```

The logger will work without any config file—just environment variables!

---

## Troubleshooting

### No logs appearing in console

**Check:** Is `init_logging()` called before using the logger?

```python
from app.configs.log_config import init_logging, logger

# WRONG - logger used before init
logger.info("This won't appear")

# RIGHT - init first, then use
init_logging("my_app")
logger.info("This will appear")
```

### Can't find log files

**Check:** The `LOG_DIR` directory and permissions

```python
from app.configs.config import LOG_DIR
print(f"Logs are in: {LOG_DIR}")
```

Or set it explicitly:

```bash
export LOG_DIR=/path/to/logs
```

### Logs not showing in Grafana

**Check:** JSON format is enabled on console (default behavior). Verify your log aggregation tool is parsing JSON from stdout.

Example log line format:

```json
{"timestamp": "2025-12-29T14:30:45.123456+08:00", "level": "INFO", "logger": "module", "function": "process", "line": 42, "message": "Processing started"}
```

The custom JSON sink outputs minimal, clean JSON suitable for log aggregation and dashboards.

### Disk space growing too fast

**Check:** `LOG_RETENTION_DAYS` and `MAX_LOG_FILES` settings. Adjust to be more aggressive:

```bash
export LOG_RETENTION_DAYS=3    # Keep 3 days instead of 7
export MAX_LOG_FILES=25         # Keep 25 files instead of 50
```

Or disable cleanup (not recommended):

```python
init_logging("my_app", cleanup=False)
```

---

## Best Practices

### ✅ DO

- Call `init_logging()` **exactly once** in your main script
- Import logger in all your modules: `from app.configs.log_config import logger`
- Use appropriate log levels: `logger.debug()`, `logger.info()`, `logger.error()`
- Include context in error logs: `logger.error(f"Failed to process {item_id}", exc_info=True)`
- Let cleanup run automatically (it won't interfere with your application)

### ❌ DON'T

- Call `init_logging()` multiple times in the same application
- Try to reinitialize or modify the logger in imported modules
- Ignore exceptions in production (always log them)
- Leave `cleanup=False` in production (will fill up disk)
- Hardcode log levels (use environment variables instead)

---

## Quick Reference

**Main entry point (main.py):**

```python
from app.configs.log_config import init_logging, logger

if __name__ == "__main__":
    init_logging("my_script")
    logger.info("Starting...")
```

**Any module:**

```python
from app.configs.log_config import logger

logger.info("Message")
logger.error("Error", exc_info=True)
```

**Environment variables:**

```bash
LOG_LEVEL=DEBUG              # DEBUG, INFO, WARNING, ERROR
LOG_DIR=./logs               # Where to store log files
LOG_FILE_PREFIX=myapp        # Prefix for log filenames
LOG_RETENTION_DAYS=7         # Delete logs older than 7 days
MAX_LOG_FILES=50             # Keep maximum 50 log files
```

---

---

## Advanced Features

### Custom JSON Console Output

The logging system uses a custom JSON sink (`_console_json_sink`) for console output that:

- Outputs minimal JSON with only essential fields
- Excludes sensitive file paths and system information
- Automatically includes exception details when present
- Supports context fields via `logger.bind()` or `logger.contextualize()`

This provides clean, secure JSON suitable for log aggregation tools like Grafana Loki while keeping file logs detailed with full diagnostics.

### Thread-Safe Logging

File logging uses `enqueue=True` to ensure thread-safe operations in concurrent environments. This is essential for:

- FastAPI/async applications
- Multi-threaded data processing
- Background task workers
- Parallel batch jobs

No additional configuration needed—it's enabled by default.

---

**Last updated:** December 29, 2025
