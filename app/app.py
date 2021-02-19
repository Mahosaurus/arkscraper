import atexit
import pickle
import os
import requests

from collections import OrderedDict
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
    logging.critical("No Webhook Env Var provided")

def get_data():
    URL="https://ark-funds.com/wp-content/fundsiteliterature/holdings/ARK_INNOVATION_ETF_ARKK_HOLDINGS.pdf"
    PDF = requests.get(URL, stream=True)
    with open('tmp.pdf', 'wb') as fd:
        for chunk in PDF.iter_content(2000):
            fd.write(chunk)

def read_pdf():
    file = open('tmp.pdf', 'rb')
    fileReader = PyPDF2.PdfFileReader(file)
    content = fileReader.getPage(0).extractText()
    return content

def compare_sets(COMPANIES, NEW_COMPANIES):
    if len(COMPANIES) != len(NEW_COMPANIES):
        logging.info("Something changed in Company Sets!")
        res = COMPANIES.difference(NEW_COMPANIES)
        logging.info(res)
        return res
    return []

def compare_share(COMPANIES, NEW_COMPANIES):
    result = {}
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
            result[old_share] = old_share - new_share
            logging.info("Compare share found a difference!")
            logging.info(result[old_share])
    return result

def get_companies():
    content = read_pdf()
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
                curr_comp = tmp[1].lower()
                COMPANIES.append(curr_comp)
                COMPANY_DICT[curr_comp] = ""
            except Exception as exc:
                pass

    COMPANIES = set(COMPANIES)
    return COMPANIES, COMPANY_DICT

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
        COMPANIES, COMPANY_DICT = get_companies()
        with open("COMPANIES.pkl", "wb") as write_file:
            pickle.dump(COMPANIES, write_file)
        with open("COMPANY_DICT.pkl", "wb") as write_file:
            pickle.dump(COMPANY_DICT, write_file)

    get_data()
    NEW_COMPANIES, NEW_COMPANY_DICT = get_companies()

    res_sets = compare_sets(COMPANIES, NEW_COMPANIES)
    if res_sets:
        payload ={
                "due":
                "a"
                ,
                "email":
                "b"
                ,
                "task":
                    res_sets
                }
        headers = {'Content-type': 'application/json', 'Accept': 'text/plain'}
        requests.post(WEBHOOK, json=payload, headers=headers)
        return
    else:
        logging.info("No change in sets")

    res_share = compare_share(COMPANY_DICT, NEW_COMPANY_DICT)
    if res_share:
        payload ={
                "due":
                "a"
                ,
                "email":
                "b"
                ,
                "task":
                    res_share
                }
        headers = {'Content-type': 'application/json', 'Accept': 'text/plain'}
        requests.post(WEBHOOK, json=payload, headers=headers)
    else:
        logging.info("No change in share")

    if res_sets or res_share:
        with open("COMPANIES.pkl", "wb") as write_file:
            pickle.dump(NEW_COMPANIES, write_file)
        with open("COMPANY_DICT.pkl", "wb") as write_file:
            pickle.dump(NEW_COMPANY_DICT, write_file)
        logging.info("Setting new companies as standard")

if __name__ == '__main__':
    app = Flask(__name__)

    logging.info("Running app...")

    scheduler = BackgroundScheduler()
    scheduler.add_job(func=provide, trigger="interval", seconds=2000)
    scheduler.start()

    # Shut down the scheduler when exiting the app
    #atexit.register(lambda: scheduler.shutdown())

    logging.info("Starting app...")
    HTTP_SERVER = WSGIServer(('0.0.0.0', int(5555)), app)
    HTTP_SERVER.serve_forever()
