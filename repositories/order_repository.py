"""Repository pattern implementation for order data access.

This module provides a domain-specific abstraction over database operations
for the orders domain, using the Strategy pattern for database connectivity.
"""

import pandas as pd
from app.connections.strategies import create_strategy


class OrderRepository:
    """Repository for order-related database operations using MSSQL.
    
    Implements the Repository pattern to encapsulate data access logic
    and provide a clean interface for order domain operations.
    
    Usage:
        - Context manager automatically handles connection lifecycle
            with OrderRepository() as repo:
                pending_orders = repo.get_pending_orders(days=30)
            
        - Or manual connection management
            repo = OrderRepository()
            try:
                orders = repo.get_pending_orders()
            finally:
                repo.__exit__(None, None, None)
    
    Attributes:
        strategy: Database strategy instance (auto-inferred as MSSQLStrategy).
    """

    def __init__(self):
        """Initialize repository with MSSQL database connection.
        
        Automatically connects to MSSQL using configuration from
        app.configs.config.database_config["mssql"].
        """
        self.strategy = create_strategy("mssql")
        self.strategy.connect()

    def get_pending_orders(self, days: int = 7) -> pd.DataFrame:
        """Retrieve orders with PENDING status within specified time window.
        
        Args:
            days: Number of days to look back from current date (default: 7).
        
        Returns:
            DataFrame with columns: order_id, customer_name, order_date, total_amount.
            Sorted by order_date descending.
        
        Raises:
            RuntimeError: If query execution fails.
            ConnectionError: If database connection is not established.
        
        Example:
            >>> with OrderRepository() as repo:
            ...     recent_pending = repo.get_pending_orders(days=14)
            ...     print(f"Found {len(recent_pending)} pending orders")
        """
        query = """
        SELECT 
            order_id, 
            customer_name, 
            order_date,
            total_amount
        FROM orders
        WHERE status = 'PENDING'
          AND order_date >= DATEADD(day, -?, GETDATE())
        ORDER BY order_date DESC
        """
        return self.strategy.execute_query(query, params=(days,))

    def insert_bulk_orders(self, orders_df: pd.DataFrame) -> str:
        """Insert multiple orders into staging table for batch processing.
        
        Uses pandas DataFrame for efficient bulk insertion into the
        dbo.orders_staging table. Data is appended to existing records.
        
        Args:
            orders_df: DataFrame containing order data to insert.
                Expected to have valid order schema columns.
        
        Returns:
            Success message indicating table name and operation result.
        
        Raises:
            RuntimeError: If table creation/insertion fails.
            ValueError: If DataFrame has invalid schema or column names.
        
        Note:
            Column names will be sanitized to replace non-alphanumeric
            characters with underscores for database compatibility.
        
        Example:
            >>> import pandas as pd
            >>> new_orders = pd.DataFrame({
            ...     'order_id': [1001, 1002],
            ...     'customer_name': ['Alice', 'Bob'],
            ...     'total_amount': [99.99, 149.99]
            ... })
            >>> with OrderRepository() as repo:
            ...     result = repo.insert_bulk_orders(new_orders)
            ...     print(result)
        """
        return self.strategy.create_table(
            schema="dbo",
            table_name="orders_staging",
            df=orders_df,
            if_exists="append",
            index=False,
        )

    def __enter__(self):
        """Enter context manager (connection already established in __init__)."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit context manager and ensure connection cleanup.
        
        Args:
            exc_type: Exception type if raised during context.
            exc_val: Exception value if raised during context.
            exc_tb: Exception traceback if raised during context.
        
        Note:
            Disconnect is called regardless of whether an exception occurred.
        """
        self.strategy.disconnect()
