import re
import sys
import logging

from datetime import datetime

logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)-5s - %(message)s",
                    level=logging.INFO, datefmt='%Y-%m-%d %H:%M:%S')

logger = logging.getLogger(__name__)

date_pattern_1 = re.compile(r"(\d{1,2}[\/\-.]\d{1,2}[\/\-.]\d{4}).{1,6}\d{1,2}[\/\-.]\d{1,2}[\/\-.]\d{2,4}")

date_pattern_2 = re.compile(r"(\d{2,4}[/\-.]\d{2}[/\-.]\d{1,2}).{1,6}\d{2,4}[/\-.]\d{2}[/\-.]\d{1,2}")

date_pattern_3 = re.compile(r"((Jan(uary)?|Feb(ruary)?|Mar(ch)?|Apr(il)?|May|Jun(e)?|Jul(y)?|Aug(ust)?|"
                            r"Sep(tember)?|Oct(ober)?|Nov(ember)?|Dec(ember)?)\s+\d{1,2},\s+\d{4}).{1,6}"
                            r"(Jan(uary)?|Feb(ruary)?|Mar(ch)?|Apr(il)?|May|Jun(e)?|Jul(y)?|Aug(ust)?|"
                            r"Sep(tember)?|Oct(ober)?|Nov(ember)?|Dec(ember)?)\s+\d{1,2},\s+\d{4}")

date_pattern_4 = re.compile(r"((Jan(uary)?|Feb(ruary)?|Mar(ch)?|Apr(il)?|May|Jun(e)?|Jul(y)?|Aug(ust)?|Sep(tember)?|"
                            r"Oct(ober)?|Nov(ember)?|Dec(ember)?)\s+\d{1,2}).{1,4}\d{1,2}.{1,4}(\d{2,4})")

date_pattern_5 = re.compile(r"(\d{1,2}[/\-.](Jan(uary)?|Feb(ruary)?|Mar(ch)?|Apr(il)?|May|Jun(e)?|Jul(y)?|Aug(ust)?|"
                            r"Sep(tember)?|Oct(ober)?|Nov(ember)?|Dec(ember)?)[/\-.]\d{2,4}).{1,6}"
                            r"\d{1,2}[/\-.](Jan(uary)?|Feb(ruary)?|Mar(ch)?|Apr(il)?|May|Jun(e)?|Jul(y)?|Aug(ust)?|"
                            r"Sep(tember)?|Oct(ober)?|Nov(ember)?|Dec(ember)?)[/\-.]\d{2,4}")

date_pattern_6 = re.compile(r"(\d{1,2}[\/\-.] {0,1}\d{2}[\/\-.] {0,1}\d{4}) ")


range_separator = re.compile(r"(?i)(^\D*)(?:\d|[a-z])")

delimiter_pattern = re.compile(r"(?i)[\da-z] *([/\-.]) *[\da-z]")

