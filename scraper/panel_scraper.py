# -*- coding: utf-8 -*-
# #!/bin/env python

import sys
import logging
import os

import pandas as pd

logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)-5s - %(message)s",
                    level=logging.DEBUG,
                    datefmt="%Y-%m-%d %H:%M:%S")

logger = logging.getLogger(__name__)

p_list = [os.path.abspath("./classes/"), os.path.abspath("..")]
for p in p_list:
    if p not in sys.path:
        sys.path.append(p)

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
MODE = "A"  # Always try A first, then B (to insert homepage manually) or C (to enter list of links to officials tables)
ENABLE_PAUSE = True  # If True script will pause for confirmation before writing from staging to final
PER_DISCIPLINE_SETTINGS = {"men": True, "ladies": True, "pairs": True, "dance": True}
SEARCH_CAT = "junior"  # Set to "junior" to search for juniors

# IF MODE A ALSO POPULATE
GOOGLE_SEARCH_TERMS = ["jgp+ljubljana"]  # use one of the searches in SEARCHNAME_TO_DBNAME (in search.py)
START_YEAR, END_YEAR = 2018, 2018

# IF MODE IS EITHER B OR C ALSO POPULATE
MANUAL_SEARCH_PHR = "world+team+trophy"  # e.g. "tallinn+trophy", use searches in SEARCHNAME_TO_DBNAME (in search.py)
MANUAL_SEARCH_YR = 2017  # e.g. 2014

# IF MODE B ALSO POPULATE:
MANUAL_HOMEPAGE = "https://www.jsfresults.com/intl/2016-2017/wtt/"
# "http://www.isuresults.com/results/season1718/gpjpn2017/"
# "http://www.isuresults.com/results/season1718/gpf1718/"
# "http://www.kraso.sk/wp-content/uploads/sutaze/2018_2019/20180920_ont/"
# "https://sharp-jackson-2e11d8.netlify.com/"
# e.g. "http://www.figureskatingresults.fi/results/1718/CSFIN2017/index.htm"

# IF MODE C ALSO POPULATE:
manual_list = ["https://data.tallinntrophy.eu/2017/Tallinn_Trophy/Challenger/SEG00" + str(x) + "OF.HTM" for x in range(1, 9)]  # Examples below
# tt_15 = ["https://data.tallinntrophy.eu/2015/Tallinn_Trophy/CSEST2015/SEG00"+ str(x) + "OF.HTM" for x in range(1, 9)]
# tt_16 = ["https://data.tallinntrophy.eu/2016/Tallinn_Trophy/International/SEG00"+ str(x) + "OF.HTM" for x in range(1, 9)]
# tt_17 = ["https://data.tallinntrophy.eu/2017/Tallinn_Trophy/Challenger/SEG00" + str(x) + "OF.HTM" for x in range(1, 9)]
# ----------------------------------------------------------------------------------------------------------------------


def convert_and_upload(search_obj, list_of_officials, list_of_panels, conn_dic, segment_df):
    officials_df, ided = None, None
    official_dics, panel_dics = [], []
    if list_of_officials:
        for o in list_of_officials:
            official_dics.append(o.get_official_dict())
        officials_df = pd.DataFrame(official_dics)
        off_id = officials_df["id"]
        officials_df.drop(labels=["id"], axis=1, inplace=True)
        officials_df.insert(0, "id", off_id)
        logger.debug(officials_df.head(10))
        db_builder.create_staging_table(df=officials_df, conn_dic=conn_dic, table_name="officials")
    else:
        logger.info(f"No new officials found for {search_obj.event.name} {search_obj.event.year}")

    if list_of_panels:
        seg_columns = ["season", "name", "sub_event", "category", "discipline", "segment"]
        for panel in list_of_panels:
            panel_dics.append(panel.get_panel_dict())
        panels_df = pd.DataFrame(panel_dics)
        panels_df["name"] = search_obj.event.name
        panels_df["season"] = search_obj.event.season
        melted_df = panels_df.melt(id_vars=seg_columns, var_name="official_role", value_name="official_id")
        filtered = melted_df.loc[melted_df["official_id"].notnull()]

        # Set segment ID
        ided = pd.merge(filtered, segment_df, how="left",
                        on=["season", "name", "sub_event", "category", "discipline", "segment"])

        check = ided[ided["segment_id"].isnull()]
        try:
            assert check.dropna().empty
        except AssertionError:
            logger.error("Not all segments matched:")
            logger.error(check)

        ided = ided[ided["segment_id"].notnull()]
        ided.drop(axis="columns",
                  labels=seg_columns + ["is_h2_event", "is_A_comp", "is_cs_event", "year", "start_date"],
                  inplace=True)
        db_builder.create_staging_table(df=ided, conn_dic=conn_dic, table_name="panels", fetch_last_row=True)
    else:
        logger.info(f"No panels found for {search_obj.event.name} {search_obj.event.year}")

    if ENABLE_PAUSE:
        input("Hit Enter to write to main tables")
    if officials_df is not None and not officials_df.empty:
        db_builder.write_to_final_table(df=officials_df, conn_dic=conn_dic, table_name="officials")
    if ided is not None and not ided.empty:
        db_builder.write_to_final_table(df=ided, conn_dic=conn_dic, table_name="panels")

    return [], []


