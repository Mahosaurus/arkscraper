import logging
import os

from pathlib import Path
from collections import defaultdict

import random
import requests
import string
import subprocess

import PyPDF2

from flask import Flask, render_template, request, redirect, flash, send_file
from flask import request

from gevent.pywsgi import WSGIServer

from apscheduler.schedulers.background import BackgroundScheduler

import time
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
    for el in split_by_newline:
        if el.startswith("€"):
            tmp = el.split(" ")
            try:
                COMPANIES.append(tmp[1])
            except Exception as exc:
                pass
    return set(COMPANIES)

def provide():
    print(datetime.datetime.now())
    print("Requesting the data...")
    get_data()
    NEW_COMPANIES = get_companies()
    if len(COMPANIES) != len(NEW_COMPANIES):
        print("Alert!")
        print(COMPANIES.difference(NEW_COMPANIES))
        WEBHOOK = os.environ.get("WEBHOOK")
        request.post(WEBHOOK)

if __name__ == '__main__':
    app = Flask(__name__)

    get_data()
    COMPANIES = get_companies()
    pprint(len(COMPANIES))
    pprint(COMPANIES)

    print("Running app...")

    scheduler = BackgroundScheduler()
    scheduler.add_job(func=provide, trigger="interval", seconds=60)
    scheduler.start()

    # Shut down the scheduler when exiting the app
    #atexit.register(lambda: scheduler.shutdown())

    print("Starting app...")
    HTTP_SERVER = WSGIServer(('0.0.0.0', int(5555)), app)
    HTTP_SERVER.serve_forever()

