#!/bin/env python

import os
import glob
import re
import pandas as pd
from openpyxl import load_workbook
import numpy as np
from datetime import datetime
import sys

READ_PATH, WRITE_PATH, DATE, VER = "", "", "", ""
try:
    from settings import *
except ImportError as exc:
    sys.stderr.write("Error: failed to import module ({})".format(exc))
    pass

event_dic = {'gpjpn': 'NHK', 'gpfra': 'TDF', 'gpcan': 'SC', 'gprus': 'COR', 'gpusa': 'SA', 'gpchn': 'COC',
             'gpf': 'GPF', 'wc': 'WC', 'fc': '4CC', 'owg': 'OWG', 'wtt': 'WTT', 'sc': 'SC', 'ec': 'EC', 'sa': 'SA',
             'jgpfra': 'JGPFRA', 'nhk': 'NHK'}
calls = ['!', 'e', '<', '<<', '*', '+REP', 'V1', 'V2', 'x', 'X', 'V']
ded_types = ['falls', 'time violation', 'costume failure', 'late start', 'music violation',
             'interruption in excess', 'costume & prop violation', 'illegal element/movement']
key_cols = ['discipline', 'category', 'season', 'event', 'sub_event', 'skater_name', 'segment']


def return_isu_abbrev(s):
    temp = [_f for _f in re.split(r'(\d+)', s) if _f]
    return temp[0]


def is_nan(x):
    return x is np.nan or x != x


def return_row_list(i, k_min, df, a_list):
    for k in range(k_min, len(df.columns)):
        if df.iloc[i, k] is not None and not is_nan(df.iloc[i, k]):
            a_list.append(df.iloc[i, k])
    return a_list


def clean_elt_name(cur_string, replace_list):
    for cur_word in replace_list:
        cur_string = cur_string.replace(cur_word, '')
    return cur_string


def reorder_cols(df, col_to_move, new_pos):
    cols = df.columns.tolist()
    cols.insert(new_pos, cols.pop(cols.index(col_to_move)))
    return df[cols]


def add_segment_identifiers(df, identifiers, segment_competitors_list, segment_exploded_names):
    competitor_short_name = segment_exploded_names[-1][1] + segment_exploded_names[-1][0]
    #counldn't use first name initials bc of asado mao and asada mai...
    df['index'] = identifiers[2] + identifiers[3] + identifiers[4] + identifiers[1] + identifiers[0] + \
        competitor_short_name + identifiers[5]
    df.set_index('index', append=True, inplace=True)
    df['discipline'] = identifiers[0]
    df.set_index('discipline', append=True, inplace=True)
    df['category'] = identifiers[1]
    df.set_index('category', append=True, inplace=True)
    df['season'] = identifiers[2]
    df.set_index('season', append=True, inplace=True)
    df['event'] = identifiers[3]
    df.set_index('event', append=True, inplace=True)
    df['sub_event'] = identifiers[4]
    df.set_index('sub_event', append=True, inplace=True)
    df['skater_name'] = segment_competitors_list[-1][3]
    df.set_index('skater_name', append=True, inplace=True)
    df['segment'] = identifiers[5]
    df.set_index('segment', append=True, inplace=True)
    df['event_start_date'] = identifiers[6]
    df.set_index('event_start_date', append=True, inplace=True)


