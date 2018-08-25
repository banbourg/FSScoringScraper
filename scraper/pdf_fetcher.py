#!/bin/env python

import requests
from bs4 import BeautifulSoup
from datetime import datetime
import urllib.request, urllib.error, urllib.parse

import re
import sys
import logging

LOG_FILENAME = 'log_pdf_fetcher.log'
logging.basicConfig(# filename=LOG_FILENAME,
                    format="%(asctime)s - %(name)s - %(levelname)-5s - %(message)s",
                    level=logging.INFO,
                    datefmt='%Y-%m-%d %H:%M:%S')

logger = logging.getLogger(__name__)

try:
    import settings as s
except ImportError as exc:
    logger.error(f"Failed to import settings module ({exc})")
    sys.exit(1)


# ------------------------------------------- CHANGE SEARCH PARAMETERS HERE --------------------------------------------
START_YEAR, END_YEAR = 2016, 2017
GOOGLE_SEARCH_TERMS = ["lombardia+trophy", "nebelhorn+trophy", "finlandia+trophy", "autumn+classic+international"]
PER_DISCIPLINE_SETTINGS = {"men": True, "ladies": True, "pairs": True, "dance": True}
SENIOR_FLAG = 1 # set to 0 to search for juniors
# ----------------------------------------------------------------------------------------------------------------------

# CONSTANTS AND CONVERTER DICTIONARIES, NO NEED TO AMEND THESE EXCEPT IF ADDING NEW EVENTS
date_pattern_1 = re.compile(r"(\d{1,2}[/\-.]\d{2}[/\-.]\d{4}).{1,6}\d{1,2}[/\-.]\d{2}[/\-.]\d{4}")
date_pattern_2 = re.compile(r"((Jan(uary)?|Feb(ruary)?|Mar(ch)?|Apr(il)?|May|Jun(e)?|Jul(y)?|Aug(ust)?|"
                            r"Sep(tember)?|Oct(ober)?|Nov(ember)?|Dec(ember)?)\s+\d{1,2},\s+\d{4}).{1,6}"
                            r"(Jan(uary)?|Feb(ruary)?|Mar(ch)?|Apr(il)?|May|Jun(e)?|Jul(y)?|Aug(ust)?|"
                            r"Sep(tember)?|Oct(ober)?|Nov(ember)?|Dec(ember)?)\s+\d{1,2},\s+\d{4}")
date_pattern_3 = re.compile(r"(Jan(uary)?|Feb(ruary)?|Mar(ch)?|Apr(il)?|May|Jun(e)?|Jul(y)?|Aug(ust)?|Sep(tember)?|"
                           r"Oct(ober)?|Nov(ember)?|Dec(ember)?)\s+\d{1,2}.{1,4}\d{1,2}.{1,4}\d{4}")
root_domain_pattern = re.compile(r"^((?:http(?:s)?://)?(www)?[A-Za-z\d\-]{3,}\.[a-z\.]{2,6})(?:\/)")

MAX_TRIES = 10  # before timeout on .get() requests

EXPECTED_DOMAIN = {"AO": "fsatresults", "Lombardia": "fisg", "USClassic": "usfigureskating", "Nepela": "kraso",
                   "ACI": "skatecanada", "Nebelhorn": "isuresults", "Finlandia": "figureskatingresults",
                   "Tallinn": "data.tallinntrophy", "Warsaw": "pfsa"}

SEARCHTERM_TO_DBNAME = {"nhk": "NHK", "france": "TDF", "canada": "SC", "russia": "COR", "america": "SA", "china": "COC",
                        "GPF": "GPF", "world": "WC", "continents": "4CC", "olympic": "OWG", "wtt": "WTT",
                        "europeans": "EC", "bompard": "TDF", "asian+open": "AO", "lombardia+trophy": "Lombardia",
                        "us+figure+skating+classic": "USClassic", "ondrej+nepela": "Nepela",
                        "autumn+classic+international": "ACI", "nebelhorn+trophy": "Nebelhorn",
                        "finlandia+trophy": "Finlandia", "talinn+trophy": "Tallinn", "warsaw+cup": "Warsaw"}

