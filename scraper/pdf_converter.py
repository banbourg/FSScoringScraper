#!/bin/env python

import requests
from robobrowser import RoboBrowser
import random
import hashlib
import re
import pdftables_api
import PyPDF2
from tenacity import retry, wait_exponential, wait_fixed, retry_if_result

import os
from pathlib import Path
import sys
from time import sleep
import string
import logging
import glob

logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)-5s - %(message)s",
                    level=logging.INFO,
                    datefmt='%Y-%m-%d %H:%M:%S')

logger = logging.getLogger(__name__)

try:
    import settings
except ImportError as exc:
    logger.error(f"Failed to import settings module ({exc})")
    sys.exit(1)


def generate_random_email(mail_browser):
    # Generate a random email (temp mail API does not let you do this)
    mail_browser.open("https://temp-mail.org/en/")
    email = mail_browser.find("input").get("value")
    name = email.partition("@")[0]
    password = ''.join(random.SystemRandom().choice(string.ascii_uppercase + string.digits) for _ in range(8))
    logger.info(f"Generated temp-mail details: {email}, {name}, {password}")
    return email, name, password


def is_lockout(browser_text):
    if "too many requests" in browser_text.lower():
        logger.info(f"Currently locked out")
        return True
    elif "check your email" in browser_text.lower():
        logger.info(f"Got through")
        return False
    else:
        logger.error(f"Found unexpected text in browser response {browser_text}")
        sys.exit(1)


#@retry(wait=wait_exponential(multiplier=1, min=60, max=7200), retry=retry_if_result(is_lockout))
@retry(wait=wait_fixed(60), retry=retry_if_result(is_lockout))
def create_pdftables_account(pdf_browser, email, name, password):
    # Fill in the form on pdftables to register
    pdf_browser.open("https://pdftables.com/join")
    sign_up_form = pdf_browser.get_form(id="form")
    sign_up_form["name"].value = name
    sign_up_form["email"].value = email
    sign_up_form["password"].value = password

    pdf_browser.submit_form(sign_up_form, submit="become-member")
    return pdf_browser.parsed.get_text()


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


def get_xlsx(pdf_api_key, pdf_path, output_path):
    c = pdftables_api.Client(pdf_api_key)
    c.xlsx_single(pdf_path, output_path)
    logger.info(f'Converted pdf to csv and saved in path {output_path}')


def check_remaining_pages(pdf_api_key):
    c = pdftables_api.Client(pdf_api_key)
    return c.remaining()


def new_api_key():
    pdf_browser = RoboBrowser(parser="lxml")
    mail_browser = RoboBrowser(parser="lxml")
    email, name, password = generate_random_email(mail_browser)
    create_pdftables_account(pdf_browser, email, name, password)
    sleep(60)
    activation_link = fetch_activation_email(email)
    pdf_browser.open(activation_link)
    log_into_pdftables(pdf_browser, email, password)
    pdf_api_key = get_api_key(pdf_browser)

    return pdf_api_key


def get_pdf_pages(file_path):
    file = open(file_path, 'rb')
    reader = PyPDF2.PdfFileReader(file)

    return reader.numPages


def clean_up_directory():
    if len(sys.argv) == 2:
        file_path = sys.argv[1]
    else:
        file_path = os.path.join(Path(os.getcwd()).parent, "pdf_files")

    pdfs = sorted(glob.glob(file_path + '*.pdf'))

    output_path = os.path.join(file_path, "converted_excels")
    if not os.path.exists(output_path):
        os.makedirs(output_path)

    excels = sorted(glob.glob(output_path + '/*.xlsx'))

    done_path = os.path.join(file_path, "done")
    if not os.path.exists(done_path):
        os.makedirs(done_path)
    logger.info(f"Done path is {done_path}")

    for pdf in pdfs:
        pdf_file = os.path.split(pdf)[1]
        pdf_basename = pdf_file.rpartition(".")[0]
        logger.info(f"Checking {pdf_file}, {pdf_basename}")

        for excel in excels:
            excel_basename = os.path.split(excel)[1].rpartition(".")[0]
            if pdf_basename == excel_basename:
                logger.info(f"Pdf {pdf_basename} already converted, moving to {done_path}")

                pdf_path = os.path.join(file_path, pdf)
                logger.info(os.path.join(done_path, pdf))
                os.rename(pdf_path, os.path.join(done_path, pdf_file))
                logger.info(f"Moved {pdf_basename} to {done_path}")
                break

    logger.info(f"Finished checks.")


if __name__ == '__main__':
    if len(sys.argv) == 2:
        file_path = sys.argv[1]
        logger.debug(f"Passed in {file_path}")
    else:
        file_path = os.path.join(Path(os.getcwd()).parent, "pdf_files")

    pdfs = sorted(glob.glob(file_path + '*.pdf'))

    page_count = 0
    api_key = ''
    email_count = 10

    output_path = os.path.join(file_path, "converted_excels")
    if not os.path.exists(output_path):
        os.makedirs(output_path)

    done_dir_path = os.path.join(file_path, "done")
    if not os.path.exists(done_dir_path):
        os.makedirs(done_dir_path)

    for pdf in pdfs:
        filename = os.path.split(pdf)[1]
        basename = os.path.splitext(filename)[0]
        logger.debug(f"Seeking to convert {filename}")

        pdf_path = os.path.join(file_path, filename)
        done_path = os.path.join(done_dir_path, filename)
        excel_path = os.path.join(output_path, basename + ".xlsx")

        if email_count >= 100 and get_pdf_pages(pdf_path) > page_count:
            sys.exit("Daily email limit reached.")

        if page_count == 0:
            api_key = new_api_key()
            page_count = check_remaining_pages(api_key)
            email_count += 1

        else:
            if get_pdf_pages(pdf_path) > page_count:
                api_key = new_api_key()
                page_count = check_remaining_pages(api_key)
                email_count += 1

        logger.info(f"Converting {pdf} to excel")
        get_xlsx(api_key, pdf_path, excel_path)
        page_count -= get_pdf_pages(pdf_path)

        os.rename(pdf_path, done_path)
        logger.info(f"Current email count: {email_count}")
        logger.info(f"Current page count: {page_count}") # Keeps breaking every so often so need this count

    logger.info(f"Loaded all pdfs in {file_path}")
