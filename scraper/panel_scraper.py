# -*- coding: utf-8 -*-
# #!/bin/env python

import sys
import logging
import os

import pandas as pd
from datetime import datetime

logging.basicConfig(  # filename="panel_scraper" + datetime.today().strftime("%Y-%m-%d_%H-%M-%S") + ".log",
                    format="%(asctime)s - %(name)s - %(levelname)-5s - %(message)s",
                    level=logging.INFO,
                    datefmt="%Y-%m-%d %H:%M:%S")

logger = logging.getLogger(__name__)

sys.path.extend([os.path.abspath("./classes/"), os.path.abspath("..")])

pd.set_option('display.max_columns', None)
pd.set_option('display.width', 1900)

try:
    import db_builder
    import search
    import event
    import person
    import settings
except ImportError as exc:
    sys.exit(f"Error: failed to import module ({exc})")

# ------------------------------------------ CHANGE SEARCH PARAMETERS HERE ---------------------------------------------
# POPULATE THESE WHATEVER YOU DO
MODE = "B"  # Always try A first, then B (to insert homepage manually) or C (to enter list of links to officials tables)
ENABLE_PAUSE = True  # If True script will pause for confirmation before writing from staging to final
PER_DISCIPLINE_SETTINGS = {"men": True, "ladies": True, "pairs": True, "dance": True}
SEARCH_CAT = "senior"  # Set to "junior" to search for juniors

# IF MODE A ALSO POPULATE
GOOGLE_SEARCH_TERMS = ["golden+spin+zagreb"]  # use one of the searches in SEARCHNAME_TO_DBNAME (in search.py)
START_YEAR, END_YEAR = 2017, 2017

# IF MODE IS EITHER B OR C ALSO POPULATE
MANUAL_SEARCH_PHR = "golden+spin+zagreb"  # e.g. "tallinn+trophy", use one of the searches in SEARCHNAME_TO_DBNAME (in search.py)
MANUAL_SEARCH_YR = 2017  # e.g. 2014

# IF MODE B ALSO POPULATE:
MANUAL_HOMEPAGE = "https://sharp-jackson-2e11d8.netlify.com/"  # e.g. "http://www.figureskatingresults.fi/results/1718/CSFIN2017/index.htm"

# IF MODE C ALSO POPULATE:
manual_list = [] # Examples below
# tt_15 = ["https://data.tallinntrophy.eu/2015/Tallinn_Trophy/CSEST2015/SEG00"+ str(x) +"OF.HTM" for x in range(1,9)]
# tt_16 = ["https://data.tallinntrophy.eu/2016/Tallinn_Trophy/International/SEG00"+ str(x) +"OF.HTM" for x in range(1,9)]
# tt_17 = ["https://data.tallinntrophy.eu/2017/Tallinn_Trophy/Challenger/SEG00" + str(x) + "OF.HTM" for x in range(1, 9)]
# ----------------------------------------------------------------------------------------------------------------------


def convert_and_upload(search_obj, list_of_officials, list_of_panels, conn_dic):
    official_dics, panel_dics = [], []
    if list_of_officials:
        for o in list_of_officials:
            official_dics.append(o.get_dict())
        officials_df = pd.DataFrame(official_dics)
        off_id = officials_df["id"]
        officials_df.drop(labels=["id"], axis=1, inplace=True)
        officials_df.insert(0, "id", off_id)
        logger.debug(officials_df.head(10))
        db_builder.create_staging_table(df=officials_df, conn_dic=conn_dic, table_name="officials")
        if ENABLE_PAUSE:
            input("Hit Enter to write to main tables")
        db_builder.write_to_final_table(df=officials_df, conn_dic=conn_dic, table_name="officials")
    else:
        logger.info(f"No new officials found for {search_obj.event.name} {search_obj.event.year}")

    if list_of_panels:
        for p in list_of_panels:
            panel_dics.append(p.get_dict())
        panels_df = pd.DataFrame(panel_dics)
        panels_df["event"] = search_obj.event.name
        panels_df["season"] = search_obj.event.season
        melted_df = panels_df.melt(id_vars=["season", "event", "sub_event", "category", "discipline", "segment"],
                                   var_name="official_role", value_name="official_id")
        filtered_melt = melted_df.loc[melted_df["official_id"].notnull()]
        db_builder.create_staging_table(df=filtered_melt, conn_dic=conn_dic, table_name="panels", fetch_last_row=True)
        if ENABLE_PAUSE:
            input("Hit Enter to write to main tables")
        db_builder.write_to_final_table(df=filtered_melt, conn_dic=conn_dic, table_name="panels")
    else:
        logger.info(f"No panels found for {search_obj.event.name} {search_obj.event.year}")

    return [], []


