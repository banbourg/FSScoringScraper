#!/bin/env python

import psycopg2
import pandas as pd
from sqlalchemy import create_engine
import glob
import os
import sys

# Ensure python can find modules for import
p = os.path.abspath("/Users/clarapouletty/Desktop/bias/scripts/scraper/")
if p not in sys.path:
    sys.path.append(p)

READ_PATH, UN, PW = "", "", ""
H, DB, PORT = "", "", ""
MODE = "fail" #or "append"

# Load global variables and functions
try:
    from settings import *
    from one_off_date_join import join_dates
    from db_builder import upload_new_table
except ImportError as exc:
    sys.stderr.write("Error: failed to import module ({})".format(exc))
    pass

pd.set_option('display.max_columns', None)


def add_missing_deductions():

    # --- FORMAT DATA FOR UPLOAD
    # a. Melt the ded_type columns back into stacked format
    df = pd.read_csv(READ_PATH + "missing_deduction_info_singles.csv", index_col=False, encoding="macroman")
    df.drop(labels=["allocated to", "ded_type", "total_ded_points"], axis=1, inplace=True)
    df = df.melt(id_vars=["index", "discipline", "category", "season", "event", "sub_event", "skater_name", "segment"],
                 var_name="ded_type", value_name="ded_points")
    df = df[df.ded_points.notnull()].reset_index(drop=True)

    # b. Join comp dates
    dates = pd.read_csv(DATE_PATH, index_col=False)
    missing_ded = join_dates(df.reset_index(), dates)

    # --- APPEND TO DEDUCTIONS TABLE AND WRITE TO CSV (RDS CHARGES FOR BACKUPS, NEED TO INVESTIGATE)
    file = sorted(glob.glob(READ_PATH + "deductions_*.csv"))

    incomplete_df = pd.read_csv(file[0], index_col=0, na_values="", low_memory=False, parse_dates=["event_start_date"],
                                infer_datetime_format=True, encoding="utf-8")

    filtered = incomplete_df.loc[incomplete_df["ded_type"] != "unknown"]

    complete_df = filtered.append(missing_ded, ignore_index=True)
    complete_df.to_csv(WRITE_PATH + "complete_deductions" + "_" + DATE + VER + ".csv", index_label="line_id", mode="w",
                       encoding="utf-8", header=True)

    # --- UPLOAD NEW COMPLETE DEDUCTIONS TABLE
    conn = psycopg2.connect(database=DB, user=UN, password=PW, host=H, port=PORT)
    cur = conn.cursor()
    engine = create_engine("postgresql://" + UN + ":" + PW + "@" + H + ":" + PORT + "/" + DB, echo=True)
    print("Engines created.")

    upload_new_table(cur, conn, engine, complete_df, "deductions")

    df1 = incomplete_df
    df1["source"] = "incomplete"
    df2 = complete_df
    df_conc = pd.concat([df1, df2])
    df_conc.drop_duplicates(subset=["index"], keep=False, inplace=True)
    print(df_conc)


def main():
    add_missing_deductions()

if __name__ == "__main__":
    main()