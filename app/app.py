import atexit
import logging
import os
import pickle
import sys
sys.path.append(".")

from flask import Flask

from gevent.pywsgi import WSGIServer

from apscheduler.schedulers.background import BackgroundScheduler

import helpers as hs

logging.basicConfig(filename='app.log', filemode='a', format='%(asctime)s: %(name)s - %(levelname)s - %(message)s', level="INFO")

WEBHOOK = os.environ.get("WEBHOOK")
if WEBHOOK is None:
    print("No Webhook Env Var provided!")
    sys.exit(1)

def provide():
    logging.info("Requesting the data...")
    try:
        with open('COMPANIES.pkl', 'rb') as json_file:
            COMPANIES = pickle.load(json_file)
        with open('COMPANY_DICT.pkl', 'rb') as json_file:
            COMPANY_DICT = pickle.load(json_file)
    except:
        logging.info("--> Getting data the first time...")
        hs.get_data("tmp.pdf")
        content = hs.read_pdf("tmp.pdf")
        COMPANIES, COMPANY_DICT = hs.get_companies(content)
        with open("COMPANIES.pkl", "wb") as write_file:
            pickle.dump(COMPANIES, write_file)
        with open("COMPANY_DICT.pkl", "wb") as write_file:
            pickle.dump(COMPANY_DICT, write_file)

    hs.get_data("tmp.pdf")
    content = hs.read_pdf("tmp.pdf")
    NEW_COMPANIES, NEW_COMPANY_DICT = hs.get_companies(content)

    removed, added = hs.compare_sets(COMPANIES, NEW_COMPANIES)
    res_share = hs.compare_share(COMPANY_DICT, NEW_COMPANY_DICT)
    if removed or added or res_share:
        hs.send_payload(WEBHOOK, removed, added, res_share)
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
    scheduler.add_job(func=provide, trigger="interval", seconds=1000)
    scheduler.start()

    # Shut down the scheduler when exiting the app
    atexit.register(lambda: scheduler.shutdown())

    logging.info("Starting app...")
    HTTP_SERVER = WSGIServer(('0.0.0.0', int(5555)), app)
    HTTP_SERVER.serve_forever()
