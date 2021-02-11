import json
import os
import requests

from collections import OrderedDict
import PyPDF2

from flask import Flask

from gevent.pywsgi import WSGIServer

from apscheduler.schedulers.background import BackgroundScheduler

from pprint import pprint
import datetime

def get_data():
    URL="https://ark-funds.com/wp-content/fundsiteliterature/holdings/ARK_INNOVATION_ETF_ARKK_HOLDINGS.pdf"
    PDF = requests.get(URL, stream=True)
    with open('tmp.pdf', 'wb') as fd:
        for chunk in PDF.iter_content(2000):
            fd.write(chunk)

def get_companies():
    file = open('tmp.pdf', 'rb')
    fileReader = PyPDF2.PdfFileReader(file)
    content = fileReader.getPage(0).extractText()
    COMPANIES = []
    split_by_newline = content.split("\n")
    share_index = 0
    company_dict = OrderedDict()
    curr_comp = "Company"
    for el in split_by_newline:
        if share_index == 3:
            company_dict[curr_comp] = el
            share_index = 0
        if share_index < 3 and share_index != 0:
            share_index += 1
        if el.startswith("€"):
            share_index = 1
            tmp = el.split(" ")
            try:
                curr_comp = tmp[1].lower()
                COMPANIES.append(curr_comp)
                company_dict[curr_comp] = ""
            except Exception as exc:
                pass

    with open("COMPANIES.json", "w") as write_file:
        json.dump(company_dict, write_file)

    return set(COMPANIES)

def lifesign():
    with open('lifesign', 'w') as fd:
        fd.write("")

def provide():
    print(datetime.datetime.now())
    print("Requesting the data...")
    get_data()
    NEW_COMPANIES = get_companies()
    if len(COMPANIES) != len(NEW_COMPANIES):
        print("Something changed!")
        res = COMPANIES.difference(NEW_COMPANIES)
        print(res)

        WEBHOOK = os.environ.get("WEBHOOK")
        if WEBHOOK == "":
            print("No Webhook Env Var provided")
            return

        payload ={
                "due":
                "a"
                ,
                "email":
                "b"
                ,
                "task":
                    res
                }
        headers = {'Content-type': 'application/json', 'Accept': 'text/plain'}
        res = requests.post(WEBHOOK, json=payload, headers=headers)

if __name__ == '__main__':
    app = Flask(__name__)

    get_data()
    COMPANIES = get_companies()
    pprint(len(COMPANIES))
    pprint(COMPANIES)

    print("Running app...")

    scheduler = BackgroundScheduler()
    scheduler.add_job(func=provide, trigger="interval", seconds=10000)
    scheduler.add_job(func=lifesign, trigger="interval", seconds=3)
    scheduler.start()

    # Shut down the scheduler when exiting the app
    #atexit.register(lambda: scheduler.shutdown())

    print("Starting app...")
    HTTP_SERVER = WSGIServer(('0.0.0.0', int(5555)), app)
    HTTP_SERVER.serve_forever()
