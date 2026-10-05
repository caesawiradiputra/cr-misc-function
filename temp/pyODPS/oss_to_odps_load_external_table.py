##@resource_reference{"config.py"}
import io
import json
import re
import sys
from datetime import date, datetime
from os.path import abspath, dirname

import oss2
import pandas as pd

sys.path.append(dirname(abspath("config.py")))
from config import CONFIG


class LoadExternalTableMapper:
    def __init__(self, processType: str, path_oss: str, table_name: str):
        self.env: str = o.get_project().name
        self.logger = CONFIG[self.env].get("logger")
        self.logger.info(f"Environment: {self.env}")
        today: date
        self.today = CONFIG[self.env].get("today")
        self.processType = processType
        self.path = path_oss
        self.table_nm = table_name
        # self.__conn = o
        self.__oss_conn_bucket = self.__get_oss_conn()
        self.logger.info(self.__oss_conn_bucket)
        self.text_schema = {
            ', <partition pt, type string>]' : '\n}'
            ,']' : '\n}'
            ,'<column ' : '"'
            ,", type " : '":"'
            ,">" : '"'
            ,",  " : "\n, "
            ,"bigint" : "Int64"
            ,"[" : "{\n"
        }

        # self.__result_table = self.__get_result_table()
        self.__batch_executor()

    def __batch_executor(self):
        process_file = f"{self.path}/{self.processType}_{args['bizdate']}"
        self.logger.info(f"process_file: {process_file}")
        all_cache_file_paths = []
        t_schema, column_use, dict_dtype = self.get_schema_table_odps( self.table_nm)
        if (self.processType == 'liveagent'):
            t_schema["tanggal_jatuh_tempo"] = 'datetime'
        self.logger.info(f"t_schema: {t_schema}")
        df_persist = pd.DataFrame()
        for obj in oss2.ObjectIteratorV2(self.__oss_conn_bucket, prefix=self.path):
            self.logger.info(f"iterator: {obj.key} , processType: {self.processType}")
            if (process_file in str(obj.key)):
                all_cache_file_paths.append(obj.key)
                df_persist = df_persist.append(self.process_df_persist(self.processType, obj.key, column_use, dict_dtype), ignore_index=True)
        if(len(df_persist)>0):
            df_persist = df_persist.reset_index(drop=True)
            self.logger.info(f"-- {len(df_persist)} row(s) processed. --")
            df_persist = DataFrame(df_persist, as_type=t_schema)
            df_persist.persist(self.table_nm, partition=f"pt={args['bizdate']}")
        self.logger.info(f"-- {len(all_cache_file_paths)} file(s) processed: {all_cache_file_paths} --")

    # v.0.2 Connection to OSS using da-ops RAM user
    def __get_oss_conn(self):
        auth = oss2.Auth(args['access_key'], args['access_key_secret'])
        bucket = oss2.Bucket(auth, 'https://oss-ap-southeast-5.aliyuncs.com', args['bucket'])
        return bucket

    # get schema and list of column from table odps
    def get_schema_table_odps(self, table_nm : str):
        t = o.get_table(self.table_nm)
        t_schema =  str(t.schema.columns)
        idx = t.schema.names.index("logdate")
        t.schema.names.pop(idx)
        t.schema.types.pop(idx)
        # print("-- testtypesBF: ", t.schema.types)
        for idx, item in enumerate(t.schema.types):
            # print ("ini str: ", str(item))
            if "VARCHAR" in str(item):
                t.schema.types[idx] = 'string'
            elif "BIGINT" in str(item):
                t.schema.types[idx] = 'Int64'
            elif "DATE" in str(item):
                t.schema.types[idx] = 'string'
            print ("ini str after: ", t.schema.types[idx])
        dict_dtype = dict(zip(t.schema.names, t.schema.types))
        for old,new in self.text_schema.items():
            t_schema = t_schema.replace(old,new)
        # t_schema = re.sub("decimal\(\d+,\d+\)|^decimal", "float64", t_schema)
        t_schema = re.sub("varchar\(\d+\)|^varchar", "string", t_schema)
        t_schema_dict = json.loads(t_schema)
        return t_schema_dict, t.schema.names, dict_dtype

    def process_df_persist(self, processType, processFile, column_use, dict_dtype):
        now = datetime.now()
        obj = self.__oss_conn_bucket.get_object(processFile)
        self.logger.info(f"Column use: {column_use}")
        obj_buffer = io.BytesIO(obj.read())
        df = pd.read_csv(obj_buffer,delimiter='|', usecols = column_use, dtype= dict_dtype, keep_default_na = False, encoding='latin1')
        df = df.reset_index(drop=True)
        if (processType == "atlasat" or processType == "asliri"):
            df = df.drop(df[df.nik == ''].index)
        elif (processType == "hitech"):
            df = df.drop(df[df.application_id == ''].index)
        elif (processType == "liveagent"):
            df = df.drop(df[df.nama_konsumen == ''].index)
            df['tanggal_jatuh_tempo'] = pd.to_datetime(df['tanggal_jatuh_tempo'], errors='coerce')
            df['tanggal_jatuh_tempo'] = df['tanggal_jatuh_tempo'].dt.strftime('%Y-%m-%d')
            #-----
            df['assigned_time'] = pd.to_datetime(df['assigned_time'], errors='coerce')
            df['assigned_time'] = df['assigned_time'].dt.strftime('%Y-%m-%d %H:%M:%S')
        elif (processType == "digitalchannel"):
            df = df.drop(df[df.no_kontrak == ''].index)
            df['sentat'] = pd.to_datetime(df['sentat'], errors='coerce')
            # df['sentat'] = df['sentat'].dt.strftime('%Y-%m-%d %H:%M:%S')
        elif (processType == "smart"):
            df = df.drop(df[df.application_id == ''].index)
            df['last_updated'] = pd.to_datetime(df['last_updated'], errors='coerce')
        elif (processType == "welcoming"):
            df = df.drop(df[df.mobilephone == ''].index)
        elif (processType == "sasonline"):
            df['created_date'] = pd.to_datetime(df['created_date'], errors='coerce')
        df['logdate']= now.strftime("%Y-%m-%d %H:%M:%S")
        self.logger.info(f"process File: {processFile} , {df.shape[0]} rows process.")
        return df

if __name__ == "__main__":
    #list_crawl = ['atlasat','asliri','liveagent','hitech'
    #                ,'newphonenumber','exception','digitalchannel'
    #                # ,'smart' #vincent 20240313
    #                ,'welcoming','sasonline' #riski 20240323
    #                ,'newphonenumberinbound' #caesa 20240418
    #                #,'telesas', #vincent 20240321
    #                ,'skiptrace' #20250210
    #                ]
    list_crawl = ['exception']
    for obj in list_crawl:
        oss_dir = f"master_data_nomor_telepon/{obj}/source"
        table_name = f"dgo_mdt_raw_data_{obj}"
        print("obj: ", obj, ", oss: ", oss_dir)
        olxProcess = LoadExternalTableMapper(processType=obj, path_oss=oss_dir, table_name=table_name)
    # for filecrawled in list_crawl:
