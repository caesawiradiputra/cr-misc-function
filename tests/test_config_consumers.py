"""Tests for the modules that consume app.configs.config.

These modules were written against an older dict-based config API and failed to
import once config.py moved to Pydantic objects, so the first group of tests is
a plain import smoke test.
"""

import importlib
from datetime import datetime, timedelta

import pytest
import pytz

from app.configs.config_schemas import DatabaseConfig, ODPSConfig, OSSConfig

CONSUMER_MODULES = [
    "app.connections.strategies.factory",
    "app.connections.oss",
    "app.connections.connection",
    "app.connections.connection_strategy",
    "app.utils",
    "app.utils.date_util",
    "app.utils.pvc_data_manager",
]


@pytest.mark.parametrize("module", CONSUMER_MODULES)
def test_consumer_module_imports(module: str) -> None:
    importlib.import_module(module)


# ---- date_util ---------------------------------------------------------------


def _fixed_now(year: int, month: int, day: int) -> datetime:
    return pytz.timezone("Asia/Jakarta").localize(datetime(year, month, day, 10, 30))


def test_date_util_formats_from_current_time(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.utils import date_util

    monkeypatch.setattr(date_util, "_now", lambda: _fixed_now(2024, 1, 16))

    assert date_util.get_partition() == "20240115"
    assert date_util.get_partition(timedelta(days=0)) == "20240116"
    assert date_util.get_partition(is_start_month=True) == "20240101"
    assert date_util.get_partition(is_datetime=True) == "2024-01-15 00:00:00"
    assert date_util.get_bizdate() == "2024-01-15"
    assert date_util.get_bizdate(is_datetime=True) == "2024-01-15 00:00:00"
    assert date_util.get_bizdate_with_time(time_format="12:30:45") == (
        "2024-01-16 12:30:45"
    )


def test_date_util_reads_the_clock_on_every_call(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.utils import date_util

    monkeypatch.setattr(date_util, "_now", lambda: _fixed_now(2024, 1, 16))
    assert date_util.get_partition() == "20240115"

    monkeypatch.setattr(date_util, "_now", lambda: _fixed_now(2024, 2, 1))
    assert date_util.get_partition() == "20240131"


def test_date_util_now_uses_configured_timezone() -> None:
    from app.utils import date_util

    assert date_util._now().tzinfo is not None
    assert str(date_util._now().tzinfo) == "Asia/Jakarta"


# ---- strategy factory --------------------------------------------------------


def test_factory_builds_odps_strategy_from_config(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.connections.strategies import factory

    monkeypatch.setattr(
        factory,
        "ODPS",
        ODPSConfig(
            access_id="id",
            secret_access_key="secret",
            project="proj",
            endpoint="https://example.invalid/api",
        ),
    )

    strategy = factory.create_strategy("odps")

    assert isinstance(strategy, factory.ODPSStrategy)
    assert strategy.config.default_project == "proj"
    assert strategy.config.access_id == "id"
    assert strategy.config.endpoint == "https://example.invalid/api"


def test_factory_rejects_odps_config_missing_a_field(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.connections.strategies import factory

    monkeypatch.setattr(factory, "ODPS", ODPSConfig(access_id="id"))

    with pytest.raises(
        ValueError, match="Missing ODPS config field: secret_access_key"
    ):
        factory.create_strategy("odps")


def test_factory_builds_rdbms_strategy_from_config(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.connections.strategies import factory

    monkeypatch.setattr(
        factory,
        "database_config",
        {
            "mssql": DatabaseConfig(
                host="db.invalid",
                port="1433",
                user="u",
                password="p",
                database="d",
                pool_size=7,
                max_overflow=3,
            )
        },
    )

    strategy = factory.create_strategy("mssql")

    assert isinstance(strategy, factory.MSSQLStrategy)
    assert strategy.config.host == "db.invalid"
    assert strategy.config.port == 1433
    assert (strategy.config.pool_size, strategy.config.max_overflow) == (7, 3)


def test_factory_rejects_rdbms_config_missing_a_field(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.connections.strategies import factory

    monkeypatch.setattr(
        factory, "database_config", {"mssql": DatabaseConfig(host="db.invalid")}
    )

    with pytest.raises(ValueError, match="Missing DB config field: port"):
        factory.create_strategy("mssql")


def test_factory_rejects_unknown_db_type() -> None:
    from app.connections.strategies import factory

    with pytest.raises(ValueError, match="Unsupported database type"):
        factory.create_strategy("nope")


# ---- OSSConnector ------------------------------------------------------------

_OSS = OSSConfig(
    access_key_id="AKID",
    access_key_secret="TOP-SECRET-VALUE",
    bucket_name="bucket",
    endpoint="oss.invalid",
)


def test_oss_connector_reads_fields_from_config(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.connections import oss

    monkeypatch.setattr(oss, "oss_config", {"negative_list": _OSS})

    connector = oss.OSSConnector("negative_list")

    assert connector.bucket_name == "bucket"
    assert connector.endpoint == "oss.invalid"
    assert connector.region == ""


def test_oss_connector_rejects_unknown_key(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.connections import oss

    monkeypatch.setattr(oss, "oss_config", {"negative_list": _OSS})

    with pytest.raises(ValueError, match="OSS config key not found: other"):
        oss.OSSConnector("other")


def test_oss_connector_rejects_empty_credentials(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.connections import oss

    monkeypatch.setattr(oss, "oss_config", {"negative_list": OSSConfig()})

    with pytest.raises(ValueError, match="access_key_id and access_key_secret"):
        oss.OSSConnector("negative_list")


def test_oss_connector_does_not_log_the_secret(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.connections import oss

    monkeypatch.setattr(oss, "oss_config", {"negative_list": _OSS})
    messages: list[str] = []
    sink_id = oss.logger.add(messages.append, level="DEBUG")
    try:
        oss.OSSConnector("negative_list")
    finally:
        oss.logger.remove(sink_id)

    assert messages, "expected a debug log line from OSSConnector.__init__"
    assert not any("TOP-SECRET-VALUE" in m for m in messages)
