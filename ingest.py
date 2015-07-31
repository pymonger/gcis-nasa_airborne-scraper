#!/usr/bin/env python
import os, sys, re, logging, json, requests, argparse
from requests.packages.urllib3.exceptions import InsecureRequestWarning

from gcis_clients import GcisClient

requests.packages.urllib3.disable_warnings(InsecureRequestWarning)


log_format = "[%(asctime)s: %(levelname)s/%(funcName)s] %(message)s"
logging.basicConfig(format=log_format, level=logging.INFO)

# globals
PERSONS = {}


def ingest(url, instr_dir, map_dir):
    """Crawl instruments directory and ingest into GCIS using the GCIS API."""

    gcis = GcisClient(url)

    # get gcis id map for aircrafts
    with open(os.path.join(map_dir, 'aircraft-gcis-map.json')) as f:
        platform_map = json.load(f)

    # get gcis id map for instruments
    with open(os.path.join(map_dir, 'instrument-gcis-map.json')) as f:
        instrument_map = json.load(f)

    # get gcis id map for organization
    with open(os.path.join(map_dir, 'organization-gcis-map.json')) as f:
        organization_map = json.load(f)

    # get gcis id map for person
    with open(os.path.join(map_dir, 'person-gcis-map.json')) as f:
        person_map = json.load(f)

    # loop over instruments and ingest into GCIS
    for root, dirs, files in os.walk(instr_dir, followlinks=True):
        files.sort()
        for file in files:
            if not file.endswith('.json'): continue
            with open(os.path.join(root, file)) as f:
                instr_json = json.load(f)

            # add instrument
            instr_id = instrument_map[instr_json['title']]
            logging.info("#" * 80)
            logging.info('instr_id: %s' % instr_id)
            instr_doc = {
                'description': instr_json['summary'],
                'description_attribution': instr_json['href'],
                u'identifier': instr_id,
                u'name': instr_json['title'],
            }
            r = gcis.s.head("%s/instrument/%s" % (url, instr_id), verify=False)
            if r.status_code == 404:
                r = gcis.s.post("%s/instrument" % url, data=json.dumps(instr_doc), verify=False)
                r.raise_for_status()

            # add platforms
            for plat_json in instr_json['aircraft']:
                plat_id = platform_map[plat_json['name']]
                logging.info('plat_id: %s' % plat_id)
                plat_doc = {
                    'description': plat_json['summary'],
                    u'description_attribution': plat_json['url'],
                    u'identifier': plat_id,
                    u'name': plat_json['name'],
                    u'platform_type_identifier': 'aircraft',
                    u'url': plat_json['url']
                }
                r = gcis.s.head("%s/platform/%s" % (url, plat_id), verify=False)
                if r.status_code == 404:
                    r = gcis.s.post("%s/platform" % url, data=json.dumps(plat_doc), verify=False)
                    r.raise_for_status()

                # add contributors
                for org_name in plat_json['organization']:
                    org_id = organization_map[org_name]
                    logging.info('org_id: %s' % org_id)

                    # add organization
                    org_doc = {
                        'identifier': org_id,
                        'name': org_name,
                    }
                    r = gcis.s.head("%s/organization/%s" % (url, org_id), verify=False)
                    if r.status_code == 404:
                        r = gcis.s.post("%s/organization" % url, data=json.dumps(org_doc), verify=False)
                        r.raise_for_status()

                    # add organization as contributor
                    cont_doc = {
                        'organization_identifier': org_id,
                        'role': 'contributing_agency',
                    }
                    r = gcis.s.head("%s/platform/contributors/%s" % (url, plat_id), verify=False)
                    if r.status_code == 404:
                        r = gcis.s.post("%s/platform/contributors/%s" % (url, plat_id),
                                        data=json.dumps(cont_doc), verify=False)
                        r.raise_for_status()

                # link to instrument
                instr_add = {
                    'add': {
                        'instrument_identifier': instr_id,
                    }
                } 
                r = gcis.s.post("%s/platform/rel/%s" % (url, plat_id),
                                data=json.dumps(instr_add), verify=False)
                r.raise_for_status()

                # add POC
                person_json = instr_json.get('contact', None)
                if person_json is None: continue
                if person_json['name'] not in PERSONS:
                    name_cmps = person_json['name'].split()
                    if len(name_cmps) == 2:
                        person_doc = {
                            'first_name': name_cmps[0],
                            'last_name': name_cmps[1],
                            'url': person_json['website'],
                        }
                    elif len(name_cmps) == 3:
                        person_doc = {
                            'first_name': name_cmps[0],
                            'middle_name': name_cmps[1],
                            'last_name': name_cmps[2],
                            'url': person_json['website'],
                        }
                    else: raise(RuntimeError("Failed to parse name %s." % person_json['name']))
                    r = gcis.s.post("%s/person/" % url, data=json.dumps(person_doc), verify=False)
                    r.raise_for_status()
                    person_id = r.json()['id']
                    PERSONS[person_json['name']] = person_id
                else: person_id = PERSONS[person_json['name']]
                #logging.info(person_id)

                # add person's organization
                if person_json['organization'] is not None:
                    person_org_id = organization_map[person_json['organization']]
                    org_doc = {
                        'identifier': person_org_id,
                        'name': person_json['organization'],
                    }
                    r = gcis.s.head("%s/organization/%s" % (url, person_org_id), verify=False)
                    if r.status_code == 404:
                        r = gcis.s.post("%s/organization" % url, data=json.dumps(org_doc), verify=False)
                        r.raise_for_status()
                else: person_org_id = None

                # add person as contributor
                cont_doc = {
                    'person_id': person_id,
                    'role': 'point_of_contact',
                }
                if person_org_id: cont_doc['organization_identifier'] = person_org_id
                r = gcis.s.head("%s/instrument/contributors/%s" % (url, instr_id), verify=False)
                if r.status_code == 404:
                    r = gcis.s.post("%s/instrument/contributors/%s" % (url, instr_id),
                                    data=json.dumps(cont_doc), verify=False)
                    r.raise_for_status()



if __name__ == "__main__":
    desc = "Ingest airborne platforms, instruments, measurements, organizations and persons."
    parser = argparse.ArgumentParser(description=desc)
    parser.add_argument('url', help="GCIS url")
    parser.add_argument('instr_dir', help="directory containing instrument JSON dumps")
    parser.add_argument('map_dir', help="directory containing name->GCIS identifier map files")
    args = parser.parse_args()
    ingest(args.url, args.instr_dir, args.map_dir)
