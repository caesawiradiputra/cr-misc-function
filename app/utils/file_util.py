"""File utility functions for safe parquet/JSON loading with fallback handling.

Provides robust file I/O operations with built-in fallback strategies and error handling.

Usage:
    from app.utils.file_util import load_parquet_safe, load_json_values

    # Load parquet with automatic fallback from pyarrow to fastparquet
    df = load_parquet_safe("data/file.parquet")

    # Batch load JSON files with graceful error handling
    values = load_json_values([
        "stats/avg_value.json",
        "stats/median_value.json"
    ])

Features:
    - Automatic engine fallback for parquet loading (pyarrow -> fastparquet)
    - Graceful error handling - returns empty results instead of raising exceptions
    - JSON file batch loading with individual error tracking
    - No external dependencies beyond pandas (standard installations)

Template Customization:
    To use in another workspace:
    1. Copy this file to your project's app/utils/ directory
    2. No additional configuration needed
    3. Ensure pandas is installed (typically included in most environments)
"""

import json
from typing import Any

import pandas as pd

# Try to import logger from log_config; use print if not available
try:
    from app.configs.log_config import logger
except ImportError:
    import logging
    logger = logging.getLogger(__name__)


def load_parquet_safe(file_path: str) -> pd.DataFrame:
    """Load a parquet file safely with fallback engine selection.

    Attempts to load parquet files using pyarrow engine first, then falls back
    to fastparquet if the primary engine fails. This provides maximum compatibility
    across different parquet file variations and system configurations.

    Args:
        file_path: Full path to the parquet file to load.

    Returns:
        Loaded pandas DataFrame, or empty DataFrame if loading fails.

    Example:
        >>> df = load_parquet_safe("data/output.parquet")
        >>> print(f"Shape: {df.shape}")
        Shape: (1000, 5)
    """
    try:
        return pd.read_parquet(file_path, engine="pyarrow")  # type: ignore[arg-type]
    except Exception as e:
        logger.debug("pyarrow engine failed for {}, trying fastparquet: {}", file_path, e)
        try:
            return pd.read_parquet(file_path, engine="fastparquet")
        except Exception as e2:
            logger.error("Failed to load {} with both engines: {}", file_path, e2)
            return pd.DataFrame()


def load_json_values(file_paths: list[str]) -> dict[str, Any | None]:
    """Load a numeric value from each JSON file in a list with individual error handling.

    Expects each JSON file to contain a "value" key at the top level.
    Files that cannot be loaded or parsed return None in the result dict.

    Args:
        file_paths: List of file paths to JSON files, each expected to have a "value" key.

    Returns:
        Dictionary mapping each file path to its value (from JSON), or None if file missing/invalid.

    Example:
        >>> values = load_json_values([
        ...     "stats/avg.json",    # Contains {"value": 42.5}
        ...     "stats/median.json",  # Contains {"value": 40.0}
        ...     "missing.json"        # File doesn't exist
        ... ])
        >>> print(values)
        {'stats/avg.json': 42.5, 'stats/median.json': 40.0, 'missing.json': None}
    """
    avg_values: dict[str, Any | None] = {}

    for path in file_paths:
        try:
            with open(path, encoding="utf-8") as f:
                data = json.load(f)
                avg_values[path] = data.get("value")
                logger.debug("Loaded value from {}: {}", path, data.get("value"))
        except FileNotFoundError:
            logger.warning("File not found: {}", path)
            avg_values[path] = None
        except json.JSONDecodeError as e:
            logger.warning("Invalid JSON in {}: {}", path, e)
            avg_values[path] = None
        except Exception as e:
            logger.error("Unexpected error loading {}: {}", path, e)
            avg_values[path] = None

    return avg_values
