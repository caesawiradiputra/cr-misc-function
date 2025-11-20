from urllib.parse import quote_plus
import pyodbc
from pyodbc import Connection as PyodbcConnection

from .base import RDBMSBaseStrategy

class MSSQLStrategy(RDBMSBaseStrategy):
    """Strategy for Microsoft SQL Server."""

    def _create_connection(self) -> PyodbcConnection:
        driver = self.config.driver or "ODBC Driver 17 for SQL Server"
        conn_str = (
            f"DRIVER={driver};"
            f"SERVER={self.config.host},{self.config.port};"
            f"DATABASE={self.config.database};"
            f"UID={self.config.user};"
            f"PWD={self.config.password}"
        )
        return pyodbc.connect(conn_str)

    def _build_connection_url(self) -> str:
        encoded_password = quote_plus(self.config.password)
        driver = quote_plus(self.config.driver or "ODBC Driver 17 for SQL Server")
        return f"mssql+pyodbc://{self.config.user}:{encoded_password}@{self.config.host}:{self.config.port}/{self.config.database}?driver={driver}"