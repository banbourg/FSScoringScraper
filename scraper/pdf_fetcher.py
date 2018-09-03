# -*- coding: utf-8 -*-
# #!/bin/env python

import requests
from bs4 import BeautifulSoup

import urllib.request, urllib.error, urllib.parse

import re
import sys
import logging
import os

logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)-5s - %(message)s",
                    level=logging.DEBUG,
                    datefmt='%Y-%m-%d %H:%M:%S')

logger = logging.getLogger(__name__)

# Ensure python can find modules for import
p = os.path.abspath("../classes/")
if p not in sys.path:
    sys.path.append(p)

try:
    import settings
    import event
    import start_date
except ImportError as exc:
    logger.error(f"Failed to import settings module ({exc})")
    sys.exit(1)


# ------------------------------------------- CHANGE SEARCH PARAMETERS HERE --------------------------------------------
START_YEAR, END_YEAR = 2004, 2018
GOOGLE_SEARCH_TERMS = ["nhk+trophy"]
PER_DISCIPLINE_SETTINGS = {"men": True, "ladies": True, "pairs": True, "dance": True}
SEARCH_CAT = "senior" # set to "junior" to search for juniors
# ----------------------------------------------------------------------------------------------------------------------

# CONSTANTS AND CONVERTER DICTIONARIES, NO NEED TO AMEND THESE EXCEPT IF ADDING NEW EVENTS

EXPECTED_DOMAIN = {"AO": "fsatresults", "Lombardia": "fisg", "USClassic": "usfigureskating", "Nepela": "kraso",
                   "ACI": "skatecanada", "Nebelhorn": "isuresults", "Finlandia": "figureskatingresults",
                   "Tallinn": "data.tallinntrophy", "Warsaw": "pfsa", "GoldenSpin": "netlify",
                   "DenkovaStaviksi": "clubdenkovastaviski", "IceStar": "figure.skating.by",
                   "MordovianOrnament": "fsrussia"}

DBNAME_TO_URLNAME = {"NHK": "gpjpn", "TDF": "gpfra", "SC": "gpcan", "COR": "gprus", "SA": "gpusa", "COC": "gpchn",
                     "GPF": "gpf", "WC": "wc", "4CC": "fc", "OWG": "owg", "WTT": "wtt", "EC": "ec", "AO": "ISUCSAO",
                     "Lombardia": "lombardia", "Nepela": "ont", "Finlandia": "CSFIN", "Nebelhorn": "nt",
                     "ACI": "CSCAN", "Warsaw": "warsawcup", "USClassic": "us_intl_classic",
                     "GoldenSpin": "", "DenkovaStaviksi": "ISUCS", "IceStar": "Ice_Star", "MordovianOrnament": "CSRUS"}

MAX_TRIES = 10  # before timeout on .get() requests


HEADERS = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_13_6) AppleWebKit/537.36 (KHTML, like Gecko) "
                         "Chrome/68.0.3440.106 Safari/537.36"}

