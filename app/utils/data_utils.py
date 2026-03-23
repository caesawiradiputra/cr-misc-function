"""Data format I/O and conversion utilities for repositories.

Provides unified interface for importing/exporting DataFrames across multiple
file formats (CSV, Parquet, JSON) with automatic dtype handling and file validation.

Conversion layer enables seamless transformations between formats:
  CSV ↔ Parquet ↔ JSON

All conversions go through pandas DataFrame as intermediate representation.

Example:
    >>> from app.utils.data_utils import export_to_csv, convert_csv_to_parquet
    >>> df = pd.read_sql("SELECT * FROM orders", connection)
    >>> export_to_csv(df, "orders.csv")
    >>> convert_csv_to_parquet("orders.csv", "orders.parquet")
"""

import json
import logging
from pathlib import Path
from typing import Any, Literal

import pandas as pd

logger = logging.getLogger(__name__)


# ============================================================================
# CSV Operations
# ============================================================================


def export_to_csv(
    df: pd.DataFrame,
    file_path: str,
    overwrite: bool = False,
    include_index: bool = False,
    encoding: str = "utf-8",
) -> bool:
    """Export DataFrame to CSV file.

    Args:
        df: DataFrame to export.
        file_path: Output CSV file path.
        overwrite: If False, raises FileExistsError if file exists.
        include_index: Include DataFrame index in output.
        encoding: Character encoding (default: utf-8).

    Returns:
        True if successful.

    Raises:
        FileExistsError: If file exists and overwrite=False.
        ValueError: If DataFrame is empty.
        PermissionError: If cannot write to destination.

    Example:
        >>> df = pd.DataFrame({"id": [1, 2], "name": ["A", "B"]})
        >>> export_to_csv(df, "data.csv", overwrite=True)
        True
        >>> logger.info("Exported 2 rows to data.csv (156 B)")
    """
    if df.empty:
        raise ValueError("Cannot export empty DataFrame")

    path = Path(file_path)

    # Check if file exists and overwrite not allowed
    if path.exists() and not overwrite:
        raise FileExistsError(f"File already exists: {file_path}")

    # Create parent directories
    path.parent.mkdir(parents=True, exist_ok=True)

    try:
        df.to_csv(
            path,
            index=include_index,
            encoding=encoding,
        )
        file_size = path.stat().st_size
        logger.info(
            f"Exported {len(df)} rows to {file_path} ({file_size} B)",
        )
        return True
    except PermissionError as e:
        logger.error(f"Permission denied writing to {file_path}: {e}")
        raise
    except Exception as e:
        logger.error(f"Failed to export CSV {file_path}: {e}", exc_info=True)
        raise


def import_from_csv(
    file_path: str,
    columns: list[str] | None = None,
    encoding: str = "utf-8",
    dtype: dict[Any, Any] | None = None,
) -> pd.DataFrame:
    """Import DataFrame from CSV file.

    Args:
        file_path: Input CSV file path.
        columns: Specific columns to load (subset). If None, loads all.
        encoding: Character encoding (default: utf-8).
        dtype: Column type mapping (e.g., {"id": "int64", "amount": "float64"}).

    Returns:
        Imported DataFrame with types applied.

    Raises:
        FileNotFoundError: If file does not exist.
        ValueError: If file is empty or not valid CSV.
        UnicodeDecodeError: If encoding mismatch.

    Example:
        >>> df = import_from_csv(
        ...     "data.csv",
        ...     columns=["id", "name"],
        ...     dtype={"id": "int64"}
        ... )
        >>> logger.info("Imported 2,345 rows with 2 columns")
    """
    path = Path(file_path)

    # Validate file exists
    if not path.exists():
        raise FileNotFoundError(f"CSV file not found: {file_path}")

    if not path.is_file():
        raise ValueError(f"Path is not a file: {file_path}")

    if path.stat().st_size == 0:
        raise ValueError(f"CSV file is empty: {file_path}")

    try:
        df = pd.read_csv(
            path,
            encoding=encoding,
            usecols=columns,
            dtype=dtype,
        )
        logger.info(
            f"Imported {len(df)} rows with {len(df.columns)} columns from {file_path}",
        )
        return df
    except UnicodeDecodeError as e:
        logger.error(f"Encoding error reading CSV {file_path}: {e}")
        raise
    except Exception as e:
        logger.error(f"Failed to import CSV {file_path}: {e}", exc_info=True)
        raise


