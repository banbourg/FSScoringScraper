import re
import logging
import unicodedata
import sys
import unittest

from psycopg2 import sql

logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)-5s - %(message)s",
                    level=logging.DEBUG,
                    datefmt='%Y-%m-%d %H:%M:%S')
logger = logging.getLogger(__name__)


try:
    import db_builder
    import settings
except ImportError as exc:
    sys.exit(f"Error: failed to import module ({exc})")


def _parse_name(full_name):
    exploded_name = full_name.split(" ")
    first_name_list, last_name_list = [], []
    for w in [word.replace(".", "") for word in exploded_name]:
        if len(w) > 1 and (w[1].isupper() or w[:2] == "Mc" or w[:2] == "O'" or (w[:3] == "Mac" and w[3].isupper())):
            last_name_list.append(w)
        else:
            first_name_list.append(w)
    return " ".join(first_name_list), " ".join(last_name_list), "".join(first_name_list), "".join(last_name_list)


def flatten_dict(init_dict):
    res_dict = {}
    if type(init_dict) is not dict:
        return res_dict

    for k, v in init_dict.items():
        if type(v) == dict:
            res_dict.update(flatten_dict(v))
        else:
            res_dict[k] = v

    return res_dict


class Person:
    def __init__(self, name_string, person_list, last_row_dic, season_observed, fed_observed, mode, cursor):

        self.first_name, self.last_name, self.tight_first_name, self.tight_last_name = _parse_name(name_string)
        self.full_name = self.first_name + " " + self.last_name
        self.fed_dic = {season_observed + "_fed": fed_observed}
        for k in self.fed_dic:
            if self.fed_dic[k] == "OAR":
                self.fed_dic[k] = "RUS"

        self.id = self._check_and_complete_record(person_list, last_row_dic, season_observed, mode, cursor)

    def _check_and_complete_record(self, person_list, last_row_dic, season_observed, mode, cursor):

        if db_builder.check_table_exists(mode, cursor):
            table = sql.Identifier(mode)
            field = season_observed + "_fed"

            cursor.execute(sql.SQL(f"SELECT id, {field} FROM {table} WHERE name = '{self.full_name}';"))
            prev_id = cursor.fetchall()
            assert prev_id is None or len(prev_id) == 1

            if prev_id:
                if prev_id[0][1] is None:
                    cursor.execute(sql.SQL(f"UPDATE {table} SET {field} = {self.fed_dic[field]} WHERE id = {prev_id};"))
                return int(prev_id[0][0])

        for person in person_list:
            if person.full_name == self.full_name:
                if season_observed + "_fed" not in person.fed_dic:
                    person.fed_dic[season_observed + "_fed"] = self.fed_dic[season_observed + "_fed"]
                return int(person.id)

        person_list.append(self)
        last_row_dic[mode] += 1
        return int(last_row_dic[mode] - 1)

    def get_dict(self):
        return flatten_dict(vars(self))


class SinglesSkater(Person):
    def __init__(self, name_row, skater_list, last_row_dic, season_observed, cursor):

        super().__init__(name_string=name_row.clean[1], person_list=skater_list, last_row_dic=last_row_dic,
                         season_observed=season_observed, fed_observed=name_row.clean[2], mode="competitors",
                         cursor=cursor)

        self.printout = self.full_name

        logger.debug(f"Instantiated SinglesSkater with id {self.id}, name "
                     f"{unicodedata.normalize('NFKD', self.full_name).encode('ascii','ignore')}, fed "
                     f"{self.fed_dic[season_observed + '_fed']}")


class Team:
    def __init__(self, name_row, skater_list, last_row_dic, season_observed, cursor):
        names = re.split(" / | - ", name_row.clean[1])
        try:
            self.lady = Person(name_string=names[0], person_list=skater_list, last_row_dic=last_row_dic,
                               season_observed=season_observed, fed_observed=name_row.clean[2], mode="competitors",
                               cursor=cursor)
            self.man = Person(name_string=names[1], person_list=skater_list, last_row_dic=last_row_dic,
                              season_observed=season_observed, fed_observed=name_row.clean[2], mode="competitors",
                              cursor=cursor)
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
    def __init__(self, name_string, last_row_dic, list_of_officials, season_observed, fed, cursor):
        name = name_string.partition(" ")[2] if "." in name_string else name_string

        super().__init__(name_string=name, person_list=list_of_officials, last_row_dic=last_row_dic,
                         season_observed=season_observed, fed_observed=fed, mode="officials", cursor=cursor)

        logger.debug(f"Instantiated official with id {self.id}, name "
                     f"{unicodedata.normalize('NFKD', self.full_name).encode('ascii','ignore')}, fed "
                     f"{self.fed_dic[season_observed + '_fed']}")


class Panel:
    def __init__(self, roles_table, last_row_dic, list_of_officials, sub_event, category, discipline, segment,
                 season_observed, cursor):
        self.role_dic = {}
        self.sub_event = sub_event
        self.category = category
        self.discipline = discipline
        self.segment = segment

        # Find increment (sometimes country appears twice)
        if roles_table:
            indices = [roles_table.index(r) for r in
                       ["Referee", "Technical Controller", "Technical Controller"]]
            first_entry = min(indices)
            increment = 4 if (roles_table[first_entry + 2] == roles_table[first_entry + 3]) else 3
            last = 16 * increment
            logger.debug(f"Table starts at {first_entry}, incrementing by {increment}, len {len(roles_table)}, "
                         f"stopping at {last}")

            for i in range(first_entry, min(last, len(roles_table) - 2), increment):
                logger.debug(f"i is {i}")
                # Align 'judge' notation with the one used in scoring tables
                if 'Judge' in roles_table[i] or 'No.' in roles_table[i]:
                    role = "J" + str(roles_table[i][-1]).zfill(2)
                else:
                    role = roles_table[i]

                official = Official(name_string=roles_table[i + 1], fed=roles_table[i + 2], last_row_dic=last_row_dic,
                                    list_of_officials=list_of_officials, season_observed=season_observed, cursor=cursor)

                self.role_dic[role] = official.id
        else:
            return

    def get_dict(self):
        return flatten_dict(vars(self))


class PersonTests(unittest.TestCase):
    def test_judges(self):
        conn, engine = db_builder.initiate_connections(settings.DB_CREDENTIALS)
        cursor = conn.cursor()
        lr = {"officials": 34}
        lof = []
        o1 = Official("Mrs. Akiko SUZUKI", lr, lof, "SB2013", "JPN", cursor)
        o2 = Official("Mr. Nobunari ODA", lr, lof, "SB2013", "JPN", cursor)
        o2 = Official("Mr. Nobunari ODA", lr, lof, "SB2014", "JPN", cursor)
        logger.debug(f"Next id assigned will be {lr['officials']}", cursor)
        assert len(lof) == 2
        assert lr["officials"] == 36


if __name__ == "__main__":
    unittest.main()
