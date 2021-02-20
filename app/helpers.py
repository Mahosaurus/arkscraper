import logging

from collections import OrderedDict
from typing import Optional, Tuple

import requests

import PyPDF2

logging.basicConfig(filename='app.log', filemode='a', format='%(asctime)s: %(name)s - %(levelname)s - %(message)s', level="INFO")

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

def compare_sets(COMPANIES: set, NEW_COMPANIES: set) -> Tuple[Optional[str], Optional[str]]:
    if len(COMPANIES) != len(NEW_COMPANIES):
        logging.info("Something changed in Company Sets!")
        removed = COMPANIES.difference(NEW_COMPANIES)
        added = NEW_COMPANIES.difference(COMPANIES)
        removed = ",".join(removed)
        added = ",".join(added)
        return removed, added
    return None, None

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
            except Exception:
                pass

    COMPANIES = set(COMPANIES)
    return COMPANIES, COMPANY_DICT

def send_payload(WEBHOOK: str, removed: str = "", added: str = "", changes= ""):
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

def read_pdf(path='tmp.pdf'):
    file = open(path, 'rb')
    file_reader = PyPDF2.PdfFileReader(file)
    content = file_reader.getPage(0).extractText()
    return content

def get_data(path="tmp.pdf"):
    URL = "https://ark-funds.com/wp-content/fundsiteliterature/holdings/ARK_INNOVATION_ETF_ARKK_HOLDINGS.pdf"
    PDF = requests.get(URL, stream=True)
    with open(path, 'wb') as fd:
        for chunk in PDF.iter_content(2000):
            fd.write(chunk)
