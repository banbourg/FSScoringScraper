#!/bin/env python

import requests
from bs4 import BeautifulSoup
from datetime import datetime
import urllib.request, urllib.error, urllib.parse
import re
import csv
import pandas as pd

START_YEAR, END_YEAR = 2004, 2019
WRITE_PATH = ""
try:
    from settings import *
except ImportError:
    pass

# --- 1. Find links to all event pages since ISU website is not mappable

search_events = ["russia", "france", "america", "canada", "europeans", "wtt", "china", "nhk", "GPF", "continents",
                 "olympic", "world", "bompard"]
event_dic = {"nhk": "NHK", "france": "TDF", "canada": "SC", "russia": "COR", "america": "SA", "china": "COC",
             "GPF": "GPF", "world": "WC", "continents": "4CC", "olympic": "OWG", "wtt": "WTT", "europeans": "EC",
             "bompard": "TDF"}
isu_names = {"NHK": "gpjpn", "TDF": "gpfra", "SC": "gpcan", "COR": "gprus", "SA": "gpusa", "COC": "gpchn",
             "GPF": "gpf", "WC": "wc", "4CC": "fc", "OWG": "owg", "WTT": "wtt", "EC": "ec"}
h2_events = ["WC", "WTT", "4CC", "OWG", "EC"]
#
# google_link_list = []
# for search_event in search_events:
#     search_year = START_YEAR
#     while search_year < END_YEAR:
#
#         search = "https://www.google.co.uk/search?q=isu+results+" + search_event + "+" + str(search_year)
#         r = requests.get(search)
#         html = BeautifulSoup(r.text, "html.parser")
#         all_links = html.find_all("cite")
#
#         # SET SEASON
#         if event_dic[search_event] not in h2_events:
#             season = "SB" + str(search_year)
#         else:
#             season = "SB" + str(search_year - 1)
#
#         for link in all_links:
#             if "isuresults" in str(link):  # and "season" in str(link):
#                 google_link_list.append((event_dic[search_event], search_year, season, link.text))
#                 break
#         search_year += 1
#
# print(google_link_list)

