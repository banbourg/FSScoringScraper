from psycopg2 import sql
import psycopg2
import pandas as pd
import glob
from sqlalchemy import create_engine

filepath, date, ver = "/users/clarapouletty/desktop/bias/output/upload/", "180717", "1"
un, pw = "cpouletty", "Ins1d10us"
h, db, port = "fsdb.c3ldus0yxoex.eu-west-1.rds.amazonaws.com", "fsscores_2010", "5432"
mode = "fail" #or "append"

conn = psycopg2.connect(database=db, user=un, password=pw, host=h, port=port)
cur = conn.cursor()
engine = create_engine("postgresql://" + un + ":" + pw + "@" + h + ":" + port + "/" + db, echo=True)
print("Engines created.")

files = sorted(glob.glob(filepath + "*.csv"))
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
        data.to_sql(table_name, engine, if_exists=mode, index=False)
        print(f"Populated {table_name} table.")

cur.close()
conn.close()