DBNAME_TO_URLNAME = {"NHK": "gpjpn", "TDF": "gpfra", "SC": "gpcan", "COR": "gprus", "SA": "gpusa", "COC": "gpchn",
                     "GPF": "gpf", "WC": "wc", "4CC": "fc", "OWG": "owg", "WTT": "wtt", "EC": "ec", "AO": "AO",
                     "Lombardia": "lombardia", "Nepela": "nepela", "Finlandia": "CSFIN", "Nebelhorn": "nt",
                     "ACI": "CSCAN"}

H2_EVENTS = ["WC", "WTT", "4CC", "OWG", "EC"]

ISU_A_COMPS = ["NHK", "TDF", "SC", "COR", "SA", "COC", "GPF", "WC", "4CC", "OWG", "WTT", "EC"]

DISC_CODES = {"LADIES_CODES": {r"(?i)lad(?:y|ies)|women.*score": "Ladies", "0203": "Ladies", "0205": "Ladies"},
              "MEN_CODES": {r"(?i)(?<!wo)men.*score": "Men", "0103": "Men", "0105": "Men"},
              "PAIRS_CODES": {r"(?i)pairs.*score": "Pairs", "0303": "Pairs", "0305": "Pairs"},
              "DANCE_CODES": {r"(?i)danc.*score": "Dance", "0403": "Dance", "0405": "Dance"}}
HEADERS = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_13_6) AppleWebKit/537.36 (KHTML, like Gecko) "
                         "Chrome/68.0.3440.106 Safari/537.36"}