# ============================================================================
# Parquet Operations
# ============================================================================


def export_to_parquet(
    df: pd.DataFrame,
    file_path: str,
    overwrite: bool = False,
    compression: Literal["snappy", "gzip", "brotli", "lz4", "zstd"] = "snappy",
    include_index: bool = False,
) -> bool:
    """Export DataFrame to Parquet file with compression.

    Parquet advantages over CSV:
      - 50-70% smaller (columnar compression)
      - 2-5x faster read/write
      - Type preservation (no inference on read)
      - Columnar format (efficient for analytics)
      - Binary safe (no escaping needed)

    Args:
        df: DataFrame to export.
        file_path: Output Parquet file path.
        overwrite: If False, raises FileExistsError if file exists.
        compression: Compression codec (snappy/gzip/brotli/lz4/zstd).
        include_index: Include DataFrame index in output.

    Returns:
        True if successful.

    Raises:
        FileExistsError: If file exists and overwrite=False.
        ValueError: If DataFrame is empty.
        PermissionError: If cannot write to destination.

    Example:
        >>> df = pd.DataFrame({"id": [1, 2], "amount": [99.9, 199.9]})
        >>> export_to_parquet(df, "data.parquet", compression="snappy")
        True
        >>> logger.info("Exported 2 rows to data.parquet (89.2 KB, snappy)")
    """
    if df.empty:
        raise ValueError("Cannot export empty DataFrame")

    path = Path(file_path)

    # Check if file exists and overwrite not allowed
    if path.exists() and not overwrite:
        raise FileExistsError(f"File already exists: {file_path}")

    # Create parent directories
    path.parent.mkdir(parents=True, exist_ok=True)

    try:
        df.to_parquet(
            path,
            index=include_index,
            compression=compression,
        )
        file_size = path.stat().st_size
        logger.info(
            f"Exported {len(df)} rows to {file_path} ({file_size / 1024:.1f} KB, {compression})",
        )
        return True
    except PermissionError as e:
        logger.error(f"Permission denied writing to {file_path}: {e}")
        raise
    except Exception as e:
        logger.error(f"Failed to export Parquet {file_path}: {e}", exc_info=True)
        raise


def import_from_parquet(
    file_path: str,
    columns: list[str] | None = None,
) -> pd.DataFrame:
    """Import DataFrame from Parquet file.

    Parquet preserves all type information during export/import,
    eliminating need for dtype casting on read.

    Args:
        file_path: Input Parquet file path.
        columns: Specific columns to load (subset). If None, loads all.

    Returns:
        Imported DataFrame with types preserved exactly as stored.

    Raises:
        FileNotFoundError: If file does not exist.
        ValueError: If file is empty or not valid Parquet.

    Example:
        >>> df = import_from_parquet(
        ...     "data.parquet",
        ...     columns=["order_id", "status"]
        ... )
        >>> logger.info("Imported 5,678 rows with 2 columns (256 KB)")
    """
    path = Path(file_path)

    # Validate file exists
    if not path.exists():
        raise FileNotFoundError(f"Parquet file not found: {file_path}")

    if not path.is_file():
        raise ValueError(f"Path is not a file: {file_path}")

    if path.stat().st_size == 0:
        raise ValueError(f"Parquet file is empty: {file_path}")

    try:
        df = pd.read_parquet(path, columns=columns)
        file_size = path.stat().st_size
        logger.info(
            f"Imported {len(df)} rows with {len(df.columns)} columns from {file_path} ({file_size / 1024:.1f} KB)",
        )
        return df
    except Exception as e:
        logger.error(f"Failed to import Parquet {file_path}: {e}", exc_info=True)
        raise


# ============================================================================
# JSON Operations
# ============================================================================


