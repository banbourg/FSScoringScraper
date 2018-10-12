# -*- coding: utf-8 -*-
# #!/bin/env python

import sys
import logging
import os
from pathlib import Path
import json

logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)-5s - %(message)s",
                    level=logging.INFO,
                    datefmt='%Y-%m-%d %H:%M:%S')

logger = logging.getLogger(__name__)

p_list = [os.path.abspath("./classes/"), os.path.abspath("../")]
for p in p_list:
    if p not in sys.path:
        sys.path.append(p)

try:
    import search
    import settings
except ImportError as exc:
    sys.exit(f"Failed to import module ({exc})")

# ------------------------------------------- CHANGE SEARCH PARAMETERS HERE --------------------------------------------
START_YEAR, END_YEAR = 2017, 2017
GOOGLE_SEARCH_TERMS = ["finlandia+trophy"] # look at the dic in events for good search strings
PER_DISCIPLINE_SETTINGS = {"men": True, "ladies": True, "pairs": True, "dance": True}
SEARCH_CAT = "junior" # set to "junior" to search for juniors
# ----------------------------------------------------------------------------------------------------------------------


class HomepageNotFound(ValueError):
    def __init__(self, year, message):
        self.year = year
        self.message = message


def scrape_event_pdfs(search_term, start_year, end_year, category, per_disc_settings, write_path):
    for y in range(start_year, end_year + 1):
        event_search = search.EventSearch(search_phrase=search_term,
                                          search_year=y,
                                          category=category,
                                          per_disc_settings=per_disc_settings)
        success = event_search.set_event_homepage()
        if not success:
            raise HomepageNotFound(year=y, message=f"Could not find google result that passed tests for "
                                                   f"{event_search.event.name} {event_search.event.year}")
        else:
            event_search.download_pdf_protocols(write_path=write_path)
            logger.info(f"Downloaded protocols for {event_search.event.name} {event_search.event.year}")


if __name__ == '__main__':
    if len(sys.argv) == 1:
        search_terms = GOOGLE_SEARCH_TERMS
        start_year = START_YEAR
        end_year = END_YEAR
        category = SEARCH_CAT,
        per_disc_settings = PER_DISCIPLINE_SETTINGS
        write_path = settings.WRITE_PATH
    else:
        search_terms = sys.argv[1]
        start_year = int(sys.argv[2])
        end_year = int(sys.argv[3])
        category = sys.argv[4],
        per_disc_settings = json.loads(sys.argv[5])
        for k in per_disc_settings:
            if per_disc_settings[k] == "True":
                per_disc_settings[k] = True
            else:
                per_disc_settings[k] = False

        write_path = os.path.join(Path(os.getcwd()).parent.parent, "pdf_files/")
        if not os.path.exists(write_path):
            os.makedirs(write_path)

    if not isinstance(search_terms, list):
        search_terms = [search_terms]

    for t in search_terms:
        try:
            scrape_event_pdfs(search_term=t,
                              start_year=start_year,
                              end_year=end_year,
                              category=category,
                              per_disc_settings=per_disc_settings,
                              write_path=write_path)
        except HomepageNotFound as err:
            url = input("Homepage matching expected patterns not found. Please input it manually below:")
            event_search = search.EventSearch(search_phrase=t,
                                              search_year=err.year,
                                              category=category,
                                              per_disc_settings=per_disc_settings,
                                              url=url)
            event_search.set_start_date()
            event_search.download_pdf_protocols(write_path=write_path)