import re
import sys
import logging

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

DISC_CODES_DICS = {"LADIES_CODES": {re.compile(r"(?i)(lad(?:y|ies)|women).*score"): "Ladies",
                                    re.compile(r"data020[35]"): "Ladies"},
                   "MEN_CODES": {re.compile(r"(?i)(?<!wo)men.*score"): "Men", re.compile(r"data010[35]"): "Men"},
                   "PAIRS_CODES": {re.compile(r"(?i)pairs.*score"): "Pairs", re.compile(r"data030[35]"): "Pairs"},
                   "DANCE_CODES": {re.compile(r"(?i)danc.*score"): "IceDance", re.compile(r"data040[35]"): "IceDance"}}

SEGMENT_LIST = ["SP", "FS", "SD", "FP", "FD", "OD", "CD", "RD", "QA", "QB", "Prelim"]
SEGMENT_CORRECTIONS = {"Prelim": "QA", "FP": "FS"}
SUB_EVENT_DIC = {"Team": "team", "Preliminary": "qual", "QA": "qual_1", "QB": "qual_2"}


def _parse_category(string_input):
    return "Jr" if "Junior" in string_input or "Jr" in string_input else "Sr"


def _parse_sub_event(string_input):
    sub = [SUB_EVENT_DIC[s] for s in SUB_EVENT_DIC if s in string_input]
    if not sub:
        return None
    elif len(sub) > 1:
        logger.warning(f"Unexpectedly found multiple segment patterns in string input {string_input}. "
                       f"Will use the first ({sub[0]}).")
    return sub[0]


def _parse_segment(string_input, disc):
    new_format = re.search(r"data[0-9]{2}([0-9]{2})", string_input)
    if new_format:
        letter_1 = "S" if new_format.group(1) == "03" else "F"
        letter_2 = "D" if disc == "Dance" else "P"
        return letter_1 + letter_2
    else:
        raw_seg = [s for s in SEGMENT_LIST if s in string_input]
        if not raw_seg:
            sys.exit(f"Could not find segment pattern in {string_input}")
        elif len(raw_seg) > 1:
            if "Prelim" in raw_seg:
                raw_seg = ["Prelim"]
            else:
                logger.warning(f"Unexpectedly found multiple segment patterns in string input {string_input}. "
                               f"Will use the first ({raw_seg[0]}).")
        if raw_seg[0] in SEGMENT_CORRECTIONS:
            raw_seg = [SEGMENT_CORRECTIONS[raw_seg[0]]]
        return raw_seg[0]


def parse_discipline(string_input):
    for dic in DISC_CODES_DICS:
        for key in DISC_CODES_DICS[dic]:
            if re.search(key, string_input) and "novice" not in string_input.lower():
                logger.info(f"Code {key} matches {string_input}")
                return list(DISC_CODES_DICS[dic].values())[0]
    raise ValueError(f"Could not find discipline in {string_input}")


class Event:
    def __init__(self, name, year, start_date=None):
        self.name, self.year, self.start_date = name, year, start_date
        self.is_A_comp = True if self.name in ISU_A_COMPS else False
        self.is_h2_event = True if self.name in H2_EVENTS else False
        self.season = self._set_season() if self.year else None
        self.cs_flag = "CS" if self.name not in NATIONALS and not self.is_A_comp else None
        self.start_date = start_date

    def _set_season(self):
        season_start = self.year if not self.is_h2_event else self.year - 1
        return "sb" + str(season_start)


class Segment(Event):
    def __init__(self, id, name, year, start_date, sub_event, category, discipline, segment):
        super().__init__(name=name, year=year, start_date=start_date)
        self.id = id
        self.category = category
        self.discipline = discipline
        self.segment = segment
        self.sub_event = sub_event


class SegmentProtocols(Segment):
    def __init__(self, filename, discipline, id_dic):
        sd = datetime.strptime(filename.partition("_")[0], "%y%m%d").date()
        y = sd.year

        super().__init__(id=id_dic["segments"], name=filename.partition("_")[2].partition("_")[0], year=y, start_date=sd,
                         sub_event=_parse_sub_event(filename), category=_parse_category(filename),
                         discipline=discipline, segment=_parse_segment(filename, discipline))
        self.protocol_list = []
        logger.info(f"Instantiated SegmentProtocols object {self.name} ({self.sub_event}) {self.year} {self.category} "
                    f"{self.discipline} {self.segment}")

    def get_segment_dic(self):
        dic = vars(self)
        del dic["protocol_list"]
        del dic["search_string"]
        del dic["url"]
        logger.debug(f"Segment dic is {dic}")
        return dic
    #
    # def construct_elt_calls_dics(self):
    #     for p in self.protocol_list:
    #         for e in p.elements:
    #             elt_dic = vars(e)
    #             elt_dic["skate_id"] = self._generate_skate_id(protocol=p)


if __name__ == "__main__":
    # Woot tests
    g = SegmentProtocols("130418_4CC_LadiesJrFS", "Ladies", {"segments": 20})
    print(vars(g))