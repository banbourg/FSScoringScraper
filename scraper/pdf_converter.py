import glob
import requests
from bs4 import BeautifulSoup
from robobrowser import RoboBrowser
import string
import random
import sys
import hashlib
from time import sleep
import re


READ_PATH, WRITE_PATH, DATE, VER = "", "", "", ""
DATE_PATH, MAIL_API_KEY = "", ""
try:
    from settings import *
except ImportError as exc:
    sys.stderr.write("Error: failed to import module ({})".format(exc))
    sys.exit(1)

# files = sorted(glob.glob(READ_PATH + "*.csv"))
# for f in files:

# Generate a random email (temp mail API does not let you do this)
mail_browser = RoboBrowser(parser="lxml", history=True)
mail_browser.open("https://temp-mail.org/en/")
email = mail_browser.find("input").get("value")
name = email.partition("@")[0]
password = ''.join(random.SystemRandom().choice(string.ascii_uppercase + string.digits) for _ in range(8))
print(email, name, password)

# Fill in the form on pdftables to register
api_browser = RoboBrowser(parser="lxml")
api_browser.open("https://pdftables.com/join")
sign_up_form = api_browser.get_form(id="form")
sign_up_form["name"].value = name
sign_up_form["email"].value = email
sign_up_form["password"].value = password
try:
    api_browser.submit_form(sign_up_form, submit="become-member")
    check = api_browser.find("h1").get_text()
    assert check == "Check your email!"
    print("Signed up with email {}".format(email))
except AssertionError as a:
    sys.stderr.write("Error: Sign-up did not succeed ({})".format(a))
    sys.exit(1)

sleep(60)

# Fetch activation email
hash = hashlib.md5(email.encode("utf-8")).hexdigest()
print(hash)
endpoint = "https://privatix-temp-mail-v1.p.mashape.com/request/mail/id/" + hash + "/"

s = requests.Session()
req = s.get(endpoint, headers={
    "X-Mashape-Key": MAIL_API_KEY,
    "Accept": "application/json"
  })

try:
    assert isinstance(req.json(), list)
except AssertionError as a:
    sys.stderr.write("Error: Inbox requirest did not return list ({})".format(a))
    sys.exit(1)

try:
    link_search = re.search(r'(?:<a href=")(https:\/\/pdftables\.com\/activate\/[\w]+)(?:")', req.json()[0]["mail_html"])
    assert link_search
except AssertionError as a:
    sys.stderr.write("Error: could not find activation link in email ({})".format(a))
    sys.exit(1)

activation_link = link_search.group(1)
print(activation_link)

# Activate account
api_browser.open(activation_link)

# Log in
api_browser.open("https://pdftables.com/login")
log_in_form = api_browser.get_form(id="form")
log_in_form["email"].value = email
log_in_form["password"].value = password
try:
    api_browser.submit_form(log_in_form, submit="login")
except AssertionError as a:
    sys.stderr.write("Error: Could not log in ({})".format(a))
    sys.exit(1)

api_browser.open("https://pdftables.com/pdf-to-excel-api")
pdf_api_key = api_browser.find("code").get_text()
print(pdf_api_key)