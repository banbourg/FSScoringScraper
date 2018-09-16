# -*- coding: utf-8 -*-
# #!/bin/env python


import sys
import logging

logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)-5s - %(message)s",
                    level=logging.DEBUG,
                    datefmt="%Y-%m-%d %H:%M:%S")

logger = logging.getLogger(__name__)

try:
    import pdf_fetcher
    import event
    import person
except ImportError as exc:
    sys.exit(f"Error: failed to import module ({exc})")

# ------------------------------------------- CHANGE SEARCH PARAMETERS HERE --------------------------------------------
START_YEAR, END_YEAR = 2014, 2018
GOOGLE_SEARCH_TERMS = ["golden+spin+zagreb"] # look at the dic in events for good search strings
PER_DISCIPLINE_SETTINGS = {"men": True, "ladies": True, "pairs": True, "dance": True}
SEARCH_CAT = "senior" # set to "junior" to search for juniors
# ----------------------------------------------------------------------------------------------------------------------


if __name__ == '__main__':
    # If homepage search works, use this block of code
    for search_event in GOOGLE_SEARCH_TERMS:
        for search_year in range(START_YEAR, END_YEAR + 1):
            search = pdf_fetcher.EventSearch(search_event, search_year)
            success = search.set_event_homepage()
            if not success:
                logger.error(f"Could not find google result that passed tests for {search.event.name} "
                             f"{search.event.year}")
                sys.exit(1)
            else:
                search.scrape_judging_panel(self, last_row_dic, panel_list, judge_list)
                logger.info(f"Scraped judges for {search.event.name} {search.event.year}")

    # # If homepage needs to be inserted manually, uncomment and paste into "url=" below
    # search = EventSearch(search_phrase="ondrej+nepela+trophy", search_year=2014,
    #                      url="http://www.kraso.sk/wp-content/uploads/sutaze/2014_2015/20141001_ont/html/")
    # search.set_start_date()
    # search.scrape_judge_names()