root_domain_pattern = re.compile(r"^((?:http(?:s)?://)?(www)?[A-Za-z\d\-]{3,}\.[a-z\.]{2,6})(?:\/)")
# -- A CHEAT: My internet was being super slow so I pasted the output from step 1 below to avoid having to rerun it.
# This covers '''
# google_link_list = [('COR', 2004, 'SB2004', 'www.isuresults.com/results/gprus04/index.htm'), ('COR', 2005, 'SB2005', 'www.isuresults.com/results/gprus05/'), ('COR', 2006, 'SB2006', 'www.isuresults.com/results/gprus06/'), ('COR', 2007, 'SB2007', 'www.isuresults.com/results/gprus07/'), ('COR', 2008, 'SB2008', 'www.isuresults.com/results/gprus08/index.htm'), ('COR', 2009, 'SB2009', 'www.isuresults.com/results/gprus09/'), ('COR', 2010, 'SB2010', 'www.isuresults.com/results/gprus2010/'), ('COR', 2011, 'SB2011', 'www.isuresults.com/results/gprus2011/'), ('COR', 2012, 'SB2012', 'www.isuresults.com/results/gprus2012/'), ('COR', 2013, 'SB2013', 'www.isuresults.com/results/gprus2013/'), ('COR', 2014, 'SB2014', 'www.isuresults.com/results/gprus2014/'), ('COR', 2015, 'SB2015', 'www.isuresults.com/results/season1516/gprus2015/'), ('COR', 2016, 'SB2016', 'www.isuresults.com/results/season1617/gprus2016/'), ('COR', 2017, 'SB2017', 'www.isuresults.com/results/season1718/gprus2017/'), ('COR', 2018, 'SB2018', 'www.isuresults.com/results/season1718/wc2018/'), ('TDF', 2005, 'SB2005', 'www.isuresults.com/results/gpfra05/'), ('TDF', 2006, 'SB2006', 'www.isuresults.com/results/gpfra06/'), ('TDF', 2007, 'SB2007', 'www.isuresults.com/results/wc2007/CAT004RS.HTM'), ('TDF', 2008, 'SB2008', 'www.isuresults.com/results/jgpfra2008/'), ('TDF', 2009, 'SB2009', 'www.isuresults.com/results/gpfra09/'), ('TDF', 2010, 'SB2010', 'www.isuresults.com/results/jgpfra2010/'), ('TDF', 2011, 'SB2011', 'www.isuresults.com/results/gpfra2011/'), ('TDF', 2012, 'SB2012', 'www.isuresults.com/results/jgpfra2012/'), ('TDF', 2013, 'SB2013', 'www.isuresults.com/results/gpfra2013/'), ('TDF', 2014, 'SB2014', 'www.isuresults.com/results/gpfra2014/'), ('TDF', 2015, 'SB2015', 'www.isuresults.com/results/season1617/gpfra2016/'), ('TDF', 2016, 'SB2016', 'www.isuresults.com/results/season1617/gpfra2016/'), ('TDF', 2017, 'SB2017', 'www.isuresults.com/results/season1718/gpfra2017/'), ('TDF', 2018, 'SB2018', 'www.isuresults.com/events/fsevent03111630.htm'), ('SA', 2004, 'SB2004', 'www.isuresults.com/results/gpusa04/index.htm'), ('SA', 2005, 'SB2005', 'www.isuresults.com/results/gpusa05/'), ('SA', 2006, 'SB2006', 'www.isuresults.com/results/gpusa06/'), ('SA', 2007, 'SB2007', 'www.isuresults.com/results/gpusa07/'), ('SA', 2008, 'SB2008', 'www.isuresults.com/results/gpusa08/index.htm'), ('SA', 2009, 'SB2009', 'www.isuresults.com/results/gpusa09/index.htm'), ('SA', 2010, 'SB2010', 'www.isuresults.com/results/gpusa2010/'), ('SA', 2011, 'SB2011', 'www.isuresults.com/results/gpusa2011/'), ('SA', 2012, 'SB2012', 'www.isuresults.com/results/gpusa2012/'), ('SA', 2013, 'SB2013', 'www.isuresults.com/results/gpusa2013/'), ('SA', 2014, 'SB2014', 'www.isuresults.com/results/gpusa2014/'), ('SA', 2015, 'SB2015', 'www.isuresults.com/results/season1516/gpusa2015/'), ('SA', 2016, 'SB2016', 'www.isuresults.com/results/season1617/gpusa2016/'), ('SA', 2017, 'SB2017', 'www.isuresults.com/results/season1718/gpusa2017/'), ('SA', 2018, 'SB2018', 'www.isuresults.com/events/fsevent03111613.htm'), ('SC', 2004, 'SB2004', 'www.isuresults.com/results/gpcan04/index.htm'), ('SC', 2005, 'SB2005', 'www.isuresults.com/results/gpcan05/'), ('SC', 2006, 'SB2006', 'www.isuresults.com/results/gpcan06/'), ('SC', 2007, 'SB2007', 'www.isuresults.com/results/gpcan07/'), ('SC', 2008, 'SB2008', 'www.isuresults.com/results/gpcan08/index.htm'), ('SC', 2009, 'SB2009', 'www.isuresults.com/results/gpcan09/index.htm'), ('SC', 2010, 'SB2010', 'www.isuresults.com/results/gpcan2010/'), ('SC', 2011, 'SB2011', 'www.isuresults.com/results/gpcan2011/'), ('SC', 2012, 'SB2012', 'www.isuresults.com/results/gpcan2012/'), ('SC', 2013, 'SB2013', 'www.isuresults.com/results/gpcan2013/'), ('SC', 2014, 'SB2014', 'www.isuresults.com/results/gpcan2014/'), ('SC', 2015, 'SB2015', 'www.isuresults.com/results/season1516/gpcan2015/'), ('SC', 2016, 'SB2016', 'www.isuresults.com/results/season1617/gpcan2016/'), ('SC', 2017, 'SB2017', 'www.isuresults.com/results/season1718/gpcan2017/'), ('SC', 2018, 'SB2018', 'www.isuresults.com/results/season1718/owg2018/TEC001RS.HTM'), ('EC', 2004, 'SB2003', 'www.isuresults.com/results/ec2004/index.htm'), ('EC', 2005, 'SB2004', 'www.isuresults.com/results/ec2005/'), ('EC', 2006, 'SB2005', 'www.isuresults.com/results/ec2006/'), ('EC', 2007, 'SB2006', 'www.isuresults.com/results/ec2007/'), ('EC', 2008, 'SB2007', 'www.isuresults.com/results/ec2008/'), ('EC', 2009, 'SB2008', 'www.isuresults.com/results/ec2009/'), ('EC', 2010, 'SB2009', 'www.isuresults.com/results/ec2010/'), ('EC', 2011, 'SB2010', 'www.isuresults.com/results/ec2011/'), ('EC', 2012, 'SB2011', 'www.isuresults.com/results/ec2012/'), ('EC', 2013, 'SB2012', 'www.isuresults.com/results/ec2013/'), ('EC', 2014, 'SB2013', 'www.isuresults.com/results/ec2014/'), ('EC', 2015, 'SB2014', 'www.isuresults.com/results/ec2015/'), ('EC', 2016, 'SB2015', 'www.isuresults.com/results/season1516/ec2016/'), ('EC', 2017, 'SB2016', 'www.isuresults.com/results/season1617/ec2017/'), ('EC', 2018, 'SB2017', 'www.isuresults.com/results/season1718/ec2018/'), ('WTT', 2004, 'SB2003', 'www.isuresults.com/results/ec2004/index.htm'), ('WTT', 2005, 'SB2004', 'www.isuresults.com/results/gpf0405/index.htm'), ('WTT', 2006, 'SB2005', 'www.isuresults.com/results/wc2006/'), ('WTT', 2007, 'SB2006', 'www.isuresults.com/results/wc2007/'), ('WTT', 2008, 'SB2007', 'www.isuresults.com/results/wc2008/'), ('WTT', 2009, 'SB2008', 'www.isuresults.com/results/wtt2009/'), ('WTT', 2010, 'SB2009', 'www.isuresults.com/results/wjc2010/index.htm'), ('WTT', 2011, 'SB2010', 'www.isuresults.com/results/wtt2012/'), ('WTT', 2012, 'SB2011', 'www.isuresults.com/results/wtt2012/'), ('WTT', 2013, 'SB2012', 'www.isuresults.com/results/wtt2013/'), ('WTT', 2014, 'SB2013', 'www.isuresults.com/results/wtt2015/'), ('WTT', 2015, 'SB2014', 'www.isuresults.com/results/wtt2015/'), ('WTT', 2016, 'SB2015', 'www.isuresults.com/results/season1516/wc2016/'), ('WTT', 2017, 'SB2016', 'www.isuresults.com/events/wtt2017/wtt-17_teams.htm'), ('WTT', 2018, 'SB2017', 'www.isuresults.com/results/season1718/wc2018/'), ('COC', 2004, 'SB2004', 'www.isuresults.com/results/gpchn04/index.htm'), ('COC', 2005, 'SB2005', 'www.isuresults.com/results/gpchn05/'), ('COC', 2006, 'SB2006', 'www.isuresults.com/results/gpchn06/'), ('COC', 2007, 'SB2007', 'www.isuresults.com/results/gpchn07/'), ('COC', 2008, 'SB2008', 'www.isuresults.com/results/gpchn08/index.htm'), ('COC', 2009, 'SB2009', 'www.isuresults.com/results/gpchn09/index.htm'), ('COC', 2010, 'SB2010', 'www.isuresults.com/results/gpchn2010/'), ('COC', 2011, 'SB2011', 'www.isuresults.com/results/gpchn2011/'), ('COC', 2012, 'SB2012', 'www.isuresults.com/results/gpchn2012/'), ('COC', 2013, 'SB2013', 'www.isuresults.com/results/gpchn2013/'), ('COC', 2014, 'SB2014', 'www.isuresults.com/results/gpchn2014/'), ('COC', 2015, 'SB2015', 'www.isuresults.com/results/season1516/gpchn2015/'), ('COC', 2016, 'SB2016', 'www.isuresults.com/results/season1617/gpchn2016/'), ('COC', 2017, 'SB2017', 'www.isuresults.com/results/season1718/gpchn2017/'), ('COC', 2018, 'SB2018', 'www.isuresults.com/.../gpchn2017_ColouredTimeSchedule.pdf'), ('NHK', 2004, 'SB2004', 'www.isuresults.com/results/gpjpn04/index.htm'), ('NHK', 2005, 'SB2005', 'www.isuresults.com/results/gpjpn05/'), ('NHK', 2006, 'SB2006', 'www.isuresults.com/results/gpjpn06/'), ('NHK', 2007, 'SB2007', 'www.isuresults.com/results/gpjpn07/'), ('NHK', 2008, 'SB2008', 'www.isuresults.com/results/gpjpn08/index.htm'), ('NHK', 2009, 'SB2009', 'www.isuresults.com/results/gpjpn09/index.htm'), ('NHK', 2010, 'SB2010', 'www.isuresults.com/results/gpjpn2010/'), ('NHK', 2011, 'SB2011', 'www.isuresults.com/results/gpjpn2011/'), ('NHK', 2012, 'SB2012', 'www.isuresults.com/results/gpjpn2012/'), ('NHK', 2013, 'SB2013', 'www.isuresults.com/results/gpjpn2013/'), ('NHK', 2014, 'SB2014', 'www.isuresults.com/results/gpjpn2014/'), ('NHK', 2015, 'SB2015', 'www.isuresults.com/results/season1516/gpjpn2015/'), ('NHK', 2016, 'SB2016', 'www.isuresults.com/results/season1617/gpjpn2016/'), ('NHK', 2017, 'SB2017', 'www.isuresults.com/results/season1718/gpjpn2017/'), ('NHK', 2018, 'SB2018', 'www.isuresults.com/.../gpjpn2017_ColouredTimeSchedule.pdf'), ('GPF', 2004, 'SB2004', 'www.isuresults.com/results/gpf0405/index.htm'), ('GPF', 2005, 'SB2005', 'www.isuresults.com/results/gpf0506/'), ('GPF', 2006, 'SB2006', 'www.isuresults.com/results/gpf0607/'), ('GPF', 2007, 'SB2007', 'www.isuresults.com/results/gpf0708/'), ('GPF', 2008, 'SB2008', 'www.isuresults.com/results/gpf0809/index.htm'), ('GPF', 2009, 'SB2009', 'www.isuresults.com/results/gpf0910/index.htm'), ('GPF', 2010, 'SB2010', 'www.isuresults.com/results/gpf1011/'), ('GPF', 2011, 'SB2011', 'www.isuresults.com/results/gpf1112/'), ('GPF', 2012, 'SB2012', 'www.isuresults.com/results/gpf1213/'), ('GPF', 2013, 'SB2013', 'www.isuresults.com/results/gpf1314/'), ('GPF', 2014, 'SB2014', 'www.isuresults.com/results/gpf1415/'), ('GPF', 2015, 'SB2015', 'www.isuresults.com/results/season1516/gpf1516/'), ('GPF', 2016, 'SB2016', 'www.isuresults.com/results/season1617/gpf1617/'), ('GPF', 2017, 'SB2017', 'www.isuresults.com/results/season1718/gpf1718/'), ('GPF', 2018, 'SB2018', 'www.isuresults.com/results/season1718/gpf1718/'), ('4CC', 2004, 'SB2003', 'www.isuresults.com/results/fc2004/index.htm'), ('4CC', 2005, 'SB2004', 'www.isuresults.com/results/fc2005/'), ('4CC', 2006, 'SB2005', 'www.isuresults.com/results/fc2006/'), ('4CC', 2007, 'SB2006', 'www.isuresults.com/results/fc2007/'), ('4CC', 2008, 'SB2007', 'www.isuresults.com/results/fc2008/'), ('4CC', 2009, 'SB2008', 'www.isuresults.com/results/fc2009/'), ('4CC', 2010, 'SB2009', 'www.isuresults.com/results/fc2010/index.htm'), ('4CC', 2011, 'SB2010', 'www.isuresults.com/results/fc2011/'), ('4CC', 2012, 'SB2011', 'www.isuresults.com/results/fc2012/'), ('4CC', 2013, 'SB2012', 'www.isuresults.com/results/fc2013/'), ('4CC', 2014, 'SB2013', 'www.isuresults.com/results/fc2014/'), ('4CC', 2015, 'SB2014', 'www.isuresults.com/results/fc2015/'), ('4CC', 2016, 'SB2015', 'www.isuresults.com/results/season1516/fc2016/'), ('4CC', 2017, 'SB2016', 'www.isuresults.com/results/season1617/fc2017/'), ('4CC', 2018, 'SB2017', 'www.isuresults.com/results/season1718/fc2018/'), ('OWG', 2004, 'SB2003', 'www.isuresults.com/bios/isufs_cr_00000595.htm'), ('OWG', 2005, 'SB2004', 'www.isuresults.com/bios/isufs_cr_00005733.htm'), ('OWG', 2006, 'SB2005', 'www.isuresults.com/results/owg2006/'), ('OWG', 2007, 'SB2006', 'www.isuresults.com/results/EYOF2007/'), ('OWG', 2008, 'SB2007', 'www.isuresults.com/results/owg2010/'), ('OWG', 2009, 'SB2008', 'www.isuresults.com/results/owg2010/'), ('OWG', 2010, 'SB2009', 'www.isuresults.com/results/owg2010/'), ('OWG', 2011, 'SB2010', 'www.isuresults.com/results/jgpaus2011/'), ('OWG', 2012, 'SB2011', 'www.isuresults.com/results/yog2012/'), ('OWG', 2013, 'SB2012', 'www.isuresults.com/results/owg2014/'), ('OWG', 2014, 'SB2013', 'www.isuresults.com/results/owg2014/'), ('OWG', 2015, 'SB2014', 'www.isuresults.com/results/owg2014/'), ('OWG', 2016, 'SB2015', 'www.isuresults.com/results/season1718/owg2018/SEG009.HTM'), ('OWG', 2017, 'SB2016', 'www.isuresults.com/results/season1718/owg2018/'), ('OWG', 2018, 'SB2017', 'www.isuresults.com/results/season1718/owg2018/'), ('WC', 2004, 'SB2003', 'www.isuresults.com/results/wc2004/index.htm'), ('WC', 2005, 'SB2004', 'www.isuresults.com/results/wc2005/'), ('WC', 2006, 'SB2005', 'www.isuresults.com/results/wc2006/'), ('WC', 2007, 'SB2006', 'www.isuresults.com/results/wc2007/'), ('WC', 2008, 'SB2007', 'www.isuresults.com/results/wc2008/'), ('WC', 2009, 'SB2008', 'www.isuresults.com/results/wc2009/'), ('WC', 2010, 'SB2009', 'www.isuresults.com/results/wc2010/'), ('WC', 2011, 'SB2010', 'www.isuresults.com/results/wc2011/'), ('WC', 2012, 'SB2011', 'www.isuresults.com/results/wc2012/'), ('WC', 2013, 'SB2012', 'www.isuresults.com/results/wc2013/'), ('WC', 2014, 'SB2013', 'www.isuresults.com/results/wc2014/'), ('WC', 2015, 'SB2014', 'www.isuresults.com/results/wc2015/'), ('WC', 2016, 'SB2015', 'www.isuresults.com/results/season1516/wc2016/'), ('WC', 2017, 'SB2016', 'www.isuresults.com/results/season1617/wc2017/'), ('WC', 2018, 'SB2017', 'www.isuresults.com/results/season1718/wc2018/'), ('TDF', 2004, 'SB2004', 'www.isuresults.com/results/gpfra04/index.htm'), ('TDF', 2006, 'SB2006', 'www.isuresults.com/results/gpfra06/'), ('TDF', 2007, 'SB2007', 'www.isuresults.com/results/gpfra07/'), ('TDF', 2008, 'SB2008', 'www.isuresults.com/results/gpfra08/index.htm'), ('TDF', 2009, 'SB2009', 'www.isuresults.com/results/gpfra09/'), ('TDF', 2010, 'SB2010', 'www.isuresults.com/results/gpfra2010/'), ('TDF', 2011, 'SB2011', 'www.isuresults.com/results/gpfra2011/'), ('TDF', 2012, 'SB2012', 'www.isuresults.com/results/gpfra2012/'), ('TDF', 2013, 'SB2013', 'www.isuresults.com/results/gpfra2013/'), ('TDF', 2014, 'SB2014', 'www.isuresults.com/results/gpfra2014/'), ('TDF', 2015, 'SB2015', 'www.isuresults.com/results/season1516/gpfra2015/'), ('TDF', 2016, 'SB2016', 'www.isuresults.com/results/season1617/gpfra2016/'), ('TDF', 2017, 'SB2017', 'www.isuresults.com/results/season1718/gpfra2017/'), ('TDF', 2018, 'SB2018', 'www.isuresults.com/results/season1718/fc2018/')]


