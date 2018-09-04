import logging
import re
import sys

try:
    import datarow
except ImportError as exc:
    sys.stderr.write("Error: failed to import module ({})".format(exc))
    sys.exit(1)

logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)-5s - %(message)s",
                    level=logging.DEBUG,
                    datefmt='%Y-%m-%d %H:%M:%S')
logger = logging.getLogger(__name__)

old_pattern_dance_notation = re.compile(r"^(?i)([1-2]S[1-4])$")
indiv_scored_elts = re.compile(r"^(?i)([A-Z]{2,})L([B1-4])\+[A-Z]{2,}M([B1-4])$")
combo_nonjump_elts = re.compile(r"^(?i)([A-Z]{2,})([B1-4])\+([A-Z]{2,})([B1-4])$")
pattern_dance = re.compile(r"^(1[A-Z]{2}|2[A-Z]{2})([B1-4])\+kp([YTN]{3,4})$")
other_leveled_elts = re.compile(r"^(?i)([a-z]{2,})([B1-4]{0,1})$")
jump = re.compile(r"[1-4](T|S|Lo|F|Lz|A|LZ|LO)")


ELT_PATTERNS = {"IceDance": [indiv_scored_elts, combo_nonjump_elts, pattern_dance, other_leveled_elts,
                             old_pattern_dance_notation]}
ELT_TYPES =  {"IceDance": {"Tw": "twizzles", "St": "steps", "Li": "lift", "Sp": "spin", "RH": "pattern_dance",
                           "FS": "pattern_dance", "ChSl": "slide", "1S": "pattern_dance", "2S": "pattern_dance"},
              "Pairs": {"Tw": "throw_twist", "Th": "throw_jump", "Li": "lift", "Sp": "spin", "Ds": "death_spiral",
                        "St": "steps"}
              }


class Element:
    def __init__(self, no, name, type, bv, goe, sov_goe, total):
        if round(bv + sov_goe,2) != total:
            raise ValueError(f"Instantiation of element {name} failed as bv ({bv}) and goe ({sov_goe}) did not sum to "
                             f"total ({total})")
        self.name = name
        self.no = no
        self.type = type
        self.bv = bv
        self.goe = goe
        self.sov_goe = sov_goe
        self.total = total
        logger.debug(f"Instantiated Element object: {self.no}, {self.name} ({self.type}), {self.bv} + {self.sov_goe} "
                     f"= {self.total}")

    def _parse_elt_level(self, elt_row):
        if self.type != "jump":
            return re.search(r"\d$", elt_row).group(0)
        else:
            return None

    def _classify_elt(self, elt_name, disc):
        for key in ELT_TYPES[disc]:
            if key in elt_name:
                return ELT_TYPES[disc][key]
        if re.search(jump, elt_name):
            return "jump"
        logger.error(f"Could not find element type for {elt_name}")
        sys.exit(1)

    def _parse_elt_scores(self, elt_row, judges):
        cutoff = -1 - judges
        factored_totals = datarow.DataRow(raw_list=elt_row[2:cutoff]).clean_scores_row(mode="float")
        bv, sov_goe = factored_totals[0], factored_totals[1]
        goe = datarow.DataRow(raw_list=elt_row[cutoff:-1]).clean_scores_row(mode="int")
        total = float(elt_row[-1])
        return bv, goe, sov_goe, total


