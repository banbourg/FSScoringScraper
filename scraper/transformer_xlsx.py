# -*- coding: utf-8 -*-
# #!/bin/env python


import glob
import pandas as pd
from openpyxl import load_workbook
from datetime import datetime

import os
import re
import sys
import logging

logging.basicConfig(filename="transformer" + datetime.today().strftime("%Y-%m-%d_%H-%M-%S") + ".log",
                    format="%(asctime)s - %(name)s - %(levelname)-5s - %(message)s",
                    level=logging.DEBUG,
                    datefmt="%Y-%m-%d %H:%M:%S")

logger = logging.getLogger(__name__)

# Ensure python can find modules for import
p = os.path.abspath("../classes/")
if p not in sys.path:
    sys.path.append(p)

try:
    import settings
    import event
    import person
    import protocol
    import db_builder
except ImportError as exc:
    sys.exit(f"Error: failed to import module ({exc})")

ABBREV_DIC = {'gpjpn': 'NHK', 'gpfra': 'TDF', 'gpcan': 'SC', 'gprus': 'COR', 'gpusa': 'SA', 'gpchn': 'COC',
             'gpf': 'GPF', 'wc': 'WC', 'fc': '4CC', 'owg': 'OWG', 'wtt': 'WTT', 'sc': 'SC', 'ec': 'EC', 'sa': 'SA',
             'jgpfra': 'JGPFRA', 'nhk': 'NHK'}
calls = ['!', 'e', '<', '<<', '*', '+REP', 'V1', 'V2', 'x', 'X', 'V']

key_cols = ['discipline', 'category', 'season', 'event', 'sub_event', 'skater_name', 'segment']


# --------------------------------------- REGEX PATTERNS ---------------------------------------
combo_pattern = re.compile(r"\+[0-9]")


def reorder_cols(df, col_to_move, new_pos):
    cols = df.columns.tolist()
    cols.insert(new_pos, cols.pop(cols.index(col_to_move)))
    return df[cols]


def find_protocol_coordinates(df):
    protocol_starts, protocol_ends = [], []
    for i in df.index:
        for j in range(0,6):
            if "Name" in str(df.iloc[i, j]):
                protocol_starts.append(i)
            if "Deductions" in str(df.iloc[i, j]) and j < 4:
                protocol_ends.append(i)
    return list(zip(protocol_starts, protocol_ends))


def scrape_sheet(df, segment, last_row_dic, skater_list, cur):
    protocol_coords = find_protocol_coordinates(df)
    logger.debug(f"Protocol coordinates are {protocol_coords}")

    for c in protocol_coords:
        prot = protocol.Protocol(df=df, protocol_coordinates=c, segment=segment, last_row_dic=last_row_dic,
                                 skater_list=skater_list, cursor=cur)

        for i in prot.row_range:
            for j in prot.col_range:
                if "Skating Skills" in str(df.iloc[i, j]):
                    prot.parse_pcs_table(df, i, j)
                elif "Elements" in str(df.iloc[i, j]):
                    prot.parse_tes_table(df, i, j, last_row_dic)
                elif "Deductions" in str(df.iloc[i, j]) and j < 4:
                    prot.parse_deductions(df, i, j, segment)
        segment.protocol_list.append(prot)


def convert_to_dfs(segment_list):
    all_dics, all_dfs, pcs_list = {}, {}, []
    for s in segment_list:
        all_dics["segments"].append(s.get_segment_dic())

        for p in s.protocol_list:
            all_dics["competitors"].append(vars(p.skater))

            all_dics["skates"].append(p.get_skate_dic(segment=s))

            pcs_list.append(p.get_pcs_df(segment=s))

            for e in p.elements:
                all_dics["elements"].append(vars(e))


    for key in all_dics:
        all_dfs = pd.DataFrame(all_dics[key])

    all_dfs["pcs"] = pd.concat(pcs_list)

    return all_dfs


def transform_and_load(read_path, write_path, naming_schema, counter, db_credentials):
    done_dir_path = os.path.join(read_path, "done")
    if not os.path.exists(done_dir_path):
        os.makedirs(done_dir_path)

    # --- 1. Initiate connections and fetch ids
    conn, engine = db_builder.initiate_connections(db_credentials)
    cur = conn.cursor()

    # --- 2. Get max table rows for append
    ids, skater_list = {}, []
    for x in ["deductions", "pcs", "goe", "elements", "segments", "competitors", "officials", "panels", "skates"]:
        name = x + naming_schema
        ids[x] = db_builder.get_last_row_key(table_name=name, cursor=cur) + 1

    # --- 3. Iteratively read through converted .xlsx and populate tables
    segment_list = []
    file_count = 0

    files = sorted(glob.glob(read_path + '*.xlsx'))

    for f in files:
        filename = f.rpartition("/")[2]
        basename = filename.rpartition(".")[0]
        logger.info(f"Attempting to read {basename}")

        file_count += 1

        disc = event.parse_discipline(filename)
        seg = protocol.SegmentProtocols(basename, disc, ids)
        ids["segments"] += 1
        segment_list.append(seg.get_segment_dic())

        wb = load_workbook(f)
        for sheet in wb.sheetnames:
            raw_df = pd.DataFrame(wb[sheet].values)
            scrape_sheet(df=raw_df, segment=seg, last_row_dic=ids, skater_list=skater_list, cur=cur)
            segment_list.append(seg)

        if file_count % counter == 0:
            convert_to_dics(segment_list)
            segments_df = write_to_staging(pd.DataFrame(segment_list), "segments" + naming_schema, cur, conn, engine)
            write_to_csv(segments_df, "segments" + naming_schema, write_path)

            df_dic = convert_to_dfs(seg)
            for key in df_dic:
                write_to_staging(df_dic[key], key, cur, conn, engine)
                write_to_csv(df_dic[key], key, write_path)
        #
        # current_path = os.path.join(read_path, filename)
        # done_path = os.path.join(done_dir_path, filename)
        # os.rename(current_path, done_path)




# def write_to_staging(df, table_name, cursor, connection, engine):
#     keyed_df = db_builder.modify_table(cursor=cursor, connection=connection, engine=engine, df=df,
#                                        table_name=table_name)
#     return keyed_df
#
#
# def write_to_csv(df, table_name, write_path):
#     file_path = os.path.join(write_path, table_name + ".csv")
#     if os.path.isfile(file_path):
#         include_header = False
#     else:
#         include_header = True
#     df.to_csv(header=include_header, index=False, mode="a", date_format="%y-%m-%d")



def main():
    # # FOR YOGEETA AND YOGEETA ONLY
    # try:
    #     assert len(sys.argv) in [3,4]
    # except AssertionError:
    #     sys.exit("Please pass in the path to the xlsx dir, the path to which the csv backup should be written, and
    #               (optionally) an integer counter (for frequency at which results get written to the staging table,
    #               default is every 10 files), in that order")
    #
    # read_path = sys.argv[1]
    # write_path = sys.argv[2]
    # try:
    #     counter = int(sys.argv[1])
    # except (IndexError, TypeError):
    #     counter = 10

    db_credentials = settings.DB_CREDENTIALS()
    read_path = settings.READ_PATH
    write_path = settings.WRITE_PATH
    counter = 10
    naming_schema = "_new"

    transform_and_load(read_path, write_path, naming_schema, counter, db_credentials)


if __name__ == "__main__":
    main()