##@resource_reference{"config.py"}
"""Loads master_data_address OSS extracts into an ODPS external table.

Runs as a DataWorks PyODPS node. The DataWorks runtime injects `o` (ODPS
project handle), `args` (node runtime parameters), and `DataFrame` (PyODPS
DataFrame) into the global namespace at execution time, so they are used
here without import.
"""

import io
import json
import re
import sys
from datetime import date, datetime
from os.path import abspath, dirname
from typing import Dict, List, Tuple

import oss2
import pandas as pd

sys.path.append(dirname(abspath("config.py")))
from config import CONFIG

# ODPS column-type substring -> pandas/PyODPS dtype used when reading and
# persisting the raw CSV extract.
ODPS_TO_PANDAS_DTYPE = {
    "VARCHAR": "string",
    "BIGINT": "Int64",
    "DATE": "string",
}

# Textual substitutions applied to the ODPS `schema.columns` repr so it can
# be parsed as JSON and used as the DataFrame `as_type` schema.
SCHEMA_TEXT_SUBSTITUTIONS = {
    ", <partition pt, type string>]": "\n}",
    "]": "\n}",
    "<column ": '"',
    ", type ": '":"',
    ">": '"',
    ",  ": "\n, ",
    "bigint": "Int64",
    "[": "{\n",
}


class LoadExternalTableMapper:
    """Loads OSS CSV extracts for one master_data_address source into ODPS.

    Args:
        process_type: Source identifier (e.g. "branch"); selects the OSS
            file prefix and the per-source cleansing rules.
        path_oss: OSS prefix under which the source's extract files live.
        table_name: Target ODPS table to persist the cleansed batch into.
    """

    def __init__(self, process_type: str, path_oss: str, table_name: str) -> None:
        self.env: str = o.get_project().name
        self.logger = CONFIG[self.env].get("logger")
        self.logger.info(f"Environment: {self.env}")
        self.today: date = CONFIG[self.env].get("today")
        self.process_type = process_type
        self.path = path_oss
        self.table_name = table_name
        self.__oss_bucket = self.__get_oss_conn()
        self.logger.info(self.__oss_bucket)

        self.__batch_executor()

    def __batch_executor(self) -> None:
        """Finds this run's OSS files, cleanses them, and persists the batch."""
        process_file = f"{self.path}/{self.process_type}_{args['bizdate']}"
        self.logger.info(f"process_file: {process_file}")
        all_cache_file_paths = []
        t_schema, column_use, dict_dtype = self.get_schema_table_odps(self.table_name)

        if self.process_type == "branch":
            pass  # TODO: schema override placeholder, if branch source needs one

        self.logger.info(f"t_schema: {t_schema}")

        df_persist = pd.DataFrame()
        for obj in oss2.ObjectIteratorV2(self.__oss_bucket, prefix=self.path):
            self.logger.info(f"iterator: {obj.key} , processType: {self.process_type}")
            if process_file in str(obj.key):
                all_cache_file_paths.append(obj.key)
                df_persist = df_persist.append(
                    self.process_df_persist(self.process_type, obj.key, column_use, dict_dtype),
                    ignore_index=True,
                )

        if len(df_persist) > 0:
            df_persist = df_persist.reset_index(drop=True)
            self.logger.info(f"-- {len(df_persist)} row(s) processed. --")
            df_persist = DataFrame(df_persist, as_type=t_schema)
            df_persist.persist(self.table_name, partition=f"pt={args['bizdate']}")
        self.logger.info(f"-- {len(all_cache_file_paths)} file(s) processed: {all_cache_file_paths} --")

    def __get_oss_conn(self):
        """Opens the OSS bucket connection using the da-ops RAM user."""
        auth = oss2.Auth(args["access_key"], args["access_key_secret"])
        return oss2.Bucket(auth, "https://oss-ap-southeast-5.aliyuncs.com", args["bucket"])

    def get_schema_table_odps(self, table_name: str) -> Tuple[Dict, List[str], Dict]:
        """Reads the target table's schema and adapts it for DataFrame use.

        Returns:
            Tuple of (as_type schema dict, column names excluding
            `logdate`, dict of column name -> pandas dtype).
        """
        t = o.get_table(self.table_name)
        t_schema = str(t.schema.columns)
        idx = t.schema.names.index("logdate")
        t.schema.names.pop(idx)
        t.schema.types.pop(idx)

        for idx, item in enumerate(t.schema.types):
            for odps_type, pandas_dtype in ODPS_TO_PANDAS_DTYPE.items():
                if odps_type in str(item):
                    t.schema.types[idx] = pandas_dtype
                    break
            self.logger.debug(f"column type after mapping: {t.schema.types[idx]}")

        dict_dtype = dict(zip(t.schema.names, t.schema.types))
        for old, new in SCHEMA_TEXT_SUBSTITUTIONS.items():
            t_schema = t_schema.replace(old, new)
        t_schema = re.sub(r"varchar\(\d+\)|^varchar", "string", t_schema)
        t_schema_dict = json.loads(t_schema)
        return t_schema_dict, t.schema.names, dict_dtype

    def process_df_persist(
        self,
        process_type,
        process_file,
        column_use,
        dict_dtype,
    ) -> pd.DataFrame:
        """Reads one OSS CSV extract and applies per-source cleansing rules.

        Args:
            process_type: Source identifier controlling which cleansing
                branch below is applied.
            process_file: OSS object key of the CSV extract to read.
            column_use: Columns to keep from the CSV.
            dict_dtype: Column name -> dtype mapping for `pd.read_csv`.
        """
        now = datetime.now()
        obj = self.__oss_bucket.get_object(process_file)
        self.logger.info(f"Column use: {column_use}")
        obj_buffer = io.BytesIO(obj.read())
        df = pd.read_csv(
            obj_buffer,
            delimiter="|",
            usecols=column_use,
            dtype=dict_dtype,
            keep_default_na=False,
            encoding="latin1",
        )
        df = df.reset_index(drop=True)

        if process_type == "branch":
            pass  # TODO: define branch-specific cleansing rules

        df["logdate"] = now.strftime("%Y-%m-%d %H:%M:%S")
        self.logger.info(f"process File: {process_file} , {df.shape[0]} rows process.")
        return df


if __name__ == "__main__":
    list_crawl = ["branch"]
    for source in list_crawl:
        oss_dir = f"master_data_address/{source}/source"  # TODO: confirm OSS source path
        table_name = f"dgo_mda_raw_data_{source}"
        print("obj: ", source, ", oss: ", oss_dir)
        LoadExternalTableMapper(process_type=source, path_oss=oss_dir, table_name=table_name)