# -- A CHEAT: My internet was being super slow so I pasted the output from step 1 below to avoid having to rerun it.
# This covers '''
# google_link_list = [('COR', 2004, 'SB2004', 'www.isuresults.com/results/gprus04/index.htm'), ('COR', 2005, 'SB2005', 'www.isuresults.com/results/gprus05/'), ('COR', 2006, 'SB2006', 'www.isuresults.com/results/gprus06/'), ('COR', 2007, 'SB2007', 'www.isuresults.com/results/gprus07/'), ('COR', 2008, 'SB2008', 'www.isuresults.com/results/gprus08/index.htm'), ('COR', 2009, 'SB2009', 'www.isuresults.com/results/gprus09/'), ('COR', 2010, 'SB2010', 'www.isuresults.com/results/gprus2010/'), ('COR', 2011, 'SB2011', 'www.isuresults.com/results/gprus2011/'), ('COR', 2012, 'SB2012', 'www.isuresults.com/results/gprus2012/'), ('COR', 2013, 'SB2013', 'www.isuresults.com/results/gprus2013/'), ('COR', 2014, 'SB2014', 'www.isuresults.com/results/gprus2014/'), ('COR', 2015, 'SB2015', 'www.isuresults.com/results/season1516/gprus2015/'), ('COR', 2016, 'SB2016', 'www.isuresults.com/results/season1617/gprus2016/'), ('COR', 2017, 'SB2017', 'www.isuresults.com/results/season1718/gprus2017/'), ('COR', 2018, 'SB2018', 'www.isuresults.com/results/season1718/wc2018/'), ('TDF', 2005, 'SB2005', 'www.isuresults.com/results/gpfra05/'), ('TDF', 2006, 'SB2006', 'www.isuresults.com/results/gpfra06/'), ('TDF', 2007, 'SB2007', 'www.isuresults.com/results/wc2007/CAT004RS.HTM'), ('TDF', 2008, 'SB2008', 'www.isuresults.com/results/jgpfra2008/'), ('TDF', 2009, 'SB2009', 'www.isuresults.com/results/gpfra09/'), ('TDF', 2010, 'SB2010', 'www.isuresults.com/results/jgpfra2010/'), ('TDF', 2011, 'SB2011', 'www.isuresults.com/results/gpfra2011/'), ('TDF', 2012, 'SB2012', 'www.isuresults.com/results/jgpfra2012/'), ('TDF', 2013, 'SB2013', 'www.isuresults.com/results/gpfra2013/'), ('TDF', 2014, 'SB2014', 'www.isuresults.com/results/gpfra2014/'), ('TDF', 2015, 'SB2015', 'www.isuresults.com/results/season1617/gpfra2016/'), ('TDF', 2016, 'SB2016', 'www.isuresults.com/results/season1617/gpfra2016/'), ('TDF', 2017, 'SB2017', 'www.isuresults.com/results/season1718/gpfra2017/'), ('TDF', 2018, 'SB2018', 'www.isuresults.com/events/fsevent03111630.htm'), ('SA', 2004, 'SB2004', 'www.isuresults.com/results/gpusa04/index.htm'), ('SA', 2005, 'SB2005', 'www.isuresults.com/results/gpusa05/'), ('SA', 2006, 'SB2006', 'www.isuresults.com/results/gpusa06/'), ('SA', 2007, 'SB2007', 'www.isuresults.com/results/gpusa07/'), ('SA', 2008, 'SB2008', 'www.isuresults.com/results/gpusa08/index.htm'), ('SA', 2009, 'SB2009', 'www.isuresults.com/results/gpusa09/index.htm'), ('SA', 2010, 'SB2010', 'www.isuresults.com/results/gpusa2010/'), ('SA', 2011, 'SB2011', 'www.isuresults.com/results/gpusa2011/'), ('SA', 2012, 'SB2012', 'www.isuresults.com/results/gpusa2012/'), ('SA', 2013, 'SB2013', 'www.isuresults.com/results/gpusa2013/'), ('SA', 2014, 'SB2014', 'www.isuresults.com/results/gpusa2014/'), ('SA', 2015, 'SB2015', 'www.isuresults.com/results/season1516/gpusa2015/'), ('SA', 2016, 'SB2016', 'www.isuresults.com/results/season1617/gpusa2016/'), ('SA', 2017, 'SB2017', 'www.isuresults.com/results/season1718/gpusa2017/'), ('SA', 2018, 'SB2018', 'www.isuresults.com/events/fsevent03111613.htm'), ('SC', 2004, 'SB2004', 'www.isuresults.com/results/gpcan04/index.htm'), ('SC', 2005, 'SB2005', 'www.isuresults.com/results/gpcan05/'), ('SC', 2006, 'SB2006', 'www.isuresults.com/results/gpcan06/'), ('SC', 2007, 'SB2007', 'www.isuresults.com/results/gpcan07/'), ('SC', 2008, 'SB2008', 'www.isuresults.com/results/gpcan08/index.htm'), ('SC', 2009, 'SB2009', 'www.isuresults.com/results/gpcan09/index.htm'), ('SC', 2010, 'SB2010', 'www.isuresults.com/results/gpcan2010/'), ('SC', 2011, 'SB2011', 'www.isuresults.com/results/gpcan2011/'), ('SC', 2012, 'SB2012', 'www.isuresults.com/results/gpcan2012/'), ('SC', 2013, 'SB2013', 'www.isuresults.com/results/gpcan2013/'), ('SC', 2014, 'SB2014', 'www.isuresults.com/results/gpcan2014/'), ('SC', 2015, 'SB2015', 'www.isuresults.com/results/season1516/gpcan2015/'), ('SC', 2016, 'SB2016', 'www.isuresults.com/results/season1617/gpcan2016/'), ('SC', 2017, 'SB2017', 'www.isuresults.com/results/season1718/gpcan2017/'), ('SC', 2018, 'SB2018', 'www.isuresults.com/results/season1718/owg2018/TEC001RS.HTM'), ('EC', 2004, 'SB2003', 'www.isuresults.com/results/ec2004/index.htm'), ('EC', 2005, 'SB2004', 'www.isuresults.com/results/ec2005/'), ('EC', 2006, 'SB2005', 'www.isuresults.com/results/ec2006/'), ('EC', 2007, 'SB2006', 'www.isuresults.com/results/ec2007/'), ('EC', 2008, 'SB2007', 'www.isuresults.com/results/ec2008/'), ('EC', 2009, 'SB2008', 'www.isuresults.com/results/ec2009/'), ('EC', 2010, 'SB2009', 'www.isuresults.com/results/ec2010/'), ('EC', 2011, 'SB2010', 'www.isuresults.com/results/ec2011/'), ('EC', 2012, 'SB2011', 'www.isuresults.com/results/ec2012/'), ('EC', 2013, 'SB2012', 'www.isuresults.com/results/ec2013/'), ('EC', 2014, 'SB2013', 'www.isuresults.com/results/ec2014/'), ('EC', 2015, 'SB2014', 'www.isuresults.com/results/ec2015/'), ('EC', 2016, 'SB2015', 'www.isuresults.com/results/season1516/ec2016/'), ('EC', 2017, 'SB2016', 'www.isuresults.com/results/season1617/ec2017/'), ('EC', 2018, 'SB2017', 'www.isuresults.com/results/season1718/ec2018/'), ('WTT', 2004, 'SB2003', 'www.isuresults.com/results/ec2004/index.htm'), ('WTT', 2005, 'SB2004', 'www.isuresults.com/results/gpf0405/index.htm'), ('WTT', 2006, 'SB2005', 'www.isuresults.com/results/wc2006/'), ('WTT', 2007, 'SB2006', 'www.isuresults.com/results/wc2007/'), ('WTT', 2008, 'SB2007', 'www.isuresults.com/results/wc2008/'), ('WTT', 2009, 'SB2008', 'www.isuresults.com/results/wtt2009/'), ('WTT', 2010, 'SB2009', 'www.isuresults.com/results/wjc2010/index.htm'), ('WTT', 2011, 'SB2010', 'www.isuresults.com/results/wtt2012/'), ('WTT', 2012, 'SB2011', 'www.isuresults.com/results/wtt2012/'), ('WTT', 2013, 'SB2012', 'www.isuresults.com/results/wtt2013/'), ('WTT', 2014, 'SB2013', 'www.isuresults.com/results/wtt2015/'), ('WTT', 2015, 'SB2014', 'www.isuresults.com/results/wtt2015/'), ('WTT', 2016, 'SB2015', 'www.isuresults.com/results/season1516/wc2016/'), ('WTT', 2017, 'SB2016', 'www.isuresults.com/events/wtt2017/wtt-17_teams.htm'), ('WTT', 2018, 'SB2017', 'www.isuresults.com/results/season1718/wc2018/'), ('COC', 2004, 'SB2004', 'www.isuresults.com/results/gpchn04/index.htm'), ('COC', 2005, 'SB2005', 'www.isuresults.com/results/gpchn05/'), ('COC', 2006, 'SB2006', 'www.isuresults.com/results/gpchn06/'), ('COC', 2007, 'SB2007', 'www.isuresults.com/results/gpchn07/'), ('COC', 2008, 'SB2008', 'www.isuresults.com/results/gpchn08/index.htm'), ('COC', 2009, 'SB2009', 'www.isuresults.com/results/gpchn09/index.htm'), ('COC', 2010, 'SB2010', 'www.isuresults.com/results/gpchn2010/'), ('COC', 2011, 'SB2011', 'www.isuresults.com/results/gpchn2011/'), ('COC', 2012, 'SB2012', 'www.isuresults.com/results/gpchn2012/'), ('COC', 2013, 'SB2013', 'www.isuresults.com/results/gpchn2013/'), ('COC', 2014, 'SB2014', 'www.isuresults.com/results/gpchn2014/'), ('COC', 2015, 'SB2015', 'www.isuresults.com/results/season1516/gpchn2015/'), ('COC', 2016, 'SB2016', 'www.isuresults.com/results/season1617/gpchn2016/'), ('COC', 2017, 'SB2017', 'www.isuresults.com/results/season1718/gpchn2017/'), ('COC', 2018, 'SB2018', 'www.isuresults.com/.../gpchn2017_ColouredTimeSchedule.pdf'), ('NHK', 2004, 'SB2004', 'www.isuresults.com/results/gpjpn04/index.htm'), ('NHK', 2005, 'SB2005', 'www.isuresults.com/results/gpjpn05/'), ('NHK', 2006, 'SB2006', 'www.isuresults.com/results/gpjpn06/'), ('NHK', 2007, 'SB2007', 'www.isuresults.com/results/gpjpn07/'), ('NHK', 2008, 'SB2008', 'www.isuresults.com/results/gpjpn08/index.htm'), ('NHK', 2009, 'SB2009', 'www.isuresults.com/results/gpjpn09/index.htm'), ('NHK', 2010, 'SB2010', 'www.isuresults.com/results/gpjpn2010/'), ('NHK', 2011, 'SB2011', 'www.isuresults.com/results/gpjpn2011/'), ('NHK', 2012, 'SB2012', 'www.isuresults.com/results/gpjpn2012/'), ('NHK', 2013, 'SB2013', 'www.isuresults.com/results/gpjpn2013/'), ('NHK', 2014, 'SB2014', 'www.isuresults.com/results/gpjpn2014/'), ('NHK', 2015, 'SB2015', 'www.isuresults.com/results/season1516/gpjpn2015/'), ('NHK', 2016, 'SB2016', 'www.isuresults.com/results/season1617/gpjpn2016/'), ('NHK', 2017, 'SB2017', 'www.isuresults.com/results/season1718/gpjpn2017/'), ('NHK', 2018, 'SB2018', 'www.isuresults.com/.../gpjpn2017_ColouredTimeSchedule.pdf'), ('GPF', 2004, 'SB2004', 'www.isuresults.com/results/gpf0405/index.htm'), ('GPF', 2005, 'SB2005', 'www.isuresults.com/results/gpf0506/'), ('GPF', 2006, 'SB2006', 'www.isuresults.com/results/gpf0607/'), ('GPF', 2007, 'SB2007', 'www.isuresults.com/results/gpf0708/'), ('GPF', 2008, 'SB2008', 'www.isuresults.com/results/gpf0809/index.htm'), ('GPF', 2009, 'SB2009', 'www.isuresults.com/results/gpf0910/index.htm'), ('GPF', 2010, 'SB2010', 'www.isuresults.com/results/gpf1011/'), ('GPF', 2011, 'SB2011', 'www.isuresults.com/results/gpf1112/'), ('GPF', 2012, 'SB2012', 'www.isuresults.com/results/gpf1213/'), ('GPF', 2013, 'SB2013', 'www.isuresults.com/results/gpf1314/'), ('GPF', 2014, 'SB2014', 'www.isuresults.com/results/gpf1415/'), ('GPF', 2015, 'SB2015', 'www.isuresults.com/results/season1516/gpf1516/'), ('GPF', 2016, 'SB2016', 'www.isuresults.com/results/season1617/gpf1617/'), ('GPF', 2017, 'SB2017', 'www.isuresults.com/results/season1718/gpf1718/'), ('GPF', 2018, 'SB2018', 'www.isuresults.com/results/season1718/gpf1718/'), ('4CC', 2004, 'SB2003', 'www.isuresults.com/results/fc2004/index.htm'), ('4CC', 2005, 'SB2004', 'www.isuresults.com/results/fc2005/'), ('4CC', 2006, 'SB2005', 'www.isuresults.com/results/fc2006/'), ('4CC', 2007, 'SB2006', 'www.isuresults.com/results/fc2007/'), ('4CC', 2008, 'SB2007', 'www.isuresults.com/results/fc2008/'), ('4CC', 2009, 'SB2008', 'www.isuresults.com/results/fc2009/'), ('4CC', 2010, 'SB2009', 'www.isuresults.com/results/fc2010/index.htm'), ('4CC', 2011, 'SB2010', 'www.isuresults.com/results/fc2011/'), ('4CC', 2012, 'SB2011', 'www.isuresults.com/results/fc2012/'), ('4CC', 2013, 'SB2012', 'www.isuresults.com/results/fc2013/'), ('4CC', 2014, 'SB2013', 'www.isuresults.com/results/fc2014/'), ('4CC', 2015, 'SB2014', 'www.isuresults.com/results/fc2015/'), ('4CC', 2016, 'SB2015', 'www.isuresults.com/results/season1516/fc2016/'), ('4CC', 2017, 'SB2016', 'www.isuresults.com/results/season1617/fc2017/'), ('4CC', 2018, 'SB2017', 'www.isuresults.com/results/season1718/fc2018/'), ('OWG', 2004, 'SB2003', 'www.isuresults.com/bios/isufs_cr_00000595.htm'), ('OWG', 2005, 'SB2004', 'www.isuresults.com/bios/isufs_cr_00005733.htm'), ('OWG', 2006, 'SB2005', 'www.isuresults.com/results/owg2006/'), ('OWG', 2007, 'SB2006', 'www.isuresults.com/results/EYOF2007/'), ('OWG', 2008, 'SB2007', 'www.isuresults.com/results/owg2010/'), ('OWG', 2009, 'SB2008', 'www.isuresults.com/results/owg2010/'), ('OWG', 2010, 'SB2009', 'www.isuresults.com/results/owg2010/'), ('OWG', 2011, 'SB2010', 'www.isuresults.com/results/jgpaus2011/'), ('OWG', 2012, 'SB2011', 'www.isuresults.com/results/yog2012/'), ('OWG', 2013, 'SB2012', 'www.isuresults.com/results/owg2014/'), ('OWG', 2014, 'SB2013', 'www.isuresults.com/results/owg2014/'), ('OWG', 2015, 'SB2014', 'www.isuresults.com/results/owg2014/'), ('OWG', 2016, 'SB2015', 'www.isuresults.com/results/season1718/owg2018/SEG009.HTM'), ('OWG', 2017, 'SB2016', 'www.isuresults.com/results/season1718/owg2018/'), ('OWG', 2018, 'SB2017', 'www.isuresults.com/results/season1718/owg2018/'), ('WC', 2004, 'SB2003', 'www.isuresults.com/results/wc2004/index.htm'), ('WC', 2005, 'SB2004', 'www.isuresults.com/results/wc2005/'), ('WC', 2006, 'SB2005', 'www.isuresults.com/results/wc2006/'), ('WC', 2007, 'SB2006', 'www.isuresults.com/results/wc2007/'), ('WC', 2008, 'SB2007', 'www.isuresults.com/results/wc2008/'), ('WC', 2009, 'SB2008', 'www.isuresults.com/results/wc2009/'), ('WC', 2010, 'SB2009', 'www.isuresults.com/results/wc2010/'), ('WC', 2011, 'SB2010', 'www.isuresults.com/results/wc2011/'), ('WC', 2012, 'SB2011', 'www.isuresults.com/results/wc2012/'), ('WC', 2013, 'SB2012', 'www.isuresults.com/results/wc2013/'), ('WC', 2014, 'SB2013', 'www.isuresults.com/results/wc2014/'), ('WC', 2015, 'SB2014', 'www.isuresults.com/results/wc2015/'), ('WC', 2016, 'SB2015', 'www.isuresults.com/results/season1516/wc2016/'), ('WC', 2017, 'SB2016', 'www.isuresults.com/results/season1617/wc2017/'), ('WC', 2018, 'SB2017', 'www.isuresults.com/results/season1718/wc2018/'), ('TDF', 2004, 'SB2004', 'www.isuresults.com/results/gpfra04/index.htm'), ('TDF', 2006, 'SB2006', 'www.isuresults.com/results/gpfra06/'), ('TDF', 2007, 'SB2007', 'www.isuresults.com/results/gpfra07/'), ('TDF', 2008, 'SB2008', 'www.isuresults.com/results/gpfra08/index.htm'), ('TDF', 2009, 'SB2009', 'www.isuresults.com/results/gpfra09/'), ('TDF', 2010, 'SB2010', 'www.isuresults.com/results/gpfra2010/'), ('TDF', 2011, 'SB2011', 'www.isuresults.com/results/gpfra2011/'), ('TDF', 2012, 'SB2012', 'www.isuresults.com/results/gpfra2012/'), ('TDF', 2013, 'SB2013', 'www.isuresults.com/results/gpfra2013/'), ('TDF', 2014, 'SB2014', 'www.isuresults.com/results/gpfra2014/'), ('TDF', 2015, 'SB2015', 'www.isuresults.com/results/season1516/gpfra2015/'), ('TDF', 2016, 'SB2016', 'www.isuresults.com/results/season1617/gpfra2016/'), ('TDF', 2017, 'SB2017', 'www.isuresults.com/results/season1718/gpfra2017/'), ('TDF', 2018, 'SB2018', 'www.isuresults.com/results/season1718/fc2018/')]


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