class EventSearch:
    def __init__(self, search_phrase, search_year, category=SEARCH_CAT, per_disc_settings=PER_DISCIPLINE_SETTINGS,
                 url=None):
        """ Placeholder
        """
        self.event = event.Event(search_phrase=search_phrase, search_year=search_year)
        self.category = category
        self.per_disc_settings = per_disc_settings
        self.expected_domain = EXPECTED_DOMAIN[self.event.name] if self.event.name in EXPECTED_DOMAIN else None
        self.fed_abbrev = DBNAME_TO_URLNAME[self.event.name] if self.event.name in DBNAME_TO_URLNAME else None
        self.homepage_url = url
        self.homepage, self.homepage_text = self.__get_homepage_content()
        self.start_date = None

    def __get_homepage_content(self):
        if self.homepage_url:
            r = request_url("http://" + self.homepage_url if "http" not in self.homepage_url else self.homepage_url)
            page = BeautifulSoup(r.content, "html5lib")
            raw_text = " ".join([s for s in page.strings])
            compact_text = "".join([i for i in raw_text if i != "\t" and i != "\n"])
            return page, compact_text
        else:
            return None, None

    def __test_result(self, url):
        """Checks that a google search hit satisfies the condition that make it a likely event homepage
        (e.g. that it occurs in the expected year, was posted on the expected domain, etc.)
        """
        if self.expected_domain:
            domain_test = (self.event.is_A_comp and "isuresults" in url) or \
                          (not self.event.is_A_comp and self.expected_domain in url)
        else:
            domain_test = False
        logger.debug(f"Testing {url} -- domain test: {domain_test}")

        if self.fed_abbrev:
            gpf_pattern = (self.fed_abbrev == "gpf") and (str(self.event.year)[-2:] + str(self.event.year + 1)[-2:] in url)
            name_test = self.fed_abbrev in url
            logger.debug(f"Testing {url} -- name test: {name_test}")
        else:
            gpf_pattern, name_test = False, False

        season_pattern = str(self.event.year) in url or \
                         (self.event.season[2:] in url and str(int(self.event.season[2:])+1) in url) or \
                         self.event.season[4:] + str(int(self.event.season[4:])+1) in url

        filters = all(domain not in url for domain in ["goldenskate", "wiki", "bios", "revolvy"])
        url_test = [domain_test, (gpf_pattern or season_pattern), name_test]

        r = request_url("http://" + url if "http" not in url else url)
        event_page = BeautifulSoup(r.content, "html5lib")
        raw_text = " ".join([s for s in event_page.strings])
        compact_text = "".join([i for i in raw_text if i != "\t" and i != "\n"])
        required_strings = self.event.search_string.split("+") + [str(self.event.year)]
        text_test = all(i.lower() in compact_text.lower() for i in required_strings)

        if filters and (sum(url_test) >= 3 or text_test):
            logger.info(f"URL {url} passed tests for {self.event.name} {self.event.year} with {sum(url_test)}, {text_test}.")
            return True, event_page, compact_text
        else:
            logger.info(f"URL {url} failed tests for {self.event.name} {self.event.year}.")
            return False, None, None

    def __construct_absolute_url(self, sublink):
        """Combines a url and a relative link found on the url's page and returns one absolute url.

        Two cases: (1) If sublink is relative to a subdomain (e.g. "xx.pdf"), strips "index" portion of the the subdomain
        url and appends sublink to it (e.g. "pokemon.io/woot/index.html" becomes "pokemon.io/woot/"). (2) If sublink has an
        address that is relative to the root domain (e.g. "/wahey/yeah/xx.pdf"), extract root domain only ("pokemon.io")
        from subdomain url and append to that
        sub_link -- A relative link found on the event homepage
        """
        if sublink[:4] == "http":
            root = ""
        elif sublink[0] == "/":
            root = re.search(root_domain_pattern, self.homepage_url).group(1)
        elif "index" in self.homepage_url:
            root = re.sub(r"/index[A-Za-z\d]*\.htm[l]*$", "/", self.homepage_url)
        else:
            root = self.homepage_url
        temp = root + sublink
        return "http://" + temp if temp[:4] != "http" else temp

    def set_event_homepage(self):
        """Performs google search for results from a given event & year, returns first result that passes tests/
        """
        domain = "isu+" if self.event.is_A_comp else ""
        search = "https://www.google.co.uk/search?q=" + domain + "+results+" + self.event.search_string \
                 + "+" + str(self.event.year) #+ self.category
        logger.info(f"Running google search {search}")

        google_r = request_url(url=search, on_failure=None)
        google_page = BeautifulSoup(google_r.text, "html.parser")

        for l in google_page.find_all("cite"):
            test, homepage, homepage_text = self.__test_result(url=l.text)
            if test:
                self.homepage_url = l.text
                self.homepage = homepage
                self.homepage_text = homepage_text
                self.set_start_date()
                break
        if not self.homepage_url:
            return False
        else:
            return True

    def set_start_date(self):
        """Scrapes an event page and returns its start date in datetime (extracted from a "start date - end date" range)
        """
        try:
            self.start_date = start_date.EventDate(year=self.event.year, text_to_parse=self.homepage_text)
        except ValueError:
            logger.error(f"Could not parse date from text for {self.event.name} {self.event.year}")


    def generate_pdf_filename(self, pdf_link, disc_code):
        """Generates the pdf filename from the sublink and other known event identifiers
        """
        raw_name = pdf_link.rpartition("/")[2]
        if re.search(r"data[0-9]{4}", raw_name):
            length = "S" if disc_code[2:] == "03" else "F"
            programme_type = "D" if event.DISC_CODES_DIC[disc_code] == "Dance" else "P"
            filename = "_".join([self.event.name + str(self.event.year), event.DISC_CODES_DIC[disc_code], length + programme_type]) + ".pdf"
        else:
            filename = self.event.name + "_" + raw_name
        return self.start_date.start_date.strftime("%y%m%d") + "_" + filename

    def download_pdf_protocols(self):
        """Downloads the pdf scoring protocols for the requested disciplines from the event page.

        Keyword arguments:
        event_page -- BeautifulSoup parsed requests object
        event_start_date -- datetime object denoting the start of the event, used in pdf filename
        per_discipline_settings -- Dictionary of bools structured as follows {"men": True, "ladies": True, "pairs": True,
        "dance": True}
        """
        all_sublinks = list(set([a.get("href") for a in self.homepage.find_all("a")]))
        for sublink in all_sublinks:
            logger.info(f"Examining {sublink} for {self.event.name} {self.event.year}")

            # Loop through each discipline, checking the setting in settings dic and loading the correct dic of codes
            for disc in self.per_disc_settings:
                if self.per_disc_settings[disc]:

                    for code in event.DISC_CODES_DICS[disc.upper() + "_CODES"]:
                        if re.search(code, str(sublink)) and "novice" not in str(sublink).lower():
                            logger.info(f"Code {code} matches {sublink}")

                            filename = self.generate_pdf_filename(pdf_link=sublink, disc_code=code)
                            full_url = self.__construct_absolute_url(sublink=sublink)

                            # Get contents of sublink
                            try:
                                req = urllib.request.Request(full_url, headers=HEADERS)
                                res = urllib.request.urlopen(req)
                            except urllib.error.HTTPError as herr:
                                logger.error(f"HTTP {str(herr.code)} error opening {full_url}")
                            except urllib.error.URLError as uerr:
                                logger.error(f"URL error opening {full_url}: {uerr.reason}")
                            else:
                                pdf = open(settings.WRITE_PATH + filename, "wb")
                                pdf.write(res.read())
                                pdf.close()


