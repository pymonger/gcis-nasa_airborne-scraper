#!/usr/bin/env python
import os, sys, re, json, requests, requests_cache, argparse
from bs4 import BeautifulSoup
from unidecode import unidecode


requests_cache.install_cache('airbornescience-import')


BASE_URL = "http://airbornescience.nasa.gov"

COUNT_RE = re.compile(r'Currently\s+displayed:\s*instruments\s+1\s+-\s+(\d+)\s+of\s+(\d+)\.')

ROLE_RE = re.compile(r'\((.*?)\)')

# globals
AIRCRAFTS = set()
ORGS = set()
INSTRUMENTS = set()
PERSONS = set()


def dump(curated_file, output_file, val_set):

    with open(curated_file) as f:
        curated = json.load(f)
    with open(output_file, 'w') as f:
        j = {}
        for k in sorted([i for i in list(val_set) if i is not None]):
            if k in curated and curated[k] is not None: val = curated[k]
            else:
                val = "-".join([unidecode(c.lower()) for c in k.split() if c not in ('of', '-')])\
                         .replace('.', '').replace('(', '').replace(')', '')\
                         .replace('/', '-').replace(',', '').replace("'", '')\
                         .replace('"', '')
            j[k] = val
        json.dump(j, f, indent=2, sort_keys=True)


def get_paging_info():
    """Parse out total number of instruments and results per page."""

    r = requests.get("%s/instrument/all" % BASE_URL)
    r.raise_for_status()
    match = COUNT_RE.search(r.content)
    if not match:
        raise RuntimeError("Failed to find total count of instruments.")
    return map(int, match.groups())


def get_aircraft_info(name, url):
    """Parse aircraft info, scrape metadata, and return as JSON."""

    # set defaults
    summary = None
    orgs = []
    a_type = None

    if url is not None:
        r = requests.get(url)
        r.raise_for_status()
        soup = BeautifulSoup(r.content, 'lxml')

        # extract summary
        summary_div = soup.find('div', class_="field-type-text-with-summary")
        if summary_div is not None:
            summaries = summary_div.find_all('p')
            if len(summaries) > 0:
                summary = ""
                for s in summaries:
                    summary += " ".join(s.stripped_strings)
    
        # extract organization
        org_div = soup.find('div', class_="field-name-field-ac-org")
        if org_div is not None and len(org_div.contents) >= 2:
            for o in org_div.contents[1].find_all('div'):
                orgs.append(o.string)
                ORGS.add(o.string)

        # extract aircraft type
        type_div = soup.find('div', class_="field-name-field-ac-type")
        if type_div is not None and len(type_div.contents) >= 2:
            a_type = type_div.contents[1].find('div').string

    info = {
        'name': name,
        'url': url,
        'summary': summary,
        'organization': orgs,
        'type': a_type,
    }
    return info


def get_instrument_info(td):
    """Parse instrument info, scrape metadata and return as JSON."""

    url = "%s%s" % (BASE_URL, td.a.get('href'))
    r = requests.get(url)
    r.raise_for_status()
    soup = BeautifulSoup(r.content, 'lxml')

    # extract summary
    summary_div = soup.find('div', class_="white_article_wrap_detail").div.contents[2]
    summary = None
    if summary_div is not None:
        summaries = summary_div.find_all('p')
        if len(summaries) > 0:
            summary = ""
            for s in summaries:
                summary += " ".join(s.stripped_strings)

    # extract photo of instrument
    photo_div = soup.find('div', class_="field-name-field-photo")
    if photo_div is not None and photo_div.img is not None:
        photo = photo_div.img.get('src')
    else: photo = None

    # extract representative image of data
    data_img_div = soup.find('div', class_="field-name-field-data-image")
    if data_img_div is not None and data_img_div.img is not None:
        data_img = data_img_div.img.get('src')
    else: data_img = None

    # extract aircrafts
    aircrafts = []
    aircraft_div = soup.find('div', class_="field-name-field-aircraft")
    if aircraft_div is not None and len(aircraft_div.contents) >= 2:
        aircraft_div = aircraft_div.contents[1]
        aircraft_names = [i.strip() for i in "".join(aircraft_div.stripped_strings).split(',')]
        for aircraft_name in aircraft_names:
            aircraft_href = "/aircraft/%s" % aircraft_name.replace(' ', '_')
            aircraft_link = aircraft_div.find('a', attrs={'href': aircraft_href})
            if aircraft_link is not None:
                aircraft_url = "%s%s" % (BASE_URL, aircraft_href)
            else: aircraft_url = None
            aircrafts.append(get_aircraft_info(aircraft_name, aircraft_url))
            AIRCRAFTS.add(aircraft_name)

    INSTRUMENTS.add(td.a.string)

    return { 
        'title': td.a.string,
        'href': url,
        'summary': summary,
        'photo': photo,
        'data_image': data_img,
        'aircraft': aircrafts,
    }
    

