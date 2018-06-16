#!/bin/env python

import requests
from bs4 import BeautifulSoup
import os
import re
import pandas as pd
import itertools


# TO DOs: (1) Fix encoding issue so we don't have to manually replace non ASCII chars (some pages are in utf-8, others
# in cp1252, can't get an overall solution to work (2) Automatically check for judges who are variously listed as
# repping one country and the ISU, and find and replace the ISU with the country -- are there special cases where the
# country itself changes?

def main():
    # STEP 1: Find links to all event pages since ISU website is not mappable. Judges stopped being anonymous in 2016-17
    start_year = 2016
    search_events = ['canada', 'GPF', 'nhk', 'china', 'russia', 'france', 'america', 'continents', 'olympic',
                     'world', 'wtt']
    event_dic = {'nhk': 'NHK', 'france': 'TDF', 'canada': 'SC', 'russia': 'COR', 'america': 'SA', 'china': 'COC',
                 'GPF': 'GPF', 'world': 'WC', 'continents': '4CC', 'olympic': 'OWG', 'wtt': 'WTT'}
    isu_names = {'NHK': 'gpjpn', 'TDF': 'gpfra', 'SC': 'gpcan', 'COR': 'gprus', 'SA': 'gpusa', 'COC': 'gpchn',
                 'GPF': 'gpf', 'WC': 'wc', '4CC': 'fc', 'OWG': 'owg', 'WTT': 'wtt'}

    google_link_list = []

    disciplines = ['Junior Men', 'Junior Ladies', 'Team Men', 'Team Ladies', 'Men', 'Ladies', 'Men Single Skating',
                   'Ladies Single Skating']
    segments = ['- Short Program', '- Free Skating']
    combinations = list(itertools.product(*[disciplines, segments]))
    search_captions = [' '.join(combination) for combination in combinations]

    for search_event in search_events:
        for search_year in range(start_year, 2019):

            # Don't bother searching for events in second half of 2015-16 as judges were still anonymous
            flag = 1 if (search_event in ['world', 'continents', 'olympic', 'wtt'] and search_year == 2016) else 0

            if flag == 0:
                if search_event != 'wtt':
                    search = 'https://www.google.co.uk/search?q=isu+results+' + search_event + '+' + str(search_year)
                else:
                    search = 'https://www.google.co.uk/search?q=jsf+results+index+' + search_event + '+' + \
                             str(search_year)
                print search
                r = requests.get(search)
                html = BeautifulSoup(r.text, 'html.parser')
                all_links = html.find_all('cite')

                # SET SEASON
                season_begins = search_year if search_event not in search_events[-4:] else search_year - 1
                season = 'SB' + str(season_begins)

                for link in all_links:
                    if 'pdf' not in str(link):
                        if all(x in str(link) for x in ['isuresults', 'season']) or 'jsfresults' in str(link):

                            print 'passed'
                            google_link_list.append((event_dic[search_event], search_year, season, link.text))
                            break
    print google_link_list

    # STEP 2: On each page, locate the 4 (or 8 at OWG) links to the singles judging panels
    all_judges = []

    for (event, year, season, link) in google_link_list:
        # Clean link
        if 'http' not in link:
            link = 'http://' + link
        print link

        response = requests.get(link, stream=True)
        event_page = BeautifulSoup(response.text, 'html.parser')
        isu_name = isu_names[event]
        print 'got response and name'

        # Check that the top google result is for the right year (avoids 'OWG 2016' search returning pyeongchang)
        # Note: Using the google search method bc url construction is not uniform over time.
        if isu_name in link and (str(year) in link or ('gpf'+str(year)[-2:] in link)):
            print 'passed url check:', event, year, link

            event_judges = []
            for a in event_page.find_all('a'):
                event_domain = link.replace('index.htm', '')
                segment_page = a.get('href')

                if ('.htm' in segment_page or '.HTM' in segment_page) and 'index' not in segment_page:
                    url_to_test = event_domain + segment_page

                    page_resp = requests.get(url_to_test)
                    html = BeautifulSoup(page_resp.text, 'html.parser')

                    # Check we're on a judging panel page
                    caption2 = [cap2.get_text().replace('\r', '').replace('\n', '') for cap2
                                in html.find_all('tr', 'caption2')]
                    caption3 = [cap3.get_text().replace('\r', '').replace('\n', '')for cap3
                                in html.find_all('tr', 'caption3')]
                    words = [p.get_text().replace('\r', '').replace('\n', '')for p in html.find_all('p', 'Font14')]

                    if caption2:
                        title = caption2[0]
                    elif words:
                        title = words[0]
                    else:
                        title = []

                    if caption3:
                        subtitle = caption3[0]
                    elif len(words) > 1:
                        subtitle = words[1]
                    else:
                        subtitle = []

                    if title in search_captions and 'Panel of' in subtitle:
                        print event, title, subtitle

                        # SET SEGMENT, SUB EVENT, DISCIPLINE AND CATEGORY
                        segment = 'SP' if 'Short' in title else 'FS'
                        discipline = 'Men' if 'Men' in title else 'Ladies'
                        category = 'Jr' if 'Junior' in title else 'Sr'
                        sub_event = 'Team' if 'Team' in title else ''

                        # EXTRACT DATA AND CLEAN IT: First, names and roles
                        raw_roles = [re.sub(r'[\n]+', '', td.get_text()) for td in html.find_all('td')]
                        raw_roles = filter(None, [entry.replace(u'\xa0', u' ').replace(u'\xd6', u'OE').
                                           replace(u'\xf6',u'oe').strip() for entry in raw_roles])
                        print 'raw roles: ', raw_roles

                        segment_judges = []

                        # Find increment (sometimes country appears twice)
                        indices = [raw_roles.index(r) for r in [u'Referee', u'Technical Controller',
                                                                u'Technical Controller']]
                        first_entry = min(indices)
                        if raw_roles[first_entry+2] == raw_roles[first_entry+3]:
                            incr = 4
                        else:
                            incr = 3

                        last = 16 * incr

                        for i in range(first_entry, last, incr):

                            # Align 'judge' notation with the one used in scoring tables
                            if 'Judge' in raw_roles[i] or 'No.' in raw_roles[i]:
                                role = 'J' + raw_roles[i][-1]
                            else:
                                role = raw_roles[i]

                            # Clean name for Mr., Ms.
                            temp_name = raw_roles[i+1].split(' ', 1)[1] if '.' in raw_roles[i+1] else raw_roles[i+1]

                            # Clean for name order
                            if temp_name[1].isupper():
                                exploded_name = temp_name.split(' ')
                                first_name_list, last_name_list = [], []
                                for part in exploded_name:
                                    if part[1].isupper():
                                        last_name_list.append(part)
                                    else:
                                        first_name_list.append(part)
                                first_name = ' '.join(first_name_list)
                                last_name = ' '.join(last_name_list)
                                name = first_name + ' ' + last_name
                            else:
                                name = unicode(temp_name)

                            # Construct and append tuple
                            segment_judges.append((season, event, sub_event, discipline, category, segment,
                                                   role, name, raw_roles[i+2]))

                        print 'segment judges: ', segment_judges
                        event_judges.extend(segment_judges)

            all_judges.extend(event_judges)

        else:
            print 'link failed url check:', event, year, link

    labels = ['season', 'event', 'sub_event', 'discipline', 'category', 'segment', 'role', 'name', 'country']

    df = pd.DataFrame.from_records(all_judges, columns=labels)

    # pairs_df = df.drop_duplicates(subset=['name', 'country'])

    path = os.path.expanduser('~/Desktop/bias/output/')
    df.to_csv(path + 'judges_1617to1718.csv', mode='a', header=True)


main()
