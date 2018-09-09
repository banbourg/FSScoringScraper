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
    def __init__(self, name_row):
        super().__init__(name_string=name_row.clean[1], fed=name_row.clean[2])
        self.printout = self.full_name
        logger.debug(f"Instantiated SinglesSkater with name {unicodedata.normalize('NFKD', self.full_name).encode('ascii','ignore')}, fed {self.federation}")


class Team:
    def __init__(self, name_row):
        names = re.split(" / | - ", name_row.clean[1])
        try:
            self.lady = Person(name_string=names[0], fed=name_row.clean[2])
            self.man = Person(name_string=names[1], fed=name_row.clean[2])
        except IndexError as ie:
            sys.exit(f"Index error on one of {names}, {name_row.clean}: {ie}")
        self.team_name = self.lady.tight_last_name + "/" + self.man.tight_last_name
        self.printout = self.team_name
        logger.debug(f"Instantiated Team with name {unicodedata.normalize('NFKD', self.team_name).encode('ascii','ignore')}, fed {self.lady.federation}")

