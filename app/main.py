"""
Database connection and query execution demonstration.

This module provides a simple entry point for testing database connectivity
using the MSSQL strategy.
"""

from app.connections.strategies import create_strategy


def main() -> None:
    """
    Execute a test query against the MSSQL database.

    Demonstrates basic database connectivity by creating an MSSQL strategy
    and executing a simple test query.
    """
    mssql_connector = create_strategy("mssql")

    with mssql_connector as mssql:
        mssql.execute_query("SELECT 1 AS test_col")
