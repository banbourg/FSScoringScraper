import re
import sys
import logging

import glob
from openpyxl import load_workbook
from settings import READ_PATH
import pandas as pd
import numpy as np

from datetime import datetime

try:
    import person
    import datarow
except ImportError as exc:
    sys.stderr.write("Error: failed to import module ({})".format(exc))
    sys.exit(1)

logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)-5s - %(message)s",
                    level=logging.DEBUG,
                    datefmt='%Y-%m-%d %H:%M:%S')
logger = logging.getLogger(__name__)

NATIONALS = []

H2_EVENTS = ["WC", "WTT", "4CC", "OWG", "EC"]

ISU_A_COMPS = ["NHK", "TDF", "SC", "COR", "SA", "COC", "GPF", "WC", "4CC", "OWG", "WTT", "EC"]

SEARCHTERM_TO_DBNAME = {"nhk+trophy": "NHK", "rostelecom+cup": "COR", "france": "TDF", "canada": "SC", "russia": "COR",
                        "skate+america": "SA", "cup+of+china": "COC", "grand+prix+final": "GPF",
                        "world+figure+skating+championships": "WC", "four+continents+championship": "4CC",
                        "olympic+winter+games": "OWG", "world+team+trophy": "WTT",
                        "european+figure+skating+championships": "EC",
                        "trophee+eric+bompard": "TDF", "asian+open": "AO", "lombardia+trophy": "Lombardia",
                        "us+figure+skating+classic": "USClassic", "ondrej+nepela+trophy": "Nepela",
                        "autumn+classic+international": "ACI", "nebelhorn+trophy": "Nebelhorn",
                        "finlandia+trophy": "Finlandia", "tallinn+trophy": "Tallinn", "warsaw+cup": "Warsaw",
                        "golden+spin+zagreb": "GoldenSpin", "denkova+staviski+cup": "DenkovaStaviksi",
                        "ice+challenge": "IceChallenge", "ice+star": "IceStar", "volvo+open+cup": "Volvo",
                        "mordovian+ornament": "MordovianOrnament"}

DISC_CODES_DICS = {"LADIES_CODES": {re.compile(r"(?i)(lad(?:y|ies)|women).*score"): "Ladies",
                                   re.compile(r"data020[35]"): "Ladies"},
                   "MEN_CODES": {re.compile(r"(?i)(?<!wo)men.*score"): "Men",
                                re.compile(r"data010[35]"): "Men"},
                   "PAIRS_CODES": {re.compile(r"(?i)pairs.*score"): "Pairs",
                                  re.compile(r"data030[35]"): "Pairs"},
                   "DANCE_CODES": {re.compile(r"(?i)danc.*score"): "IceDance",
                                  re.compile(r"data040[35]"): "IceDance"}}

SEGMENT_LIST = ["SP", "FS", "SD", "FP", "FD", "OD", "CD", "RD", "QA", "QB", "Prelim"]
SEGMENT_CORRECTIONS = {"Prelim": "QA", "FP": "FS"}
SUB_EVENT_DIC = {"Team": "team", "Preliminary": "qual", "QA": "qual_1", "QB": "qual_2"}
SEG_IDENTIFIER_COLUMNS = ['index', 'season', 'event_start_date', 'cs_flag', 'event', 'sub_event', 'category', 'discipline',
                          'skater_name', 'segment']

class Event:
    def __init__(self, filename=None, search_phrase=None, search_year=None, homepage=None):
        """

        :param filename:
        :param search_phrase:
        :param search_year:
        """
        self.start_date, self.name, self.year, self.search_string, self.url = None, None, None, None, None
        if filename:
            self.__event_from_filename(filename)
        elif search_phrase and search_year:
            self.__event_from_search(search_phrase, search_year)
        else:
            raise ValueError("Event must be constructed from either a filename, a homepage url or a search & year")
        self.url = homepage if homepage else None
        self.is_A_comp = True if self.name in ISU_A_COMPS else False
        self.is_h2_event = True if self.name in H2_EVENTS else False
        self.season = self.__set_season() if self.year else None
        self.cs_flag = "CS" if self.name not in NATIONALS and not self.is_A_comp else None

    def __event_from_filename(self, filename):
        """

        :param filename:
        :return:
        """
        self.start_date = datetime.strptime(filename.partition("_")[0], "%y%m%d").date()
        self.name = filename.partition("_")[2].partition("_")[0]
        self.year = self.start_date.year

    def __event_from_search(self, search_phrase, search_year):
        """

        :param search_phrase:
        :param search_year:
        :return:
        """
        self.name = SEARCHTERM_TO_DBNAME[search_phrase]
        self.year = search_year
        self.search_string = search_phrase

    def __set_season(self):
        """Sets FS season from event year by checking which half of the season the event in question takes place in
        """
        season_start = self.year if not self.is_h2_event else self.year - 1
        return "SB" + str(season_start)


