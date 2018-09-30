import logging
import re
import sys
import decimal as dec
import unittest

try:
    import datarow
    import person
except ImportError as exc:
    sys.exit("Error: failed to import module ({})".format(exc))

logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)-5s - %(message)s",
                    level=logging.DEBUG,
                    datefmt='%Y-%m-%d %H:%M:%S')
logger = logging.getLogger(__name__)

# ICE DANCE PATTERNS
old_choreo_elts = re.compile(r"^((?:Li|Sp)\+TRANS)$")
pattern_dance = re.compile(r"^(1[A-Z]{2}|2[A-Z]{2}|PSt)([B1-4])?\+kp([YTN]{1,4})(!?\*?)$")
old_pattern_dance_notation = re.compile(r"^(?i)([1-4]S[1-4])([B1-4])?(\*?)$")
another_old_pattern_dance_notation = re.compile(r"^(?i)((?:GW|VW|R|CC)[1-2]S(?:[eq]))([B1-4])?"
                                                r"(?:\+kp([YTN]{3,4}))?(\*?)$")
old_twizzles = re.compile(r"^((?:Ch|S|NtMi|FS|BS|Sq)?Tw)([B1-4])?(\*)?$")  # used to be \b
combo_lifts = re.compile(r"^([A-Za-z]{2,}Li)([B1-4])?(\*)?\+(([A-Za-z]{2,}Li)([B1-4])?|COMBO)(\*)?$")
step_twizzle_combo = re.compile(r"^([A-Za-z]{1,4}St)([B1-4])?(\*)?\+((?:Ch|S|NtMi|FS|BS)?Tw)([B1-4])?(\*)?$")

# PAIRS PATTERNS
new_twists = re.compile(r"^([1-4]?Tw)([B1-4])?([!e<*]{0,3})$")
old_twists = re.compile(r"^([1-4]?(Eu|T|S|Lo|F|Lz|A|LZ|LO)Tw)([B1-4])?([!e<*]{0,3})$")
throw_jumps = re.compile(r"^([1-4]?(Eu|T|S|Lo|F|Lz|A|LZ|LO)Th)([!e<*]{0,3})$")
old_lifts = re.compile(r"^([1-5]?(?:Eu|T|S|Lo|F|Lz|A|LZ|LO)Li)([B1-4])?([!e<*]{0,3})$")
other_pairs_elts = re.compile(r"^([1-5][A-Za-z]{2,3}(?<!Tw|Th|Eu|Lz|LZ|LO|Lo|Fe)(?<![TSFA])"
                              r"(?<!TwB|TTw|STw|FTw|ATw|ALi|TLi|FLi|SLi|Lze|LZe|LOe|Loe))([B1-4])?(\*?)$")
indiv_scored_elts = re.compile(r"^(?i)([A-Z]{2,})L([B1-4])?\+[A-Z]{2,}M([B1-4])?$")

# PAIRS AND SINGLES PATTERNS
jumps = re.compile(r"\b([1-4]?(Eu|T(?!w)|S|Lo|F|Lz|A|LZ|LO)(?![A-Za-df-z]))([e<*]{0,3})\+?(COMBO|SEQ|REP)?"
                   r"(?!eSt)(?!St)")
old_single_jump = re.compile(r"\b(Eu|T(?!w)|S|Lo|F|Lz|A|LZ|LO)$")

# CROSS-DISCIPLINE PATTERNS
spins = re.compile(r"^([A-Za-z]*Sp)(([1-4])p)?([B1-4])?(V([1-5])|V)?(\*?)$")
other_leveled_elts = re.compile(r"^(?i)([a-z]{2,}(?<!Tw|Sp|Th|Eu|Lz|LZ|LO|Lo)(?<!SpB|SpV)(?<!SpBV))([B1-4]?)(\*?)$")


