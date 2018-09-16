# -*- coding: utf-8 -*-
# #!/bin/env python

import sys
import logging
import os

logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)-5s - %(message)s",
                    level=logging.INFO,
                    datefmt='%Y-%m-%d %H:%M:%S')

logger = logging.getLogger(__name__)

p = os.path.abspath("../classes/")
if p not in sys.path:
    sys.path.append(p)

try:
    import search
except ImportError as exc:
    sys.exit(f"Failed to import module ({exc})")

# ------------------------------------------- CHANGE SEARCH PARAMETERS HERE --------------------------------------------
START_YEAR, END_YEAR = 2014, 2018
GOOGLE_SEARCH_TERMS = ["golden+spin+zagreb"] # look at the dic in events for good search strings
PER_DISCIPLINE_SETTINGS = {"men": True, "ladies": True, "pairs": True, "dance": True}
SEARCH_CAT = "senior" # set to "junior" to search for juniors
# ----------------------------------------------------------------------------------------------------------------------

if __name__ == '__main__':
    # If homepage search works, use this block of code
    for t in GOOGLE_SEARCH_TERMS:
        for y in range(START_YEAR, END_YEAR + 1):
            event_search = search.EventSearch(search_phrase=t, search_year=y, category=SEARCH_CAT,
                                        per_disc_settings=PER_DISCIPLINE_SETTINGS)
            success = event_search.set_event_homepage()
            if not success:
                sys.exit(f"Could not find google result that passed tests for {search.event.name} {search.event.year}")
            else:
                event_search.download_pdf_protocols()
                logger.info(f"Downloaded protocols for {search.event.name} {search.event.year}")

    # # If homepage needs to be inserted manually, uncomment and paste into "url=" below
    # event_search = search.EventSearch(search_phrase="ondrej+nepela+trophy", search_year=2014, category=SEARCH_CAT,
    #                                   per_disc_settings=PER_DISCIPLINE_SETTINGS,
    #                                   url="http://www.kraso.sk/wp-content/uploads/sutaze/2014_2015/20141001_ont/html/")
    # event_search.set_start_date()
    # event_search.download_pdf_protocols()