# -- A CHEAT: My internet was being super slow so I pasted the output from step 1 below to avoid having to rerun it.
# google_link_list = [('COR', 2004, 'SB2004', 'www.isuresults.com/results/gprus04/index.htm'), ('COR', 2005, 'SB2005', 'www.isuresults.com/results/gprus05/'), ('COR', 2006, 'SB2006', 'www.isuresults.com/results/gprus06/'), ('COR', 2007, 'SB2007', 'www.isuresults.com/results/gprus07/'), ('COR', 2008, 'SB2008', 'www.isuresults.com/results/gprus08/index.htm'), ('COR', 2009, 'SB2009', 'www.isuresults.com/results/gprus09/'), ('COR', 2010, 'SB2010', 'www.isuresults.com/results/gprus2010/'), ('COR', 2011, 'SB2011', 'www.isuresults.com/results/gprus2011/'), ('COR', 2012, 'SB2012', 'www.isuresults.com/results/gprus2012/'), ('COR', 2013, 'SB2013', 'www.isuresults.com/results/gprus2013/'), ('COR', 2014, 'SB2014', 'www.isuresults.com/results/gprus2014/'), ('COR', 2015, 'SB2015', 'www.isuresults.com/results/season1516/gprus2015/'), ('COR', 2016, 'SB2016', 'www.isuresults.com/results/season1617/gprus2016/'), ('COR', 2017, 'SB2017', 'www.isuresults.com/results/season1718/gprus2017/'), ('COR', 2018, 'SB2018', 'www.isuresults.com/results/season1718/wc2018/'), ('TDF', 2005, 'SB2005', 'www.isuresults.com/results/gpfra05/'), ('TDF', 2006, 'SB2006', 'www.isuresults.com/results/gpfra06/'), ('TDF', 2007, 'SB2007', 'www.isuresults.com/results/wc2007/CAT004RS.HTM'), ('TDF', 2008, 'SB2008', 'www.isuresults.com/results/jgpfra2008/'), ('TDF', 2009, 'SB2009', 'www.isuresults.com/results/gpfra09/'), ('TDF', 2010, 'SB2010', 'www.isuresults.com/results/jgpfra2010/'), ('TDF', 2011, 'SB2011', 'www.isuresults.com/results/gpfra2011/'), ('TDF', 2012, 'SB2012', 'www.isuresults.com/results/jgpfra2012/'), ('TDF', 2013, 'SB2013', 'www.isuresults.com/results/gpfra2013/'), ('TDF', 2014, 'SB2014', 'www.isuresults.com/results/gpfra2014/'), ('TDF', 2015, 'SB2015', 'www.isuresults.com/results/season1617/gpfra2016/'), ('TDF', 2016, 'SB2016', 'www.isuresults.com/results/season1617/gpfra2016/'), ('TDF', 2017, 'SB2017', 'www.isuresults.com/results/season1718/gpfra2017/'), ('TDF', 2018, 'SB2018', 'www.isuresults.com/events/fsevent03111630.htm'), ('SA', 2004, 'SB2004', 'www.isuresults.com/results/gpusa04/index.htm'), ('SA', 2005, 'SB2005', 'www.isuresults.com/results/gpusa05/'), ('SA', 2006, 'SB2006', 'www.isuresults.com/results/gpusa06/'), ('SA', 2007, 'SB2007', 'www.isuresults.com/results/gpusa07/'), ('SA', 2008, 'SB2008', 'www.isuresults.com/results/gpusa08/index.htm'), ('SA', 2009, 'SB2009', 'www.isuresults.com/results/gpusa09/index.htm'), ('SA', 2010, 'SB2010', 'www.isuresults.com/results/gpusa2010/'), ('SA', 2011, 'SB2011', 'www.isuresults.com/results/gpusa2011/'), ('SA', 2012, 'SB2012', 'www.isuresults.com/results/gpusa2012/'), ('SA', 2013, 'SB2013', 'www.isuresults.com/results/gpusa2013/'), ('SA', 2014, 'SB2014', 'www.isuresults.com/results/gpusa2014/'), ('SA', 2015, 'SB2015', 'www.isuresults.com/results/season1516/gpusa2015/'), ('SA', 2016, 'SB2016', 'www.isuresults.com/results/season1617/gpusa2016/'), ('SA', 2017, 'SB2017', 'www.isuresults.com/results/season1718/gpusa2017/'), ('SA', 2018, 'SB2018', 'www.isuresults.com/events/fsevent03111613.htm'), ('SC', 2004, 'SB2004', 'www.isuresults.com/results/gpcan04/index.htm'), ('SC', 2005, 'SB2005', 'www.isuresults.com/results/gpcan05/'), ('SC', 2006, 'SB2006', 'www.isuresults.com/results/gpcan06/'), ('SC', 2007, 'SB2007', 'www.isuresults.com/results/gpcan07/'), ('SC', 2008, 'SB2008', 'www.isuresults.com/results/gpcan08/index.htm'), ('SC', 2009, 'SB2009', 'www.isuresults.com/results/gpcan09/index.htm'), ('SC', 2010, 'SB2010', 'www.isuresults.com/results/gpcan2010/'), ('SC', 2011, 'SB2011', 'www.isuresults.com/results/gpcan2011/'), ('SC', 2012, 'SB2012', 'www.isuresults.com/results/gpcan2012/'), ('SC', 2013, 'SB2013', 'www.isuresults.com/results/gpcan2013/'), ('SC', 2014, 'SB2014', 'www.isuresults.com/results/gpcan2014/'), ('SC', 2015, 'SB2015', 'www.isuresults.com/results/season1516/gpcan2015/'), ('SC', 2016, 'SB2016', 'www.isuresults.com/results/season1617/gpcan2016/'), ('SC', 2017, 'SB2017', 'www.isuresults.com/results/season1718/gpcan2017/'), ('SC', 2018, 'SB2018', 'www.isuresults.com/results/season1718/owg2018/TEC001RS.HTM'), ('EC', 2004, 'SB2003', 'www.isuresults.com/results/ec2004/index.htm'), ('EC', 2005, 'SB2004', 'www.isuresults.com/results/ec2005/'), ('EC', 2006, 'SB2005', 'www.isuresults.com/results/ec2006/'), ('EC', 2007, 'SB2006', 'www.isuresults.com/results/ec2007/'), ('EC', 2008, 'SB2007', 'www.isuresults.com/results/ec2008/'), ('EC', 2009, 'SB2008', 'www.isuresults.com/results/ec2009/'), ('EC', 2010, 'SB2009', 'www.isuresults.com/results/ec2010/'), ('EC', 2011, 'SB2010', 'www.isuresults.com/results/ec2011/'), ('EC', 2012, 'SB2011', 'www.isuresults.com/results/ec2012/'), ('EC', 2013, 'SB2012', 'www.isuresults.com/results/ec2013/'), ('EC', 2014, 'SB2013', 'www.isuresults.com/results/ec2014/'), ('EC', 2015, 'SB2014', 'www.isuresults.com/results/ec2015/'), ('EC', 2016, 'SB2015', 'www.isuresults.com/results/season1516/ec2016/'), ('EC', 2017, 'SB2016', 'www.isuresults.com/results/season1617/ec2017/'), ('EC', 2018, 'SB2017', 'www.isuresults.com/results/season1718/ec2018/'), ('WTT', 2004, 'SB2003', 'www.isuresults.com/results/ec2004/index.htm'), ('WTT', 2005, 'SB2004', 'www.isuresults.com/results/gpf0405/index.htm'), ('WTT', 2006, 'SB2005', 'www.isuresults.com/results/wc2006/'), ('WTT', 2007, 'SB2006', 'www.isuresults.com/results/wc2007/'), ('WTT', 2008, 'SB2007', 'www.isuresults.com/results/wc2008/'), ('WTT', 2009, 'SB2008', 'www.isuresults.com/results/wtt2009/'), ('WTT', 2010, 'SB2009', 'www.isuresults.com/results/wjc2010/index.htm'), ('WTT', 2011, 'SB2010', 'www.isuresults.com/results/wtt2012/'), ('WTT', 2012, 'SB2011', 'www.isuresults.com/results/wtt2012/'), ('WTT', 2013, 'SB2012', 'www.isuresults.com/results/wtt2013/'), ('WTT', 2014, 'SB2013', 'www.isuresults.com/results/wtt2015/'), ('WTT', 2015, 'SB2014', 'www.isuresults.com/results/wtt2015/'), ('WTT', 2016, 'SB2015', 'www.isuresults.com/results/season1516/wc2016/'), ('WTT', 2017, 'SB2016', 'www.isuresults.com/events/wtt2017/wtt-17_teams.htm'), ('WTT', 2018, 'SB2017', 'www.isuresults.com/results/season1718/wc2018/'), ('COC', 2004, 'SB2004', 'www.isuresults.com/results/gpchn04/index.htm'), ('COC', 2005, 'SB2005', 'www.isuresults.com/results/gpchn05/'), ('COC', 2006, 'SB2006', 'www.isuresults.com/results/gpchn06/'), ('COC', 2007, 'SB2007', 'www.isuresults.com/results/gpchn07/'), ('COC', 2008, 'SB2008', 'www.isuresults.com/results/gpchn08/index.htm'), ('COC', 2009, 'SB2009', 'www.isuresults.com/results/gpchn09/index.htm'), ('COC', 2010, 'SB2010', 'www.isuresults.com/results/gpchn2010/'), ('COC', 2011, 'SB2011', 'www.isuresults.com/results/gpchn2011/'), ('COC', 2012, 'SB2012', 'www.isuresults.com/results/gpchn2012/'), ('COC', 2013, 'SB2013', 'www.isuresults.com/results/gpchn2013/'), ('COC', 2014, 'SB2014', 'www.isuresults.com/results/gpchn2014/'), ('COC', 2015, 'SB2015', 'www.isuresults.com/results/season1516/gpchn2015/'), ('COC', 2016, 'SB2016', 'www.isuresults.com/results/season1617/gpchn2016/'), ('COC', 2017, 'SB2017', 'www.isuresults.com/results/season1718/gpchn2017/'), ('COC', 2018, 'SB2018', 'www.isuresults.com/.../gpchn2017_ColouredTimeSchedule.pdf'), ('NHK', 2004, 'SB2004', 'www.isuresults.com/results/gpjpn04/index.htm'), ('NHK', 2005, 'SB2005', 'www.isuresults.com/results/gpjpn05/'), ('NHK', 2006, 'SB2006', 'www.isuresults.com/results/gpjpn06/'), ('NHK', 2007, 'SB2007', 'www.isuresults.com/results/gpjpn07/'), ('NHK', 2008, 'SB2008', 'www.isuresults.com/results/gpjpn08/index.htm'), ('NHK', 2009, 'SB2009', 'www.isuresults.com/results/gpjpn09/index.htm'), ('NHK', 2010, 'SB2010', 'www.isuresults.com/results/gpjpn2010/'), ('NHK', 2011, 'SB2011', 'www.isuresults.com/results/gpjpn2011/'), ('NHK', 2012, 'SB2012', 'www.isuresults.com/results/gpjpn2012/'), ('NHK', 2013, 'SB2013', 'www.isuresults.com/results/gpjpn2013/'), ('NHK', 2014, 'SB2014', 'www.isuresults.com/results/gpjpn2014/'), ('NHK', 2015, 'SB2015', 'www.isuresults.com/results/season1516/gpjpn2015/'), ('NHK', 2016, 'SB2016', 'www.isuresults.com/results/season1617/gpjpn2016/'), ('NHK', 2017, 'SB2017', 'www.isuresults.com/results/season1718/gpjpn2017/'), ('NHK', 2018, 'SB2018', 'www.isuresults.com/.../gpjpn2017_ColouredTimeSchedule.pdf'), ('GPF', 2004, 'SB2004', 'www.isuresults.com/results/gpf0405/index.htm'), ('GPF', 2005, 'SB2005', 'www.isuresults.com/results/gpf0506/'), ('GPF', 2006, 'SB2006', 'www.isuresults.com/results/gpf0607/'), ('GPF', 2007, 'SB2007', 'www.isuresults.com/results/gpf0708/'), ('GPF', 2008, 'SB2008', 'www.isuresults.com/results/gpf0809/index.htm'), ('GPF', 2009, 'SB2009', 'www.isuresults.com/results/gpf0910/index.htm'), ('GPF', 2010, 'SB2010', 'www.isuresults.com/results/gpf1011/'), ('GPF', 2011, 'SB2011', 'www.isuresults.com/results/gpf1112/'), ('GPF', 2012, 'SB2012', 'www.isuresults.com/results/gpf1213/'), ('GPF', 2013, 'SB2013', 'www.isuresults.com/results/gpf1314/'), ('GPF', 2014, 'SB2014', 'www.isuresults.com/results/gpf1415/'), ('GPF', 2015, 'SB2015', 'www.isuresults.com/results/season1516/gpf1516/'), ('GPF', 2016, 'SB2016', 'www.isuresults.com/results/season1617/gpf1617/'), ('GPF', 2017, 'SB2017', 'www.isuresults.com/results/season1718/gpf1718/'), ('GPF', 2018, 'SB2018', 'www.isuresults.com/results/season1718/gpf1718/'), ('4CC', 2004, 'SB2003', 'www.isuresults.com/results/fc2004/index.htm'), ('4CC', 2005, 'SB2004', 'www.isuresults.com/results/fc2005/'), ('4CC', 2006, 'SB2005', 'www.isuresults.com/results/fc2006/'), ('4CC', 2007, 'SB2006', 'www.isuresults.com/results/fc2007/'), ('4CC', 2008, 'SB2007', 'www.isuresults.com/results/fc2008/'), ('4CC', 2009, 'SB2008', 'www.isuresults.com/results/fc2009/'), ('4CC', 2010, 'SB2009', 'www.isuresults.com/results/fc2010/index.htm'), ('4CC', 2011, 'SB2010', 'www.isuresults.com/results/fc2011/'), ('4CC', 2012, 'SB2011', 'www.isuresults.com/results/fc2012/'), ('4CC', 2013, 'SB2012', 'www.isuresults.com/results/fc2013/'), ('4CC', 2014, 'SB2013', 'www.isuresults.com/results/fc2014/'), ('4CC', 2015, 'SB2014', 'www.isuresults.com/results/fc2015/'), ('4CC', 2016, 'SB2015', 'www.isuresults.com/results/season1516/fc2016/'), ('4CC', 2017, 'SB2016', 'www.isuresults.com/results/season1617/fc2017/'), ('4CC', 2018, 'SB2017', 'www.isuresults.com/results/season1718/fc2018/'), ('OWG', 2004, 'SB2003', 'www.isuresults.com/bios/isufs_cr_00000595.htm'), ('OWG', 2005, 'SB2004', 'www.isuresults.com/bios/isufs_cr_00005733.htm'), ('OWG', 2006, 'SB2005', 'www.isuresults.com/results/owg2006/'), ('OWG', 2007, 'SB2006', 'www.isuresults.com/results/EYOF2007/'), ('OWG', 2008, 'SB2007', 'www.isuresults.com/results/owg2010/'), ('OWG', 2009, 'SB2008', 'www.isuresults.com/results/owg2010/'), ('OWG', 2010, 'SB2009', 'www.isuresults.com/results/owg2010/'), ('OWG', 2011, 'SB2010', 'www.isuresults.com/results/jgpaus2011/'), ('OWG', 2012, 'SB2011', 'www.isuresults.com/results/yog2012/'), ('OWG', 2013, 'SB2012', 'www.isuresults.com/results/owg2014/'), ('OWG', 2014, 'SB2013', 'www.isuresults.com/results/owg2014/'), ('OWG', 2015, 'SB2014', 'www.isuresults.com/results/owg2014/'), ('OWG', 2016, 'SB2015', 'www.isuresults.com/results/season1718/owg2018/SEG009.HTM'), ('OWG', 2017, 'SB2016', 'www.isuresults.com/results/season1718/owg2018/'), ('OWG', 2018, 'SB2017', 'www.isuresults.com/results/season1718/owg2018/'), ('WC', 2004, 'SB2003', 'www.isuresults.com/results/wc2004/index.htm'), ('WC', 2005, 'SB2004', 'www.isuresults.com/results/wc2005/'), ('WC', 2006, 'SB2005', 'www.isuresults.com/results/wc2006/'), ('WC', 2007, 'SB2006', 'www.isuresults.com/results/wc2007/'), ('WC', 2008, 'SB2007', 'www.isuresults.com/results/wc2008/'), ('WC', 2009, 'SB2008', 'www.isuresults.com/results/wc2009/'), ('WC', 2010, 'SB2009', 'www.isuresults.com/results/wc2010/'), ('WC', 2011, 'SB2010', 'www.isuresults.com/results/wc2011/'), ('WC', 2012, 'SB2011', 'www.isuresults.com/results/wc2012/'), ('WC', 2013, 'SB2012', 'www.isuresults.com/results/wc2013/'), ('WC', 2014, 'SB2013', 'www.isuresults.com/results/wc2014/'), ('WC', 2015, 'SB2014', 'www.isuresults.com/results/wc2015/'), ('WC', 2016, 'SB2015', 'www.isuresults.com/results/season1516/wc2016/'), ('WC', 2017, 'SB2016', 'www.isuresults.com/results/season1617/wc2017/'), ('WC', 2018, 'SB2017', 'www.isuresults.com/results/season1718/wc2018/'), ('TDF', 2004, 'SB2004', 'www.isuresults.com/results/gpfra04/index.htm'), ('TDF', 2006, 'SB2006', 'www.isuresults.com/results/gpfra06/'), ('TDF', 2007, 'SB2007', 'www.isuresults.com/results/gpfra07/'), ('TDF', 2008, 'SB2008', 'www.isuresults.com/results/gpfra08/index.htm'), ('TDF', 2009, 'SB2009', 'www.isuresults.com/results/gpfra09/'), ('TDF', 2010, 'SB2010', 'www.isuresults.com/results/gpfra2010/'), ('TDF', 2011, 'SB2011', 'www.isuresults.com/results/gpfra2011/'), ('TDF', 2012, 'SB2012', 'www.isuresults.com/results/gpfra2012/'), ('TDF', 2013, 'SB2013', 'www.isuresults.com/results/gpfra2013/'), ('TDF', 2014, 'SB2014', 'www.isuresults.com/results/gpfra2014/'), ('TDF', 2015, 'SB2015', 'www.isuresults.com/results/season1516/gpfra2015/'), ('TDF', 2016, 'SB2016', 'www.isuresults.com/results/season1617/gpfra2016/'), ('TDF', 2017, 'SB2017', 'www.isuresults.com/results/season1718/gpfra2017/'), ('TDF', 2018, 'SB2018', 'www.isuresults.com/results/season1718/fc2018/')]