def export_to_json(
    df: pd.DataFrame,
    file_path: str,
    orient: Literal["records", "split", "index", "columns", "values"] = "records",
    overwrite: bool = False,
    indent: int = 2,
) -> bool:
    """Export DataFrame to JSON file.

    Orient options:
      - "records": List of {"column": value} dicts (default, human-readable)
      - "split": {columns: [...], index: [...], data: [[...]]}
      - "index": {index: {column: value}}
      - "columns": {column: {index: value}}
      - "values": Nested lists [[...], [...]]

    Args:
        df: DataFrame to export.
        file_path: Output JSON file path.
        orient: JSON structure format (default: "records").
        overwrite: If False, raises FileExistsError if file exists.
        indent: JSON indentation (None for compact, 2 for readable).

    Returns:
        True if successful.

    Raises:
        FileExistsError: If file exists and overwrite=False.
        ValueError: If DataFrame is empty.
        PermissionError: If cannot write to destination.

    Example:
        >>> df = pd.DataFrame({"id": [1, 2], "name": ["A", "B"]})
        >>> export_to_json(df, "data.json", orient="records", indent=2)
        True
        >>> # Output: [{"id": 1, "name": "A"}, {"id": 2, "name": "B"}]
    """
    if df.empty:
        raise ValueError("Cannot export empty DataFrame")

    path = Path(file_path)

    # Check if file exists and overwrite not allowed
    if path.exists() and not overwrite:
        raise FileExistsError(f"File already exists: {file_path}")

    # Create parent directories
    path.parent.mkdir(parents=True, exist_ok=True)

    try:
        df.to_json(
            path,
            orient=orient,
            indent=indent,
        )
        file_size = path.stat().st_size
        logger.info(
            f"Exported {len(df)} rows to {file_path} ({file_size / 1024:.1f} KB, orient={orient})",
        )
        return True
    except PermissionError as e:
        logger.error(f"Permission denied writing to {file_path}: {e}")
        raise
    except Exception as e:
        logger.error(f"Failed to export JSON {file_path}: {e}", exc_info=True)
        raise


def import_from_json(
    file_path: str,
    orient: Literal["records", "split", "index", "columns", "values"] = "records",
    dtype: dict[Any, Any] | None = None,
) -> pd.DataFrame:
    """Import DataFrame from JSON file.

    Orient options should match how the JSON was exported:
      - "records": List of dicts (default)
      - "split": {columns, index, data}
      - "index": {index: {column: value}}
      - "columns": {column: {index: value}}
      - "values": Nested lists

    Args:
        file_path: Input JSON file path.
        orient: JSON structure format (must match export format).
        dtype: Column type mapping (e.g., {"id": "int64"}).

    Returns:
        Imported DataFrame with types applied.

    Raises:
        FileNotFoundError: If file does not exist.
        ValueError: If file is empty or not valid JSON.
        json.JSONDecodeError: If JSON is malformed.

    Example:
        >>> df = import_from_json(
        ...     "data.json",
        ...     orient="records",
        ...     dtype={"id": "int64"}
        ... )
        >>> logger.info("Imported 2 rows from data.json")
    """
    path = Path(file_path)

    # Validate file exists
    if not path.exists():
        raise FileNotFoundError(f"JSON file not found: {file_path}")

    if not path.is_file():
        raise ValueError(f"Path is not a file: {file_path}")

    if path.stat().st_size == 0:
        raise ValueError(f"JSON file is empty: {file_path}")

    try:
        df = pd.read_json(path, orient=orient, dtype=dtype)
        logger.info(
            f"Imported {len(df)} rows with {len(df.columns)} columns from {file_path}",
        )
        return df
    except json.JSONDecodeError as e:
        logger.error(f"JSON decode error in {file_path}: {e}")
        raise
    except Exception as e:
        logger.error(f"Failed to import JSON {file_path}: {e}", exc_info=True)
        raise


# ============================================================================
# Format Converters
# ============================================================================