def fetch_event_start_date(event_page, event, year):
    """Scrapes an event page for its start date, based on known page layouts and tags, and returns it in datetime.

    Note: Uses specific BS tags to avoid picking up page update dates, 'last modified' dates etc by mistake. Three
    cases were observed when scraping ISU pages for dates: (1) base case - date range for the event is stored in the
    header (<tr> tags); (2) first special case (and new layout I think) schedule is stored in separate table below
    "main", with no date range provided in title (<td> tags); (3) second special case - dates are written in text
    (<p> tags)
    Keyword arguments:
    event_page -- BeautifulSoup parsed requests object
    year -- Year in which event took place (to double check dates)
    """
    # --- a. Fetch date of 1st day of comp (to allow ordering within season)
    text = " ".join([s for s in event_page.strings])
    text = "".join([i for i in text if i != "\t" and i != "\n"])
    date_search_1 = re.search(date_pattern_1, text)
    date_search_2 = re.search(date_pattern_2, text) if date_search_1 is None else date_search_1
    date_search_3 = re.search(date_pattern_3, text) if date_search_2 is None else date_search_2
    try:
        date = date_search_3.group(1)
    except AttributeError:
        logger.error(f"Could not find [begins]-[ends] date pattern for {event} {year}")
    else:
        # --- b. Convert to datetime date
        date = date.replace(".", "/").replace("-", "/")
        date_patterns = ["%d/%m/%Y", "%m/%d/%Y", "%Y/%m/%d", "%d %b %Y", "%B %d, %Y", "%b %d, %Y"]

        event_start_date = None
        for pattern in date_patterns:
            try:
                event_start_date = datetime.strptime(date, pattern).date()
            except ValueError:
                pass
            else:
                break
        if not event_start_date:
            logger.error(f"Could not find date pattern to parse start date for {event} {year}")
        else:
            return event_start_date