# Used this to make sure the programme would break when it encountered something it hadn't seen before - can probs
# get rid of in refactoring
ELT_TYPES = {"IceDance": {"NtMiSt+STw": "step twizzle combo",
                          "Tw": "twizzles",
                          "StaLi": "lift",
                          "St": "steps",
                          "Li": "lift",
                          "Sp": "spin",
                          "PiF": "pivot",
                          "ChSl": "slide",
                          "RH": "pattern dance",
                          "FS": "pattern dance",
                          "1S": "pattern dance",
                          "2S": "pattern dance",
                          "3S": "pattern dance",
                          "4S": "pattern dance",
                          "GW": "pattern dance",
                          "PD": "pattern dance",
                          "CC": "pattern dance",
                          "YP": "pattern dance",
                          "BL": "pattern dance",
                          "QS": "pattern dance",
                          "RW": "pattern dance",
                          "MB": "pattern dance",
                          "TR": "pattern dance",
                          "AT": "pattern dance"
                          },
             "Pairs": {"Tw": "throw twist", "Th": "throw jump", "Li": "lift", "SpSq": "spiral", "Sp": "spin",
                       "Ds": "death spiral", "St": "steps", "ChSq": "choreo"},
             "Singles": {"St": "steps", "SpSq": "spiral", "ChSq": "choreo", "ChSp": "spiral", r"Sp": "spin"}
             }


def _parse_jumps(match_list, dic):
    logger.debug(f"Match list is {match_list}")
    sorted_tuples = [list(t) for t in zip(*match_list)]

    namechecked_jumps = []
    for j in sorted_tuples[0]:
        if re.search(old_single_jump, j):
            namechecked_jumps.append(re.sub(old_single_jump, r"1\1", j))
        else:
            namechecked_jumps.append(j)
    dic["elt_name"] = "+".join(namechecked_jumps)

    jump_keys = ["jump_" + str(j) for j in range(1, len(sorted_tuples[0]) + 1)]
    dic["jump_list"] = dict(zip(jump_keys, namechecked_jumps))

    dic["call_dic"] = {k + 1: v[2] if v[2] != "" else None for (k, v) in dict(enumerate(match_list)).items()}
    logger.log(15, f"Unconverted call dic is {dic['call_dic']}")
    for jump in dic["call_dic"]:
        if dic["call_dic"][jump] is not None and "*" in dic["call_dic"][jump]:
            dic["invalid_flag"] = 1
            dic["call_dic"][jump] = dic["call_dic"][jump].replace("*", "")

    flag_list = [f for f in sorted_tuples[3] if f != ""]
    dic["seq_flag"] = 1 if "SEQ" in flag_list else 0
    dic["combo_flag"] = 1 if ("+" in dic["elt_name"] and dic["seq_flag"] == 0) or "COMBO" in flag_list else 0
    dic["rep_flag"] = 1 if "REP" in flag_list else 0
    return dic


def _parse_unleveled_elts(match_list, dic):
    logger.debug(f"Match list is {match_list}")
    dic["elt_name"] = match_list[0]
    return dic

def _parse_new_twists(match_list, dic):
    logger.debug(f"Match list is {match_list}")
    dic["elt_name"] = match_list[0][0]
    dic["elt_level"] = match_list[0][1]
    dic["invalid_flag"] = 1 if "*" in match_list[0][2] else 0
    if "<<" in match_list[0][2]:
        dic["downgrade_flag"] = 1
    elif "<" in match_list[0][2]:
        dic["ur_flag"] = 1
    return dic


def _parse_name_level_elts(match_list, dic):
    logger.debug(f"Match list is {match_list}")
    dic["elt_name"] = match_list[0][0]
    dic["elt_level"] = match_list[0][1]
    dic["invalid_flag"] = 1 if "*" in match_list[0][2] else 0
    return dic


def _parse_pattern_dance(match_list, dic):
    dic["elt_name"] = match_list[0][0]
    dic["elt_level"] = match_list[0][1]
    dic["elt_kps"] = match_list[0][2]
    dic["interruption_flag"] = 1 if match_list[0][3] == "!" else 0
    dic["invalid_flag"] = 1 if match_list[0][3] == "*" else 0
    return dic


def _parse_spins(match_list, dic):
    dic["elt_name"] = match_list[0][0]
    dic["no_positions"] = match_list[0][2]
    dic["elt_level"] = match_list[0][3]
    dic["failed_spin_flag"] = 1 if match_list[0][4] != "" else 0
    dic["missed_reqs"] = int(match_list[0][5]) if match_list[0][5] != "" else None
    dic["invalid_flag"] = 1 if match_list[0][6] == "*" else 0
    return dic


def _parse_indiv_scored_elts(match_list, dic):
    dic["elt_name"] = match_list[0][0]
    dic["elt_level_lady"] = match_list[0][1]
    dic["elt_level_man"] = match_list[0][2]
    # Add handling for invalidation, but not sure what those look like for these elements yet
    # invalid_flag_lady =
    # invalid_flag_man =
    # invalid_flag = 1 if invalid_flag_lady == 1 or invalid_flag_man == 1 else 0
    return dic