def convert_csv_to_parquet(
    input_path: str,
    output_path: str,
    dtype: dict[Any, Any] | None = None,
    compression: Literal["snappy", "gzip", "brotli", "lz4", "zstd"] = "snappy",
    overwrite: bool = False,
) -> bool:
    """Convert CSV file to Parquet file.

    Converts through pandas DataFrame intermediate representation:
      CSV → DataFrame (with dtype) → Parquet

    Args:
        input_path: Source CSV file path.
        output_path: Destination Parquet file path.
        dtype: Column type mapping for CSV read.
        compression: Parquet compression codec (default: snappy).
        overwrite: If False, raises FileExistsError if output exists.

    Returns:
        True if successful.

    Raises:
        FileNotFoundError: If input file doesn't exist.
        FileExistsError: If output exists and overwrite=False.

    Example:
        >>> convert_csv_to_parquet(
        ...     "raw_orders.csv",
        ...     "orders.parquet",
        ...     dtype={"order_id": "int64", "total": "float64"},
        ...     compression="snappy",
        ...     overwrite=True
        ... )
        True
    """
    try:
        df = import_from_csv(input_path, dtype=dtype)
        export_to_parquet(
            df,
            output_path,
            overwrite=overwrite,
            compression=compression,
        )
        logger.info(f"Converted {input_path} → {output_path}")
        return True
    except Exception as e:
        logger.error(
            f"Failed to convert CSV to Parquet: {input_path} → {output_path}: {e}",
            exc_info=True,
        )
        raise


def convert_parquet_to_csv(
    input_path: str,
    output_path: str,
    encoding: str = "utf-8",
    overwrite: bool = False,
) -> bool:
    """Convert Parquet file to CSV file.

    Converts through pandas DataFrame intermediate representation:
      Parquet → DataFrame → CSV

    Args:
        input_path: Source Parquet file path.
        output_path: Destination CSV file path.
        encoding: Output CSV encoding (default: utf-8).
        overwrite: If False, raises FileExistsError if output exists.

    Returns:
        True if successful.

    Raises:
        FileNotFoundError: If input file doesn't exist.
        FileExistsError: If output exists and overwrite=False.

    Example:
        >>> convert_parquet_to_csv(
        ...     "orders.parquet",
        ...     "orders_export.csv",
        ...     overwrite=True
        ... )
        True
    """
    try:
        df = import_from_parquet(input_path)
        export_to_csv(
            df,
            output_path,
            encoding=encoding,
            overwrite=overwrite,
        )
        logger.info(f"Converted {input_path} → {output_path}")
        return True
    except Exception as e:
        logger.error(
            f"Failed to convert Parquet to CSV: {input_path} → {output_path}: {e}",
            exc_info=True,
        )
        raise


def convert_csv_to_json(
    input_path: str,
    output_path: str,
    orient: Literal["records", "split", "index", "columns", "values"] = "records",
    dtype: dict[Any, Any] | None = None,
    overwrite: bool = False,
) -> bool:
    """Convert CSV file to JSON file.

    Converts through pandas DataFrame intermediate representation:
      CSV → DataFrame (with dtype) → JSON

    Args:
        input_path: Source CSV file path.
        output_path: Destination JSON file path.
        orient: JSON structure format (default: records).
        dtype: Column type mapping for CSV read.
        overwrite: If False, raises FileExistsError if output exists.

    Returns:
        True if successful.

    Raises:
        FileNotFoundError: If input file doesn't exist.
        FileExistsError: If output exists and overwrite=False.

    Example:
        >>> convert_csv_to_json(
        ...     "orders.csv",
        ...     "orders_api.json",
        ...     orient="records",
        ...     dtype={"order_id": "int64"},
        ...     overwrite=True
        ... )
        True
    """
    try:
        df = import_from_csv(input_path, dtype=dtype)
        export_to_json(df, output_path, orient=orient, overwrite=overwrite)
        logger.info(f"Converted {input_path} → {output_path}")
        return True
    except Exception as e:
        logger.error(
            f"Failed to convert CSV to JSON: {input_path} → {output_path}: {e}",
            exc_info=True,
        )
        raise


