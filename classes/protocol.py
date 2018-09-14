import sys
import re
import logging
import pandas as pd
import decimal as dec
import unicodedata

logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)-5s - %(message)s",
                    level=logging.DEBUG,
                    datefmt='%Y-%m-%d %H:%M:%S')
logger = logging.getLogger(__name__)

try:
    import event
    import person
    import datarow
    import element
except ImportError as exc:
    sys.stderr.write("Error: failed to import module ({})".format(exc))
    sys.exit(1)

NAME_LIKE_PATTERN = re.compile(r"[A-Z]{2,}")


class Protocol:
    def __init__(self, df, protocol_coordinates, segment):
        (row_start, row_end) = protocol_coordinates

        name_row = self._find_name_row(df=df, anchor_coords=(row_start, 0), size_of_sweep=(1, 4, 3))
        schema = self._find_name_row_schema(segment)

        self.season = segment.season
        self.discipline = segment.discipline
        self.row_range = range(row_start, row_end + 1)
        self.col_range = range(0, df.shape[1])
        self.elt_list_ends = None

        self.number_of_judges = self.count_judges(df)
        
        self.skater = CONSTRUCTOR_DIC[segment.discipline]["competitor"](name_row)
        self.starting_number = int(name_row.clean[3]) if schema == "new" else None
        self.tss_total = dec.Decimal(str(name_row.clean[4])) if schema == "new" else dec.Decimal(str(name_row.clean[3]))
        self.tes_total = dec.Decimal(str(name_row.clean[5])) if schema == "new" else dec.Decimal(str(name_row.clean[4]))
        self.pcs_total = dec.Decimal(str(name_row.clean[6])) if schema == "new" else dec.Decimal(str(name_row.clean[5]))
        logger.debug(f"Scores are tss {self.tss_total}, tes {self.tes_total}, pcs {self.pcs_total}")
        self.deductions = dec.Decimal(self.tss_total - self.tes_total - self.pcs_total)

        self.elts = []
        self.pcs_detail = None
        self.ded_detail = []
        logger.debug(f"Instantiated Skate object for {unicodedata.normalize('NFKD', self.skater.printout).encode('ascii','ignore')} "
                     f"with total score {self.tss_total} and starting no. {self.starting_number}")

    def _find_name_row(self, df, anchor_coords, size_of_sweep):
        (row, col) = anchor_coords
        # Case 1: Field headers and values in same cell:
        anchor_row = datarow.DataRow(df=df, row=row, col_min=0)
        for cell in anchor_row.raw:
            if "Name\n" in cell:
                return datarow.NameRow(mode="multiline", df=df, row=row, col_min=0)

        # Case 2: Field headers and values in separate cells, not necessarily aligned
        (first_row_to_sweep, last_row_to_sweep, last_col_to_sweep) = size_of_sweep
        for r in range(row + first_row_to_sweep, row + last_row_to_sweep + 1):
            for c in range(0, col + last_col_to_sweep + 1):
                if re.search(NAME_LIKE_PATTERN, str(df.iloc[r, c])):
                    return datarow.NameRow(mode="single line", df=df, row=r, col_min=0)

        sys.exit(f"Could not find name row that matched expected pattern in sweep from {anchor_coords}")

    def _find_name_row_schema(self, segment):
        if int(segment.season[2:]) >= 2009 or (int(segment.season[2:]) == 2008 and segment.name in ['WTT', 'WC']):
            return "new"
        else:
            return "old"

    def _get_elt_list_location(self, df, i, j):
        # Avoids scanning more rows than needed/false positives.
        if df.iloc[i + 1, j] or df.iloc[i + 1, j - 1]:
            increment = 1
        else:
            increment = 2

        # Get number of elements in the programme (e.g. when some are invalid there might be 14 instead of 13)
        self.elt_list_starts = i + increment
        for row in range(self.elt_list_starts, df.shape[0] + 1):
            concat_row = " ".join([str(cell) for cell in datarow.DataRow(df=df, row=row, col_min=0).raw])
            if "Program Components" in concat_row:
                break
        self.elt_list_ends = row if row == df.shape[0] else row - 1

    def count_judges(self, df):
        """ Sets the number of judges observed on this sheet of the spreadsheet.

        Scans columns, then rows to go faster since string usually found in first couple of columns. (You'd think the
        following bit only needs to be done once per WB, but no -- sometimes judges disappear mid-segment).

        :param df: Dataframe containing raw input from spreedsheet sheet.
        :return: Integer number of judges.
        """
        # Get first "Skating skills" scorelist and clean it (e.g. multiple scores in same cell, comma decimals, etc.)
        counter = None
        for j in self.col_range:
            for i in self.row_range:
                if "Skating Skills" in str(df.iloc[i, j]):
                    self.pcs_start_row = i
                    counter = datarow.PCSRow(mode="decimal", df=df, row=i, col_min=j).clean
                    break
            if counter:
                break
        no_judges = len(counter[1:-1])
        logger.debug(f"Found {no_judges} judges in current protocol")
        return no_judges

    def parse_pcs_table(self, df, i, j):
        component_names, pcs_scores = [], []
        for k in range(i, i + 6):
            component = datarow.PCSRow(judges=self.number_of_judges, df=df, row=k, col_min=j)
            component_names.append(component.row_label)
            pcs_scores.append(component.clean)

            # all_cells = datarow.DataRow(df=df, row=k, col_min=j).raw
            # scores = datarow.PCSRow(mode="decimal", raw_list=all_cells)
            # if len(scores.clean) >= self.number_of_judges:
            #     component_names.append(all_cells[0])
            #     pcs_scores.append(scores.clean[1:-1])
            # else:
            #     break

        judge_col_headers = ["j" + str(j).zfill(2) for j in range(1, self.number_of_judges + 1)]
        pcs_df = pd.DataFrame(pcs_scores, index=component_names, columns=judge_col_headers)
        pcs_df.rename_axis('judge', axis='columns', inplace=True).rename_axis('component', axis='index', inplace=True)
        self.pcs_df = pcs_df
        logger.debug(f"Loaded pcs table for "
                     f"{unicodedata.normalize('NFKD', self.skater.printout).encode('ascii','ignore')}")

    def parse_tes_table(self, df, i, j):
        self._get_elt_list_location(df, i, j)
        for k in range(self.elt_list_starts, self.elt_list_ends):
            elt_row = datarow.GOERow(df=df, row=k, col_min=0)
            logger.debug(f"Elt row is {elt_row.row_label}, {elt_row.clean}")

            self.elts.append(CONSTRUCTOR_DIC[self.discipline]["elt"](elt_row, self.season))

    def parse_deductions(self, df, i, j, segment):
        """
        For clarity, here are the formatting issues we're trying to tackle:
        (1) Fall deductions may or may not be followed (or preceded) by # of falls in parentheses
        (2) Total fall deduction may not equal # of falls * -1 (can add deductions for interruption)
        (3) Some rows have totals, some don't
        (4) In older protocols (pre 2005-06), all deduction types are listed, with 0 if no deduction
        :param df: Unstructured protocol data (pdf protocols converted to xlsx and loaded into df
        :param i: Dataframe row at which "Deductions" heading found
        :param j: Dataframe col at which "Deductions" heading found
        :return:
        """
        logger.debug(f"Total deductions for this skate known to be {self.deductions.quantize(dec.Decimal('0'))}. "
                     f"Attempting to match...")

        if self.deductions.compare(dec.Decimal('0')) == dec.Decimal('0'):
            logger.debug(f"No deductions here, move along")
        else:
            logger.debug(f"RIP so we're doing this huh")

            # Older protocols present deductions over two rows, with two different models: total at end of top row or
            # at end of bottom row (in which case
            is_old_ded_format = True if segment.year < 2005 or (segment.year == 2005 and segment.name in event.H2_EVENTS) \
                or (segment.year == 2006 and segment.name == "OWG") else False

            ded_dic = datarow.DeductionRow(df=df, row=i, col_min=j).ded_detail
            if sum(ded_dic.values()) == int(self.deductions):
                self.ded_detail = ded_dic
                return

            row_1 = datarow.DataRow(df=df, row=i, col_min=j).raw
            row_2 = datarow.DataRow(df=df, row=i + 1, col_min=j).raw
            ded_dic_2 = datarow.DeductionRow(raw=row_1 + row_2).ded_detail
            logger.debug(f"what the fuuuuuuuuu {ded_dic_2.values()}")
            if is_old_ded_format and sum(ded_dic_2.values()) == int(self.deductions):
                self.ded_detail = ded_dic_2
                return

            row_3 = datarow.DataRow(df=df, row=i + 2, col_min=j).raw
            ded_dic_3 = datarow.DeductionRow(raw=row_1 + row_2 + row_3).ded_detail
            if is_old_ded_format and sum(ded_dic_3.values()) == int(self.deductions):
                self.ded_detail = ded_dic_3
                return

            sys.exit("Some deductions are still missing")


