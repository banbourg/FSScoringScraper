# -*- coding: utf-8 -*-
# #!/bin/env python


import glob
import pandas as pd
from openpyxl import load_workbook
import numpy as np
from datetime import datetime

import os
import re
import sys
import logging

logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)-5s - %(message)s",
                    level=logging.DEBUG, datefmt='%Y-%m-%d %H:%M:%S')

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

#inv_map = {v: k for k, v in my_map.items()}


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
                    prot.parse_deductions(df, i, j)


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


# def main_2():
# #
#             for i in raw_df.index:
#                 for j in raw_df.columns:
#
#
#
#                         segment_scores_list.append(single_scores_df)
#                         segment_goe_list.append(single_goe_df)
#                         segment_calls_list.append(single_calls_df)
#
#         segment_scraped_totals_df = pd.DataFrame(segment_scraped_totals_list,
#                                                  columns=['index', 'discipline', 'category', 'season', 'event', 'sub_event',
#                                                           'skater_name', 'segment', 'scraped_pcs', 'scraped_tes',
#                                                           'scraped_total'])
#
#         segment_competitors_df = pd.DataFrame(segment_competitors_list,
#                                               columns=['season', 'disc', 'category', 'name', 'country'])
#
#         segment_deductions_df = pd.DataFrame(segment_deductions_list,
#                                              columns=['index', 'discipline', 'category', 'season', 'event', 'sub_event',
#                                                       'skater_name', 'segment', 'ded_type', 'ded_points'])
#
#         segment_scores_df = pd.concat(segment_scores_list)
#         segment_pcs_df = pd.concat(segment_pcs_list).stack()
#         segment_pcs_df.name = 'pcs'
#         segment_goe_df = pd.concat(segment_goe_list).stack()
#         segment_goe_df.name = 'goe'
#         segment_calls_df = pd.concat(segment_calls_list)
#
#         all_scraped_totals_list.append(segment_scraped_totals_df)
#         all_scores_list.append(segment_scores_df)
#         all_pcs_list.append(segment_pcs_df)
#         all_goe_list.append(segment_goe_df)
#         all_calls_list.append(segment_calls_df)
#         all_deductions_list.append(segment_deductions_df)
#         all_competitors_list.append(segment_competitors_df)
#         print('        loaded full segment df into overall summary list')
#
#     all_scraped_totals_df = pd.concat(all_scraped_totals_list)
#     all_scores_df = pd.concat(all_scores_list)
#     print('scores df concatenated')
#     all_pcs_df = pd.concat(all_pcs_list)
#     all_pcs_df = all_pcs_df.reset_index()
#     print('pcs df concatenated')
#     all_goe_df = pd.concat(all_goe_list)
#     all_goe_df = all_goe_df.reset_index()
#     print('goe df concatenated')
#     all_calls_df = pd.concat(all_calls_list)
#     print('calls df concatenated')
#     all_deductions_df = pd.concat(all_deductions_list)
#     all_deductions_df = all_deductions_df.reset_index(drop=True)
#     print('deductions df concatenated')
#     all_competitors_df = pd.concat(all_competitors_list)
#     all_competitors_df.drop_duplicates(subset=['category', 'name', 'country'], keep='last', inplace=True)
#     all_competitors_df = all_competitors_df.reset_index(drop=True)
#     print('competitors df concatenated')
#
#     header_setting = True
#     all_scraped_totals_df.to_csv(WRITE_PATH + 'scraped_totals_' + DATE + VER + '.csv', mode='a', encoding='utf-8',
#                                  header=header_setting)
#     all_scores_df.to_csv(WRITE_PATH + 'elt_scores_' + DATE + VER + '.csv', mode='a', encoding='utf-8',
#                          header=header_setting)
#     all_pcs_df.to_csv(WRITE_PATH + 'pcs_' + DATE + VER + '.csv', mode='a', encoding='utf-8', header=header_setting)
#     all_goe_df.to_csv(WRITE_PATH + 'goe_' + DATE + VER + '.csv', mode='a', encoding='utf-8', header=header_setting)
#     all_calls_df.to_csv(WRITE_PATH + 'calls_' + DATE + VER + '.csv', mode='a', encoding='utf-8', header=header_setting)
#     all_deductions_df.to_csv(WRITE_PATH + 'deductions_' + DATE + VER + '.csv', mode='a', encoding='utf-8',
#                              header=header_setting)
#     all_competitors_df.to_csv(WRITE_PATH + 'competitors_' + DATE + VER + '.csv', mode='a', encoding='utf-8',
#                               header=header_setting)
#
#     # WHERE DEDUCTIONS ARE MISSING (BC THEY DISAPPEARED IN THE CONVERSION FROM PDF TO XLS), ADD THE TOTALS AS
#     # 'UNKNOWN' PENDING MANUAL CORRECTION
#     all_scraped_totals_df['derived_ded'] = all_scraped_totals_df.apply(lambda x: \
#             int(round(x['scraped_total'] - x['scraped_tes'] - x['scraped_pcs'], 0)), axis = 1)
#     all_scraped_totals_df.drop(labels=['scraped_pcs', 'scraped_tes', 'scraped_total'], axis=1, inplace=True)
#     print(all_scraped_totals_df)
#     ded_totals = all_deductions_df.fillna('None').groupby(key_cols)['ded_points'].sum().reset_index()
#     print(ded_totals)
#     ded_comparison = all_scraped_totals_df.join(ded_totals.set_index(key_cols), on=key_cols, how='left', lsuffix='_pcs',
#                             rsuffix='_tes').fillna(0)
#     ded_comparison['ded_type'] = 'unknown'
#     ded_comparison.to_csv(WRITE_PATH + 'ded_comp_' + DATE + VER + '.csv', mode='a', encoding='utf-8',
#                           header=header_setting)
#     ded_comparison['ded_diff'] = ded_comparison.apply(lambda x: int(round(x['derived_ded'] - x['ded_points'], 0)), axis=1)
#     ded_comparison.drop(labels=['derived_ded', 'ded_points'], axis=1, inplace=True)
#     rows_to_append = ded_comparison.loc[ded_comparison['ded_diff'] != 0]
#     rows_to_append.to_csv(WRITE_PATH + 'deductions_' + DATE + VER + '.csv', mode='a', encoding='utf-8',
#                              header=False)


if __name__ == "__main__":
    main()
