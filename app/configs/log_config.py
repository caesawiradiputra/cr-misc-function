"""Unified logging pipeline bridging loguru with stdlib logging.

Provides colorized or JSON console output, structured file logging with rotation/retention,
and automatic interception of third-party library logs through the standard library logging bridge.

Uses LoggingConfig schema from app.configs.config_schemas for validated configuration.

Console Output Format:
    - LOG_FORMAT='json': JSON format for log aggregation systems (Grafana, ELK)
    - LOG_FORMAT='text' (default): Loguru colorized text format with:
        Timestamp (green) | Level (color-coded) | Logger:Function:Line (cyan) | Message

File Output Format (always colorized loguru markup, skipped if CREATE_FILE_LOGS=false):
    <green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | <level>{level: <8}</level> |
    <cyan>{name}:{function}:{line}</cyan> | <level>{message}</level>

Configuration:
    - CREATE_FILE_LOGS: Set to False to skip file creation (console-only logging).
      Useful for containerized/ephemeral environments. Default: True

Usage:
    # Main script (initialize once)
    from app.configs.log_config import init_logging, logger
    init_logging("my_script")
    logger.info("App started")

    # Any module (import, use immediately)
    from app.configs.log_config import logger
    logger.debug("Doing work...")

    # Debug logging with {} placeholders
    user_id = 42
    status = "active"
    logger.debug("Processing user={}, status={}", user_id, status)

    # With context manager (automatic lifecycle management)
    from app.configs.log_config import ScriptLogContext
    with ScriptLogContext("data_import"):
        logger.info("Importing...")
        logger.debug("Processing id={}, count={}", 123, 456)

    # With decorator (for functions)
    from app.configs.log_config import with_logging
    @with_logging("cleanup_job")
    def cleanup():
        logger.info("Cleaning...")
        logger.debug("Removed items={}", 10)

    # Console-only logging (no file creation)
    # In config.py:
    #   LOGGING_CONFIG = LoggingConfig(..., create_file_logs=False)
    # or via environment:
    #   CREATE_FILE_LOGS=false python my_script.py
"""
import json
import logging
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, TypedDict

from loguru import logger

# Import LoggingConfig schema and DEBUG flag
try:
    from app.configs.config import DEBUG, LOGGING_CONFIG
except ImportError:
    # Fallback for standalone use: create a minimal LoggingConfig
    from app.configs.config_schemas import LoggingConfig
    LOGGING_CONFIG = LoggingConfig(
        level=os.environ.get("LOG_LEVEL", "INFO").upper(),
        format=os.environ.get("LOG_FORMAT", "json").lower(),
        dir=os.environ.get("LOG_DIR", "./logs"),
        file_prefix=os.environ.get("LOG_FILE_PREFIX", "app"),
        retention_days=int(os.environ.get("LOG_RETENTION_DAYS", "7")),
        max_files=int(os.environ.get("MAX_LOG_FILES", "50")),
        create_file_logs=os.environ.get("CREATE_FILE_LOGS", "true").lower() == "true",
    )
    DEBUG = os.environ.get("DEBUG", "false").lower() == "true"


def _format_location(name: str | None, function: str | None, line: int | None, width: int = 60) -> str:
    """Format logger location (name:function:line) with smart truncation and padding.

    Combines the three components into a single fixed-width field:
    - If shorter than width: right-padded with spaces
    - If longer than width: left-truncated with '..' prefix

    Args:
        name: Logger module name (or None)
        function: Function name (or None)
        line: Line number (or None)
        width: Maximum width (default 60)

    Returns:
        Formatted location string, right-padded or left-truncated to width
    """
    # Handle None values with sensible defaults
    name = name or "unknown"
    function = function or "?"
    line = line or 0

    location = f"{name}:{function}:{line}"

    if len(location) <= width:
        return location.ljust(width)  # Right-pad with spaces
    else:
        # Left-truncate with '..' prefix
        truncated = location[-(width - 2):]  # Keep width-2 chars from right
        return f"..{truncated}"


def _location_filter(record: dict) -> bool:  # type: ignore[misc]
    """Filter to add formatted location to record extras for use in format string.

    This filter calculates the smart-truncated location (name:function:line) and
    adds it to record["extra"] so it can be referenced in the format string as
    {extra[location]}.

    Args:
        record: Loguru record dict

    Returns:
        True to allow the log record to pass through
    """
    record["extra"]["location"] = _format_location(
        record["name"], record["function"], record["line"], width=60
    )
    return True


class LogFileEntry(TypedDict):
    """Type definition for log file metadata."""
    path: str
    name: str
    mtime: float
    size: int
    age_days: int


# Ensure log directory exists
Path(LOGGING_CONFIG.dir).mkdir(parents=True, exist_ok=True)

# Log formats (both use loguru color markup)
CONSOLE_FORMAT = (
    "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
    "<level>{level: <8}</level> | "
    "<cyan>{extra[location]}</cyan> | "
    "<level>{message}</level>"
)

FILE_FORMAT = (
    "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
    "<level>{level: <8}</level> | "
    "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
    "<level>{message}</level>"
)


