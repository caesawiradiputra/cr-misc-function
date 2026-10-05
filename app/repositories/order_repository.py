"""Repository for order data access using MSSQL.

Extends BaseRepository with order-specific domain methods. Generic table
operations (select_all, select_one, select_where, insert_one, insert_bulk,
update_where, delete_where, count) are inherited automatically.

Usage:
    with OrderRepository() as repo:
        # Inherited generic operations
        all_orders    = repo.select_all()
        order         = repo.select_one("order_id", 1001)
        pending       = repo.select_where({"status": "PENDING"})
        repo.insert_one({"order_id": 9999, "customer_name": "Alice", ...})
        repo.update_where({"status": "SHIPPED"}, {"order_id": 9999})
        repo.delete_where({"order_id": 9999})
        total         = repo.count()

        # Domain-specific operations
        recent        = repo.get_pending_orders(days=14)
        repo.insert_bulk_orders(orders_df)
"""

import logging

import pandas as pd

from app.repositories.base_repository import BaseRepository

logger = logging.getLogger(__name__)


class OrderRepository(BaseRepository):
    """Repository for order-related database operations using MSSQL.

    Inherits generic CRUD operations from BaseRepository and adds
    order-domain methods on top. The class constants below drive all
    inherited query generation automatically.

    Attributes:
        strategy: Active MSSQLStrategy instance (set by BaseRepository.__init__).
    """

    DATABASE_TYPE = "mssql"
    SCHEMA = "dbo"
    TABLE_NAME = "orders"
    COLUMNS = [
        "order_id",
        "customer_name",
        "order_date",
        "total_amount",
        "status",
    ]

    def get_pending_orders(self, days: int = 7) -> pd.DataFrame:
        """Retrieve PENDING orders within a rolling time window.

        Args:
            days: Number of days to look back from today (default: 7).

        Returns:
            DataFrame with order_id, customer_name, order_date, total_amount,
            sorted by order_date descending.

        Example:
            >>> with OrderRepository() as repo:
            ...     recent = repo.get_pending_orders(days=14)
            ...     print(f"Found {len(recent)} pending orders")
        """
        logger.debug("get_pending_orders called with days=%s", days)
        query = """
        SELECT
            order_id,
            customer_name,
            order_date,
            total_amount
        FROM dbo.orders
        WHERE status = 'PENDING'
          AND order_date >= DATEADD(day, -?, GETDATE())
        ORDER BY order_date DESC
        """
        return self.strategy.execute_query(query, params=(days,))

    def insert_bulk_orders(self, orders_df: pd.DataFrame) -> str:
        """Bulk-insert orders into the staging table for batch processing.

        Appends rows to dbo.orders_staging. Column names are sanitized by
        the strategy to replace non-alphanumeric characters with underscores.

        Args:
            orders_df: DataFrame containing order data to stage.

        Returns:
            Success message from the strategy.

        Example:
            >>> import pandas as pd
            >>> new_orders = pd.DataFrame({
            ...     "order_id": [1001, 1002],
            ...     "customer_name": ["Alice", "Bob"],
            ...     "total_amount": [99.99, 149.99],
            ... })
            >>> with OrderRepository() as repo:
            ...     result = repo.insert_bulk_orders(new_orders)
        """
        return self.strategy.create_table(
            schema="dbo",
            table_name="orders_staging",
            df=orders_df,
            if_exists="append",
            index=False,
        )