def request_url(url, on_failure=None, *args):
    """Requests provided url up to MAX_TRIES times, and implements error handler function if provided.

    Requests provided url up to MAX_TRIES times, and implements error handler function if provided - e.g. to fetch
    second page of google results in case of not correct match on first page. No default error handler function provided.
    Keyword arguments:
    url -- url to request
    on_failure -- function to handle any HTTP or
    terms_to_search -- list of competition names
    """
    r = None
    for i in range(0, MAX_TRIES):
        try:
            r = requests.get(url, headers=HEADERS, timeout=3)
            r.raise_for_status()
        except requests.exceptions.Timeout as terr:
            logger.error(f"Timeout error on {url} on try {i+1}: {terr}")
            continue
        except requests.exceptions.HTTPError as herr:
            if on_failure:
                logger.error(f"HTTP error on {url}, implementing alternative: {herr}")
                on_failure(*args)
                break
            else:
                logger.error(f"HTTP error on {url}, no do overs: {herr}")
                sys.exit(1)
        except requests.exceptions.TooManyRedirects as rerr:
            if on_failure:
                logger.error(f"HTTP error on {url}, implementing alternative: {rerr}")
                on_failure(*args)
                break
            else:
                logger.error(f"HTTP error on {url}, no do overs: {rerr}")
                sys.exit(1)
        except requests.exceptions.RequestException as err:
            logger.error(f"Failed on {url}: {err}")
            sys.exit(1)
        break
    return r


if __name__ == '__main__':
    # If homepage search works, use this block of code
    for search_event in GOOGLE_SEARCH_TERMS:
        for search_year in range(START_YEAR, END_YEAR + 1):
            search = EventSearch(search_event, search_year)
            success = search.set_event_homepage()
            if not success:
                logger.error(f"Could not find google result that passed tests for {search.name} {search.year}")
            else:
                search.download_pdf_protocols()
                logger.info(f"Downloaded protocols for {search.event.name} {search.event.year}")

    # # If homepage needs to be inserted manually, uncomment and paste into "url=" below
    # search = EventSearch(search_phrase="ondrej+nepela+trophy", search_year=2014,
    #                      url="http://www.kraso.sk/wp-content/uploads/sutaze/2014_2015/20141001_ont/html/")
    # search.set_start_date()
    # search.download_pdf_protocols()