def _parse_combo_lifts(match_list, dic):
    dic["elt_1_name"] = match_list[0][0]
    dic["elt_1_level"] = match_list[0][1]
    dic["elt_1_invalid"] = 1 if match_list[0][2] == "*" else 0

    if match_list[0][3] == "COMBO":
        dic["elt_name"] = dic["elt_1_name"] + "+" + match_list[0][3]
        dic["elt_2_name"] = None
        dic["elt_2_level"] = None
        dic["elt_2_invalid"] = None
    else:
        dic["elt_2_name"] = match_list[0][4]
        dic["elt_2_level"] = match_list[0][5]
        dic["elt_2_invalid"] = 1 if match_list[0][6] == "*" else 0
        dic["elt_name"] = dic["elt_1_name"] + "+" + dic["elt_2_name"]

    dic["invalid_flag"] = 1 if dic["elt_1_invalid"] == 1 or dic["elt_2_invalid"] == 1 else 0
    return dic


def _parse_throw_jumps(match_list, dic):
    dic["elt_name"] = match_list[0][0]
    dic["call_dic"] = {1: match_list[0][2] if match_list[0][2] != "" else None}
    if dic["call_dic"][1] is not None and "*" in dic["call_dic"][1]:
        dic["invalid_flag"] = 1
        dic["call_dic"][1] = dic["call_dic"][1].replace("*", "")
    return dic


def _parse_old_twists(match_list, dic):

    dic["elt_name"] = match_list[0][0]
    dic["elt_level"] = match_list[0][2] if match_list[0][2] != "" else None
    dic["invalid_flag"] = 1 if "*" in match_list[0][3] else 0
    if "<<" in match_list[0][3]:
        dic["downgrade_flag"] = 1
    elif "<" in match_list[0][3]:
        dic["ur_flag"] = 1
    return dic


def _parse_elt_scores(clean_row):
    bv, sov_goe = dec.Decimal(clean_row[0]), dec.Decimal(clean_row[1])
    total = dec.Decimal(str(clean_row[-1]))
    for c in clean_row[2:-1]:
        if c != "NS":
            goe = clean_row[2:-1]
            return bv, goe, sov_goe, total
    return bv, None, sov_goe, total


EXPECTED_PATTERNS = {"IceDance": [indiv_scored_elts, combo_lifts, spins, pattern_dance, old_twizzles, other_leveled_elts,
                                  old_pattern_dance_notation, another_old_pattern_dance_notation, step_twizzle_combo,
                                  old_choreo_elts],
                     "Singles": [jumps, spins, other_leveled_elts],
                     "Pairs": [throw_jumps, jumps, spins, new_twists, old_twists, other_pairs_elts, other_leveled_elts,
                               old_lifts]
                     }

PATTERN_PARSERS = {jumps: _parse_jumps,
                   indiv_scored_elts: _parse_indiv_scored_elts,
                   combo_lifts: _parse_combo_lifts,
                   pattern_dance: _parse_pattern_dance,
                   other_leveled_elts: _parse_name_level_elts,
                   old_pattern_dance_notation: _parse_name_level_elts,
                   another_old_pattern_dance_notation: _parse_pattern_dance,
                   old_twists: _parse_old_twists,
                   old_lifts: _parse_name_level_elts,
                   spins: _parse_spins,
                   throw_jumps: _parse_throw_jumps,
                   other_pairs_elts: _parse_name_level_elts,
                   new_twists: _parse_new_twists,
                   old_twizzles: _parse_name_level_elts,
                   step_twizzle_combo: _parse_combo_lifts,
                   old_choreo_elts: _parse_unleveled_elts
                   }