def generate_pdf_filename(event_dic, pdf_link, disc_code):
    """Scrapes an event page for its start date, based on known page layouts and tags, and returns it in datetime.

    Note: Uses specific BS tags to avoid picking up page update dates, 'last modified' dates etc by mistake. Three
    cases were observed when scraping ISU pages for dates: (1) base case - date range for the event is stored in the
    header (<tr> tags); (2) first special case (and new layout I think) schedule is stored in separate table below
    "main", with no date range provided in title (<td> tags); (3) second special case - dates are written in text
    (<p> tags)
    Keyword arguments:
    event_page -- BeautifulSoup parsed requests object
    year -- Year in which event took place (to double check dates)
    """
    # Handle getting segment identifiers for new pdf naming schema
    # (apparently in place for some A comps since 2017-18)
    raw_name = pdf_link.rpartition("/")[2]
    if re.search(r"data[0-9]{4}", raw_name):
        length = "S" if disc_code[2:] == "03" else "F"
        programme_type = "D" if disc == "Dance" else "P"
        filename = "_".join([event_dic["name"] + str(event_dic["year"]), disc,
                             length + programme_type]) + ".pdf"
    else:
        filename = event_dic["name"] + "_" + raw_name

    return event_dic["start_date"].strftime("%y%m%d") + "_" + filename