def main(mode):
    conn, engine = db_builder.initiate_connections(settings.DB_CREDENTIALS)
    conn_dic = {"conn": conn, "engine": engine, "cursor": conn.cursor()}

    rows = {}
    for x in ["officials", "panels"]: #"deductions", "pcs", "goe", "elements", "segments", "competitors", "officials", "panels", "skates"]:
        rows[x] = db_builder.get_last_row_key(table_name=x, cursor=conn_dic["cursor"]) + 1
    logger.info(f"Last rows dic is {rows}")

    loo, lop = [], []

    if mode == "A":
        # PLAN A. If google search works, use this block of code
        for search_event in GOOGLE_SEARCH_TERMS:
            for search_year in range(START_YEAR, END_YEAR + 1):
                s = search.EventSearch(search_phrase=search_event, search_year=search_year, category=SEARCH_CAT,
                                       per_disc_settings=PER_DISCIPLINE_SETTINGS)
                success = s.set_event_homepage()
                if not success:
                    sys.exit(f"Could not find google result that passed tests for {search.event.name} "
                             f"{search.event.year}")
                else:
                    s.scrape_judging_panel(last_row_dic=rows, list_of_panels=lop, list_of_officials=loo,
                                           season=s.event.season, conn_dic=conn_dic)
                    logger.info(f"Scraped judges for {s.event.name} {s.event.year}")

                    loo, lop = convert_and_upload(conn_dic=conn_dic, list_of_panels=lop, list_of_officials=loo,
                                                  search_obj=s)

    elif mode == "B":
        # PLAN B: If homepage needs to be inserted manually, uncomment and fill out args below
        s = search.EventSearch(search_phrase=MANUAL_SEARCH_PHR, search_year=MANUAL_SEARCH_YR, category=SEARCH_CAT,
                               per_disc_settings=PER_DISCIPLINE_SETTINGS, url=MANUAL_HOMEPAGE)
        s.scrape_judging_panel(last_row_dic=rows, list_of_panels=lop, list_of_officials=loo,
                               season=s.event.season, conn_dic=conn_dic)
        logger.info(f"Scraped judges for {s.event.name} {s.event.year}")

        loo, lop = convert_and_upload(conn_dic=conn_dic, list_of_panels=lop, list_of_officials=loo, search_obj=s)

    elif mode == "C":
        # PLAN C GODDAMMIT: For those Tallinn Trophy so and sos, need to feed in the correct sublinks directly
        s = search.EventSearch(search_phrase=MANUAL_SEARCH_PHR, search_year=MANUAL_SEARCH_YR, category=SEARCH_CAT,
                               per_disc_settings=PER_DISCIPLINE_SETTINGS, override=True)
        s.scrape_judging_panel(last_row_dic=rows, list_of_panels=lop, list_of_officials=loo,
                               season=s.event.season, conn_dic=conn_dic, all_sublinks=manual_list)
        logger.info(f"Scraped judges for {s.event.name} {s.event.year}")
        loo, lop = convert_and_upload(conn_dic=conn_dic, list_of_panels=lop, list_of_officials=loo,
                                      search_obj=s)


if __name__ == '__main__':
    main(MODE)