def parse_elt_name(text, meta_disc, parsed_dic):
    keys = PATTERN_PARSERS.keys() & set(EXPECTED_PATTERNS[meta_disc])
    parser_subset = {k: PATTERN_PARSERS[k] for k in keys}

    # Check for H2 flag
    if text.endswith(" x"):
        parsed_dic["h2_bonus_flag"] = 1
        text = text[:-2]

    # Remove duplicate calls:
    if text.endswith(" <") and "<" in text[:-2]:
        text = text[:-2]
    if text.endswith(" <<") and "<<" in text[:-3]:
        text = text[:-3]

    # Remove any calls we'll need to impute later
    logger.debug(f"Text is {text}")
    if " " in text:
        calls_to_impute = text.partition(" ")[2]
        text = text.partition(" ")[0]
    else:
        calls_to_impute = None

    logger.log(15, f"After shortening, parsing {text}")

    # Check only one match
    searches = [re.findall(p, text) for p in EXPECTED_PATTERNS[meta_disc]]
    filtered_searches = [s for s in searches if s != []]
    if not filtered_searches:
        raise ValueError(f"Could not find elt matching expected patterns in {text}")
    elif len(filtered_searches) > 1:
        raise ValueError(f"Found multiple parsing possibilities for {text}: {searches}")

    # Use parser specific to each detected pattern, and impute any calls
    for pattern in parser_subset:
        if re.findall(pattern, text):
            return parser_subset[pattern](match_list=re.findall(pattern, text), dic=parsed_dic), calls_to_impute


def _impute_jump_calls(parsed_dic, calls_to_impute):
    logger.debug(f"Entering impute_jump_calls: {parsed_dic}, {calls_to_impute}")
    jumps_list = parsed_dic["elt_name"].split("+")
    if parsed_dic["combo_flag"] == 0 and parsed_dic["seq_flag"] == 0:
        if parsed_dic["call_dic"][1]:
            parsed_dic["call_dic"][1] += calls_to_impute
        else:
            parsed_dic["call_dic"][1] = calls_to_impute
        calls_to_impute = None
    else:
        edge_calls = [ec for ec in ["e", "!"] if ec in calls_to_impute]
        if len(edge_calls) > 1:
            sys.exit(f"Err your jumps have multiple edge calls to impute fuck your life: {calls_to_impute}")
        if edge_calls:
            no_edge_jumps, edge_jump_placement = 0, []
            for i in range(0, len(jumps_list)):
                if any(x in jumps_list[i] for x in ["F", "Lz"]):
                    no_edge_jumps += 1
                    edge_jump_placement.append(i + 1)
            if no_edge_jumps == 1:
                if parsed_dic["call_dic"][edge_jump_placement[0]]:
                    parsed_dic["call_dic"][edge_jump_placement[0]] += edge_calls[0]
                else:
                    parsed_dic["call_dic"][edge_jump_placement[0]] = edge_calls[0]
                calls_to_impute = calls_to_impute.replace(edge_calls[0], "")
            elif no_edge_jumps == 0:
                sys.exit(f"Found an edge call but no edge jumps so fuck me I guess {jumps_list}, "
                         f"{calls_to_impute}")
    return parsed_dic, calls_to_impute


def _convert_call_dic(call_dic, season):
    logger.debug(f"Call dic is {call_dic}")
    if not call_dic:
        return {}
    converted_dic = {}
    for i in range(1, len(call_dic) + 1):
        jump = "jump_" + str(i)
        if int(season[-2:]) < 10:
            converted_dic[jump + "_ur"] = 1 if call_dic[i] and "<" in call_dic[i] else 0
            converted_dic[jump + "_downgrade"] = 0
        else:
            converted_dic[jump + "_ur"] = 1 if call_dic[i] and "<" in call_dic[i] and "<<" not in call_dic[i] else 0
            converted_dic[jump + "_downgrade"] = 1 if call_dic[i] and "<<" in call_dic[i] else 0
        converted_dic[jump + "_sev_edge"] = 1 if call_dic[i] and "e" in call_dic[i] else 0
        converted_dic[jump + "_unc_edge"] = 1 if call_dic[i] and "!" in call_dic[i] else 0

    for call in ["ur", "downgrade", "sev_edge", "unc_edge"]:
        converted_dic[call + "_flag"] = 1 if 1 in [v for k, v in converted_dic.items() if k.endswith(call)] else 0

    return converted_dic


