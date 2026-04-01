from typing import Literal, overload

from app.configs.config import database_config, odps_config

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
        for field in ["access_id", "secret_access_key", "default_project", "endpoint"]:
            if not odps_config.get(field):
                raise ValueError(f"[{db_type}] Missing ODPS config field: {field}")
        cfg = ODPSConfig(db_type="odps", **odps_config)
        return ODPSStrategy(cfg)

    if db_type not in database_config:
        raise ValueError(f"[{db_type}] Unsupported database type")

    db_cfg_raw: dict = database_config[db_type]
    for field in ["host", "port", "user", "password", "database"]:
        if not db_cfg_raw.get(field):
            raise ValueError(f"[{db_type}] Missing DB config field: {field}")

    cfg = DBConfig(
        db_type=db_type,
        host=db_cfg_raw["host"],
        port=db_cfg_raw["port"],
        user=db_cfg_raw["user"],
        password=db_cfg_raw["password"],
        database=db_cfg_raw["database"],
        driver=db_cfg_raw.get("driver"),
        pool_size=db_cfg_raw.get("pool_size", 5),
        max_overflow=db_cfg_raw.get("max_overflow", 10),
    )

    strategy_cls = _STRATEGY_MAP.get(db_type)
    if not strategy_cls:
        raise ValueError(f"[{db_type}] No strategy implementation found")
    return strategy_cls(cfg)