class IceDanceProtocol(Protocol):
    def __init___(self, df, protocol_coordinates, segment):
        super().__init__(df, protocol_coordinates, segment)


class PairsProtocol(Protocol):
    def __init___(self, df, protocol_coordinates, segment):
        super().__init__(df, protocol_coordinates, segment)


class SinglesProtocol(Protocol):
    def __init___(self, df, protocol_coordinates, segment):
        super().__init__(df, protocol_coordinates, segment)




#                     elif 'Elements' in str(raw_df.iloc[i, j]):
#                         single_goe_list = []
#                         single_calls_list = []
#                         single_scores_list = []
#                         elt_id_list = []
#
#                                 # Some jumps are just labeled "Lz" instead of "1Lz"; others are labelled "LZ"
#                                 rot_regex_1 = re.search(r'^\d+', elt_less_calls)
#                                 jump_types = ['A', 'F', 'Lo', 'Lz', 'S', 'T']
#                                 if elt_type == 'jump':
#                                     elt_name = elt_name.replace('LZ','Lz').replace('LO','Lo')
#                                     if rot_regex_1 is None:
#                                         elt_name = '1' + elt_name
#                                     for jump in jump_types:
#                                         elt_name = re.sub(r'\+' + jump + r'$', '+1' + jump, elt_name)
#                                         elt_name = re.sub(r'\+' + jump + r'\+', '+1' + jump + '+', elt_name)
#
#
#                                 # Note: Distinction between UR and Downgrade was brought in from SB2011
#                                 # multiple calls per jumping pass
#                                 if int(season[-2:]) < 11 and any('<' in str(cell) for cell in elt_row):
#                                     downgrade_flag = 1
#                                 elif any('<<' in str(cell) for cell in elt_row):
#                                     downgrade_flag = 1
#                                 else:
#                                     downgrade_flag = 0
#
#                                 severe_edge_flag = 1 if any('e' in str(cell) for cell in elt_row) else 0
#                                 unclear_edge_flag = 1 if any('!' in str(cell) for cell in elt_row) else 0
#                                 rep_flag = 1 if any('+REP' in str(cell) for cell in elt_row) else 0
#                                 failed_spin = 1 if any('V' in str(cell) for cell in elt_row) else 0
#
#                                 if combo_flag == 1 or seq_flag == 1:
#                                     jumps = elt_row[1].split('+')
#
#                                     jump_1 = clean_elt_name(jumps[0], calls)
#                                     j1_sev_edge = 1 if 'e' in jumps[0] else 0
#                                     j1_unc_edge = 1 if '!' in jumps[0] else 0
#                                     j1_down = 1 if '<<' in jumps[0] else 0
#                                     j1_ur = 1 if ('<' in jumps[0] and '<<' not in jumps[0]) else 0
#
#                                     if jumps[-1] not in ['SEQ', 'COMBO']:
#                                         jump_2 = clean_elt_name(jumps[1], calls)
#                                         j2_sev_edge = 1 if 'e' in jumps[1] else 0
#                                         j2_unc_edge = 1 if '!' in jumps[1] else 0
#                                         j2_down = 1 if '<<' in jumps[1] else 0
#                                         j2_ur = 1 if ('<' in jumps[1] and '<<' not in jumps[1]) else 0
#                                     else:
#                                        jump_2, j2_sev_edge, j2_unc_edge, j2_down, j2_ur = None, None, None, None, None
#
#                                     if len(jumps) >= 3:
#                                         jump_3 = clean_elt_name(jumps[2], calls)
#                                         j3_sev_edge = 1 if 'e' in jumps[2] else 0
#                                         j3_unc_edge = 1 if '!' in jumps[2] else 0
#                                         j3_down = 1 if '<<' in jumps[2] else 0
#                                         j3_ur = 1 if '<' in jumps[2] and '<<' not in jumps[2] else 0
#                                     else:
#                                         jump_3, j3_sev_edge, j3_unc_edge, j3_down, j3_ur = None, None, None, None, None
#
#                                     if len(jumps) >= 4:
#                                         jump_4 = clean_elt_name(jumps[3], calls)
#                                         j4_sev_edge = 1 if 'e' in jumps[3] else 0
#                                         j4_unc_edge = 1 if '!' in jumps[3] else 0
#                                         j4_down = 1 if '<<' in jumps[3] else 0
#                                         j4_ur = 1 if '<' in jumps[3] and '<<' not in jumps[3] else 0
#                                     else:
#                                         jump_4, j4_sev_edge, j4_unc_edge, j4_down, j4_ur = None, None, None, None, None
#
#                                 else:
#                                     jump_1 = clean_elt_name(elt_row[1], calls) if lvl_regex is None else None
#                                     j1_sev_edge = severe_edge_flag
#                                     j1_unc_edge = unclear_edge_flag
#                                     j1_ur = 1 if downgrade_flag == 0 and any(
#                                         '<' in str(cell) for cell in elt_row) else 0
#                                     j1_down = downgrade_flag
#                                     jump_2, j2_sev_edge, j2_unc_edge, j2_ur = None, None, None, None
#                                     j2_down, jump_3, j3_sev_edge, j3_unc_edge = None, None, None, None
#                                     j3_ur, j3_down, jump_4, j4_sev_edge = None, None, None, None
#                                     j4_unc_edge, j4_ur, j4_down = None, None, None
#
#                                 ur_flag = 1 if 1 in [j1_ur, j2_ur, j3_ur, j4_ur] else 0
#
#                                 temp_numbers = []
#                                 cutoff = -1 - no_judges
#                                 for cell in elt_row[2:cutoff]:
#                                     temp_numbers.extend(str(cell).split(' '))
#                                 numbers = [str(cell).strip() for cell in temp_numbers if cell not in calls]
#                                 for call_notation in calls:
#                                     numbers[0] = numbers[0].replace(call_notation, '').strip()
#                                 elt_bv = float(numbers[0])
#                                 elt_sov_goe, elt_total = float(numbers[1]), float(elt_row[-1])
#
#                                 # SCRAPE GOE SCORES
#                                 goe_row = []
#                                 for b in elt_row[cutoff:-1]:
#                                     try:
#                                         clean = int(b)
#                                     except:
#                                         clean = 0
#                                     goe_row.append(clean)
#
#                             else:
#                                 elt_no = k - i
#                                 elt_name = 'MISSING_ELEMENT'
#                                 elt_type = None
#                                 level, h2, combo_flag, seq_flag, ur_flag = None, None, None, None, None
#                                 downgrade_flag, severe_edge_flag, unclear_edge_flag, rep_flag = None, None, None, None
#                                 called_jumps, invalid, failed_spin, missing_reqs = None, None, None, None
#
#                                 jump_1, j1_sev_edge, j1_unc_edge, j1_ur = None, None, None, None
#                                 j1_down, jump_2, j2_sev_edge, j2_unc_edge = None, None, None, None
#                                 j2_ur, j2_down, jump_3, j3_sev_edge = None, None, None, None
#                                 j3_unc_edge, j3_ur, j3_down, jump_4 = None, None, None, None
#                                 j4_sev_edge, j4_unc_edge, j4_ur, j4_down = None, None, None, None
#                                 elt_bv, elt_sov_goe, elt_total = None, None, None
#                                 goe_row = [None, None, None, None, None, None, None, None, None]
#
#                             elt_id = 'SB' + season[-2:] + event + sub_event[:1].upper() + dc_short \
#                                      + competitor_short_name + segment + str(elt_no)
#                             elt_id_list.append(elt_id)
#
#                             calls_row = (elt_no, elt_name, elt_type, level, no_positions, invalid, h2, combo_flag,
#                                          seq_flag, ur_flag, downgrade_flag, severe_edge_flag, unclear_edge_flag, rep_flag,
#                                          jump_1, j1_sev_edge, j1_unc_edge, j1_ur, j1_down,
#                                          jump_2, j2_sev_edge, j2_unc_edge, j2_ur, j2_down,
#                                          jump_3, j3_sev_edge, j3_unc_edge, j3_ur, j3_down,
#                                          jump_4, j4_sev_edge, j4_unc_edge, j4_ur, j4_down, failed_spin, missing_reqs)
#                             scores_row = (elt_name, elt_type, level, no_positions, h2, elt_bv, elt_sov_goe, elt_total)
#
#                             single_scores_list.append(scores_row)
#                             single_calls_list.append(calls_row)
#                             single_goe_list.append(goe_row)
#
#                         call_cols = ['elt_no', 'elt_name', 'elt_type', 'level', 'no_positions', 'invalid', 'h2',
#                                      'combo_flag','seq_flag', 'ur_flag', 'downgrade_flag', 'severe_edge_flag',
#                                      'unclear_edge_flag', 'rep_flag',
#                                      'jump_1', 'j1_sev_edge', 'j1_unc_edge', 'j1_ur', 'j1_down',
#                                      'jump_2', 'j2_sev_edge', 'j2_unc_edge', 'j2_ur', 'j2_down',
#                                      'jump_3', 'j3_sev_edge', 'j3_unc_edge', 'j3_ur', 'j3_down',
#                                      'jump_4', 'j4_sev_edge', 'j4_unc_edge', 'j4_ur', 'j4_down',
#                                      'failed_spin', 'missing_reqs']
#                         single_calls_df = pd.DataFrame(single_calls_list, index=elt_id_list, columns=call_cols)
#
#                         single_scores_df = pd.DataFrame(single_scores_list, index=elt_id_list,
#                                                         columns=['elt_name', 'elt_type', 'level', 'no_positions', 'h2',
#                                                                  'elt_bv', 'elt_sov_goe', 'elt_total'])
#
#                         single_goe_df = pd.DataFrame(single_goe_list, index=elt_id_list,
#                                                      columns=judge_col_headers)
#                         single_goe_df.rename_axis('judge', axis='columns', inplace=True)
#
#                         # ADD THE OTHER INFO COLUMNS - Figure how to loop through the dfs without python thinking
#                         add_segment_identifiers(single_scores_df, identifiers, segment_competitors_list,
#                                                 segment_exploded_names)
#                         add_segment_identifiers(single_goe_df, identifiers, segment_competitors_list,
#                                                 segment_exploded_names)
#                         add_segment_identifiers(single_calls_df, identifiers, segment_competitors_list,
#                                                 segment_exploded_names)

        # self.competitors = []
        # self.skate_ids = []
        # self.scraped_totals = []
        # self.goe = []
        # self.calls = []
        # self.pcs = []
        # self.elt_scores = []
        # self.deductions = []
        #
        #


CONSTRUCTOR_DIC = {"IceDance": {"seg_obj": event.IceDanceSegmentProtocols, "prot": IceDanceProtocol,
                                "competitor": person.Team, "elt": element.IceDanceElement},
                   "Pairs": {"seg_obj":event.PairsSegmentProtocols, "prot": SinglesProtocol,
                            "competitor": person.Team, "elt": element.PairsElement},
                   "Ladies": {"seg_obj":event.SinglesSegmentProtocols, "prot": SinglesProtocol,
                              "competitor": person.SinglesSkater, "elt": element.SinglesElement},
                   "Men": {"seg_obj":event.SinglesSegmentProtocols, "prot": SinglesProtocol,
                           "competitor":person.SinglesSkater, "elt": element.SinglesElement}}