class InterceptHandler(logging.Handler):
    """Intercept standard logging and redirect to loguru for unified pipeline.

    This bridges the standard library logging (used by many third-party packages)
    into the loguru pipeline, ensuring all logs use the same handlers and format.
    """

    def emit(self, record: logging.LogRecord) -> None:
        """Emit a log record to loguru."""
        try:
            logger.opt(depth=6, exception=record.exc_info).log(
                record.levelname, record.getMessage()
            )
        except Exception:
            self.handleError(record)


def _setup_std_logging_bridge(level: str = "INFO") -> None:
    """Route all standard library logging through loguru.

    This ensures that logs from third-party libraries (requests, sqlalchemy, etc.)
    are captured and formatted through the same loguru pipeline. The log level
    matches the application's configured logging level.

    Args:
        level: Logging level for stdlib bridge (default: "INFO"). Should match
            the application's LOGGING.level to respect user configuration.
    """
    logging.root.handlers = [InterceptHandler()]
    logging.root.setLevel(getattr(logging, level.upper(), logging.INFO))


def _console_json_sink(message: dict) -> None:  # type: ignore[arg-type]
    """Output formatted JSON log record to stdout for structured logging.

    This custom sink transforms loguru message records into minimal JSON output
    suitable for log aggregation systems (Grafana, ELK, etc.). Includes timestamp,
    level, logger name, and any exception information.

    Args:
        message: Loguru message record dict containing 'record' key with full log data.

    Side Effects:
        Writes JSON string + newline to sys.stdout.
        Calls sys.stdout.flush() to prevent buffering in containerized environments.
    """
    record = message.record  # type: ignore[attr-defined]
    log_dict: dict = {
        "timestamp": record["time"].isoformat(),
        "level": record["level"].name,
        "logger": record["name"],
        "function": record["function"],
        "line": record["line"],
        "message": record["message"].strip(),
    }

    # Add extra context if provided
    if record["extra"]:
        log_dict["context"] = record["extra"]

    # Add exception info if present
    if record["exception"]:
        log_dict["exception"] = str(record["exception"])

    # Write JSON to stdout with flush to avoid buffering issues in containers
    sys.stdout.write(json.dumps(log_dict) + "\n")
    sys.stdout.flush()


def _cleanup_old_logs() -> None:
    """Clean up old log files based on retention policy.

    Removes log files older than LOGGING.retention_days and limits total file count to LOGGING.max_files.
    This function is called automatically by init_logging() when cleanup=True.

    Retention Logic (applied in this order):
        1. Delete files older than LOGGING.retention_days
        2. Keep only the most recent LOGGING.max_files (sorted by modification time)

    Returns:
        None. Any errors during cleanup are silently caught to prevent logger initialization from failing.

    Side Effects:
        May delete files from LOGGING.dir that match the pattern "{LOGGING.file_prefix}*.log"
    """
    if not os.path.exists(LOGGING_CONFIG.dir):
        return

    try:
        log_files: list[LogFileEntry] = []
        for file in os.listdir(LOGGING_CONFIG.dir):
            if file.startswith(LOGGING_CONFIG.file_prefix) and file.endswith(".log"):
                filepath = os.path.join(LOGGING_CONFIG.dir, file)
                mtime = os.path.getmtime(filepath)
                file_size = os.path.getsize(filepath)
                age_days = (datetime.now() - datetime.fromtimestamp(mtime)).days
                log_files.append({
                    "path": filepath,
                    "name": file,
                    "mtime": mtime,
                    "size": file_size,
                    "age_days": age_days,
                })

        # Sort by modification time (newest first)
        log_files.sort(key=lambda x: x["mtime"], reverse=True)

        deleted_count = 0

        # Remove old files by age
        cutoff_time = (datetime.now() - timedelta(days=LOGGING_CONFIG.retention_days)).timestamp()
        for log_file in log_files:
            if log_file["mtime"] < cutoff_time:
                try:
                    os.remove(log_file["path"])
                    deleted_count += 1
                except Exception:
                    pass

        # Remove excess files by count
        remaining_files = [f for f in log_files if os.path.exists(f["path"])]
        if len(remaining_files) > LOGGING_CONFIG.max_files:
            for log_file in remaining_files[LOGGING_CONFIG.max_files:]:
                try:
                    os.remove(log_file["path"])
                    deleted_count += 1
                except Exception:
                    pass
    except Exception:
        pass