# --- 2. On each page, locate the scoring pdfs and download them and get date info
pdf_link_list = []
disciplines = {"Danc": "Dance", "Pairs": "Pairs", "0403": "Dance", "0405": "Dance", "0303": "Pairs", "0305": "Pairs", 
               "Ladies": "Ladies", "Men": "Men", "0103": "Men", "0105": "Men", "0203": "Ladies", "0205": "Ladies"}
# -- TO DO: if isu keeps using 4 digit codes, parse disc and segment directly from them

date_list = []
span_regex = re.compile(r'\d{2}[\/\-.]\d{2}[\/\-.]\d{4}.+\d{2}[\/\-.]\d{2}[\/\-.]\d{4}')
for (event, year, season, link) in google_link_list:

    print(event, year, season, link)

    response = requests.get("http://"+link, stream=True)
    event_page = BeautifulSoup(response.text, "html.parser")
    isu_name = isu_names[event]

    if event in h2_events:
        right_year = str(int(season[-4:]) + 1)
    else:
        right_year = season[-4:]

    print(event, right_year)

    # Check that the top google result is for the right hear (avoids "OWG 2016" search returning pyeongchang)
    # Note: Using the google search method bc url construction is not uniform over time.
    if isu_name in link and "jgp" not in link and (right_year in link or (str(year)[-2:] in link and isu_name != "gpf")
                                                   or (isu_name == "gpf" and str(year)[-2:]+str(year+1)[-2:] in link)):

        # --- a. Fetch date of 1st day of comp (to allow ordering within season)
        # NOTE: Using specific BS tags to avoid picking up page update dates, modified dates etc by mistake.
        # Basic case - date range for event is in header
        captions = [cap3.get_text() for cap3 in event_page.find_all("tr", "caption3")]
        if captions:
            date = captions[0].partition(" - ")[0]
        # First special case (and new layout I think) schedule in separate table below main, no date range in title
        elif [cap3.get_text() for cap3 in event_page.find_all("td") if str(year) in cap3.get_text()]:
            captions = [cap3.get_text() for cap3 in event_page.find_all("td") if str(year) in cap3.get_text()]
            print(captions)
            date = captions[0]
        # Second special case - dates just written in text
        else:
            captions = [cap3.get_text() for cap3 in event_page.find_all("p") if re.search(span_regex, cap3.get_text())
                        is not None]
            try:
                date = re.search(r'\d{2}[\/\-.]\d{2}[\/\-.]\d{4}', captions[0]).group(0)
            except AttributeError:
                print("DATE RANGE NOT FOUND")


        # Convert to datetime date
        date = date.replace(".", "/").replace("-", "/")
        date_patterns = ["%d/%m/%Y", "%m/%d/%Y", "%Y/%m/%d", "%d %b %Y"]
        for pattern in date_patterns:
            try:
                event_start_date = datetime.strptime(date, pattern).date()
            except ValueError:
                pass

        print(event_start_date.year, right_year)

        if int(event_start_date.year) == int(right_year):

            date_list.append((event, season, event_start_date)) # -- only useful for creating date list (one-off)

            # --- b. Fetch and download pdfs
            for sublink in event_page.find_all("a"):
                url = sublink.get("href")
                for discipline in disciplines:
                    if discipline in str(url):
                        if "index.htm" in link:
                            clean_link = link.replace("index.htm", "")
                        else:
                            clean_link = link
                        full_url = "http://" + clean_link + url
                        req = urllib.request.Request(full_url)

                        try:
                            res = urllib.request.urlopen(req)
                        except urllib.request.HTTPError as e:
                            print("HTTPError = ", str(e.code), full_url)
                        except urllib.request.URLError as e:
                            print("URLError = ", str(e.reason), full_url)
                        except Exception:
                            import traceback

                            print("generic exception: ", traceback.format_exc(), full_url)

                        if re.search(r"data[0-9]+", url) is not None:
                            length = "S" if discipline[2:] == "03" else "F"
                            seg_type = "P" if discipline[:2] == "03" else "D"
                            segment = length + seg_type
                            name = "_".join([event, str(right_year), disciplines[discipline], segment])
                        else:
                            name = url
                        pdf = open(WRITE_PATH + event_start_date.strftime("%y%m%d") + "_" + name, "wb")
                        pdf.write(res.read())
                        pdf.close()
                        pdf_link_list.append(full_url)
                    else:
                        print("No discipline found in url: ", str(url))
        else:
            print("WRONG YEAR DETECTED")
    else:
        print("Top google result for ", event, year, " returned an incorrect link")

print(pdf_link_list)

# # Wrote this to create standalone list of dates to join to existing tables. Not needed in normal operation.
# dates_df = pd.DataFrame.from_records(date_list, index=None, columns=["event", "season", "event_start_date"])
# dates_df.drop_duplicates(keep='first', inplace=True)
# dates_df.to_csv(WRITE_PATH + "dates.csv", mode="w", encoding="utf-8", header=True)