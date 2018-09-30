import re
import os
import logging
import unicodedata
import sys
import unittest

from psycopg2 import sql

logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)-5s - %(message)s",
                    level=logging.DEBUG,
                    datefmt='%Y-%m-%d %H:%M:%S')
logger = logging.getLogger(__name__)

sys.path.extend([os.path.abspath("../.."), os.path.abspath("..")])

try:
    import db_builder
    import settings
except ImportError as exc:
    sys.exit(f"Error: failed to import module ({exc})")


def _parse_name(full_name):
    exploded_name = full_name.split(" ")
    first_name_list, last_name_list = [], []
    for w in [word.replace(".", "").strip() for word in exploded_name]:
        if len(w) > 1 and (w[1].isupper() or w[:2] == "Mc" or w[:2] == "O'" or (w[:3] == "Mac" and w[3].isupper())
           or w == "van" or w == "von"):
            last_name_list.append(w.upper())
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
    def __init__(self, name_string, person_list, last_row_dic, season_observed, fed_observed, mode, conn_dic):

        self.first_name, self.last_name, self.tight_first_name, self.tight_last_name = _parse_name(name_string)
        self.full_name = self.first_name + " " + self.last_name
        self.tight_full_name = self.tight_first_name + " " + self.tight_last_name
        self.fed_dic = {season_observed + "_fed": fed_observed}
        for k in self.fed_dic:
            if self.fed_dic[k] == "OAR":
                self.fed_dic[k] = "RUS"

        self.id = self._check_and_complete_record(person_list, last_row_dic, season_observed, mode, conn_dic)

    def _check_and_complete_record(self, person_list, last_row_dic, season_observed, mode, conn_dic):
        field = season_observed + "_fed"
        if db_builder.check_table_exists(mode, conn_dic["cursor"]):
            table = sql.Identifier(mode)
            conn_dic["cursor"].execute(sql.SQL("SELECT id, {} FROM {} WHERE tight_full_name=%s;")
                                       .format(sql.Identifier(field), table),
                                       (self.tight_full_name,))
            prev_id = conn_dic["cursor"].fetchall()
            try:
                assert len(prev_id) in [0, 1]
            except AssertionError as ae:
                logger.error(f"prev_id returned {prev_id}: {ae}")

            if prev_id:
                if prev_id[0][1] is None or (prev_id[0][1] == "ISU" and self.fed_dic[field] != "ISU"):
                    query = sql.SQL("UPDATE {} SET {} = %s WHERE id = %s;").format(table, sql.Identifier(field))
                    conn_dic["cursor"].execute(query, (self.fed_dic[field], prev_id[0][0]))
                    conn_dic["conn"].commit()
                return int(prev_id[0][0])

        for person in person_list:
            if isinstance(person, Person) and person.tight_full_name == self.tight_full_name:
                if field not in person.fed_dic or (person.fed_dic[field] == "ISU" and self.fed_dic[field] != "ISU"):
                    person.fed_dic[season_observed + "_fed"] = self.fed_dic[season_observed + "_fed"]
                return int(person.id)

        person_list.append(self)
        last_row_dic[mode] += 1
        return int(last_row_dic[mode] - 1)

    def get_competitor_dict(self):
        dic = {"id": self.id,
               "competitor_name": self.full_name,
               "competitor_type": "person",
               "spaced_first_name": self.first_name,
               "spaced_last_name": self.last_name,
               "tight_full_name": self.tight_full_name,
               "tight_first_name": self.tight_first_name,
               "tight_last_name": self.tight_last_name,
               "dic": self.fed_dic}
        return flatten_dict(dic)


class SinglesSkater(Person):
    def __init__(self, name_row, competitor_list, last_row_dic, season_observed, conn_dic):

        super().__init__(name_string=name_row.data[1], person_list=competitor_list, last_row_dic=last_row_dic,
                         season_observed=season_observed, fed_observed=name_row.data[2], mode="competitors",
                         conn_dic=conn_dic)

        logger.log(15, f"Instantiated SinglesSkater with id {self.id}, name "
                       f"{unicodedata.normalize('NFKD', self.full_name).encode('ascii','ignore')}, fed "
                       f"{self.fed_dic[season_observed + '_fed']}")


