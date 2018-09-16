# -*- coding: utf-8 -*-
import psycopg2
from psycopg2 import sql
import pandas as pd
import glob
from sqlalchemy import create_engine
import sys

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


def get_last_row_key(table_name, cursor):
    current_table = sql.Identifier(table_name)

    existence_query = sql.SQL(f"SELECT EXISTS(SELECT * FROM information_schema.tables WHERE "
                              f"table_name={current_table});")
    table_exists = cursor.execute(existence_query)

    if table_exists:
        cursor.execute(sql.SQL(f"SELECT MAX(id) AS max_index FROM {current_table};"))
        return cursor.fetchone()
    else:
        return 0


def create_staging_table(df, engine, table_name):
    staging_name = table_name + "_staging"
    try:
        df.to_sql(staging_name, engine, chunksize=10000, index="incr_line_id")
    except ValueError:
        sys.exit(f"Could not create staging table {staging_name}")
    print(f"Created staging table {staging_name}")
    return staging_name


def modify_table(cursor, connection, engine, df, table_name, last_row_num=None):
    if not last_row_num:
        last_row_num = get_last_row_key(table_name, cursor)

    # Create row counter column for new data frame beginning from the largest line_id of the existing table
    df.insert(0, "id", range(last_row_num + 1, last_row_num + len(df)))

    # Create staging table
    staging_name = create_staging_table(df, engine, table_name)

    # Dropping staging table
    staging_table = sql.Identifier(staging_name)
    cursor.execute(sql.SQL(f"DROP TABLE {staging_table};"))

    # Appending to table
    df.to_sql(table_name, engine, if_exists="append", index=False)
    connection.commit()

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
