# -*- coding: utf-8 -*-
# #!/bin/env python


import glob
import pandas as pd
from openpyxl import load_workbook
import numpy as np
from datetime import datetime
import unicodedata
from sqlalchemy import create_engine

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
except ImportError as exc:
    sys.stderr.write("Error: failed to import module ({})".format(exc))
    sys.exit(1)

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


def scrape_sheet(df, segment):
    protocol_coords = find_protocol_coordinates(df)
    logger.debug(f"Protocol coodinates are {protocol_coords}")

    sheet_protocols = []
    for c in protocol_coords:
        prot = protocol.CONSTRUCTOR_DIC[segment.discipline]["prot"](df, c, segment)
        for i in prot.row_range:
            for j in prot.col_range:
                if "Skating Skills" in str(df.iloc[i, j]):
                    prot.parse_pcs_table(df, i, j)
                elif "Elements" in str(df.iloc[i, j]):
                    prot.parse_tes_table(df, i, j)
                elif "Deductions" in str(df.iloc[i, j]) and j < 4:
                    prot.parse_deductions(df, i, j, segment)
        sheet_protocols.append(prot)
    return sheet_protocols


def write_protocols_to_staging(engine, protocol_list):
    for protocol in protocol_list:


        df.to_sql(table_name, engine, chunksize=10000, if_exists=MODE, index=False)

    return True

def write_protocols_to_csv(protocol_list, write_path)




def transform_and_load(read_path, write_path, counter, db_credentials):
    done_dir_path = os.path.join(read_path, "done")
    if not os.path.exists(done_dir_path):
        os.makedirs(done_dir_path)

    sheet_count, protocol_list = 0, []
    engine = create_engine("postgresql://" + db_credentials["un"] + ":" + db_credentials["pw"] + "@" +
                           db_credentials["host"] + ":" + db_credentials["port"] + "/" + db_credentials["db_name"],
                           echo=False)

    # ---- If tables don't exist yet, set up schema



    # ---- Iteratively read through converted .xlsx and populate tables
    files = sorted(glob.glob(read_path + '*.xlsx'))
    for f in files:
        filename = f.rpartition("/")[2]
        basename = filename.rpartition(".")[0]

        logger.info(f"Attempting to read {basename}")

        disc = event.parse_discipline(filename)
        seg = protocol.CONSTRUCTOR_DIC[disc]["seg_obj"](basename, disc)

        wb = load_workbook(f)
        for sheet in wb.sheetnames:
            raw_df = pd.DataFrame(wb[sheet].values)
            protocol_list.append(scrape_sheet(raw_df, seg))
            sheet_count += 1

            if sheet_count % counter == 0:
                write_protocols_to_staging(engine, protocol_list)
                write_protocols_to_csv(protocol_list, write_path)
                protocol_list = []

        current_path = os.path.join(read_path, filename)
        done_path = os.path.join(done_dir_path, filename)
        os.rename(current_path, done_path)




if __name__ == "__main__":

    # # FOR YOGEETA AND YOGEETA ONLY
    # try:
    #     assert len(sys.argv) in [3,4]
    # except AssertionError:
    #     sys.exit("Please pass in the path to the xlsx dir, the path to which the csv backup should be written, and
    #               (optionally) an integer counter (for frequency at which results get written to the staging table,
    #               default is every 10 sheets), in that order")
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


    transform_and_load(read_path, write_path, counter, db_credentials)
