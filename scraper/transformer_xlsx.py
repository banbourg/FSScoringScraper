# -*- coding: utf-8 -*-
# #!/bin/env python


import glob
import pandas as pd
from openpyxl import load_workbook
import numpy as np
from datetime import datetime
import unicodedata

import os
import re
import sys
import logging

logging.basicConfig(filename="transformer.log",
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
    for j in df.columns:
        for i in df.index:
            if "Name" in str(df.iloc[i, j]):
                protocol_starts.append(i)
            if "Deductions" in str(df.iloc[i, j]) and j < 4:
                protocol_ends.append(i)
    return list(zip(protocol_starts, protocol_ends))


def scrape_sheet(df, segment):
    protocol_coords = find_protocol_coordinates(df)
    logger.debug(f"Protocol coodinates are {protocol_coords}")
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


def main():
    files = sorted(glob.glob(settings.READ_PATH + '*.xlsx'))
    for f in files:
        filename = f.rpartition("/")[2].rpartition(".")[0]
        logger.info(f"Attempting to read {filename}")

        # Initialise SegmentProtocols object
        disc = event.parse_discipline(filename)
        seg = protocol.CONSTRUCTOR_DIC[disc]["seg_obj"](filename, disc)

        wb = load_workbook(f)
        for sheet in wb.sheetnames:
            raw_df = pd.DataFrame(wb[sheet].values)
            scrape_sheet(raw_df, seg)


if __name__ == "__main__":
    main()
