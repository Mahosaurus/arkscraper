import atexit
import pickle
import os
import time
import sys
import requests

from collections import OrderedDict
from typing import Optional, Tuple
import PyPDF2

from flask import Flask

from gevent.pywsgi import WSGIServer

from apscheduler.schedulers.background import BackgroundScheduler

from pprint import pprint
import datetime

import logging

logging.basicConfig(filename='app.log', filemode='a', format='%(asctime)s: %(name)s - %(levelname)s - %(message)s', level="INFO")

WEBHOOK = os.environ.get("WEBHOOK")
if WEBHOOK is None:
    print("No Webhook Env Var provided!")
    sys.exit(1)

def get_data():
    URL="https://ark-funds.com/wp-content/fundsiteliterature/holdings/ARK_INNOVATION_ETF_ARKK_HOLDINGS.pdf"
    PDF = requests.get(URL, stream=True)
    with open('tmp.pdf', 'wb') as fd:
        for chunk in PDF.iter_content(2000):
            fd.write(chunk)

def read_pdf(path='tmp.pdf'):
    file = open(path, 'rb')
    fileReader = PyPDF2.PdfFileReader(file)
    content = fileReader.getPage(0).extractText()
    return content

def get_companies(content):
    split_by_newline = content.split("\n")
    share_index = 0
    COMPANIES = []
    COMPANY_DICT = OrderedDict()
    curr_comp = "Company"
    for el in split_by_newline:
        if share_index == 3: # Case of no shares
            COMPANY_DICT[curr_comp] = el
            share_index = 0
        if share_index < 3 and share_index != 0:
            share_index += 1
        if el.startswith("€"): # Case of company name
            share_index = 1
            tmp = el.split(" ")
            try:
                curr_comp = " ".join(tmp[1:]).lower()
                COMPANIES.append(curr_comp)
                COMPANY_DICT[curr_comp] = ""
            except Exception as exc:
                pass

    COMPANIES = set(COMPANIES)
    return COMPANIES, COMPANY_DICT


def compare_sets(COMPANIES: set, NEW_COMPANIES: set) -> Tuple[Optional[str], Optional[str]]:
    if len(COMPANIES) != len(NEW_COMPANIES):
        logging.info("Something changed in Company Sets!")
        removed = COMPANIES.difference(NEW_COMPANIES)
        added = NEW_COMPANIES.difference(COMPANIES)
        removed = ",".join(removed)
        added = ",".join(added)
        return removed, added
    return None, None

def compare_share(COMPANIES: set, NEW_COMPANIES: set):
    result = OrderedDict()
    for stock in COMPANIES:
        try:
            old_share = int(COMPANIES[stock].replace(",", ""))
        except:
            continue
        try:
            new_share = int(NEW_COMPANIES[stock].replace(",", ""))
        except:
            continue
        if old_share != new_share:
            result[stock] = old_share - new_share
    formatted_result = "<br>".join([key + ": " + str(result[key]) for key in result])
    if result:
        logging.info("Compare share found a difference!")
    return formatted_result

def send_payload(removed: str = "", added: str = "", changes= ""):
    if added == "":
        added = "/"
    if removed == "":
        removed = "/"
    if changes == "":
        changes = "/"

    payload ={
        "added":
            added
        ,
        "changes":
            changes
        ,
        "removed":
            removed
        }
    headers = {'Content-type': 'application/json', 'Accept': 'text/plain'}
    req = requests.post(WEBHOOK, json=payload, headers=headers)
    if req.status_code == 200:
        logging.info("Sent a mail! Payload was:")
        logging.info(payload)

def provide():
    logging.info(datetime.datetime.now())
    logging.info("Requesting the data...")
    try:
        with open('COMPANIES.pkl', 'rb') as json_file:
            COMPANIES = pickle.load(json_file)
        with open('COMPANY_DICT.pkl', 'rb') as json_file:
            COMPANY_DICT = pickle.load(json_file)
    except:
        logging.info("--> Getting data the first time...")
        get_data()
        content = read_pdf()
        COMPANIES, COMPANY_DICT = get_companies(content)
        with open("COMPANIES.pkl", "wb") as write_file:
            pickle.dump(COMPANIES, write_file)
        with open("COMPANY_DICT.pkl", "wb") as write_file:
            pickle.dump(COMPANY_DICT, write_file)

    get_data()
    content = read_pdf("tmp.pdf")
    NEW_COMPANIES, NEW_COMPANY_DICT = get_companies(content)

    removed, added = compare_sets(COMPANIES, NEW_COMPANIES)
    res_share = compare_share(COMPANY_DICT, NEW_COMPANY_DICT)
    if removed or added or res_share:
        send_payload(removed, added, res_share)
    else:
        logging.info("No change in sets")

    # Update local cache
    if removed or added or res_share:
        with open("COMPANIES.pkl", "wb") as write_file:
            pickle.dump(NEW_COMPANIES, write_file)
        with open("COMPANY_DICT.pkl", "wb") as write_file:
            pickle.dump(NEW_COMPANY_DICT, write_file)
        logging.info("Setting new data as standard")

if __name__ == '__main__':
    app = Flask(__name__)

    logging.info("Running app...")

    scheduler = BackgroundScheduler()
    scheduler.add_job(func=provide, trigger="interval", seconds=10)
    scheduler.start()

    # Shut down the scheduler when exiting the app
    atexit.register(lambda: scheduler.shutdown())

    logging.info("Starting app...")
    HTTP_SERVER = WSGIServer(('0.0.0.0', int(5555)), app)
    HTTP_SERVER.serve_forever()
