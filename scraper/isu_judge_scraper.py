# -*- coding: utf-8 -*-
# #!/bin/env python

import sys
import logging
import os

import pandas as pd

logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)-5s - %(message)s",
                    level=logging.INFO,
                    datefmt="%Y-%m-%d %H:%M:%S")

logger = logging.getLogger(__name__)

# Ensure python can find modules for import
p = os.path.abspath("../classes/")
if p not in sys.path:
    sys.path.append(p)

pd.set_option('display.max_columns', None)
pd.set_option('display.width', 1900)

try:
    import search
    import event
    import person
    import db_builder
    import settings
except ImportError as exc:
    sys.exit(f"Error: failed to import module ({exc})")

# ------------------------------------------- CHANGE SEARCH PARAMETERS HERE --------------------------------------------
START_YEAR, END_YEAR = 2016, 2018
GOOGLE_SEARCH_TERMS = ["nhk+trophy"] # look at the SEARCHNAME_TO_DBNAME dic in search.py for good search strings
PER_DISCIPLINE_SETTINGS = {"men": True, "ladies": True, "pairs": True, "dance": True}
SEARCH_CAT = "senior" # set to "junior" to search for juniors
# ----------------------------------------------------------------------------------------------------------------------


if __name__ == '__main__':
    conn, engine = db_builder.initiate_connections(settings.DB_CREDENTIALS)
    cur = conn.cursor()
    rows = {}
    for x in ["deductions", "pcs", "goe", "elements", "segments", "competitors", "officials", "panels", "skates"]:
        name = x + "_new"
        rows[x] = db_builder.get_last_row_key(table_name=name, cursor=cur) + 1
    logger.debug(f"Last rows dic is {rows}")

    loo, lop = [], []

    # # If homepage search works, use this block of code
    # for search_event in GOOGLE_SEARCH_TERMS:
    #     for search_year in range(START_YEAR, END_YEAR + 1):
    #         s = search.EventSearch(search_event, search_year)
    #         success = s.set_event_homepage()
    #         if not success:
    #             sys.exit(f"Could not find google result that passed tests for {search.event.name} {search.event.year}")
    #         else:
    #             s.scrape_judging_panel(last_row_dic=rows, list_of_panels=lop, list_of_officials=loo,
    #                                    season=s.event.season, cursor=cur)
    #             logger.info(f"Scraped judges for {search.event.name} {search.event.year}")

    # If homepage needs to be inserted manually, uncomment and paste into "url=" below
    s = search.EventSearch(search_phrase="grand+prix+final", search_year=2014, category="senior",
                           per_disc_settings=PER_DISCIPLINE_SETTINGS, url="http://www.isuresults.com/results/gpf1415/")
    s.set_start_date()
    s.scrape_judging_panel(last_row_dic={"officials": 1}, list_of_officials=loo, list_of_panels=lop,
                           season=s.event.season, cursor=cur)

    # Convert lists of objects to dataframes and upload
    official_dics, panel_dics = [], []
    # for o in loo:
    #     official_dics.append(o.get_dict())
    # officials_df = pd.DataFrame(official_dics)
    # off_id = officials_df["id"]
    # officials_df.drop(labels=["id"], axis=1, inplace=True)
    # officials_df.insert(0, "id", off_id)
    # logger.debug(officials_df.head(10))
    # db_builder.modify_table(cursor=cur, connection=conn, engine=engine, df=officials_df, table_name="officials")

    for p in lop:
        panel_dics.append(p.get_dict())
    panels_df = pd.DataFrame(panel_dics)
    panels_df["event"] = s.event.name
    panels_df["season"] = s.event.season
    melted_df = panels_df.melt(id_vars=["season", "event", "sub_event", "category", "discipline", "segment"],
                               var_name="official_role", value_name="official_id")
    logger.info(melted_df.head(10))
    db_builder.modify_table(cursor=cur, connection=conn, engine=engine, df=melted_df, table_name="panels",
                            fetch_last_row=True)