class EventDate:
    def __init__(self, year, h2_event_flag, text_to_parse=None, date=None):
        self.expected_year = year
        self.match_string_start = None
        self.match_string_end = None
        self.start_date = self._set_start_date(date, text_to_parse, h2_event_flag)
        logger.info(f"Constructed EventDate object with start date {self.start_date}")

    def _set_start_date(self, date, text_to_parse, h2_event_flag):
        if date:
            return date
        elif text_to_parse:
            return self.parse_start_date(text_to_parse, h2_event_flag)
        else:
            raise ValueError("Please instantiate StartDate with either a date or a string for me to parse a date from")

    def parse_start_date(self, text_to_parse, h2_event_flag):
        if not text_to_parse:
            raise ValueError("Please call parse_start_date with with some text so I can parse the date")
        date_searches = [_s for _s in [re.search(date_pattern_1, text_to_parse),
                                       re.search(date_pattern_2, text_to_parse),
                                       re.search(date_pattern_3, text_to_parse),
                                       re.search(date_pattern_4, text_to_parse),
                                       re.search(date_pattern_5, text_to_parse),
                                       re.search(date_pattern_6, text_to_parse)] if _s is not None]
        if not date_searches:
            raise ValueError(f"Could not find date matching expected patterns in {text_to_parse[:200]}")

        # Get start date string
        logger.debug(f"Date pattern search results are {date_searches}")
        self.match_string_start = date_searches[0].group(1) if date_searches[0].group(1) is not None else date_searches[0].group(2)
        logger.debug(f"Setting self.match_string_start to {self.match_string_start}")

        # Get end date string
        self.match_string_end = self._extract_end_date(date_searches[0])

        # Clean up formats
        date_range = self._homogenise_formats()

        logger.debug(f"Passing {date_range} to handler for unclear formats")
        test = self._handle_unclear_format(date_range, h2_event_flag)
        if test:
            logger.debug(f"Inferred start date {test}")
            return test

        other_patterns = ["%Y/%m/%d", "%d/%b/%Y", "%B/%d/%Y", "%b/%d/%Y", "%d/%b/%y"]
        for pattern in other_patterns:
            try:
                date = datetime.strptime(date_range[0], pattern).date()
                logger.debug(f"No inference needed, found clear start date in {date_range[0]}")
                return date
            except ValueError:
                pass
        logger.error(f"Could not find date pattern to parse start date for {date_range}")
        sys.exit(1)

    def _handle_unclear_format(self, date_range, h2_event_flag):
        start, end = date_range[0], date_range[1]

        base_patterns = ["%m/%d/%", "%d/%m/%"]
        yr_format = "Y" if start.endswith(str(self.expected_year)) else "y"
        results = []
        for p in [p + yr_format for p in base_patterns]:
            try:
                results.append(datetime.strptime(start, p).date())
            except ValueError:
                pass

        if len(results) == 1:
            return results[0]
        elif len(results) == 0:
            return None

        exploded_start = [int(s) for s in start.split("/")]

        # Inferring when no end date is available -- rough proxy
        if end is None and not h2_event_flag:
            if abs(exploded_start[0] -11) < abs(exploded_start[1] -11):
                return datetime.strptime(start, "%m/%d/%" + yr_format).date()
            else:
                return datetime.strptime(start, "%m/%d/%" + yr_format).date()
        elif end is None:
            if abs(exploded_start[0] - 2) < abs(exploded_start[1] - 2):
                return datetime.strptime(start, "%m/%d/%" + yr_format).date()
            else:
                return datetime.strptime(start, "%m/%d/%" + yr_format).date()

        exploded_end = [int(s) for s in end.split("/")]

        delta_0 = exploded_end[0] - exploded_start[0]
        delta_1 = exploded_end[1] - exploded_start[1]

        pattern = "%m/%d/%" if delta_0 < delta_1 else "%d/%m/%"
        return datetime.strptime(start, pattern + yr_format).date()

    def _test_missing_year(self, date_string):
        if date_string is None:
            return False

        years = range(max(2004, self.expected_year - 10), min(datetime.today().year + 1, self.expected_year + 10))
        logger.debug(f"Testing {date_string} for missing year")
        for y in years:
            if str(y) in date_string or (date_string.endswith(str(y)[2:])):
                return False
        return True

    def _add_back_year(self, date_string):
        if re.match(r"[A-Z]", date_string):
            return ", " + str(self.expected_year)
        else:
            return "/" + str(self.expected_year)

    def _homogenise_formats(self):
        temp_start_date = re.sub(r", |[.\- ,] *|/ ", "/", self.match_string_start)
        if self.match_string_end:
            temp_end_date = re.sub(r", |[.\- ,] *|/ ", "/", self.match_string_end)
        else:
            temp_end_date = None

        # Add year back if missing
        dates = [d + self._add_back_year(d) if self._test_missing_year(d) else d
                 for d in [temp_start_date, temp_end_date]]
        return dates

    def _extract_end_date(self, date_match_object):
        raw_end_date = re.sub(self.match_string_start, "", date_match_object.group(0))
        logger.debug(f"Raw end date is {raw_end_date}")
        head_to_remove = re.match(range_separator, raw_end_date)
        if head_to_remove:
            return re.sub(head_to_remove.group(1), "", raw_end_date)
        else:
            return None