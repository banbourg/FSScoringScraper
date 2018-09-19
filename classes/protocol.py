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
    def __init__(self, df, protocol_coordinates, segment, skater_list, last_row_dic, cursor):
        (row_start, row_end) = protocol_coordinates

        name_row = self._find_name_row(df=df, anchor_coords=(row_start, 0), size_of_sweep=(1, 4, 3))
        schema = self._find_name_row_schema(segment)

        self.season = segment.season
        self.discipline = segment.discipline
        self.row_range = range(row_start, row_end + 1)
        self.col_range = range(0, df.shape[1])
        self.elt_list_ends = None

        self.number_of_judges = self.count_judges(df)
        
        self.skater = CONSTRUCTOR_DIC[segment.discipline]["competitor"](name_row, skater_list, last_row_dic,
                                                                        self.season, cursor)

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
        self.pcs_detail = pd.DataFrame(pcs_scores, index=component_names, columns=judge_col_headers)
        self.pcs_detail.rename_axis('judge', axis='columns', inplace=True)
        self.pcs_detail.rename_axis('component', axis='index', inplace=True)
        logger.debug(f"Loaded pcs table for "
                     f"{unicodedata.normalize('NFKD', self.skater.printout).encode('ascii','ignore')}")

    def parse_tes_table(self, df, i, j, last_row_dic):
        self._get_elt_list_location(df, i, j)
        for k in range(self.elt_list_starts, self.elt_list_ends):
            elt_row = datarow.GOERow(df=df, row=k, col_min=0)
            logger.debug(f"Elt row is {elt_row.row_label}, {elt_row.clean}")

            self.elts.append(CONSTRUCTOR_DIC[self.discipline]["elt"](elt_row, self.season, last_row_dic))
            last_row_dic["elements"] += 1

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

    def get_skate_dic(self, segment):
        dic = {"segment_id": segment.id, "competitor_id": self.skater.id, "tes": self.tes_total,
               "pcs": self.pcs_total, "tss": self.tss_total, "ded": self.deductions,
               "starting_number": self.starting_number, "number_of_judges": self.number_of_judges}
        return dic

    def get_pcs_df(self, segment):
        self.pcs_detail["segment_id"] = segment.id
        self.pcs_detail["competitor_id"] = self.skater.id
        return self.pcs_detail


CONSTRUCTOR_DIC = {"IceDance": {"competitor": person.Team, "elt": element.IceDanceElement},
                   "Pairs": {"competitor": person.Team, "elt": element.PairsElement},
                   "Ladies": {"competitor": person.SinglesSkater, "elt": element.SinglesElement},
                   "Men": {"competitor": person.SinglesSkater, "elt": element.SinglesElement}}
