# -*- coding: utf-8 -*-
import psycopg2
from psycopg2 import sql
import pandas as pd
import glob
from sqlalchemy import create_engine
import sys

READ_PATH, UN, PW = "", "", ""
H, DB, PORT = "", "", ""
MODE = "fail" #or "append"
try:
    from settings import *
except ImportError as exc:
    sys.stderr.write("Error: failed to import module ({})".format(exc))
    pass


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

def modify_table(cursor, connection, engine, df, table_name):

	# Grabbing new table and finding maximum line_id in previously existing table
    old_table, new_table = sql.Identifier(table_name + "_old"), sql.Identifier(table_name)
    cursor.execute(sql.SQL("SELECT MAX(line_id) AS max_index FROM {};".format(old_table)))
    max_result = cursor.fetchall()

	# Indexing new data frame beginning from the largest line_id of the existing table

    df.insert(0, "Index", range(max_result+1, max_result+len(df)))

	# Creating staging table

    try:
        df.to_sql(new_staging, engine, chunksize=10000, index="Index")
        print(f"Created staging table")
    except ValueError:
        print(f"Could not create staging table")
        sys.exit()

	# Dropping staging table
    cursor.execute(sql.SQL("DROP TABLE {};").format(new_staging))

	# Appending to table
    df.to_sql(table_name, engine, if_exists="append",index=False)

def main():
    conn = psycopg2.connect(database=DB, user=UN, password=PW, host=H, port=PORT)
    cur = conn.cursor()
    engine = create_engine("postgresql://" + UN + ":" + PW + "@" + H + ":" + PORT + "/" + DB, echo=True)
    print("Engines created.")

    files = sorted(glob.glob(READ_PATH + "*.csv"))
    for f in files:
        table_name = f.rpartition('_')[0].rpartition('/')[2]
        print(table_name)

        parse_setting = False if table_name in ["competitors", "judges"] else ["event_start_date"]
        infer_setting = False if table_name in ["competitors", "judges"] else True

        data = pd.read_csv(f, na_values='', low_memory=False, parse_dates=parse_setting,
                           infer_datetime_format=infer_setting)
        upload_new_table(cur, conn, engine, data, table_name)

    cur.close()
    conn.close()

main()