def convert_parquet_to_json(
    input_path: str,
    output_path: str,
    orient: Literal["records", "split", "index", "columns", "values"] = "records",
    overwrite: bool = False,
) -> bool:
    """Convert Parquet file to JSON file.

    Converts through pandas DataFrame intermediate representation:
      Parquet → DataFrame → JSON

    Args:
        input_path: Source Parquet file path.
        output_path: Destination JSON file path.
        orient: JSON structure format (default: records).
        overwrite: If False, raises FileExistsError if output exists.

    Returns:
        True if successful.

    Raises:
        FileNotFoundError: If input file doesn't exist.
        FileExistsError: If output exists and overwrite=False.

    Example:
        >>> convert_parquet_to_json(
        ...     "orders.parquet",
        ...     "orders_snapshot.json",
        ...     orient="records",
        ...     overwrite=True
        ... )
        True
    """
    try:
        df = import_from_parquet(input_path)
        export_to_json(df, output_path, orient=orient, overwrite=overwrite)
        logger.info(f"Converted {input_path} → {output_path}")
        return True
    except Exception as e:
        logger.error(
            f"Failed to convert Parquet to JSON: {input_path} → {output_path}: {e}",
            exc_info=True,
        )
        raise


def convert_json_to_parquet(
    input_path: str,
    output_path: str,
    orient: Literal["records", "split", "index", "columns", "values"] = "records",
    compression: Literal["snappy", "gzip", "brotli", "lz4", "zstd"] = "snappy",
    dtype: dict[Any, Any] | None = None,
    overwrite: bool = False,
) -> bool:
    """Convert JSON file to Parquet file.

    Converts through pandas DataFrame intermediate representation:
      JSON → DataFrame (with dtype) → Parquet

    Args:
        input_path: Source JSON file path.
        output_path: Destination Parquet file path.
        orient: JSON structure format (must match input format).
        compression: Parquet compression codec (default: snappy).
        dtype: Column type mapping for JSON read.
        overwrite: If False, raises FileExistsError if output exists.

    Returns:
        True if successful.

    Raises:
        FileNotFoundError: If input file doesn't exist.
        FileExistsError: If output exists and overwrite=False.

    Example:
        >>> convert_json_to_parquet(
        ...     "api_orders.json",
        ...     "orders_snapshot.parquet",
        ...     orient="records",
        ...     compression="snappy",
        ...     dtype={"order_id": "int64"},
        ...     overwrite=True
        ... )
        True
    """
    try:
        df = import_from_json(input_path, orient=orient, dtype=dtype)
        export_to_parquet(
            df,
            output_path,
            compression=compression,
            overwrite=overwrite,
        )
        logger.info(f"Converted {input_path} → {output_path}")
        return True
    except Exception as e:
        logger.error(
            f"Failed to convert JSON to Parquet: {input_path} → {output_path}: {e}",
            exc_info=True,
        )
        raise


def convert_json_to_csv(
    input_path: str,
    output_path: str,
    orient: Literal["records", "split", "index", "columns", "values"] = "records",
    encoding: str = "utf-8",
    dtype: dict[Any, Any] | None = None,
    overwrite: bool = False,
) -> bool:
    """Convert JSON file to CSV file.

    Converts through pandas DataFrame intermediate representation:
      JSON → DataFrame (with dtype) → CSV

    Args:
        input_path: Source JSON file path.
        output_path: Destination CSV file path.
        orient: JSON structure format (must match input format).
        encoding: Output CSV encoding (default: utf-8).
        dtype: Column type mapping for JSON read.
        overwrite: If False, raises FileExistsError if output exists.

    Returns:
        True if successful.

    Raises:
        FileNotFoundError: If input file doesn't exist.
        FileExistsError: If output exists and overwrite=False.

    Example:
        >>> convert_json_to_csv(
        ...     "api_orders.json",
        ...     "orders_export.csv",
        ...     orient="records",
        ...     dtype={"order_id": "int64"},
        ...     overwrite=True
        ... )
        True
    """
    try:
        df = import_from_json(input_path, orient=orient, dtype=dtype)
        export_to_csv(df, output_path, encoding=encoding, overwrite=overwrite)
        logger.info(f"Converted {input_path} → {output_path}")
        return True
    except Exception as e:
        logger.error(
            f"Failed to convert JSON to CSV: {input_path} → {output_path}: {e}",
            exc_info=True,
        )
        raise