class Segment (Event):
    def __init__(self, filename=None, search_phrase=None, year=None, sublink=None, discipline=None):
        super().__init__(filename=filename, search_phrase=search_phrase, search_year=year)

        if not filename and not sublink:
            raise ValueError("Segment object must be constructed with either a filename or a searchphrase, year and "
                             "sublink")
        elif filename and sublink:
            raise ValueError("How are you even doing that, segment object must be constructed with EITHER a filename OR "
                             "a searchphrase, year and sublink")
        elif sublink:
            string_input = str(sublink.rpartition("/")[2].rpartition(".")[0])
        else:
            string_input = filename

        self.category = self.__parse_category(string_input)
        self.discipline = discipline if discipline else parse_discipline(string_input)
        self.segment = self.__parse_segment(string_input)
        self.sub_event = self.__parse_sub_event(string_input)

    def __parse_category(self, string_input):
        if "Junior" in string_input or "Jr" in string_input:
            return "Jr"
        else:
            return "Sr"

    def __parse_segment(self, string_input):
        new_format = re.search(r"data[0-9]{2}([0-9]{2})", string_input)
        if new_format:
            letter_1 = "S" if new_format.group(1) == "03" else "F"
            letter_2 = "D" if self.discipline == "Dance" else "P"
            return letter_1 + letter_2
        else:
            raw_seg = [s for s in SEGMENT_LIST if s in string_input]
            if not raw_seg:
                logger.error(f"Could not find segment pattern in {string_input} for {self.name} {self.year}")
                sys.exit(1)
            elif len(raw_seg) > 1:
                if "Prelim" in raw_seg:
                    raw_seg = ["Prelim"]
                else:
                    logger.warning(f"Unexpectedly found multiple segment patterns in string input {string_input}. "
                                   f"Will use the first ({raw_seg[0]}).")
            if raw_seg[0] in SEGMENT_CORRECTIONS:
                raw_seg = [SEGMENT_CORRECTIONS[raw_seg[0]]]
            return raw_seg[0]

    def __parse_sub_event(self, string_input):
        sub = [SUB_EVENT_DIC[s] for s in SUB_EVENT_DIC if s in string_input]
        if not sub:
            return None
        elif len(sub) > 1:
            logger.warning(f"Unexpectedly found multiple segment patterns in string input {string_input}. "
                           f"Will use the first ({sub[0]}).")
        return sub[0]


class SegmentProtocols(Segment):
    def __init__(self, filename=None, discipline=None):
        super().__init__(filename=filename, search_phrase=None, year=None, sublink=None, discipline=discipline)
        self.skate_list = []
        #self.sheet_judges = []
        #self.skate_id_list = []
        # if len(self.sheet_judges) > 1 and self.sheet_judges[-1] != self.sheet_judges[-2]:
        #     logger.info(f"Number of judges changed mid-segment from {self.sheet_judges[-2]} to {self.sheet_judges[-1]}")
        logger.info(f"Instantiated SegmentProtocols object {self.name} ({self.sub_event}) {self.year} {self.category} "
                    f"{self.discipline} {self.segment}")

    def generate_skate_id(self):
        if isinstance(self.competitors[-1], p.Team):
            name = self.competitors[-1].team_name
        else:
            name = self.competitors[-1].tight_full_name

        if self.sub_event:
            id = self.season + self.name + self.sub_event + self.category + self.discipline + name + self.segment
        else:
            id = self.season + self.name + self.category + self.discipline + name + self.segment
        logger.debug(f"skate_id set to {id}")
        return id

    def add_segment_identifiers(self, df, segment_competitors_list, segment_exploded_names):
        """
        Note: Couldn't use first name initials bc of Asado Mao and Asada Mai
        :param df:
        :param segment_competitors_list:
        :param segment_exploded_names:
        :return:
        """
        competitor_short_name = segment_exploded_names[-1][1] + segment_exploded_names[-1][0]
        df['season'] = self.season
        df['event_start_date'] = self.start_date
        df['cs_flag'] = self.cs_flag
        df['event'] = self.name
        df['sub_event'] = self.sub_event
        df['category'] = self.category
        df['discipline'] = self.discipline
        df['segment'] = self.segment
        for col in SEG_IDENTIFIER_COLUMNS:
            df.set_index(col, append=True, inplace=True)
        return df


def parse_discipline(string_input):
    for dic in DISC_CODES_DICS:
        for key in DISC_CODES_DICS[dic]:
            if re.search(key, string_input) and "novice" not in string_input.lower():
                logger.info(f"Code {key} matches {string_input}")
                return list(DISC_CODES_DICS[dic].values())[0]
    raise ValueError(f"Could not find discipline in {string_input}")


class SinglesSegmentProtocols (Segment):
    def __init__(self, filename=None, search_phrase=None, year=None, sublink=None):
        super().__init__(filename, search_phrase, year, sublink)

        #
        # def return_isu_abbrev(self, s):
        #     temp = [_f for _f in re.split(r'(\d+)', s) if _f]
        # return temp[0]

class IceDanceSegmentProtocols(SegmentProtocols):
    def __init__(self, filename, discipline):
        super().__init__(filename, discipline)


class PairsSegmentProtocols(SegmentProtocols):
    def __init__(self, filename, discipline):
        super().__init__(filename, discipline)