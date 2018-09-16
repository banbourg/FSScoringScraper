import re
import logging
import unicodedata
import sys

logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)-5s - %(message)s",
                    level=logging.DEBUG,
                    datefmt='%Y-%m-%d %H:%M:%S')
logger = logging.getLogger(__name__)


class Person:
    def __init__(self, name_string, fed):  # anchor coordinates refers to where "Name has been found on the sheet
        self.first_name, self.last_name, self.tight_first_name, self.tight_last_name = self.__parse_name(name_string)
        self.full_name = self.first_name + " " + self.last_name
        self.federation = "RUS" if fed == "OAR" else fed

    def __parse_name(self, full_name):
        exploded_name = full_name.split(" ")
        first_name_list, last_name_list = [], []
        for w in [word.replace(".", "") for word in exploded_name]:
            if len(w) > 1 and (w[1].isupper() or w[:2] == "Mc" or w[:2] == "O'"):
                last_name_list.append(w)
            else:
                first_name_list.append(w)
        return " ".join(first_name_list), " ".join(last_name_list), "".join(first_name_list), "".join(last_name_list)


class SinglesSkater(Person):
    def __init__(self, name_row, last_row_dic, skater_list):
        super().__init__(name_string=name_row.clean[1], fed=name_row.clean[2])
        self.printout = self.full_name
        self.id = last_row_dic["competitors"]
        for skater in skater_list:
            if skater.printout == self.full_name and skater.federation == self.federation:
                self.id = skater.id
                break
        logger.debug(f"Instantiated SinglesSkater with id {self.id}, name "
                     f"{unicodedata.normalize('NFKD', self.full_name).encode('ascii','ignore')}, fed {self.federation}")


class Team:
    def __init__(self, name_row, last_row_dic, skater_list):
        names = re.split(" / | - ", name_row.clean[1])
        try:
            self.lady = Person(name_string=names[0], fed=name_row.clean[2])
            self.man = Person(name_string=names[1], fed=name_row.clean[2])
        except IndexError as ie:
            sys.exit(f"Index error on one of {names}, {name_row.clean}: {ie}")

        self.id = last_row_dic["competitors"]
        self.federation = self.lady.federation
        for skater in skater_list:
            if skater.printout == self.team_name and skater.federation == self.federation:
                self.id = skater.id
        self.team_name = self.lady.tight_last_name + "/" + self.man.tight_last_name
        self.printout = self.team_name
        for skater in skater_list:
            if skater.printout == self.team_name and skater.federation == self.federation:
                self.id = skater.id
        logger.debug(f"Instantiated Team with name "
                     f"{unicodedata.normalize('NFKD', self.team_name).encode('ascii','ignore')}, "
                     f"fed {self.lady.federation}")


class Official(Person):
    def __init__(self, name_string, fed, last_row_dic, judge_list):
        # Clean name for Mr., Ms.
        name = name_string.partition(" ")[2] if "." in name_string else name_string

        super().__init__(name, fed)
        self.id = last_row_dic["judges"]
        for judge in judge_list:
            if judge.full_name == self.full_name:
                self.id = judge.id

class Panel:
    def __init__(self):
        self.judge_dic = {}
        self.referee = None