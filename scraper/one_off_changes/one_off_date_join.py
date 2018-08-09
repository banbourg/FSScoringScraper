import pandas as pd
import glob
import sys

READ_PATH, WRITE_PATH, DATE, VER = "", "", "", ""
DATE_PATH = ""
try:
    from settings import *
except ImportError as exc:
    sys.stderr.write("Error: failed to import module ({})".format(exc))
    pass

pd.set_option('display.max_columns', None)
pd.set_option('display.width', 1900)


def join_dates(a_df, date_df):
    merged_df = pd.merge(a_df, date_df, how="left", on=["season", "event"], sort=False,
                         suffixes=("_a", "_d"), indicator=True).set_index("level_0")
    print("LEFTOVERS",
          merged_df.loc[(merged_df["_merge"] == "left_only") | (merged_df["_merge"] == "right_only")]
          .loc[:, "discipline":"event"].drop_duplicates())

    merged_df.drop(columns="_merge", inplace=True)
    # merged_df.rename({"level_0": "elt_id"}, axis="columns", inplace=True)

    return merged_df


def main():
    dates = pd.read_csv(DATE_PATH, index_col=0)
    files = sorted(glob.glob(READ_PATH + "*.csv"))

    for f in files:
        name = "".join(f.split(READ_PATH)).rpartition("_")[0]
        print(name)

        df = pd.read_csv(f, index_col=0, na_values="", low_memory=False).rename({"level_0": "elt_id"}, axis="columns")
        print(df.head(3))

        if name not in ["competitors", "judges", "dates"]:
            with_dates = join_dates(df.reset_index(), dates)

            index_name = "elt_id" if name in ["calls", "elt_scores"] else "line_id"
            with_dates.to_csv(WRITE_PATH + name + "_" + DATE + VER + ".csv", index_label=index_name, mode="w",
                              encoding="utf-8", header=True)

main()