def download_pdf_protocols(event_page, event_identifier, per_discipline_settings=PER_DISCIPLINE_SETTINGS):
    """Downloads the pdf scoring protocols for the requested disciplines from the event page.

    Keyword arguments:
    event_page -- BeautifulSoup parsed requests object
    event_start_date -- datetime object denoting the start of the event, used in pdf filename
    per_discipline_settings -- Dictionary of bools structured as follows {"men": True, "ladies": True, "pairs": True,
    "dance": True}
    """
    all_sublinks = list(set([a.get("href") for a in event_page.find_all("a")]))
    for sublink in all_sublinks:
        logger.info(f"Examining {sublink} for {event_identifier['name']} {event_identifier['year']}")

        # Loop through each discipline, checking the setting in settings dic and loading the correct dic of codes
        for disc in per_discipline_settings:
            if per_discipline_settings[disc]:

                code_dic = DISC_CODES[disc.upper() + "_CODES"]
                for code in code_dic:
                    if re.search(code, str(sublink)):
                        logger.info(f"Code {code} matches {sublink}")

                        filename = generate_pdf_filename()
                        full_url = construct_absolute_url(event_identifier["url"], sublink)

                        # Get contents of sublink
                        try:
                            req = urllib.request.Request(full_url, headers=HEADERS)
                            res = urllib.request.urlopen(req)
                        except urllib.error.HTTPError as herr:
                            logger.error(f"HTTP {str(herr.code)} error opening {full_url}")
                        except urllib.error.URLError as uerr:
                            logger.error(f"URL error opening {full_url}: {uerr.reason}")
                        else:
                            pdf = open(s.WRITE_PATH + filename, "wb")
                            pdf.write(res.read())
                            pdf.close()