def get_contact_info(td):
    """Parse contact info, scrape metadata and return as JSON."""

    # extract role
    role = None
    for i in td.contents:
        match = ROLE_RE.search(i.string)
        if match:
            role = match.group(1)
            break
    if td.a is None: return None

    # extract organization
    url = "%s%s" % (BASE_URL, td.a.get('href'))
    r = requests.get(url)
    r.raise_for_status()
    soup = BeautifulSoup(r.content, 'lxml')
    org_div = soup.find('div', class_="field-name-field-org-tid-combo")
    if org_div is not None and len(org_div.contents) >= 2:
        org = org_div.contents[1].string
    else: org = None
    ORGS.add(org)

    # extract phone number
    phone_div = soup.find('div', attrs={'rel': 'foaf:phone'})
    if phone_div is None: phone = None
    else: phone = phone_div.get('resource', None)

    # extract address
    addr_div = soup.find('div', class_="field-name-field-address-new")
    if addr_div is not None and len(addr_div.contents) >= 2:
        addr = " ".join(addr_div.contents[1].stripped_strings)
    else: addr = None

    # extract website
    website_div = soup.find('div', class_="field-name-field-website")
    if website_div is not None and len(website_div.contents) >= 2:
        website = website_div.contents[1].a.get('href', None)
    else: website = None

    PERSONS.add(td.a.string)

    return { 
        'name': td.a.string,
        'href': "%s%s" % (BASE_URL, td.a.get('href')),
        'role': role,
        'organization': org,
        'phone': phone,
        'address': addr,
        'website': website,
    }
    

def get_value_list(tr, cls):
    """Return list of values from <a/> tags."""

    return [a.string for a in tr.find('td', class_=cls).find_all('a')]
        

def parse_row_data(tr):
    """Parse row data."""

    info = get_instrument_info(tr.find('td', class_="views-field-title"))
    info['acronym'] = tr.find('td', class_="views-field-entity-id").string.strip()
    info['contact'] = get_contact_info(tr.find('td', class_="views-field-entity-id-5"))
    info['instrument'] = get_value_list(tr, "views-field-field-itype")
    info['measurements'] = get_value_list(tr, "views-field-field-meas")
    return info


def crawl_all(output_dir):
    """Crawl the Airborne Science website for instruments."""

    # get total instruments
    page_size, total = get_paging_info()

    # loop over pages
    instr_dir = os.path.join(output_dir, "instruments")
    if not os.path.isdir(instr_dir): os.makedirs(instr_dir, 0755)
    for page in range(total/page_size+1):
        r = requests.get("%s/instrument/all" % BASE_URL, params={'page': page})
        r.raise_for_status()
        soup = BeautifulSoup(r.content, 'lxml')
        tbody = soup.find('table', class_="views-table").tbody
        data = []
        for tr in tbody.find_all('tr'):
            info = parse_row_data(tr)
            data.append(info)
            info_file = os.path.join(instr_dir, "%s.json" % os.path.basename(info['href']).replace(' ', '-'))
            with open(info_file, 'w') as f:
                json.dump(info, f, indent=2, sort_keys=True)

    # curated identifiers directory
    curated_dir = os.path.join(os.path.dirname(__file__), "curated")

    # write out orgs
    dump(os.path.join(curated_dir, "organization-gcis-map.json"),
         os.path.join(output_dir, "organization.json"), ORGS)

    # write out aircrafts
    dump(os.path.join(curated_dir, "aircraft-gcis-map.json"),
         os.path.join(output_dir, "aircraft.json"), AIRCRAFTS)

    # write out instruments
    dump(os.path.join(curated_dir, "instrument-gcis-map.json"),
         os.path.join(output_dir, "instrument.json"), INSTRUMENTS)

    # write out persons
    dump(os.path.join(curated_dir, "person-gcis-map.json"),
         os.path.join(output_dir, "person.json"), PERSONS)


if __name__ == "__main__":
    desc = "Crawl and dump airborne instruments, platforms and related metadata."
    parser = argparse.ArgumentParser(description=desc)
    parser.add_argument('output_dir', help="output directory")
    args = parser.parse_args()
    crawl_all(args.output_dir)