def clean_ded_row(row):
    # Stringify and remove number of falls in brackets, split
    row = [re.sub(r'\(\d+\)', '', str(r)) for r in row]
    ded_words, ded_digits = [], []
    for r in row:
        ded_words.extend(re.findall(r'[A-Z][a-z]+/* *&* *[A-Z]*[a-z]* *[a-z]*', r))
        ded_digits.extend(re.findall(r'[-]*[0-9]+.*[0-9]*', r))

    ded_words = [x.lower() for x in ded_words]

    # print 'ded words after regex', ded_words
    # print 'ded_digits after regewx', ded_digits

    if len(ded_words) > 1:
        # If deduction names were split across multiple cells in spreadsheet, join them back together
        for x in range(len(ded_words) - 1, 0, -1):
            if ded_words[x] == 'total':
                del ded_words[x]
            s = slice(x - 1, x + 1)
            word = ''.join(ded_words[s])
            match = [full_ded for full_ded in ded_types if word in full_ded]
            assert len(match) <= 1

            if len(match) == 1:
                ded_words[s] = [''.join(ded_words[s])]

        # Remove other random numbers that might have ended up in the row, ensure all numbers negative
        ded_digits = [x.replace('.00', '').replace('.0', '') for x in ded_digits]
        ded_digits = [x if (float(x) - int(float(x))) < 0.001 else None for x in ded_digits]
        ded_digits = [_f for _f in ded_digits if _f]
        ded_digits = [-1 * int(x) if int(x) > 0 else int(x) for x in ded_digits]

        ded_words = [re.sub(r'fall$', 'falls', x) for x in ded_words]
        ded_words = [x.replace('late start', 'time violation') for x in ded_words]

    # print 'ded words, ded digits at end of function', ded_words, ded_digits
    return {'ded_words': ded_words, 'ded_digits': ded_digits}


def main():
    combo_regex = re.compile(r'\+[0-9]')

