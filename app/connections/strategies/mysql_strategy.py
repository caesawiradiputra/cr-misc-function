from typing import Union
from urllib.parse import quote_plus
import mysql.connector
from mysql.connector.abstracts import MySQLConnectionAbstract
from mysql.connector.pooling import PooledMySQLConnection

from .base import RDBMSBaseStrategy

class MySQLStrategy(RDBMSBaseStrategy):
    """Strategy for MySQL databases."""

    def _create_connection(self) -> Union[MySQLConnectionAbstract, PooledMySQLConnection]:
        return mysql.connector.connect(
            host=self.config.host,
            port=self.config.port,
            user=self.config.user,
            password=self.config.password,
            database=self.config.database,
        )

    def _build_connection_url(self) -> str:
        encoded_password = quote_plus(self.config.password)
        return f"mysql+mysqlconnector://{self.config.user}:{encoded_password}@{self.config.host}:{self.config.port}/{self.config.database}"