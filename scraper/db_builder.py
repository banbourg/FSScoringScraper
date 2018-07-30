from psycopg2 import sql
import psycopg2
import pandas as pd
import glob
from sqlalchemy import create_engine

FILEPATH, DATE, VER, UN, PW = "", "", "", "", ""
H, DB, PORT = "", "", ""
MODE = "fail" #or "append"
try:
    from dev_settings import *
except ImportError:
    pass

conn = psycopg2.connect(database=DB, user=UN, password=PW, host=H, PORT=PORT)
cur = conn.cursor()
engine = create_engine("postgresql://" + UN + ":" + PW + "@" + H + ":" + PORT + "/" + DB, echo=True)
print("Engines created.")

files = sorted(glob.glob(FILEPATH + "*.csv"))
for f in files:
        table_name = f.rpartition('_')[0].rpartition('/')[2]

        data = pd.read_csv(f, na_values='', low_memory=False)
        data.rename(columns={"Unnamed: 0": "line_id"}, inplace=True)

        old, new = sql.Identifier(table_name + "_old"), sql.Identifier(table_name)

        cur.execute(sql.SQL("DROP TABLE IF EXISTS {};").format(old))
        cur.execute(sql.SQL("ALTER TABLE IF EXISTS {} RENAME TO {};").format(new, old))
        conn.commit()
        print(f"Removed old {table_name} table and renamed current to old.")

        # CREATE NEW TABLE
        data.to_sql(table_name, engine, if_exists=MODE, index=False)
        print(f"Populated {table_name} table.")

cur.close()
conn.close()