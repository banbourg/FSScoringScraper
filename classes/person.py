import re
import logging
import unicodedata
import sys

logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)-5s - %(message)s",
                    level=logging.DEBUG,
                    datefmt='%Y-%m-%d %H:%M:%S')
logger = logging.getLogger(__name__)


def _parse_name(full_name):
    exploded_name = full_name.split(" ")
    first_name_list, last_name_list = [], []
    for w in [word.replace(".", "") for word in exploded_name]:
        if len(w) > 1 and (w[1].isupper() or w[:2] == "Mc" or w[:2] == "O'"):
            last_name_list.append(w)
        else:
            first_name_list.append(w)
    return " ".join(first_name_list), " ".join(last_name_list), "".join(first_name_list), "".join(last_name_list)


class Person:
    def __init__(self, name_string, person_list, last_row_dic, season_observed, fed_observed, mode):

        self.first_name, self.last_name, self.tight_first_name, self.tight_last_name = _parse_name(name_string)
        self.full_name = self.first_name + " " + self.last_name
        self.fed_dic = {season_observed + "_fed": fed_observed}

        self.id = self._set_id(person_list, last_row_dic, season_observed, mode)

        for k in self.fed_dic:
            if self.fed_dic[k] == "OAR":
                self.fed_dic[k] = "RUS"

    def _set_id(self, person_list, last_row_dic, season_observed, mode):
        for person in person_list:
            if person.full_name == self.full_name:
                person.fed_dic[season_observed + "_fed"] = self.fed_dic[season_observed + "_fed"]
                return person.id

        person_list.append(self)
        last_row_dic[mode] += 1
        return last_row_dic[mode] - 1


class SinglesSkater(Person):
    def __init__(self, name_row, skater_list, last_row_dic, season_observed):

        super().__init__(name_string=name_row.clean[1], person_list=skater_list, last_row_dic=last_row_dic,
                         season_observed=season_observed, fed_observed=name_row.clean[2], mode="competitors")

        self.printout = self.full_name

        logger.debug(f"Instantiated SinglesSkater with id {self.id}, name "
                     f"{unicodedata.normalize('NFKD', self.full_name).encode('ascii','ignore')}, fed "
                     f"{self.fed_dic[season_observed + '_fed']}")


class Team:
    def __init__(self, name_row, last_row_dic, skater_list, season_observed):
        names = re.split(" / | - ", name_row.clean[1])
        try:
            self.lady = Person(name_string=names[0], person_list=skater_list, last_row_dic=last_row_dic,
                               season_observed=season_observed, fed_observed=name_row.clean[2], mode="competitors")
            self.man = Person(name_string=names[1], person_list=skater_list, last_row_dic=last_row_dic,
                              season_observed=season_observed, fed_observed=name_row.clean[2], mode="competitors")
        except IndexError as ie:
            sys.exit(f"Index error on one of {names}, {name_row.clean}: {ie}")

        self.fed_dic = {season_observed + "_fed": self.lady.fed_dic[season_observed + "_fed"]}

        self.team_name = self.lady.tight_last_name + "/" + self.man.tight_last_name
        self.printout = self.team_name

        team_already_ided = False
        for team in skater_list:
            if team.printout == self.team_name:
                team_already_ided = True
                self.id = team.id
                team.fed_dic[season_observed + "_fed"] = self.fed_dic[season_observed + "_fed"]
                break

        if not team_already_ided:
            self.id = last_row_dic["competitors"]
            last_row_dic["competitors"] += 1
            skater_list.append(self)


        logger.debug(f"Instantiated Team with with id {self.id}, name "
                     f"{unicodedata.normalize('NFKD', self.team_name).encode('ascii','ignore')}, "
                     f"fed {self.fed_dic[season_observed + '_fed']}")


class Official(Person):
    def __init__(self, name_string, last_row_dic, list_of_officials, season_observed, fed):
        # Clean name for Mr., Ms.
        name = name_string.partition(" ")[2] if "." in name_string else name_string

        super().__init__(name_string=name, person_list=list_of_officials, last_row_dic=last_row_dic,
                         season_observed=season_observed, fed_observed=fed, mode="officials")

        logger.debug(f"Instantiated official with id {self.id}, name "
                     f"{unicodedata.normalize('NFKD', self.full_name).encode('ascii','ignore')}, fed "
                     f"{self.fed_dic[season_observed + '_fed']}")

class Panel:
    def __init__(self, roles_table, last_row_dic, list_of_officials):
        self.role_dic = {}

        # Find increment (sometimes country appears twice)
        indices = [roles_table.index(r) for r in
                   ["Referee", "Technical Controller", "Technical Controller"]]
        first_entry = min(indices)
        increment = 4 if (roles_table[first_entry + 2] == roles_table[first_entry + 3]) else 3
        last = 16 * increment

        for i in range(first_entry, last, increment):
            # Align 'judge' notation with the one used in scoring tables
            if 'Judge' in roles_table[i] or 'No.' in roles_table[i]:
                role = "J" + str(roles_table[i][-1]).zfill(2)
            else:
                role = roles_table[i]

            official = Official(name_string=roles_table[i + 1], fed=roles_table[i + 2], last_row_dic=last_row_dic, list_of_officials=list_of_officials)

            self.role_dic[role] = official.id


if __name__ == "__main__":
    # Woot I love unit tests
    lr = {"officials": 34}
    lof = []
    o1 = Official("Mrs. Akiko SUZUKI", lr, lof, "SB2013", "JPN")
    o2 = Official("Mr. Nobunari ODA", lr, lof, "SB2013", "JPN")
    o2 = Official("Mr. Nobunari ODA", lr, lof, "SB2014", "JPN")
    print(lr)
    for o_ in lof:
        print(vars(o_))