def return_first_google_result(start_year, end_year, terms_to_search):
    """Returns list containing url of first google hit for each term in each year of the range (start_year, end_year).

    Google search is necessary even for ISU comps as the website is not mappable and url patterns are inconsistent.
    Keyword arguments:
    start_year -- first year to search
    end_year -- last year to search
    terms_to_search -- list of competition names
    """
    google_link_list = []

    for search_event in terms_to_search:
        for search_year in range(start_year, end_year + 1):

            db_event_name = SEARCHTERM_TO_DBNAME[search_event]
            is_A_comp = True if db_event_name in ISU_A_COMPS else False
            
            domain = "isu+" if is_A_comp else ""
            cat = "senior+" if SENIOR_FLAG == 1 else "junior+"
            search = "https://www.google.co.uk/search?q=" + domain + cat + "results+" + search_event + "+" + str(search_year)
            logger.info(f"Running google search {search}")

            r = request_url(url=search, on_failure=None)
            html = BeautifulSoup(r.text, "html.parser")
            all_links = html.find_all("cite")

            # Set season
            season = "SB" + str(search_year) if db_event_name not in H2_EVENTS else str(search_year - 1)

            for link in all_links:
                isu_domain = True if is_A_comp and "isuresults" in link.text else False
                other_fed_domain = True if not is_A_comp and EXPECTED_DOMAIN[db_event_name] in link.text else False
                if isu_domain or other_fed_domain:
                    google_link_list.append((search_event, db_event_name, season, search_year, link.text))
                    break
    logger.info("Performed search on all provided terms and years")
    return google_link_list