class Team:
    def __init__(self, name_row, competitor_list, last_row_dic, season_observed, conn_dic):
        names = re.split(" / | - ", name_row.data[1])
        try:
            self.lady = Person(name_string=names[0], person_list=competitor_list, last_row_dic=last_row_dic,
                               season_observed=season_observed, fed_observed=name_row.data[2], mode="competitors",
                               conn_dic=conn_dic)
            self.man = Person(name_string=names[1], person_list=competitor_list, last_row_dic=last_row_dic,
                              season_observed=season_observed, fed_observed=name_row.data[2], mode="competitors",
                              conn_dic=conn_dic)
        except IndexError as ie:
            sys.exit(f"Index error on one of {names}, {name_row.data}: {ie}")

        self.fed_dic = {season_observed + "_fed": self.lady.fed_dic[season_observed + "_fed"]}

        self.team_name = self.lady.tight_last_name + "/" + self.man.tight_last_name

        self.id = self._check_and_complete_record(competitor_list=competitor_list,
                                                  last_row_dic=last_row_dic,
                                                  season_observed=season_observed,
                                                  conn_dic=conn_dic)

        logger.log(15, f"Instantiated Team with with id {self.id}, lady id {self.lady.id}, man id {self.man.id}, name "
                       f"{unicodedata.normalize('NFKD', self.team_name).encode('ascii','ignore')}, "
                       f"fed {self.fed_dic[season_observed + '_fed']}")

    def _check_and_complete_record(self, competitor_list, last_row_dic, season_observed, conn_dic):
        field = season_observed + "_fed"
        if db_builder.check_table_exists("competitors", conn_dic["cursor"]):
            table = sql.Identifier("competitors")
            conn_dic["cursor"].execute(sql.SQL("SELECT id, {} FROM {} WHERE competitor_name=%s;")
                                       .format(sql.Identifier(field), table),
                                       (self.team_name,))
            prev_id = conn_dic["cursor"].fetchall()
            try:
                assert len(prev_id) in [0, 1]
            except AssertionError as ae:
                logger.error(f"prev_id returned {prev_id}: {ae}")

            if prev_id:
                if prev_id[0][1] is None:
                    query = sql.SQL("UPDATE {} SET {} = %s WHERE id = %s;").format(table, sql.Identifier(field))
                    conn_dic["cursor"].execute(query, (self.fed_dic[field], prev_id[0][0]))
                    conn_dic["conn"].commit()
                return int(prev_id[0][0])

        for c in competitor_list:
            if isinstance(c, Team) and c.team_name == self.team_name:
                self.id = c.id
                c.fed_dic[season_observed + "_fed"] = self.fed_dic[season_observed + "_fed"]
                if field not in c.fed_dic:
                    c.fed_dic[season_observed + "_fed"] = self.fed_dic[season_observed + "_fed"]
                return int(c.id)

        competitor_list.append(self)
        last_row_dic["competitors"] += 1
        return int(last_row_dic["competitors"] - 1)

    def get_competitor_dict(self):
        dic = {"id": self.id,
               "competitor_name": self.team_name,
               "competitor_type": "team",
               "lady_id": self.lady.id,
               "man_id": self.man.id,
               "dic": self.fed_dic}
        return flatten_dict(dic)


class Official(Person):
    def __init__(self, name_string, last_row_dic, list_of_officials, season_observed, fed, conn_dic):
        non_break_space = u"\xa0"
        name_string = name_string.replace(non_break_space, " ").strip()

        name = re.sub(pattern=r"M(rs|r|s)\.? ", repl="", string=name_string)

        super().__init__(name_string=name, person_list=list_of_officials, last_row_dic=last_row_dic,
                         season_observed=season_observed, fed_observed=fed, mode="officials", conn_dic=conn_dic)

        logger.log(15, f"Instantiated official with id {self.id}, name "
                       f"{unicodedata.normalize('NFKD', self.full_name).encode('ascii','ignore')}, fed "
                       f"{self.fed_dic[season_observed + '_fed']}")


class Panel:
    def __init__(self, roles_table, last_row_dic, list_of_officials, sub_event, category, discipline, segment,
                 season_observed, conn_dic):
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
            logger.debug(f"Table starts at {first_entry}, incrementing by {increment}, len {len(roles_table)}")

            for i in range(first_entry, len(roles_table) - (increment - 1), increment):
                # Align 'judge' notation with the one used in scoring tables
                if 'Judge' in roles_table[i] or 'No.' in roles_table[i]:
                    role = "J" + str(roles_table[i].partition("No.")[2].strip()).zfill(2)
                else:
                    role = roles_table[i]

                official = Official(name_string=roles_table[i + 1], fed=roles_table[i + 2], last_row_dic=last_row_dic,
                                    list_of_officials=list_of_officials, season_observed=season_observed,
                                    conn_dic=conn_dic)

                self.role_dic[role] = official.id
        else:
            return

    def get_dict(self):
        return flatten_dict(dict(vars(self)))


class PersonTests(unittest.TestCase):
    def test_judges(self):
        conn, engine = db_builder.initiate_connections(settings.DB_CREDENTIALS)
        cur = conn.cursor()
        lr = {"officials": 34}
        lof = []
        o1 = Official("Mrs. Akiko SUZUKI", lr, lof, "sb2013", "JPN", {"conn": conn, "cursor": cur})
        o2 = Official("Mr Nobunari ODA", lr, lof, "sb2013", "JPN", {"conn": conn, "cursor": cur})
        o3 = Official("Ms Nobunari ODA", lr, lof, "sb2014", "JPN", {"conn": conn, "cursor": cur})
        logger.debug(f"Next id assigned will be {lr['officials']}", {"conn": conn, "cursor": cur})
        logger.debug(dict(vars(o2)))
        assert len(lof) == 2
        assert lr["officials"] == 36
        assert o3.full_name == "Nobunari ODA"


if __name__ == "__main__":
    unittest.main()