def main(mode):
    conn, engine = db_builder.initiate_connections(settings.DB_CREDENTIALS)
    conn_dic = {"conn": conn, "engine": engine, "cursor": conn.cursor()}

    rows = {}
    for x in ["officials", "panels"]:
        rows[x] = db_builder.get_last_row_key(table_name=x, cursor=conn_dic["cursor"]) + 1
    logger.debug(f"Last rows dic is {rows}")

    loo, lop = [], []

    seg_df = pd.read_sql_query("SELECT * FROM segments;", engine)
    seg_df.rename(columns={"id": "segment_id"}, inplace=True)

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

                s.scrape_judging_panel(last_row_dic=rows, list_of_panels=lop, list_of_officials=loo,
                                       season=s.event.season, conn_dic=conn_dic)
                logger.info(f"Scraped judges for {s.event.name} {s.event.year}")

                loo, lop = convert_and_upload(conn_dic=conn_dic,
                                              list_of_panels=lop,
                                              list_of_officials=loo,
                                              search_obj=s,
                                              segment_df=seg_df)

    elif mode == "B":
        # PLAN B: If homepage needs to be inserted manually
        s = search.EventSearch(search_phrase=MANUAL_SEARCH_PHR, search_year=MANUAL_SEARCH_YR, category=SEARCH_CAT,
                               per_disc_settings=PER_DISCIPLINE_SETTINGS, url=MANUAL_HOMEPAGE)
        s.scrape_judging_panel(last_row_dic=rows, list_of_panels=lop, list_of_officials=loo,
                               season=s.event.season, conn_dic=conn_dic)
        logger.info(f"Scraped judges for {s.event.name} {s.event.year}")

        loo, lop = convert_and_upload(conn_dic=conn_dic,
                                      list_of_panels=lop,
                                      list_of_officials=loo,
                                      search_obj=s,
                                      segment_df=seg_df)

    elif mode == "C":
        # PLAN C GODDAMMIT: For those Tallinn Trophy, need to feed in the correct sublinks directly
        s = search.EventSearch(search_phrase=MANUAL_SEARCH_PHR, search_year=MANUAL_SEARCH_YR, category=SEARCH_CAT,
                               per_disc_settings=PER_DISCIPLINE_SETTINGS, override=True)
        s.scrape_judging_panel(last_row_dic=rows, list_of_panels=lop, list_of_officials=loo,
                               season=s.event.season, conn_dic=conn_dic, all_sublinks=manual_list)
        logger.info(f"Scraped judges for {s.event.name} {s.event.year}")
        loo, lop = convert_and_upload(conn_dic=conn_dic,
                                      list_of_panels=lop,
                                      list_of_officials=loo,
                                      search_obj=s,
                                      segment_df=seg_df)

    goe_query = """
    UPDATE goe_detail AS g
    SET official_id = o.id
    FROM officials AS o, elements AS e, protocols as pr, panels as pa
    WHERE g.element_id = e.id AND
      e.protocol_id = pr.id AND
      pr.segment_id = pa.segment_id AND
      pa.official_role = g.judge_no AND
      pa.official_id = o.id;"""

    conn_dic["cursor"].execute(goe_query)
    conn_dic["conn"].commit()
    logger.info(f"Updated goe_detail")

    pcs_query = """
    UPDATE pcs_detail AS p
    SET official_id = o.id
    FROM officials AS o, pcs_averages as pc, protocols as pr, panels as pa
    WHERE p.pcs_avg_id = pc.id AND
      pc.protocol_id = pr.id AND
      pr.segment_id = pa.segment_id AND
      pa.official_role = p.judge_no AND
      pa.official_id = o.id;"""
    conn_dic["cursor"].execute(pcs_query)
    conn_dic["conn"].commit()
    logger.info(f"Updated pcs_detail")


if __name__ == '__main__':
    main(MODE)
