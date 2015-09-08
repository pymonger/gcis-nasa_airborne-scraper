#!/usr/bin/env python
import os, sys, re, json, requests, requests_cache, argparse, logging
from bs4 import BeautifulSoup
from unidecode import unidecode


log_format = "[%(asctime)s: %(levelname)s/%(funcName)s] %(message)s"
logging.basicConfig(format=log_format, level=logging.INFO)


requests_cache.install_cache('airbornescience-import')


BASE_URL = "https://www.eol.ucar.edu/content/dois-maintained-eol"

# regex
SECTIONS_RE = re.compile(r'<strong>')
DIVS_RE = re.compile(r'<div>(.*?)</div>', re.S)
WS_RE = re.compile(r'^\s*$', re.M)
BR_RE = re.compile(r'<br/>', re.M)
EOL_RE = re.compile(r'EOL Documents')
PLAT_RE = re.compile(r'/observing_facilities/')
INSTR_RE = re.compile(r'/instruments/')
SW_RE = re.compile(r'/data-software/')


def crawl_all(input_dir):
    """Crawl the Airborne Science website for instruments."""

    # crawl DOIs page
    r = requests.get(BASE_URL)
    r.raise_for_status()
    soup = BeautifulSoup(r.content, 'lxml')
    field_item = soup.find('div', class_="field-item")
    #logging.info(field_item)
    sections = SECTIONS_RE.split(str(field_item))
    data = []
    for section in sections[1:]:
        if EOL_RE.search(section): continue
        #logging.info(section)
        s2 = BeautifulSoup(section, 'lxml')
        divs = s2.find_all('div')
        for div in divs:
            #logging.info("div: '%s'" % div.text)
            children = div.findChildren()
            #logging.info("children: %d" % len(children))
            if len(children) == 0:
                text = div.text.strip()
                if WS_RE.search(text): continue
            elif len(children) == 1:
                tag = children[0].name
                #logging.info("tag: %s" % tag)
                if tag == 'br':
                    text = div.text.strip()
                else:
                    text = children[0].text.strip()
                if WS_RE.search(text):
                   #logging.info("continuing on '%s'" % text)
                   continue
            else: continue
            #logging.info("final value: '%s'" % text)

            # HACK: detect 3V-CPI instrument name which occurs
            # at the end of the previous div
            if re.search(r'three-view-cloud-particle-imager', text):
                data.append("3V-CPI")

            data.append(text) 
    #logging.info("\n".join(data))
    #logging.info("len: %d" % len(data))

    # build dictionary of platform/instrument metadata
    data_dict = {
        'platform': {},
        'instrument': {},
        'software': {},
    }
    key = None
    resource_type = None
    for i, val in enumerate(data):
        if i % 4 == 0:
            key = val
            #logging.info("-" * 80)
            #logging.info("key: %s" % key)
        elif i % 4 == 1:
            if PLAT_RE.search(val):
                resource_type = "platform"
            elif INSTR_RE.search(val):
                resource_type = "instrument"
            elif SW_RE.search(val):
                resource_type = "software"
            else:
                raise RuntimeError("Failed to detect resource type: %s" % val)
            #logging.info("landing_page: %s" % val)
            data_dict[resource_type].setdefault(key, {})['landing_page'] = val
        elif i % 4 == 2:
            #logging.info("doi: %s" % val)
            data_dict[resource_type][key]['doi'] = val
        elif i % 4 == 3:
            #logging.info("ezid: %s" % val)
            data_dict[resource_type][key]['ezid'] = val
            #logging.info("#" * 80)
    logging.info("%s" % json.dumps(data_dict, indent=2))
     

if __name__ == "__main__":
    desc = "Scrape DOIs from NCAR/UCAR EOL, match on platforms/instruments" + \
           " in JSON dump (output of crawl.py) and attach additional metadata."
    parser = argparse.ArgumentParser(description=desc)
    parser.add_argument('input_dir', help="input directory (output_dir of crawl.py)")
    args = parser.parse_args()
    crawl_all(args.input_dir)