class Element:
    def __init__(self, meta_disc, id, no, name, bv, goe, sov_goe, total, invalid_flag):
        if sum([bv, sov_goe]).compare(total) != dec.Decimal("0"):
            raise ValueError(f"Instantiation of element {name} failed as bv ({bv}) and goe ({sov_goe}) did not sum to "
                             f"total ({total})")
        self.id = id
        self.meta_discipline = meta_disc
        self.element_name = name
        self.element_no = no
        self.element_type = self._classify_elt()
        self.bv = dec.Decimal(bv)

        judge_keys = ["J" + str(j).zfill(2) for j in range(1, len(goe) + 1)] if goe else None
        self.goe_dic = dict(zip(["element_id"] + judge_keys, [self.id] + goe)) if goe else None

        self.sov_goe = dec.Decimal(sov_goe)
        self.total = dec.Decimal(total)
        self.invalid_flag = invalid_flag
        logger.log(15, f"Instantiated Element object: {self.id}, no {self.element_no}, {self.element_name} "
                       f"({self.element_type}), {self.bv} + {self.sov_goe} = {self.total}, "
                       f"{'invalid' if self.invalid_flag == 1 else 'valid'}")

    def _classify_elt(self):
        for key in ELT_TYPES[self.meta_discipline]:
            if key in self.element_name:
                return ELT_TYPES[self.meta_discipline][key]
        if re.search(jumps, self.element_name):
            return "jump"
        logger.error(f"Could not find element type for {self.element_name}")
        sys.exit(f"Could not find element type for {self.element_name}")

    def get_element_dic(self):
        dic = dict(vars(self))
        del dic["goe_dic"]
        del dic["case"]
        flat_dic = person.flatten_dict(dic)
        del flat_dic["meta_discipline"]
        return flat_dic


class IceDanceElement(Element):
    def __init__(self, elt_row, season, last_row_dic):
        logger.log(15, f"Raw elt row is {elt_row.row_label}, {elt_row.data}")
        parsed_dic = {"elt_name": None, "elt_1_name": None, "elt_2_name": None,
                      "elt_level": None, "elt_level_lady": None, "elt_level_man": None,
                      "elt_1_level": None, "elt_2_level": None, "elt_kps": None,
                      "elt_1_invalid": 0, "elt_2_invalid": 0, "invalid_flag": 0, "h2_bonus_flag": 0,
                      "interruption_flag": None}

        parsed_dic, calls_to_impute = parse_elt_name(text=elt_row.row_label, meta_disc="IceDance", parsed_dic=parsed_dic)
        bv, goe, sov_goe, total = _parse_elt_scores(elt_row.data)

        logger.debug(f"Parsed dic is {parsed_dic}")

        super().__init__(meta_disc="IceDance",
                         id=last_row_dic["elements"],
                         no=elt_row.row_no,
                         name=parsed_dic["elt_name"],
                         bv=bv,
                         goe=goe,
                         sov_goe=sov_goe,
                         total=total,
                         invalid_flag=parsed_dic["invalid_flag"])

        self.elt_1_name, self.elt_2_name = parsed_dic["elt_1_name"], parsed_dic["elt_2_name"]
        self.elt_level = parsed_dic["elt_level"]
        self.elt_level_lady, self.elt_level_man = parsed_dic["elt_level_lady"], parsed_dic["elt_level_man"]
        self.elt_1_level, self.elt_2_level = parsed_dic["elt_1_level"], parsed_dic["elt_2_level"]
        self.elt_kps = parsed_dic["elt_kps"]
        self.interruption_flag = parsed_dic["interruption_flag"]

        self.case = elt_row.case

        if calls_to_impute and "*" in calls_to_impute:
            self.invalid_flag = 1

        logger.log(15, f"Attributes for elt {self.element_name} are {self.get_element_dic()}")


