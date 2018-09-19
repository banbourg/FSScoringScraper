# -*- coding: utf-8 -*-
import sys
import logging

import psycopg2
from psycopg2 import sql
import pandas as pd
import glob
from sqlalchemy import create_engine

logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)-5s - %(message)s",
                    level=logging.INFO,
                    datefmt="%Y-%m-%d %H:%M:%S")

logger = logging.getLogger(__name__)

MODE = "fail" #or "append"
try:
    import settings
except ImportError as exc:
    sys.exit(f"Error: failed to import module ({exc})")


def upload_new_table(cursor, connection, engine, df, table_name):
    df.rename(columns={"Unnamed: 0": "line_id"}, inplace=True)

    old, new = sql.Identifier(table_name + "_old"), sql.Identifier(table_name)

    cursor.execute(sql.SQL("DROP TABLE IF EXISTS {};").format(old))
    cursor.execute(sql.SQL("ALTER TABLE IF EXISTS {} RENAME TO {};").format(new, old))
    connection.commit()
    print(f"Removed old {table_name} table and renamed current to old.")

    # --- CREATE NEW TABLE
    try:
        df.to_sql(table_name, engine, chunksize=10000, if_exists=MODE, index=False)
        print(f"Populated {table_name} table.")
    except ValueError:
        print(f"Could not populate {table_name} table, as it already exists")
        exit()


def check_table_exists(table_name, cursor):
    existence_query = sql.SQL(f"SELECT EXISTS(SELECT * FROM information_schema.tables WHERE "
                              f"table_name='{table_name}');")
    return cursor.execute(existence_query)


def get_last_row_key(table_name, cursor):
    current_table = sql.Identifier(table_name)
    table_exists = check_table_exists(table_name, cursor)
    if table_exists:
        cursor.execute(sql.SQL(f"SELECT MAX(id) AS max_index FROM {current_table};"))
        return cursor.fetchone()
    else:
        return 0


def create_staging_table(df, engine, table_name):
    staging_name = table_name + "_staging"
    try:
        df.to_sql(staging_name, engine, chunksize=10000, index=False)
    except ValueError:
        sys.exit(f"Could not create staging table {staging_name}")
    logger.info(f"Created staging table {staging_name}")
    return staging_name


def modify_table(cursor, connection, engine, df, table_name, fetch_last_row=False):
    if fetch_last_row:
        last_row_num = get_last_row_key(table_name, cursor)
        df.insert(0, "id", range(last_row_num + 1, last_row_num + 1 + len(df)))

    # Create staging table
    staging_name = create_staging_table(df, engine, table_name)

    input("Press Enter to continue...")

    # Dropping staging table
    cursor.execute(sql.SQL("DROP TABLE {};").format(sql.Identifier(staging_name)))
    logger.info(f"Dropped staging table {staging_name}")

    # Appending to table
    df.to_sql(table_name, engine, if_exists="append", index=False)
    connection.commit()
    logger.info(f"Wrote to {table_name}")

    return df


def initiate_connections(credentials_dic):
    engine = create_engine("postgresql://" + credentials_dic["un"] + ":" + credentials_dic["pw"] + "@" +
                           credentials_dic["host"] + ":" + credentials_dic["port"] + "/" + credentials_dic["db_name"],
                           echo=False)
    conn = psycopg2.connect(database=credentials_dic["db_name"], user=credentials_dic["un"], password=credentials_dic["pw"],
                            host=credentials_dic["host"], port=credentials_dic["port"])
    return conn, engine


def main():
    conn, engine = initiate_connections(settings.DB_CREDENTIALS)
    cur = conn.cursor()
    print("Engines created.")

    files = sorted(glob.glob(settings.READ_PATH + "*.csv"))
    for f in files:
        table_name = f.rpartition('_')[0].rpartition('/')[2]
        print(table_name)

        parse_setting = False if table_name in ["competitors", "judges"] else ["event_start_date"]
        infer_setting = False if table_name in ["competitors", "judges"] else True

        data = pd.read_csv(f, na_values="", low_memory=False, parse_dates=parse_setting,
                           infer_datetime_format=infer_setting)
        upload_new_table(cur, conn, engine, data, table_name)

    cur.close()
    conn.close()


if __name__ == "__main__":
    main()
