import glob
import requests
from bs4 import BeautifulSoup
from mechanize import ParseResponse, urlopen, urljoin

READ_PATH, WRITE_PATH, DATE, VER = "", "", "", ""
DATE_PATH = ""
try:
    from settings import *
except ImportError:
    pass

# files = sorted(glob.glob(READ_PATH + "*.csv"))
# for f in files:

# Generate a random email (temp mail API does not let you do this)
r = requests.get("https://temp-mail.org/en/")
html = BeautifulSoup(r.text, "html.parser")
email = html.find("input").get("value")
print(email)