class IceDanceElement(Element):
    def __init__(self, elt_row, disc, judges):
        logger.debug(elt_row)

        # Parse element name, levels and keypoints
        elt_name, elt_level, elt_level_lady, elt_level_man, elt_1_name, elt_1_level, elt_2_name, elt_2_level, elt_kps = self._parse_elt_name(elt_row[1])
        elt_type = self._classify_elt(elt_name, disc)

        # Parse elt scores
        bv, goe, sov_goe, total = self._parse_elt_scores(elt_row, judges)
        super().__init__(no=elt_row[0], name=elt_name, type=elt_type, bv=bv, goe=goe, sov_goe=sov_goe, total=total)

        self.elt_level = elt_level
        self.elt_level_lady, self.elt_level_man = elt_level_lady, elt_level_man
        self.elt_1_name, self.elt_1_level = elt_1_name, elt_1_level
        self.elt_2_name, self.elt_2_level = elt_2_name, elt_2_level
        self.elt_kps = elt_kps

    def _parse_elt_name(self, text):
        keys = ["indiv_scored_elts", "combo_nonjump_elts", "pattern_dance", "other_leveled_elts",
                "old_pattern_dance_notation"]

        searches = [re.search(pattern, text) for pattern in ELT_PATTERNS["IceDance"]]
        filtered_searches = [s for s in searches if s is not None]

        if not filtered_searches:
            raise ValueError(f"Could not find elt matching expected patterns in {text}")
        dic = dict(zip(keys, searches))

        elt_name, elt_level, elt_level_lady, elt_level_man = None, None, None, None
        elt_1_name, elt_1_level, elt_2_name, elt_2_level, elt_kps = None, None, None, None, None
        if dic["indiv_scored_elts"]:
            elt_name = dic["indiv_scored_elts"].group(1)
            elt_level_lady = dic["indiv_scored_elts"].group(2)
            elt_level_man = dic["indiv_scored_elts"].group(3)
        elif dic["combo_nonjump_elts"]:
            elt_1_name = dic["combo_nonjump_elts"].group(1)
            elt_1_level = dic["combo_nonjump_elts"].group(2)
            elt_2_name = dic["combo_nonjump_elts"].group(3)
            elt_2_level = dic["combo_nonjump_elts"].group(4)
            elt_name = elt_1_name + "+" + elt_2_name
        else:
            elt_name = filtered_searches[0].group(1)
            try:
                elt_level = int(filtered_searches[0].group(2))
            except IndexError:
                pass
            except ValueError:
                pass
            try:
                elt_kps = filtered_searches[0].group(3)
            except IndexError:
                pass
        return elt_name, elt_level, elt_level_lady, elt_level_man, elt_1_name, elt_1_level, elt_2_name, elt_2_level, elt_kps


class PairsElement(Element):
    def __init__(self, elt_row, disc, judges):
        logger.debug(elt_row)
        elt_name, elt_level, elt_kp = self._parse_elt_name(elt_row)
        elt_type = self._classify_elt(elt_name, disc)
        super().__init__(no=elt_row[0], name=elt_name, type=elt_type)

    def _parse_elt_name(self, text):
        return True
# ADD FETCHING CALLS

class SinglesElement(Element):
    def __init__(self, elt_row, disc, judges):
        logger.debug(elt_row)
        elt_name, elt_level = self._parse_elt_name(elt_row[1])

        elt_type = self._classify_elt(elt_name, disc)
        super().__init__(no=elt_row[0], name=elt_name, type=elt_type)

    def _parse_elt_name(self, text):
        keys = ["indiv_scored_elts", "combo_nonjump_elts", "pattern_dance", "other_leveled_elts",
                "old_pattern_dance_notation"]

        searches = [re.search(pattern, text) for pattern in ELT_PATTERNS["IceDance"]]
        filtered_searches = [s for s in searches if s is not None]

        if not filtered_searches:
            raise ValueError(f"Could not find elt matching expected patterns in {text}")
        dic = dict(zip(keys, searches))

        elt_name, elt_level, elt_level_lady, elt_level_man = None, None, None, None
        elt_1_name, elt_1_level, elt_2_name, elt_2_level, elt_kps = None, None, None, None, None
        if dic["indiv_scored_elts"]:
            elt_name = dic["indiv_scored_elts"].group(1)
            elt_level_lady = dic["indiv_scored_elts"].group(2)
            elt_level_man = dic["indiv_scored_elts"].group(3)
        elif dic["combo_nonjump_elts"]:
            elt_1_name = dic["combo_nonjump_elts"].group(1)
            elt_1_level = dic["combo_nonjump_elts"].group(2)
            elt_2_name = dic["combo_nonjump_elts"].group(3)
            elt_2_level = dic["combo_nonjump_elts"].group(4)
            elt_name = elt_1_name + "+" + elt_2_name
        else:
            elt_name = filtered_searches[0].group(1)
            try:
                elt_level = int(filtered_searches[0].group(2))
            except IndexError:
                pass
            except ValueError:
                pass
            try:
                elt_kps = filtered_searches[0].group(3)
            except IndexError:
                pass
        return elt_name, elt_level, elt_level_lady, elt_level_man, elt_1_name, elt_1_level, elt_2_name, elt_2_level, elt_kps
