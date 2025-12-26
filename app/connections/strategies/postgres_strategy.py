from urllib.parse import quote_plus

import psycopg2
from psycopg2.extensions import connection as Psycopg2Connection

from .base import RDBMSBaseStrategy


class PostgreSQLStrategy(RDBMSBaseStrategy):
    """Strategy for PostgreSQL and Hologres databases."""

    def _create_connection(self) -> Psycopg2Connection:
        return psycopg2.connect(
            database=self.config.database,
            user=self.config.user,
            password=self.config.password,
            host=self.config.host,
            port=self.config.port,
        )

    def _build_connection_url(self) -> str:
        encoded_password = quote_plus(self.config.password)
        return f"postgresql://{self.config.user}:{encoded_password}@{self.config.host}:{self.config.port}/{self.config.database}"