def init_logging(script_name: str = "app", cleanup: bool = True) -> None:
    """Initialize logging for your application.

    Call this ONCE at the start of your main script (if __name__ == "__main__").
    After initialization, all modules can simply import and use the logger.

    Sets up:
        - Console sink with JSON formatting (Grafana-compatible) or standard text format
          depending on LOGGING.format config ('json' or 'text')
        - File sink with detailed diagnostics and rotation/retention
        - Standard library logging bridge (captures third-party library logs)
        - Correlation IDs bound to all log records (script_name, execution_id)

    Args:
        script_name: Name of the script (used in log filenames and correlation IDs).
            Default: "app"
        cleanup: Whether to cleanup old logs on init. When set to False, old logs
            are preserved. Default: True

    Raises:
        None. If configuration fails to load, the function returns early without error.

    Example:
        # In your main script
        if __name__ == "__main__":
            from app.configs.log_config import init_logging, logger

            init_logging("my_script")
            logger.info("Application started")

        # In any module (no re-initialization needed)
        from app.configs.log_config import logger

        def some_function():
            logger.info("Doing work...")
    """
    logger.debug("init_logging called with script_name={}, cleanup={}", script_name, cleanup)

    # Override log level to DEBUG if DEBUG flag is True
    log_level = "DEBUG" if DEBUG else LOGGING_CONFIG.level

    # Clean up old logs if requested
    if cleanup:
        _cleanup_old_logs()

    # Remove default handler to avoid duplicates
    logger.remove()

    # Setup standard logging bridge first (captures third-party library logs)
    _setup_std_logging_bridge(level=log_level)

    # Add console handler based on LOGGING.format preference
    if LOGGING_CONFIG.format == "json":
        # JSON sink for log aggregation systems (Grafana, ELK)
        logger.add(
            _console_json_sink,  # type: ignore[arg-type]  # Custom JSON sink
            level=log_level,
        )
    else:
        # Text format with smart location truncation
        logger.add(
            sys.stdout,
            level=log_level,
            format=CONSOLE_FORMAT,
            colorize=True,
            filter=_location_filter,  # type: ignore[arg-type]
        )

    # Add file handler (detailed structured text with full diagnostics)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    if LOGGING_CONFIG.create_file_logs:
        log_file = os.path.join(LOGGING_CONFIG.dir, f"{LOGGING_CONFIG.file_prefix}_{script_name}_{timestamp}.log")
        logger.add(
            log_file,
            level=log_level,
            format=FILE_FORMAT,
            rotation="1 day",  # Rotate daily
            retention=f"{LOGGING_CONFIG.retention_days} days",  # Keep for N days
            compression="zip" if LOGGING_CONFIG.enable_compression else None,  # Compress old logs if enabled
            backtrace=True,
            diagnose=LOGGING_CONFIG.diagnose,  # Full diagnostics in file logs
            enqueue=True,  # Thread-safe
        )

    # Bind correlation ID context to every log record
    execution_id = f"{script_name}_{timestamp}"
    logger.configure(extra={"script_name": script_name, "execution_id": execution_id})

    logger.info("Logging initialized - Script: {}, Level: {}", script_name, log_level)


class ScriptLogContext:
    """Context manager for script-scoped logging with automatic init and teardown.

    Initializes logging on entry and flushes/completes the logger on exit.
    Use this when a script needs its own isolated logging lifecycle (especially for
    scheduled jobs, one-off scripts, or isolated processes).

    Attributes:
        script_name: Name used in log filenames and correlation records.
        cleanup: Whether to run log cleanup on entry.

    Args:
        script_name: Descriptive name for the script. Default: "app"
        cleanup: Whether to cleanup old logs on entry. Default: True

    Raises:
        No exceptions are raised; errors during init are caught silently.

    Example:
        with ScriptLogContext("data_import") as log:
            log.info("Starting import...")
            # ... process data ...
            # On exit, all logs are flushed and logger is completed
    """

    def __init__(self, script_name: str = "app", cleanup: bool = True) -> None:
        logger.debug("ScriptLogContext.__init__ called with script_name={}, cleanup={}", script_name, cleanup)
        self.script_name = script_name
        self.cleanup = cleanup

    def __enter__(self) -> Any:
        init_logging(self.script_name, cleanup=self.cleanup)
        logger.info("Script started: {}", self.script_name)
        return logger

    def __exit__(
        self,
        exc_type: type | None,
        exc_val: BaseException | None,
        exc_tb: object | None,
    ) -> None:
        if exc_type:
            logger.exception("Script {} failed", self.script_name)
        else:
            logger.info("Script {} completed successfully", self.script_name)
        logger.complete()


def with_logging(script_name: str | None = None, cleanup: bool = True):
    """Decorator to wrap a function with automatic logging init and teardown.

    Initializes logging before function execution and ensures cleanup
    (complete/flush) after execution, even if the function raises an exception.
    Useful for wrapping entry points, background tasks, or independent functions.

    Args:
        script_name: Name used for logging. If None, defaults to the function name.
            Default: None
        cleanup: Whether to cleanup old logs on init. Default: True

    Returns:
        Decorated function that initializes logging, runs the original function,
        and cleans up logging on exit.

    Example:
        @with_logging("daily_report")
        def run():
            logger.info("Generating report...")
            # ... generate report ...
            # Logging automatically cleaned up on exit
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            name = script_name or func.__name__
            logger.debug("@with_logging decorator executing: name={}, cleanup={}", name, cleanup)
            with ScriptLogContext(script_name=name, cleanup=cleanup):
                return func(*args, **kwargs)
        return wrapper
    return decorator