class SinglesElement(Element):
    def __init__(self, elt_row, season, last_row_dic):
        logger.log(15, f"Raw elt row is {elt_row.row_label}, {elt_row.data}")
        parsed_dic = {"elt_name": None, "jump_list": None, "call_dic": None,
                      "elt_level": None, "no_positions": None, "failed_spin_flag": None,
                      "missed_reqs": None, "combo_flag": None, "seq_flag": None, "rep_flag": None,
                      "invalid_flag": 0, "h2_bonus_flag": 0}

        parsed_dic, calls_to_impute = parse_elt_name(text=elt_row.row_label, meta_disc="Singles", parsed_dic=parsed_dic)
        bv, goe, sov_goe, total = _parse_elt_scores(elt_row.data)

        super().__init__(meta_disc="Singles",
                         id=last_row_dic["elements"],
                         no=elt_row.row_no,
                         name=parsed_dic["elt_name"],
                         bv=bv,
                         goe=goe,
                         sov_goe=sov_goe,
                         total=total,
                         invalid_flag=parsed_dic["invalid_flag"])

        self.jump_list = parsed_dic["jump_list"]
        self.elt_level = parsed_dic["elt_level"]
        self.no_positions, self.failed_spin_flag = parsed_dic["no_positions"], parsed_dic["failed_spin_flag"]
        self.missed_reqs, self.combo_flag = parsed_dic["missed_reqs"], parsed_dic["combo_flag"]
        self.seq_flag, self.rep_flag = parsed_dic["seq_flag"], parsed_dic["rep_flag"]
        self.h2_bonus_flag = parsed_dic["h2_bonus_flag"]

        if self.element_type == "jump" and calls_to_impute:
            parsed_dic, calls_to_impute = _impute_jump_calls(parsed_dic=parsed_dic, calls_to_impute=calls_to_impute)

        self.call_dic = _convert_call_dic(parsed_dic["call_dic"], season)

        self.case = elt_row.case

        if calls_to_impute and "*" in calls_to_impute:
            self.invalid_flag = 1

        logger.log(15, f"Attributes for elt {self.element_name} are {self.get_element_dic()}")


class PairsElement(Element):
    def __init__(self, elt_row, season, last_row_dic):
        logger.log(15, f"Raw elt row is {elt_row.row_label}, {elt_row.data}")
        parsed_dic = {"elt_name": None, "jump_list": None, "call_dic": None,
                      "elt_level": None, "no_positions": None, "failed_spin_flag": None,
                      "missed_reqs": None, "combo_flag": None, "seq_flag": None, "rep_flag": None,
                      "invalid_flag": 0, "h2_bonus_flag": 0, "ur_flag": 0, "downgrade_flag": 0}

        parsed_dic, calls_to_impute = parse_elt_name(text=elt_row.row_label, meta_disc="Pairs", parsed_dic=parsed_dic)
        bv, goe, sov_goe, total = _parse_elt_scores(elt_row.data)

        super().__init__(meta_disc="Pairs",
                         id=last_row_dic["elements"],
                         no=elt_row.row_no,
                         name=parsed_dic["elt_name"],
                         bv=bv, goe=goe,
                         sov_goe=sov_goe,
                         total=total,
                         invalid_flag=parsed_dic["invalid_flag"])

        self.jump_list = parsed_dic["jump_list"]
        self.elt_level = parsed_dic["elt_level"]
        self.no_positions, self.failed_spin_flag = parsed_dic["no_positions"], parsed_dic["failed_spin_flag"]
        self.missed_reqs, self.combo_flag = parsed_dic["missed_reqs"], parsed_dic["combo_flag"]
        self.seq_flag, self.rep_flag = parsed_dic["seq_flag"], parsed_dic["rep_flag"]

        if self.element_type == "jump" and calls_to_impute:
            parsed_dic, calls_to_impute = _impute_jump_calls(parsed_dic=parsed_dic, calls_to_impute=calls_to_impute)
        else:
            self.ur_flag = parsed_dic["ur_flag"]
            self.downgrade_flag = parsed_dic["downgrade_flag"]

        self.h2_bonus_flag = parsed_dic["h2_bonus_flag"]

        self.call_dic = _convert_call_dic(parsed_dic["call_dic"], season)

        self.case = elt_row.case

        if calls_to_impute and "*" in calls_to_impute:
            self.invalid_flag = 1

        logger.log(15, f"Attributes for elt {self.element_name} are {self.get_element_dic()}")


class ElementTests(unittest.TestCase):
    def test_adding_1(self):
        test = "2Lz+2T+Lo"
        match_list = re.findall(jumps, test)
        print(f"Match list is {match_list}")
        sorted_tuples = [list(t) for t in zip(*match_list)]

        namechecked_jumps = []
        for j in sorted_tuples[0]:
            if re.search(old_single_jump, j):
                namechecked_jumps.append(re.sub(old_single_jump, r"1\1", j))
            else:
                namechecked_jumps.append(j)
        elt_name = "+".join(namechecked_jumps)

        jump_keys = ["jump_" + str(j) for j in range(1, len(sorted_tuples[0]) + 1)]
        jump_dic = dict(zip(jump_keys, namechecked_jumps))
        assert elt_name == "2Lz+2T+1Lo"
        assert jump_dic["jump_3"] == "1Lo"

if __name__ == "__main__":
    unittest.main()