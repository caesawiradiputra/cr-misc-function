from typing import Literal, overload

from app.configs.config import ODPS, database_config

from .base import DatabaseStrategy, DBConfig, ODPSConfig
from .hive_strategy import HiveStrategy
from .mssql_strategy import MSSQLStrategy
from .mysql_strategy import MySQLStrategy
from .odps_strategy import ODPSStrategy
from .postgres_strategy import PostgreSQLStrategy
from .trino_strategy import TrinoStrategy

# Map db_type to strategy class
_STRATEGY_MAP = {
    "postgres": PostgreSQLStrategy,
    "hologres": PostgreSQLStrategy,  # * Shares PostgreSQL protocol
    "mysql": MySQLStrategy,
    "mssql": MSSQLStrategy,
    "trino": TrinoStrategy,
    "hive": HiveStrategy,
    "odps": ODPSStrategy,
}


@overload
def create_strategy(db_type: Literal["postgres"]) -> PostgreSQLStrategy: ...


@overload
def create_strategy(db_type: Literal["hologres"]) -> PostgreSQLStrategy: ...


@overload
def create_strategy(db_type: Literal["mysql"]) -> MySQLStrategy: ...


@overload
def create_strategy(db_type: Literal["mssql"]) -> MSSQLStrategy: ...


@overload
def create_strategy(db_type: Literal["trino"]) -> TrinoStrategy: ...


@overload
def create_strategy(db_type: Literal["hive"]) -> HiveStrategy: ...


@overload
def create_strategy(db_type: Literal["odps"]) -> ODPSStrategy: ...


@overload
def create_strategy(db_type: str) -> DatabaseStrategy: ...


def create_strategy(db_type: str):
    """Factory to create appropriate strategy instance for given db_type."""
    if db_type == "odps":
        for field in ["access_id", "secret_access_key", "project", "endpoint"]:
            if not getattr(ODPS, field):
                raise ValueError(f"[{db_type}] Missing ODPS config field: {field}")
        odps_cfg = ODPSConfig(
            db_type="odps",
            access_id=ODPS.access_id,
            secret_access_key=ODPS.secret_access_key,
            default_project=ODPS.project,
            endpoint=ODPS.endpoint,
        )
        return ODPSStrategy(odps_cfg)

    if db_type not in database_config:
        raise ValueError(f"[{db_type}] Unsupported database type")

    db_cfg = database_config[db_type]
    for field in ["host", "port", "user", "password", "database"]:
        if not getattr(db_cfg, field):
            raise ValueError(f"[{db_type}] Missing DB config field: {field}")

    cfg = DBConfig(
        db_type=db_type,
        host=db_cfg.host,
        port=int(db_cfg.port),
        user=db_cfg.user,
        password=db_cfg.password,
        database=db_cfg.database,
        driver=db_cfg.driver,
        pool_size=db_cfg.pool_size,
        max_overflow=db_cfg.max_overflow,
    )

    strategy_cls = _STRATEGY_MAP.get(db_type)
    if not strategy_cls:
        raise ValueError(f"[{db_type}] No strategy implementation found")
    return strategy_cls(cfg)
