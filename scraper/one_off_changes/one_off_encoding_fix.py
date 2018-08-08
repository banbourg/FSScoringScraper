import glob
import pandas as pd
import sys

READ_PATH, WRITE_PATH, DATE, VER = "", "", "", ""
DATE_PATH = ""
try:
    from settings import *
except ImportError:
    sys.stderr.write("Error: failed to import module ({})".format(exc))
    pass

# Note: Am using dataframes here bc trying to put an encoding wrapper around the basic csv reader was giving me a
# headache

files = sorted(glob.glob(READ_PATH + "*.csv"))
for f in files:
    name = f.rpartition('_')[0].rpartition('/')[2]
    print(name)

    parse_setting = False if name in ["competitors", "judges"] else ["event_start_date"]
    infer_setting = False if name in ["competitors", "judges"] else True
    print(parse_setting, infer_setting)
    data = pd.read_csv(f, na_values='', index_col=0, low_memory=False, parse_dates=parse_setting,
                       infer_datetime_format=infer_setting, encoding="utf-8")

    encoding_dic = {"√ñ": "Ö", "√Ñ": "Ä", "√ú": "Ü"}
    data.replace(to_replace=encoding_dic, inplace=True)

    index_name = "elt_id" if name in ["calls", "elt_scores"] else "line_id"
    data.to_csv(WRITE_PATH + name + "_" + DATE + VER + ".csv", index_label=index_name, mode="w", encoding="utf-8",
                header=True)

