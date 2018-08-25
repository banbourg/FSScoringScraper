#!/bin/env python

import requests
from robobrowser import RoboBrowser
import random
import hashlib
import re

import sys
from time import sleep
import string
import logging

logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)-5s - %(message)s",
                    level=logging.INFO,
                    datefmt='%Y-%m-%d %H:%M:%S')

logger = logging.getLogger(__name__)

try:
    import settings
except ImportError as exc:
    logger.error(f"Failed to import settings module ({exc})")
    sys.exit(1)

# ----------------    IMPORTANT NOTES
# CURRENTLY SET UP FOR YOU TO HAVE YOUR TEMP MAIL API KEY IN SETTINGS, SORRY. Also this has no error handling yet rip,
# it just exits. RUN sleep(60) BETWEEN CREATING THE ACCOUNT AND FETCHING THE ACTIVATION EMAIL
# CURRENTLY USING TWO SEPARATE BROWSERS TO KEEP THE RANDOMLY GENERATED EMAIL "ALIVE"


def generate_random_email(mail_browser):
    # Generate a random email (temp mail API does not let you do this)
    mail_browser.open("https://temp-mail.org/en/")
    email = mail_browser.find("input").get("value")
    name = email.partition("@")[0]
    password = ''.join(random.SystemRandom().choice(string.ascii_uppercase + string.digits) for _ in range(8))
    logger.info(f"Generated temp-mail details: {email}, {name}, {password}")
    return email, name, password


def create_pdftables_account(pdf_browser, email, name, password):
    # Fill in the form on pdftables to register
    pdf_browser.open("https://pdftables.com/join")
    sign_up_form = pdf_browser.get_form(id="form")
    sign_up_form["name"].value = name
    sign_up_form["email"].value = email
    sign_up_form["password"].value = password
    try:
        pdf_browser.submit_form(sign_up_form, submit="become-member")
        check = pdf_browser.find("h1").get_text()
        assert check == "Check your email!"
    except AssertionError as a:
        logger.error("Sign-up to pdftables did not succeed")
        sys.exit(1)
    logger.info(f"Signed up to pdftables with email {email}")
    return


def fetch_activation_email(email):
    # Fetch activation email
    hash = hashlib.md5(email.encode("utf-8")).hexdigest()
    endpoint = "https://privatix-temp-mail-v1.p.mashape.com/request/mail/id/" + hash + "/"

    s = requests.Session()
    req = s.get(endpoint, headers={
        "X-Mashape-Key": settings.MAIL_API_KEY,
        "Accept": "application/json"
      })

    try:
        assert isinstance(req.json(), list)
    except AssertionError as a:
        logger.error("Inbox request failed")
        sys.exit(1)
    logger.info("Found activation email")

    try:
        link_search = re.search(r'(?:<a href=")(https://pdftables\.com/activate/[\w]+)(?:")', req.json()[0]["mail_html"])
        assert link_search
    except AssertionError as a:
        logger.error("Could not find activation link in email")
        sys.exit(1)
    logger.info("Found activation link")

    activation_link = link_search.group(1)
    return activation_link


def log_into_pdftables(pdf_browser, email, password):
    # Log in
    pdf_browser.open("https://pdftables.com/login")
    login_form = pdf_browser.get_form(id="form")
    login_form["email"].value = email
    login_form["password"].value = password
    try:
        pdf_browser.submit_form(login_form, submit="login")
    except AssertionError as aerr:
        logger.error(f"Could not log in to pdf tables: {aerr})")
        sys.exit(1)
    logger.info("Logged into pdftables")
    return



def get_api_key(pdf_browser):
    pdf_browser.open("https://pdftables.com/pdf-to-excel-api")
    pdf_api_key = pdf_browser.find("code").get_text()
    logger.info(f"Got pdftables api key {pdf_api_key}")
    return pdf_api_key


def main():
    pdf_browser = RoboBrowser(parser="lxml")
    mail_browser = RoboBrowser(parser="lxml")
    email, name, password = generate_random_email(mail_browser)
    create_pdftables_account(pdf_browser, email, name, password)
    sleep(60)
    activation_link = fetch_activation_email(email)
    pdf_browser.open(activation_link)
    log_into_pdftables(pdf_browser, email, password)
    pdf_api_key = get_api_key(pdf_browser)


if __name__ == '__main__':
    main()