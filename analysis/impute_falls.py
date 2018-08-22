#!/bin/env python

import pandas as pd
import os
import sys
from sqlalchemy import create_engine
import dash
import dash_core_components as dcc
import dash_html_components as html
import pandas as pd
import plotly.graph_objs as go


'''
Clara's working file (highly WIP) to impute which jumps were falls. Need to add GOE normalisation and dash embeds
for publication on website. 
'''

UN, PW, H, DB, PORT = "", "", "", "", ""
WRITE_PATH, KEY_COLS = "", ""

p = os.path.abspath("/Users/clarapouletty/Desktop/bias/scripts/scraper/")
if p not in sys.path:
    sys.path.append(p)

try:
    from settings import *
    from generate_summary import trimmed_mean
except ImportError as exc:
    sys.stderr.write("Error: failed to import module ({})".format(exc))
    pass

pd.set_option('display.max_columns', None)
pd.set_option('display.width', 1900)

def impute_falls(disc, cat):
    conn = create_engine("postgresql://" + UN + ":" + PW + "@" + H + ":" + PORT + "/" + DB, echo=False)

    # ---- PULL GOE AND CALCULATE TRIMMED MEAN
    goe_sql = """SELECT line_id, index, elt_id, season, event_start_date, skater_name, judge, goe FROM goe 
    WHERE discipline = %(d)s AND category = %(c)s"""
    goe_df = pd.read_sql(goe_sql, conn, params={'d': disc, 'c': cat}, index_col="line_id")

    # Check for dupes
    print("--- DUPES IN GOE TABLE:", goe_df[goe_df.duplicated(subset=["elt_id", "judge"], keep=False)])
    goe_df.drop(columns="judge", inplace=True)

    # Calculate trimmed mean
    goe_means = goe_df.fillna("None").groupby(["season", "index", "elt_id", "event_start_date", "skater_name"])\
        .apply(trimmed_mean, "goe").reset_index()
    goe_means.rename(columns={0: "trimmed_mean"}, inplace=True)
    print("---- DUPES IN TRIMMED MEANS TABLE", goe_means[goe_means.duplicated(subset="elt_id", keep=False)])

    # If all went well, there should now only be one row per elt_id
    try:
        goe_means.set_index("elt_id", drop=True, inplace=True, verify_integrity=True)
    except ValueError as exc:
        sys.stderr.write("Error: duplicate 'elt_id' index found in goe_means table ({})".format(exc))

    # ---- JOIN WITH CALLS TO GET ELEMENT NAME AND TYPE
    calls_sql = """SELECT elt_id, elt_type, elt_name FROM calls 
    WHERE discipline = %(d)s AND category = %(c)s"""

    calls_df = pd.read_sql(calls_sql, conn, params={'d': disc, 'c': cat}, index_col="elt_id")
    named_df = pd.merge(goe_means, calls_df, how="outer", left_index=True, right_index=True, indicator=True)

    # Check for merge errors
    print("REMAIN UNJOINED:",
          named_df.loc[(named_df["_merge"] != "both")].drop_duplicates())
    named_df.drop(columns="_merge", inplace=True)

    # Restrict to jumps
    named_df = named_df.loc[named_df["elt_type"] == "jump"]

    # ---- RANK EVENTS BY DATE
    named_df["event_ordinal"] = named_df.event_start_date.rank(method="dense").astype(int)

    # --- GUESS WHICH JUMPS WERE GIVEN THE FALL DEDUCTIONS
    # a. Pull deductions table and isolate programmes with falls
    falls_sql = """SELECT line_id, index, ded_type, ded_points FROM deductions
    WHERE discipline = %(d)s AND category = %(c)s AND ded_type = %(f)s"""

    falls_df = pd.read_sql(falls_sql, conn, params={'d': disc, 'c': cat, 'f': "falls"}, index_col="line_id")
    falls_df["no_falls"] = falls_df["ded_points"].astype("int") * -1
    falls_df.set_index("index", drop=True, inplace=True, verify_integrity=True)
    named_df["trimmed_mean"] = pd.to_numeric(named_df["trimmed_mean"])

    def return_n_smallest(df):
        if df.name in falls_df.index:
            return df.nsmallest(falls_df.loc[df.name, "no_falls"], "trimmed_mean")

    falls = named_df.groupby("index").apply(return_n_smallest)
    falls.to_csv(WRITE_PATH + "falls_post_apply" + "_" + DATE + VER + ".csv", mode="w", encoding="utf-8", header=True)
    return named_df, falls


def main():
    all_jumps, falls = impute_falls("Men", "Sr")
    falls.reset_index(level="index", drop=True, inplace=True)

    falls.to_csv(WRITE_PATH + "falls_after_return" + "_" + DATE + VER + ".csv", mode="w", encoding="utf-8", header=True)
    all_jumps.to_csv(WRITE_PATH + "all_jumps_after_return" + "_" + DATE + VER + ".csv", mode="w", encoding="utf-8", header=True)

    print("--- ALL JUMPS", all_jumps.head(5))
    print("--- FALLS", falls.head(5))

    quads = all_jumps.loc[all_jumps["elt_name"].str.contains("4")]

    quad_falls = falls.loc[falls["elt_name"].str.contains("4")]
    quad_falls["fall_flag"] = 1
    count_falls = quad_falls.groupby(["season", "event_ordinal"])["elt_name"].count()
    count_all = quads.groupby(["season", "event_ordinal"])["elt_name"].count()
    print(count_all.head(3))

    quad_falls.drop(columns=["season", "index", "event_start_date", "trimmed_mean", "elt_type", "elt_name",
                             "skater_name", "event_ordinal", "trimmed_mean"], inplace=True)
    merged = pd.merge(quads, quad_falls, how="outer", left_index=True, right_index=True, indicator=False)
    merged.replace({"Morisi KVITELASHVILI": "Moris KVITELASHVILI", "Evgeny PLYUSHCHENKO": "Evgeni PLUSHENKO"}, inplace=True)

    col_list = ["season", "index", "event_start_date", "trimmed_mean", "elt_type", "elt_name", "skater_name", "event_ordinal"]
    medians = merged.reset_index().groupby("skater_name").agg({"trimmed_mean": ["max", "min", "median", "count"]})

    sub_merged = merged[merged.groupby(merged.skater_name).transform('count') > 20]
    boxes = sub_merged.reset_index().boxplot(column="skater_name", by="trimmed_mean", ax=None, fontsize=None, rot=0,
                                         grid=True, figsize=None, layout=(1,41), return_type=None)
    print(boxes)

    medians.to_csv(WRITE_PATH + "medians" + "_" + DATE + VER + ".csv", mode="w", encoding="utf-8", header=True)


    merged.to_csv(WRITE_PATH + "falls_table" + "_" + DATE + VER + ".csv", mode="w", encoding="utf-8", header=True)
    count_falls.to_csv(WRITE_PATH + "count_falls" + "_" + DATE + VER + ".csv", mode="w", encoding="utf-8", header=True)
    count_all.to_csv(WRITE_PATH + "count_all" + "_" + DATE + VER + ".csv", mode="w", encoding="utf-8", header=True)


if __name__ == "__main__":
    main()