def construct_absolute_url(subdomain_url, sublink):
    """Combines a url and a relative link found on the url's page and returns one absolute url.

    Two cases: (1) If sublink is relative to a subdomain (e.g. "xx.pdf"), strips "index" portion of the the subdomain
    url and appends sublink to it (e.g. "pokemon.io/woot/index.html" becomes "pokemon.io/woot/"). (2) If sublink has an
    address that is relative to the root domain (e.g. "/wahey/yeah/xx.pdf"), extract root domain only ("pokemon.io")
    from subdomain url and append to that
    subdomain_url -- The url of the page containing the sublinks, usually the competition homepage
    sublink -- A relative link found on that page
    """
    if sublink[:4] == "http":
        root = ""
    elif sublink[0] == "/":
        root = re.search(root_domain_pattern, subdomain_url).group(1)
    elif "index" in subdomain_url:
        root = re.sub(r"/index[A-Za-z\d]*\.htm[l]*$", "/", subdomain_url)
    else:
        root = subdomain_url

    temp = root + sublink
    constructed = "http://" + temp if temp[:4] != "http" else temp
    return constructed


def get_protocols(page_list, per_discipline_settings):
    """Scrapes each url provided for the urls of protocol pdfs that match the criteria provided.

    Keyword arguments:
    page_list -- list of urls from which to scrape pdfs
    men -- bool to represent whether function should fetch Men protocols
    ladies -- bool to represent whether function should fetch Ladies protocols
    pairs -- bool to represent whether function should fetch Pairs protocols
    dance -- bool to represent whether function should fetch Ice Dance protocols
    """
    flag = 0
    for (search_term, event, season, year, link) in page_list:

        # --- Check that the top google result is for the right hear (avoids "OWG 2016" search returning 2018 protocols)
        # First check url, if that fails check page text

        logger.info(f"Checking {event} {year} ({season}) at {link}")
        isu_name = DBNAME_TO_URLNAME[event]
        non_gpf_pattern = True if str(year) in link or (str(year)[-2:] in link and isu_name != "gpf") else False
        gpf_pattern = True if isu_name == "gpf" and str(year)[-2:] + str(year + 1)[-2:] in link else False

        r = request_url("http://" + link if "http" not in link else link)
        event_page = BeautifulSoup(r.content, "html5lib")

        test = True if isu_name in link and "jgp" not in link and (non_gpf_pattern or gpf_pattern) else False
        logger.info(f"Status of {link} for {event} {year} after URL test: {test}")
        if not test:
            text = " ".join([s for s in event_page.strings])
            idents = search_term.split("+") + [str(year)]
            test = True if all(i.lower() in text.lower() for i in idents) else False
        logger.info(f"Status of {link} for {event} {year} after page content test: {test}")
        if test:
            event_start_date = fetch_event_start_date(event_page, event, year)
            event_identifiers = {"name": event, "year": year, "start_date": event_start_date, "url": link}
            download_pdf_protocols(event_page, event_identifiers, per_discipline_settings)
            flag = 1
        else:
            logger.error(f"URL for {event} {year} ({link}) did not match expected naming patterns")

    if flag == 0:
        logger.error(f"Google results for {event} {year} did not return correct link")


if __name__ == '__main__':
    result_list = return_first_google_result(start_year=START_YEAR
                                             , end_year=END_YEAR
                                             , terms_to_search=GOOGLE_SEARCH_TERMS)
    get_protocols(page_list=result_list, per_discipline_settings=PER_DISCIPLINE_SETTINGS)