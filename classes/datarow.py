import sys
import re
import logging
import numpy as np
import decimal as dec

logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)-5s - %(message)s",
                    level=logging.DEBUG,
                    datefmt='%Y-%m-%d %H:%M:%S')
logger = logging.getLogger(__name__)

try:
    None
except ImportError as exc:
    sys.stderr.write("Error: failed to import module ({})".format(exc))
    sys.stderr.write("Error: failed to import module ({})".format(exc))
    sys.exit(1)

NUMBER_AND_NAME_PATTERN = re.compile(r"^\d+\s+\D+")
DED_TYPE_PATTERN = re.compile(r"[A-Z][^:\-0-9.]*")
DED_POINT_PATTERN = re.compile(r"-*\d(?:\.0|\.00)*")
DED_TOTAL_PATTERN = re.compile(r"(\d(?:\.0)*0*) -*\d+(?:\.0)*0*")

DED_ALIGNMENT_DIC = {"fall": "falls" , "late start": "time violation", "illegal element": "illegal element/movement"}

EXPECTED_DED_TYPES = ['total', 'falls', 'time violation', 'costume failure', 'late start', 'music violation',
                      'interruption in excess', 'costume & prop violation', 'illegal element/movement', 'extended lifts',
                      'extra element', 'illegal element']

class DataRow:
    def __init__(self, raw_list=None, df=None, row=None, col_min=None):
        if df is not None and row >= 0 and col_min >=0 and not raw_list:
            self.raw_list = []
            for col in range(col_min, len(df.columns)):
                if df.iloc[row, col] is not None and not is_nan(df.iloc[row, col]):
                    self.raw_list.append(df.iloc[row, col])
        elif raw_list:
            self.raw_list = raw_list
        else:
            raise ValueError(f"Please instantiate the DataRow obj with either a raw list, or a df, row and col")
        self.cleaned_list = []

    def remove_dash_columns(self, judges):
        self.cleaned_list = self.raw_list
        if "-" in self.raw_list:
            if self.raw_list.count("-") > 1:
                self.cleaned_list = ["NS" if x == "-" else x for x in self.raw_list]
            else:
                self.cleaned_list.remove("-")
        try:
            assert len(self.cleaned_list) == (5 + judges)
        except AssertionError:
            logger.error(f"Elt row does not have expected length: {self.raw_list}, {self.cleaned_list}")
            sys.exit(1)
        return self.cleaned_list

    def clean_scores_row(self, mode):
        # logger.debug(f"Raw list is {self.raw_list}")
        for raw_cell in self.raw_list:
            for c in [re.sub(r"[^\-0-9.]", "", raw_score.replace(",", ".").strip())
                                for raw_score in str(raw_cell).split()]:
                if mode == "decimal":
                    try:
                        self.cleaned_list.append(dec.Decimal(c))
                    except:
                        pass
                elif mode == "float":
                    try:
                        self.cleaned_list.append(float(c))
                    except:
                        pass
                elif mode == "int":
                    try:
                        self.cleaned_list.append(int(c))
                    except:
                        self.cleaned_list.append(0)
                else:
                    raise ValueError("Please set 'mode' parameter to 'float' or 'int'")
        # logger.debug(f"Cleaned list is {self.cleaned_list}")
        return self.cleaned_list

    def clean_name_row(self, mode):
        if mode == "single line":
            self.cleaned_list = self.raw_list
        elif mode == "multiline":
            self.cleaned_list = [c.rpartition("\n")[2] for c in self.raw_list]
        else:
            raise ValueError("Mode parameter must be set to either 'single line' or 'multiline'")
        if re.search(NUMBER_AND_NAME_PATTERN, str(self.cleaned_list[0])):
            split_cell = str(self.cleaned_list[0]).split(" ", 1)
            self.cleaned_list[0] = int(split_cell[0])
            self.cleaned_list.insert(1, split_cell[1])
        return self.cleaned_list

    def clean_deductions_row(self):
        # Stringify and remove number of falls in brackets, split
        logger.debug(f"Raw deductions list is {self.raw_list}")

        split_row = []
        for e in self.raw_list:
            split_row.extend(str(e).split("\n"))

        row_less_falls = [re.sub(r"\(\d+\)", "", str(r)) for r in split_row[1:]]
        row_text = " ".join(row_less_falls)
        logger.debug(f"Row text after join is {row_text}")

        row_text = re.sub(DED_TOTAL_PATTERN, r"\1", row_text)
        logger.debug(f"Row text after total removal is {row_text}")

        ded_words = re.findall(DED_TYPE_PATTERN, row_text)
        ded_digits = re.findall(DED_POINT_PATTERN, row_text)

        logger.debug(f"ded words after regex {ded_words}")
        logger.debug(f"ded_digits after regex {ded_digits}")

        # Clean up ded types
        ded_words = [DED_ALIGNMENT_DIC[d.lower().strip()] if d.lower().strip() in DED_ALIGNMENT_DIC
                     else d.lower().strip() for d in ded_words]
        for d in ded_words:
            if d == 'total':
                del d
            elif d not in EXPECTED_DED_TYPES:
                logger.error(f"Detected unexpected deduction: {d}")
                sys.exit(1)

        # Remove other random numbers that might have ended up in the row, ensure all numbers negative
        ded_digits = [x for x in ded_digits if x is not None]
        ded_digits = [-1 * int(float(x)) if int(float(x)) > 0 else int(float(x)) for x in ded_digits]

        if len(ded_words) != len(ded_digits):
            logger.debug(f"Lol ya deductions lists are fucked girl: {ded_words} vs. {ded_digits}")
            sys.exit(1)

        ded_dic_raw = dict(zip(ded_words, ded_digits))
        ded_dic = {k: v for k, v in ded_dic_raw.items() if int(v) != 0}
        logger.debug(f"Returning deductions dic: {ded_dic})")
        return ded_dic

def is_nan(x):
    return x is np.nan or x != x