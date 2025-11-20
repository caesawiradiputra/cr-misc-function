from urllib.parse import quote_plus
import trino.dbapi
from trino.auth import BasicAuthentication
from trino.dbapi import Connection as TrinoConnection

from .base import RDBMSBaseStrategy

class TrinoStrategy(RDBMSBaseStrategy):
    """Strategy for Trino distributed query engine."""

    def _create_connection(self) -> TrinoConnection:
        return trino.dbapi.connect(
            host=self.config.host,
            port=self.config.port,
            catalog="hive",
            schema=self.config.database,
            auth=BasicAuthentication(self.config.user, self.config.password),
            http_scheme="https",
            verify=False,
        )

    def _build_connection_url(self) -> str:
        encoded_password = quote_plus(self.config.password)
        return f"trino://{self.config.user}:{encoded_password}@{self.config.host}:{self.config.port}/hive/{self.config.database}"