"""
Database connection and query execution demonstration.

This module provides a simple entry point for testing database connectivity
using the MSSQL strategy.
"""

from app.connections.strategies import create_strategy
from app.repositories.order_repository import OrderRepository


def main() -> None:
    """
    Execute a test query against the MSSQL database.

    Demonstrates basic database connectivity by creating an MSSQL strategy
    and executing a simple test query.
    """
    mssql_connector = create_strategy("mssql")

    with mssql_connector as mssql:
        mssql.execute_query("SELECT 1 AS test_col")

    with OrderRepository() as repo:
        repo.select_all()  # Test inherited method
        pending_orders = repo.get_pending_orders(days=7)
        print(f"Found {len(pending_orders)} pending orders in the last 7 days.")