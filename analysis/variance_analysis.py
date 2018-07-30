#!/bin/env python

import pandas as pd
from sqlalchemy import create_engine

UN, PW, H, DB, PORT = "", "", "", "", ""
try:
    from settings import *
except ImportError:
    pass


def return_last_name(row):
    exploded_name = row["skater_name"].split(' ')
    last_name_list = []
    for word in exploded_name:
        if len(word) > 1 and (str(word[1]).isupper() or str(word[:2]) == 'Mc'):
            last_name_list.append(word)
    last_name = ' '.join(last_name_list)
    return last_name.title()


def return_formatted_calls(row):
    calls_dic = {"rep": "+REP", "severe_edge": "e", "sev_edge": "e", "unclear_edge": "!", "unc_edge": "!", "ur": "<",
                 "down": "<<", "downgrade": "<<"}
    jumps_dic = {}
    if row["elt_type"] == 'jump':
        # For combos, run per jump, in case detail exists
        bits = []
        if row["combo_flag"] == 1:
            for i in range(1, 5):
                start, end = "j" + str(i) + "_sev_edge", "j" + str(i) + "_down"
                keys = calls_helper(row, start, end, "left")
                bits.extend(([row["jump_" + i]] + [calls_dic[x] for x in keys]))
        else:
            keys = calls_helper(row, "ur_flag", "unclear_edge_flag", "right")
            bits.extend(([row["elt_name"]] + [calls_dic[x] for x in keys]))
        name = ''.join(bits)
    else:
        name = row["elt_name"]
        if row["no_positions"] and row["no_positions"] != "NA":
            name = name + str(row["no_positions"]) + "p"
        name += row["level"]
        if row["failed_spin"] == 1:
            name += "V"
            if row["missing_reqs"]:
                name += str(row["missing_reqs"])
    if row["invalid"] == 1:
        name += "*"
    return name


def calls_helper(row, start, end, side):
    sub = row.loc[start:end]
    bools = sub.apply(lambda x: x == 1)
    call_list = bools.index[bools == True].tolist()
    if side == "left":
        keys = [x.partition("_")[2] for x in call_list]
    elif side == "right":
        keys = [x.rpartition("_")[0] for x in call_list]
    else:
        raise ValueError("'side' argument must be either 'left' or 'right' (see script)")
    return keys


def pull_variant_elts(disc, cat, season, event, sub_event):
    conn = create_engine("postgresql://" + UN + ":" + PW + "@" + H + ":" + PORT + "/" + DB, echo=False)

    # ---- PULL AND PIVOT OUT GOE
    goe_sql = """SELECT * FROM goe 
    WHERE discipline = %(d)s AND category = %(c)s"""

    goe_df = pd.read_sql(goe_sql, conn, params={'d': disc, 'c': cat}, index_col="line_id")
    goe_pivot = goe_df.pivot(index="elt_id", columns="judge", values="goe")
    goe_pivot["elt_var"] = goe_pivot.var(axis=1, skipna=True)

    # --- PULL ELEMENT DETAILS AND SCORES
    elt_sql = """SELECT C.*, E.elt_bv, E.elt_sov_goe, E.elt_total 
    FROM calls C
    LEFT JOIN elt_scores E
      ON C.elt_id = E.elt_id
    WHERE C.discipline = %(d)s AND C.category = %(c)s"""

    elt_df = pd.read_sql(elt_sql, conn, params={'d': disc, 'c': cat}, index_col="elt_id")

    # --- JOIN WITH GOE DATA
    merge_df = pd.merge(goe_pivot, elt_df, how="outer", on='elt_id', sort=False, suffixes=("_g", "_e"), indicator=True)

    # --- GET AVERAGE VARIANCE FOR ELTS IN THIS DISC/CATEGORY (UNTRIMMED!)
    avg_var = merge_df["elt_var"].mean()

    # --- PULL TOP 3 FOR EVENT AND PREP OUTPUTS FOR PASTING INTO TEMPLATE
    event_df = merge_df.loc[(merge_df["season"] == season) & (merge_df["event"] == event)]
    if sub_event:
        event_df = event_df.loc[(event_df["sub_event"] == sub_event)]
    else:
        event_df = event_df.loc[(event_df["sub_event"].isnull())]
    top_3 = event_df.nlargest(3, "elt_var")

    # Frequency of each score
    for i in range(-5,6):
        top_3["fq_"+str(i)] = (top_3[top_3.columns[1:13]] == i).sum(1)

    # Multiple over average variance
    top_3["mult"] = round((top_3["elt_var"] - avg_var) / avg_var, 2)

    # Build bubble chart
    fq = top_3.loc[:, "fq_-5":"fq_5"].transpose()
    fq = fq.values.flatten(order='F').tolist()
    x_range = [1 for x in range(0,34)]
    y_range = list(range(-5,6)) + list(range(-5,6)) + list(range(-5,6))
    bubble_chart = pd.DataFrame.from_records(zip(x_range, y_range, fq),columns=['X','Y','Size'])
    print(bubble_chart)

    # Build table to go below bubble chart
    top_3["temp"] = top_3.apply(return_formatted_calls, axis=1)
    top_3["last_name"] = top_3.apply(return_last_name, axis=1)
    top_3["label_1"] = top_3["last_name"] + "'s " + top_3["temp"] + " (" + top_3["segment"] + top_3["elt_no"].map(str) \
                       + ")"
    top_3["label_2"] = round(top_3["elt_var"],2).map(str) + " (" + round(top_3["mult"],1).map(str) + "x)"

    tbl_row_1 = top_3.loc[:, "label_1"].transpose()
    print(list(tbl_row_1.values.flatten(order='F')))
    tbl_row_2 = top_3.loc[:, "label_2"].transpose()
    print(list(tbl_row_2.values.flatten(order='F')))


def main():
    pull_variant_elts("Ladies", "Sr", "SB2012", "NHK", None)


main()