import os
from datetime import datetime, timedelta
from typing import Any, Dict

import pytz
from app.configs.log_config import logger
from dotenv import load_dotenv

load_dotenv()

# * Check for Vault secrets (used in Docker/Kubernetes deployments)
VAULT_ENV_FILE = "/vault/secrets/.env"
if os.path.exists(VAULT_ENV_FILE):
    load_dotenv(dotenv_path=VAULT_ENV_FILE, override=True)
    logger.info(f"Loaded Vault secrets from {VAULT_ENV_FILE}")
else:
    logger.warning(f"Vault .env file not found at {VAULT_ENV_FILE}")

DEBUG = os.environ.get("DEBUG", "false").lower() == "true"
DATETIME_NOW = os.environ.get("DATETIME_NOW", "").upper()

# Log configuration
LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO").upper()
LOG_DIR = os.environ.get("LOG_DIR", "./logs")
LOG_FILE_PREFIX = os.environ.get("LOG_FILE_PREFIX", "misc_function")
LOG_RETENTION_DAYS = int(os.environ.get("LOG_RETENTION_DAYS", "7"))
MAX_LOG_FILES = int(os.environ.get("MAX_LOG_FILES", "50"))

try:
    now: datetime = (
        datetime.fromisoformat(DATETIME_NOW).replace(
            tzinfo=pytz.timezone("Asia/Jakarta")
        )
        if DATETIME_NOW != ""
        else datetime.now(pytz.timezone("Asia/Jakarta"))
    )
except ValueError as e:
    raise ValueError from e

print(f"Processing time: {now}")

start_date: str = (now - timedelta(1)).strftime("%Y-%m-%d")
end_date: str = (now - timedelta(1)).strftime("%Y-%m-%d")


start_month: datetime = (now.strptime(start_date, "%Y-%m-%d")).replace(day=1)
start_month_partition_no: str = start_month.strftime("%Y%m%d")

date_id: datetime = now.strptime(start_date, "%Y-%m-%d")
date_id_partition_no: str = date_id.strftime("%Y%m%d")


DATABASE_MSSQL_USER: str = os.environ.get("DATABASE_MSSQL_USER", "")
DATABASE_MSSQL_PASSWORD: str = os.environ.get("DATABASE_MSSQL_PASSWORD", "")
DATABASE_MSSQL_DATABASE: str = os.environ.get("DATABASE_MSSQL_DATABASE", "")
DATABASE_MSSQL_HOST: str = os.environ.get("DATABASE_MSSQL_HOST", "")
DATABASE_MSSQL_PORT: str = os.environ.get("DATABASE_MSSQL_PORT", "")
DATABASE_MSSQL_DRIVER: str = os.environ.get("DATABASE_MSSQL_DRIVER", "")
DATABASE_MSSQL: Dict[str, Any] = {
    "user": DATABASE_MSSQL_USER,
    "password": DATABASE_MSSQL_PASSWORD,
    "database": DATABASE_MSSQL_DATABASE,
    "host": DATABASE_MSSQL_HOST,
    "port": DATABASE_MSSQL_PORT,
    "driver": DATABASE_MSSQL_DRIVER,
}

database_config = {
    "mssql": DATABASE_MSSQL,
}


ODPS_ACCESS_ID = os.environ.get("ODPS_ACCESS_ID", "")
ODPS_ACCESS_KEY = os.environ.get("ODPS_ACCESS_KEY", "")
ODPS_PROJECT = os.environ.get("ODPS_PROJECT", "")
ODPS_ENDPOINT = os.environ.get("ODPS_ENDPOINT", "")
odps_config: Dict[str, Any] = {
    "access_id": ODPS_ACCESS_ID,
    "secret_access_key": ODPS_ACCESS_KEY,
    "default_project": ODPS_PROJECT,
    "endpoint": ODPS_ENDPOINT,
}