#    files = sorted(glob.glob(READ_PATH + '*.xlsx'))
    files = sorted(glob.glob(READ_PATH + '*.pdf'))

    all_scraped_totals_list = []
    all_scores_list = []
    all_pcs_list = []
    all_goe_list = []
    all_calls_list = []
    all_deductions_list = []
    all_competitors_list = []

    for f in files:
        filename = f[55:]  # 43 # 48
        print(filename)

        # 1. DERIVE YEAR AND EVENT START DATE
        event_start_date = datetime.strptime(filename.partition("_")[0], "%y%m%d").date()
        event_year = event_start_date.year

        # 2. DERIVE EVENT & SUB EVENT
        event = event_dic[return_isu_abbrev(filename.partition("_")[2].lower())]
        sub_event_dic = {"Team": "team", "Preliminary": "qual", "QA": "qual_1", "QB": "qual_2"}
        try:
            sub_event = [sub_event_dic[se] for se in sub_event_dic if se in filename][0]
        except IndexError:
            sub_event = ""

        # 3. DERIVE SEASON
        if event in ["4CC", "OWG", "WC", "WTT", "EC"]:
            season = "SB" + str(event_year - 1)
        else:
            season = "SB" + str(event_year)

        # 4. TAG SEGMENT
        segment_dic = {"SP": "SP", "FS": "FS", "SD": "SD", "FP": "FS", "FD": "FD", "OD": "OD", "CD": "CD", "RD": "RD",
                       "QA": "FS", "QB": "FS"}
        segment = [segment_dic[s] for s in segment_dic if s in filename][0]

        # 5. TAG DISCIPLINE AND CATEGORY
        discipline_dic = {"Danc": "Ice Dance", "Pairs": "Pairs", "Men": "Men", "Ladies": "Ladies"}
        discipline = [discipline_dic[d] for d in discipline_dic if d in filename][0]
        category = 'Jr' if 'Junior' in filename else 'Sr'

        dc_short = category + discipline[0]

        identifiers = [discipline, category, season, event, sub_event, segment, event_start_date]

        print("SUMMARY:", filename, season, event, sub_event, event_year, discipline, category, segment,
              event_start_date)

        wb = load_workbook(f)
        segment_scraped_totals_list = []
        segment_competitors_list = []
        segment_goe_list = []
        segment_calls_list = []
        segment_pcs_list = []
        segment_scores_list = []
        segment_deductions_list = []
        segment_exploded_names = []

        for sheet in wb.sheetnames:
            ws = wb[sheet]
            raw_df = pd.DataFrame(ws.values)

            # GET NUMBER OF JUDGES (cols then rows scan to go faster since string usually found in first couple of cols)
            # You'd think the following bit only needs to be done once per WB, but no -- sometimes judges disappear
            # in the middle of a segment apparently
            found_flag = 0
            for j in raw_df.columns:
                for i in raw_df.index:
                    if 'Skating Skills' in str(raw_df.iloc[i, j]):
                        test_row = []
                        return_row_list(i, j + 1, raw_df, test_row)
                        found_flag = 1
                        break
                    if found_flag == 1:
                        break
                if found_flag == 1:
                    break

            row_data = []
            for a in test_row:
                cleaner = [u.replace(',', '.') for u in str(a).split()]
                for b in cleaner:
                    try:
                        cleanest_cell = float(b)
                    except:
                        cleanest_cell = ''
                    row_data.append(cleanest_cell)
            row_data = [_f for _f in row_data if _f]
            row_data = [_f for _f in row_data if _f]

            no_judges = len(row_data[1:-1])
            # print 'no_judges', no_judges

            judge_col_headers = []
            for r in range (1, no_judges+1):
                judge_col_headers.append('j'+str(r))

            for i in raw_df.index:
                for j in raw_df.columns:

                    # SCRAPE COMPETITOR NAME
                    if 'Name' in str(raw_df.iloc[i, j]):
                        name_row = []
                        for k in range(i + 2, i + 5):
                            start = max(j-2, 0)
                            for l in range(start, j + 2):
                                namelike_regex = re.search(r'[A-Z]{2,}', str(raw_df.iloc[k, l]))
                                if namelike_regex is not None:
                                    return_row_list(k, 0, raw_df, name_row)
                                    break
                            if name_row:
                                break
                        assert name_row

                        # The 'fuck your names, Dutch people' exception - they break the pdf conversion
                        # Also some people have single letter names which isn't great for deducing first vs. last from
                        # case
                        spaced_patronym_regex = re.search(r'^\d+\s+\D+', str(name_row[0]))
                        if spaced_patronym_regex is not None:
                            e_handler = str(name_row[0]).split(' ', 1)
                            name_row[0] = int(e_handler[0])
                            name_row.insert(1, e_handler[1])

                        # Check name order
                        exploded_name = name_row[1].split(' ')

                        first_name_list, last_name_list = [], []
                        exploded_name = [word.replace('.', '') for word in exploded_name]
                        for word in exploded_name:
                            if len(word) > 1 and (str(word[1]).isupper() or str(word[:2]) == 'Mc'):
                                last_name_list.append(word)
                            else:
                                first_name_list.append(word)

                        first_name = ' '.join(first_name_list)
                        last_name = ' '.join(last_name_list)
                        short_last_name = ''.join(last_name_list)
                        competitor_name = first_name + ' ' + last_name
                        # print competitor_name

                        country = 'RUS' if name_row[2] == 'OAR' else name_row[2]

                        segment_competitors_list.append((season, discipline, category, competitor_name, country))
                        segment_exploded_names.append((first_name, short_last_name))

                        competitor_short_name = segment_exploded_names[-1][1] + segment_exploded_names[-1][0]
                        index = identifiers[2] + identifiers[3] + identifiers[4] + identifiers[1] + identifiers[0] + \
                            competitor_short_name + identifiers[5]

                        # Protocol format changed from SB2009 to included skater starting number
                        score_index = 6 if (int(season[2:]) >= 2009 or (event in ['WTT', 'WC'] and
                                                                        int(season[2:]) == 2008))  else 5
                        segment_scraped_totals_list.append((index, discipline, category, season, event, sub_event,
                                                           competitor_name, segment, float(name_row[score_index]),
                                                            float(name_row[score_index-1]),
                                                            float(name_row[score_index-2])))

                    # SCRAPE PCS SCORES
                    elif 'Skating Skills' in str(raw_df.iloc[i, j]):
                        single_pcs_list = []
                        for k in range(i, i + 5):
                            raw_row_data = []
                            return_row_list(k, j + 1, raw_df, raw_row_data)
                            row_data = []
                            for raw_cell in raw_row_data:
                                cleaner = [u.replace(',', '.') for u in str(raw_cell).split()]
                                for v in cleaner:
                                    try:
                                        cleanest_cell = float(v)
                                    except:
                                        cleanest_cell = ''
                                    row_data.append(cleanest_cell)
                            row_data = [_f for _f in row_data if _f]

                            single_pcs_list.append(row_data[1:-1])

                        single_pcs_df = pd.DataFrame(single_pcs_list, index=['ss', 'tr', 'pc', 'ch', 'in'],
                                                     columns=judge_col_headers)
                        single_pcs_df.rename_axis('judge', axis='columns', inplace=True)
                        single_pcs_df.rename_axis('component', axis='index', inplace=True)

                        add_segment_identifiers(single_pcs_df, identifiers, segment_competitors_list,
                                                segment_exploded_names)
                        segment_pcs_list.extend([single_pcs_df])

                    # SCRAPE DEDUCTIONS
                    # For clarity, formatting issues we're trying to tackle:
                    #    Falls may or may not be followed (or preceded) by # of falls in parentheses
                    #    Total fall deduction may not equal # of falls * -1 (can add deductions for interruption)
                    #    Some rows have totals, some don't
                    # In older protocols (pre 2005-06), all deduction types are listed, with 0 if no deduction
                    elif 'Deductions' in str(raw_df.iloc[i, j]) and j < 4:
                        ded_row = []
                        return_row_list(i, j, raw_df, ded_row)

                        row_dic = clean_ded_row(ded_row)
                        ded_words, ded_digits = row_dic['ded_words'], row_dic['ded_digits']

                        assert ded_words[0] == 'deductions'

                        # Special case for older protocols - scrape both lines
                        old_protocol = True if (int(season[-2:]) < 5 or (int(season[-2:]) == 5 and event == 'OWG')) \
                            else False

                        # Two models in old protocols: total at end of top row or at end of bottom row (in which case
                        # bottom row contains three numbers
                        if old_protocol:
                            ded_row_2 = []
                            return_row_list(i+1, j, raw_df, ded_row_2)
                            row_dic_2 = clean_ded_row(ded_row_2)
                            ded_words += row_dic_2['ded_words']
                            if event == 'OWG' or len(ded_digits) == 4:
                                # print '1 OLD PROTOCOL -- TOTAL ON TOP ROW'
                                ded_digits = ded_digits[:-1] + row_dic_2['ded_digits']
                            else:
                                assert len(row_dic_2['ded_digits']) == 3
                                # print '2 OLD PROTOCOL -- TOTAL ON BOTTOM ROW'
                                ded_digits += row_dic_2['ded_digits'][:-1]
                        else:
                            if len(ded_words) == len(ded_digits):
                                del ded_digits[-1]

                        del ded_words[0]

                        # For old school protocols, remove all the headings where there was no actual deduction
                        if old_protocol:
                            for z in range(len(ded_digits)-1, -1, -1):
                                if ded_digits[z] == 0:
                                    del ded_words[z]
                                    del ded_digits[z]

                        if ded_words is not None:
                            for z in range(0, len(ded_words)):
                                #print '(', ded_words[z], ded_digits[z], ')'
                                segment_deductions_list.append((index, discipline, category, season, event, sub_event,
                                                                segment_competitors_list[-1][3], segment, ded_words[z],
                                                                ded_digits[z]))

                    # SCRAPE ELEMENTS, CALLS, GOE AND TES SCORES
                    elif 'Elements' in str(raw_df.iloc[i, j]):
                        single_goe_list = []
                        single_calls_list = []
                        single_scores_list = []
                        elt_id_list = []

                        # Identify whether elt list starts on next line or not
                        incr = 1 if (raw_df.iloc[i + 1, j] is not None or raw_df.iloc[i + 1, j - 1] is not None) else 2

                        # Get number of elements in the programme (e.g. when some are invalid there might be 14
                        # instead of 13)
                        z, flag = i + incr, 0
                        while flag == 0:
                            test_row = []
                            return_row_list(z, 0, raw_df, test_row)
                            content = ' '.join(str(elt) for elt in test_row)
                            if 'Program Components' in content:
                                flag = 1
                                break
                            elif z == (raw_df.shape[0] - 1):
                                flag = 2
                                break
                            z += 1
                        end = (z - 1) if flag == 1 else z

                        for k in range(i + incr, end):
                            elt_row = []
                            return_row_list(k, 0, raw_df, elt_row)

                            if len(elt_row) >= 13:  # Sometimes people forget an element apparently
                                elt_no = int(elt_row[0])

                                # Get rid of random columns of dashes
                                if elt_row[-2] == '-' and elt_row[-3] != '-':
                                    del elt_row[-2]

                                # Clean elt name, capture any missing reqs, start to separate elt and level info
                                missing_req_search = re.search(r'V\d+', elt_row[1])
                                if missing_req_search is not None:
                                    missing_reqs = missing_req_search.group(0)[1:]
                                    elt_row[1] = elt_row[1].replace(missing_req_search.group(0), '')
                                else:
                                    missing_reqs = None

                                elt_less_calls = clean_elt_name(elt_row[1], calls)

                                # Separate jumps from non jumps - not all non-jump elements have levels or no_positions
                                lvl_regex = re.search(r'\d+$', elt_less_calls)
                                non_jump_regex = re.search(r'[a-y]', elt_less_calls)
                                lo_regex = re.search(r'Lo', elt_less_calls)
                                if lvl_regex is not None or (non_jump_regex is not None and lo_regex is None):
                                    elt_type = 'non_jump'
                                    if lvl_regex is not None:
                                        level = lvl_regex.group(0)
                                        split = re.split('(\d+)', elt_less_calls)
                                        elt_name = split[0]
                                        assert len(split[:-1]) in [2, 4]
                                        no_positions = split[1] if len(split[:-1]) == 4 else 'NA'
                                    else:
                                        level = None
                                        elt_name = elt_less_calls
                                        no_positions = None
                                else:
                                    elt_type = 'jump'
                                    level = None
                                    elt_name = elt_less_calls
                                    no_positions = None

                                # Some jumps are just labeled "Lz" instead of "1Lz"; others are labelled "LZ"
                                rot_regex_1 = re.search(r'^\d+', elt_less_calls)
                                jump_types = ['A', 'F', 'Lo', 'Lz', 'S', 'T']
                                if elt_type == 'jump':
                                    elt_name = elt_name.replace('LZ','Lz').replace('LO','Lo')
                                    if rot_regex_1 is None:
                                        elt_name = '1' + elt_name
                                    for jump in jump_types:
                                        elt_name = re.sub(r'\+' + jump + r'$', '+1' + jump, elt_name)
                                        elt_name = re.sub(r'\+' + jump + r'\+', '+1' + jump + '+', elt_name)

                                # POPULATE TECH CALL FLAGS
                                invalid = 1 if any('*' in str(cell) for cell in elt_row) else 0
                                h2 = 1 if any('x' in str(cell) for cell in elt_row) else 0

                                seq_flag, combo_flag = 0, 0
                                if '+SEQ' in elt_name:
                                    seq_flag = 1
                                elif len(combo_regex.findall(elt_name)) > 0 or '+COMBO' in elt_name:
                                    combo_flag = 1

                                # Note: Distinction between UR and Downgrade was brought in from SB2011
                                # multiple calls per jumping pass
                                if int(season[-2:]) < 11 and any('<' in str(cell) for cell in elt_row):
                                    downgrade_flag = 1
                                elif any('<<' in str(cell) for cell in elt_row):
                                    downgrade_flag = 1
                                else:
                                    downgrade_flag = 0

                                severe_edge_flag = 1 if any('e' in str(cell) for cell in elt_row) else 0
                                unclear_edge_flag = 1 if any('!' in str(cell) for cell in elt_row) else 0
                                rep_flag = 1 if any('+REP' in str(cell) for cell in elt_row) else 0
                                failed_spin = 1 if any('V' in str(cell) for cell in elt_row) else 0

                                if combo_flag == 1 or seq_flag == 1:
                                    jumps = elt_row[1].split('+')

                                    jump_1 = clean_elt_name(jumps[0], calls)
                                    j1_sev_edge = 1 if 'e' in jumps[0] else 0
                                    j1_unc_edge = 1 if '!' in jumps[0] else 0
                                    j1_down = 1 if '<<' in jumps[0] else 0
                                    j1_ur = 1 if ('<' in jumps[0] and '<<' not in jumps[0]) else 0

                                    if jumps[-1] not in ['SEQ', 'COMBO']:
                                        jump_2 = clean_elt_name(jumps[1], calls)
                                        j2_sev_edge = 1 if 'e' in jumps[1] else 0
                                        j2_unc_edge = 1 if '!' in jumps[1] else 0
                                        j2_down = 1 if '<<' in jumps[1] else 0
                                        j2_ur = 1 if ('<' in jumps[1] and '<<' not in jumps[1]) else 0
                                    else:
                                       jump_2, j2_sev_edge, j2_unc_edge, j2_down, j2_ur = None, None, None, None, None

                                    if len(jumps) >= 3:
                                        jump_3 = clean_elt_name(jumps[2], calls)
                                        j3_sev_edge = 1 if 'e' in jumps[2] else 0
                                        j3_unc_edge = 1 if '!' in jumps[2] else 0
                                        j3_down = 1 if '<<' in jumps[2] else 0
                                        j3_ur = 1 if '<' in jumps[2] and '<<' not in jumps[2] else 0
                                    else:
                                        jump_3, j3_sev_edge, j3_unc_edge, j3_down, j3_ur = None, None, None, None, None

                                    if len(jumps) >= 4:
                                        jump_4 = clean_elt_name(jumps[3], calls)
                                        j4_sev_edge = 1 if 'e' in jumps[3] else 0
                                        j4_unc_edge = 1 if '!' in jumps[3] else 0
                                        j4_down = 1 if '<<' in jumps[3] else 0
                                        j4_ur = 1 if '<' in jumps[3] and '<<' not in jumps[3] else 0
                                    else:
                                        jump_4, j4_sev_edge, j4_unc_edge, j4_down, j4_ur = None, None, None, None, None

                                else:
                                    jump_1 = clean_elt_name(elt_row[1], calls) if lvl_regex is None else None
                                    j1_sev_edge = severe_edge_flag
                                    j1_unc_edge = unclear_edge_flag
                                    j1_ur = 1 if downgrade_flag == 0 and any(
                                        '<' in str(cell) for cell in elt_row) else 0
                                    j1_down = downgrade_flag
                                    jump_2, j2_sev_edge, j2_unc_edge, j2_ur = None, None, None, None
                                    j2_down, jump_3, j3_sev_edge, j3_unc_edge = None, None, None, None
                                    j3_ur, j3_down, jump_4, j4_sev_edge = None, None, None, None
                                    j4_unc_edge, j4_ur, j4_down = None, None, None

                                ur_flag = 1 if 1 in [j1_ur, j2_ur, j3_ur, j4_ur] else 0

                                temp_numbers = []
                                cutoff = -1 - no_judges
                                for cell in elt_row[2:cutoff]:
                                    temp_numbers.extend(str(cell).split(' '))
                                numbers = [str(cell).strip() for cell in temp_numbers if cell not in calls]
                                for call_notation in calls:
                                    numbers[0] = numbers[0].replace(call_notation, '').strip()
                                elt_bv = float(numbers[0])
                                elt_sov_goe, elt_total = float(numbers[1]), float(elt_row[-1])

                                # SCRAPE GOE SCORES
                                goe_row = []
                                for b in elt_row[cutoff:-1]:
                                    try:
                                        clean = int(b)
                                    except:
                                        clean = 0
                                    goe_row.append(clean)

                            else:
                                elt_no = k - i
                                elt_name = 'MISSING_ELEMENT'
                                elt_type = None
                                level, h2, combo_flag, seq_flag, ur_flag = None, None, None, None, None
                                downgrade_flag, severe_edge_flag, unclear_edge_flag, rep_flag = None, None, None, None
                                called_jumps, invalid, failed_spin, missing_reqs = None, None, None, None

                                jump_1, j1_sev_edge, j1_unc_edge, j1_ur = None, None, None, None
                                j1_down, jump_2, j2_sev_edge, j2_unc_edge = None, None, None, None
                                j2_ur, j2_down, jump_3, j3_sev_edge = None, None, None, None
                                j3_unc_edge, j3_ur, j3_down, jump_4 = None, None, None, None
                                j4_sev_edge, j4_unc_edge, j4_ur, j4_down = None, None, None, None
                                elt_bv, elt_sov_goe, elt_total = None, None, None
                                goe_row = [None, None, None, None, None, None, None, None, None]

                            elt_id = 'SB' + season[-2:] + event + sub_event[:1].upper() + dc_short \
                                     + competitor_short_name + segment + str(elt_no)
                            elt_id_list.append(elt_id)

                            calls_row = (elt_no, elt_name, elt_type, level, no_positions, invalid, h2, combo_flag,
                                         seq_flag, ur_flag, downgrade_flag, severe_edge_flag, unclear_edge_flag, rep_flag,
                                         jump_1, j1_sev_edge, j1_unc_edge, j1_ur, j1_down,
                                         jump_2, j2_sev_edge, j2_unc_edge, j2_ur, j2_down,
                                         jump_3, j3_sev_edge, j3_unc_edge, j3_ur, j3_down,
                                         jump_4, j4_sev_edge, j4_unc_edge, j4_ur, j4_down, failed_spin, missing_reqs)
                            scores_row = (elt_name, elt_type, level, no_positions, h2, elt_bv, elt_sov_goe, elt_total)

                            single_scores_list.append(scores_row)
                            single_calls_list.append(calls_row)
                            single_goe_list.append(goe_row)

                        call_cols = ['elt_no', 'elt_name', 'elt_type', 'level', 'no_positions', 'invalid', 'h2',
                                     'combo_flag','seq_flag', 'ur_flag', 'downgrade_flag', 'severe_edge_flag',
                                     'unclear_edge_flag', 'rep_flag',
                                     'jump_1', 'j1_sev_edge', 'j1_unc_edge', 'j1_ur', 'j1_down',
                                     'jump_2', 'j2_sev_edge', 'j2_unc_edge', 'j2_ur', 'j2_down',
                                     'jump_3', 'j3_sev_edge', 'j3_unc_edge', 'j3_ur', 'j3_down',
                                     'jump_4', 'j4_sev_edge', 'j4_unc_edge', 'j4_ur', 'j4_down',
                                     'failed_spin', 'missing_reqs']
                        single_calls_df = pd.DataFrame(single_calls_list, index=elt_id_list, columns=call_cols)

                        single_scores_df = pd.DataFrame(single_scores_list, index=elt_id_list,
                                                        columns=['elt_name', 'elt_type', 'level', 'no_positions', 'h2',
                                                                 'elt_bv', 'elt_sov_goe', 'elt_total'])

                        single_goe_df = pd.DataFrame(single_goe_list, index=elt_id_list,
                                                     columns=judge_col_headers)
                        single_goe_df.rename_axis('judge', axis='columns', inplace=True)

                        # ADD THE OTHER INFO COLUMNS - Figure how to loop through the dfs without python thinking
                        add_segment_identifiers(single_scores_df, identifiers, segment_competitors_list,
                                                segment_exploded_names)
                        add_segment_identifiers(single_goe_df, identifiers, segment_competitors_list,
                                                segment_exploded_names)
                        add_segment_identifiers(single_calls_df, identifiers, segment_competitors_list,
                                                segment_exploded_names)

                        segment_scores_list.append(single_scores_df)
                        segment_goe_list.append(single_goe_df)
                        segment_calls_list.append(single_calls_df)

        segment_scraped_totals_df = pd.DataFrame(segment_scraped_totals_list,
                                                 columns=['index', 'discipline', 'category', 'season', 'event', 'sub_event',
                                                          'skater_name', 'segment', 'scraped_pcs', 'scraped_tes',
                                                          'scraped_total'])

        segment_competitors_df = pd.DataFrame(segment_competitors_list,
                                              columns=['season', 'disc', 'category', 'name', 'country'])

        segment_deductions_df = pd.DataFrame(segment_deductions_list,
                                             columns=['index', 'discipline', 'category', 'season', 'event', 'sub_event',
                                                      'skater_name', 'segment', 'ded_type', 'ded_points'])

        segment_scores_df = pd.concat(segment_scores_list)
        segment_pcs_df = pd.concat(segment_pcs_list).stack()
        segment_pcs_df.name = 'pcs'
        segment_goe_df = pd.concat(segment_goe_list).stack()
        segment_goe_df.name = 'goe'
        segment_calls_df = pd.concat(segment_calls_list)

        all_scraped_totals_list.append(segment_scraped_totals_df)
        all_scores_list.append(segment_scores_df)
        all_pcs_list.append(segment_pcs_df)
        all_goe_list.append(segment_goe_df)
        all_calls_list.append(segment_calls_df)
        all_deductions_list.append(segment_deductions_df)
        all_competitors_list.append(segment_competitors_df)
        print('        loaded full segment df into overall summary list')

    all_scraped_totals_df = pd.concat(all_scraped_totals_list)
    all_scores_df = pd.concat(all_scores_list)
    print('scores df concatenated')
    all_pcs_df = pd.concat(all_pcs_list)
    all_pcs_df = all_pcs_df.reset_index()
    print('pcs df concatenated')
    all_goe_df = pd.concat(all_goe_list)
    all_goe_df = all_goe_df.reset_index()
    print('goe df concatenated')
    all_calls_df = pd.concat(all_calls_list)
    print('calls df concatenated')
    all_deductions_df = pd.concat(all_deductions_list)
    all_deductions_df = all_deductions_df.reset_index(drop=True)
    print('deductions df concatenated')
    all_competitors_df = pd.concat(all_competitors_list)
    all_competitors_df.drop_duplicates(subset=['category', 'name', 'country'], keep='last', inplace=True)
    all_competitors_df = all_competitors_df.reset_index(drop=True)
    print('competitors df concatenated')

    header_setting = True
    all_scraped_totals_df.to_csv(WRITE_PATH + 'scraped_totals_' + DATE + VER + '.csv', mode='a', encoding='utf-8',
                                 header=header_setting)
    all_scores_df.to_csv(WRITE_PATH + 'elt_scores_' + DATE + VER + '.csv', mode='a', encoding='utf-8',
                         header=header_setting)
    all_pcs_df.to_csv(WRITE_PATH + 'pcs_' + DATE + VER + '.csv', mode='a', encoding='utf-8', header=header_setting)
    all_goe_df.to_csv(WRITE_PATH + 'goe_' + DATE + VER + '.csv', mode='a', encoding='utf-8', header=header_setting)
    all_calls_df.to_csv(WRITE_PATH + 'calls_' + DATE + VER + '.csv', mode='a', encoding='utf-8', header=header_setting)
    all_deductions_df.to_csv(WRITE_PATH + 'deductions_' + DATE + VER + '.csv', mode='a', encoding='utf-8',
                             header=header_setting)
    all_competitors_df.to_csv(WRITE_PATH + 'competitors_' + DATE + VER + '.csv', mode='a', encoding='utf-8',
                              header=header_setting)

    # WHERE DEDUCTIONS ARE MISSING (BC THEY DISAPPEARED IN THE CONVERSION FROM PDF TO XLS), ADD THE TOTALS AS
    # 'UNKNOWN' PENDING MANUAL CORRECTION
    all_scraped_totals_df['derived_ded'] = all_scraped_totals_df.apply(lambda x: \
            int(round(x['scraped_total'] - x['scraped_tes'] - x['scraped_pcs'], 0)), axis = 1)
    all_scraped_totals_df.drop(labels=['scraped_pcs', 'scraped_tes', 'scraped_total'], axis=1, inplace=True)
    print(all_scraped_totals_df)
    ded_totals = all_deductions_df.fillna('None').groupby(key_cols)['ded_points'].sum().reset_index()
    print(ded_totals)
    ded_comparison = all_scraped_totals_df.join(ded_totals.set_index(key_cols), on=key_cols, how='left', lsuffix='_pcs',
                            rsuffix='_tes').fillna(0)
    ded_comparison['ded_type'] = 'unknown'
    ded_comparison.to_csv(WRITE_PATH + 'ded_comp_' + DATE + VER + '.csv', mode='a', encoding='utf-8',
                          header=header_setting)
    ded_comparison['ded_diff'] = ded_comparison.apply(lambda x: int(round(x['derived_ded'] - x['ded_points'], 0)), axis=1)
    ded_comparison.drop(labels=['derived_ded', 'ded_points'], axis=1, inplace=True)
    rows_to_append = ded_comparison.loc[ded_comparison['ded_diff'] != 0]
    rows_to_append.to_csv(WRITE_PATH + 'deductions_' + DATE + VER + '.csv', mode='a', encoding='utf-8',
                             header=False)

main()
