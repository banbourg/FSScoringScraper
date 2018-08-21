from psycopg2 import sql
import psycopg2
import pandas as pd
import glob
import sys
import os


# Pokemon list from here https://gist.github.com/armgilles/194bcff35001e7eb53a2a8b441e8b2c6

# Ensure python can find modules for import
p = os.path.abspath("/Users/clarapouletty/Desktop/bias/scripts/scraper/")
if p not in sys.path:
    sys.path.append(p)

READ_PATH, UN, PW = "", "", ""
H, DB, PORT = "", "", ""
MODE = "fail" #or "append"
POKE_PATH = os.path.expanduser("~/Desktop/bias/pokemon.csv")
try:
    from settings import *
    from transformer_xlsx import split_name
except ImportError as exc:
    sys.stderr.write("Error: failed to import module ({})".format(exc))
    pass


def copy_old_tables(cursor, connection):
    table_list = ["calls", "competitors", "deductions", "elt_scores", "goe", "judges", "pcs", "scraped_totals",
                  "total_scores"]
    for t in table_list:
        print(t)
        old, new = sql.Identifier(t), sql.Identifier(t + "_test")
        cursor.execute(sql.SQL("CREATE TABLE IF NOT EXISTS {} AS SELECT * FROM {};").format(new, old))
        print(f"Cloned {t} table.")
    connection.commit()
    connection.close()


def pokemonizer(poke_names, data, table_name):
    name_cols = ["skater_name", "judge_name", "name"]
    col = data.columns.intersection(name_cols)
    names = data[col].drop_duplicates(keep='first')
    names = names[str(col[0])].tolist()
    rev_names = [(split_name(n)[2] + split_name(n)[0]) for n in names]

    poke_dict_1 = dict(zip(names, poke_names))
    poke_dict_2 = dict(zip(rev_names, poke_names))
    data.replace(poke_dict_1, inplace=True)
    data.replace(poke_dict_2, inplace=True, regex=True)
    data.to_csv(WRITE_PATH + table_name + "_test.csv", mode="w", encoding="utf-8", header=True)


def main():
    conn = psycopg2.connect(database=DB, user=UN, password=PW, host=H, port=PORT)
    cur = conn.cursor()
    print("Engines created.")

    copy_old_tables(cur, conn)

    pokemon = pd.read_csv(POKE_PATH, na_values='', low_memory=False)
    poke_names = pokemon["Name"].tolist()

    files = sorted(glob.glob(READ_PATH + "*.csv"))
    for f in files:
        table_name = f.rpartition('_')[0].rpartition('/')[2]
        print(table_name)
        parse_setting = False if table_name in ["competitors", "judges"] else ["event_start_date"]
        infer_setting = False if table_name in ["competitors", "judges"] else True

        data = pd.read_csv(f, na_values='', low_memory=False, parse_dates=parse_setting,
                           infer_datetime_format=infer_setting, nrows=200)

        pokemonizer(poke_names, data, table_name)


if __name__ == "__main__":
    main()