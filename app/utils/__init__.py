"""Shared utility modules for repositories and data handling.

This package contains two complementary utility modules:

1. **repo_utils**: SQL query building and database compatibility utilities
   - Query file loading with validation
   - Database-specific placeholder generation
   - Parameterized INSERT/UPDATE query generation
   - Column validation and SELECT list building
   - Parameter tuple merging

2. **data_utils**: Data format I/O and conversion utilities
   - CSV, Parquet, and JSON import/export functions
   - Format conversion layer (6 converters for all combinations)
   - Automatic DataFrame intermediate representation
   - Type preservation and compression handling

Example:
    >>> from app.utils.repo_utils import read_query_file, generate_placeholders
    >>> from app.utils.data_utils import export_to_csv, convert_csv_to_parquet
    >>>
    >>> # Load query and get placeholders
    >>> query = read_query_file("queries/orders/pending.sql")
    >>> params = (status, start_date, end_date)
    >>>
    >>> # Execute and export results
    >>> df = strategy.execute_query(query, params=params)
    >>> export_to_csv(df, "orders.csv")
    >>> convert_csv_to_parquet("orders.csv", "orders.parquet")
"""
