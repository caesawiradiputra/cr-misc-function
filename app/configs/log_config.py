import json
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path

from loguru import logger

# Lazy imports to avoid circular dependencies
_config_loaded = False
_log_dir = None
_log_file_prefix = None
_log_level = None
_log_retention_days = None
_max_log_files = None


def _load_config():
    """Load configuration once."""
    global _config_loaded, _log_dir, _log_file_prefix, _log_level, _log_retention_days, _max_log_files
    
    if _config_loaded:
        return
    
    try:
        from app.configs.config import (
            LOG_DIR,
            LOG_FILE_PREFIX,
            LOG_LEVEL,
            LOG_RETENTION_DAYS,
            MAX_LOG_FILES,
        )
        _log_dir = LOG_DIR
        _log_file_prefix = LOG_FILE_PREFIX
        _log_level = LOG_LEVEL
        _log_retention_days = LOG_RETENTION_DAYS
        _max_log_files = MAX_LOG_FILES
    except ImportError:
        # Fallback for standalone use (plug-and-play)
        _log_dir = os.environ.get("LOG_DIR", "./logs")
        _log_file_prefix = os.environ.get("LOG_FILE_PREFIX", "app")
        _log_level = os.environ.get("LOG_LEVEL", "INFO").upper()
        _log_retention_days = int(os.environ.get("LOG_RETENTION_DAYS", "7"))
        _max_log_files = int(os.environ.get("MAX_LOG_FILES", "50"))
    
    _config_loaded = True


# Ensure log directory exists
Path(os.environ.get("LOG_DIR", "./logs")).mkdir(parents=True, exist_ok=True)

# Log formats
FILE_FORMAT = (
    "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
    "<level>{level: <8}</level> | "
    "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
    "<level>{message}</level>"
)

CONSOLE_FORMAT = "{message}"  # JSON for Grafana dashboard views


def _console_json_sink(message):
    """
    Custom sink for console output with minimal JSON formatting.
    
    Receives the complete message object and outputs clean, minimal JSON
    without sensitive information (file paths).
    """
    record = message.record
    log_dict = {
        "timestamp": record["time"].isoformat(),
        "level": record["level"].name,
        "logger": record["name"],
        "function": record["function"],
        "line": record["line"],
        "message": record["message"].strip(),
    }
    
    # * Add extra context if provided
    if record["extra"]:
        log_dict["context"] = record["extra"]
    
    # Add exception info if present
    if record["exception"]:
        log_dict["exception"] = str(record["exception"])
    
    # Write JSON to stdout
    sys.stdout.write(json.dumps(log_dict) + "\n")


def _cleanup_old_logs():
    """Clean up old log files based on retention settings."""
    _load_config()
    
    if not os.path.exists(_log_dir):
        return
    
    try:
        log_files = []
        for file in os.listdir(_log_dir):
            if file.startswith(_log_file_prefix) and file.endswith(".log"):
                filepath = os.path.join(_log_dir, file)
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
        cutoff_time = (datetime.now() - timedelta(days=_log_retention_days)).timestamp()
        for log_file in log_files:
            if log_file["mtime"] < cutoff_time:
                try:
                    os.remove(log_file["path"])
                    deleted_count += 1
                except Exception:
                    pass
        
        # Remove excess files by count
        remaining_files = [f for f in log_files if os.path.exists(f["path"])]
        if len(remaining_files) > _max_log_files:
            for log_file in remaining_files[_max_log_files:]:
                try:
                    os.remove(log_file["path"])
                    deleted_count += 1
                except Exception:
                    pass
    except Exception:
        pass



def init_logging(script_name: str = "app", cleanup: bool = True) -> None:
    """
    Initialize logging for your application.
    
    Call this ONCE at the start of your main script (if __name__ == "__main__").
    After initialization, all modules can simply import and use the logger.
    
    Args:
        script_name (str): Name of the script (used in log filenames). Default: "app"
        cleanup (bool): Whether to cleanup old logs on init. Default: True
    
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
    _load_config()
    
    # Clean up old logs if requested
    if cleanup:
        _cleanup_old_logs()
    
    # Remove default handler to avoid duplicates
    logger.remove()
    
    # Add console handler with custom JSON sink (minimal output)
    logger.add(
        _console_json_sink,  # Custom sink instead of stdout
        level=_log_level,
    )
    
    # Add file handler (detailed structured text with full diagnostics)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = os.path.join(_log_dir, f"{_log_file_prefix}_{script_name}_{timestamp}.log")
    logger.add(
        log_file,
        level=_log_level,
        format=FILE_FORMAT,
        backtrace=True,
        diagnose=True,  # Full diagnostics in file logs
        enqueue=True,  # Thread-safe
    )
    
    logger.info(f"Logging initialized - Script: {script_name}, Level: {_log_level}")
