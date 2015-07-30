#!/usr/bin/env python
import os, sys, re, logging, json, requests, argparse
from bs4 import BeautifulSoup

from gcis_clients import GcisClient


log_format = "[%(asctime)s: %(levelname)s/%(funcName)s] %(message)s"
logging.basicConfig(format=log_format, level=logging.INFO)


def create_platform(url):
    """Create platform."""

    gcis = GcisClient(url)

    # add platform
    platform = {
                u'description': u"ACRIMSAT is a NASA funded minisatellite mission to monitor the amount of total solar energy received (part of EOS program). The objective is to monitor the solar constant, or TSI (Total Solar Irradiation), with maximum precision and provide an important link in the long-term TSI database. ACRIMSAT is part of a multi-decade effort to understand variations in the sun's output and resulting effects on Earth.",
                u'description_attribution': u'https://directory.eoportal.org/web/eoportal/satellite-missions/a/acrimsat',
                u'end_date': u'2015-09-01T00:00:00',
                u'identifier': u'active-cavity-radiometer-irradiance-monitor',
                u'name': u'Active Cavity Radiometer Irradiance Monitor',
                u'platform_type_identifier': u'spacecraft',
                u'start_date': u'1999-12-20T00:00:00',
                u'url': u'http://acrim.jpl.nasa.gov/'}
    r = gcis.s.post("%s/platform" % url, data=json.dumps(platform), verify=False)
    r.raise_for_status()
    print(r.json())

    # add contributor
    contributor = {
        u'organization_identifier': u'national-aeronautics-space-administration',
        u'role': u'contributing_agency',
    }
    r = gcis.s.post("%s/platform/contributors/%s" % (url, platform['identifier']),
                    data=json.dumps(contributor), verify=False)
    r.raise_for_status()
    print(r.json())

    # add instrument
    instrument = {
        'add': {
            u'instrument_identifier': u'active-cavity-radiometer-irradiance-monitor-2',
        }
    }
    r = gcis.s.post("%s/platform/rel/%s" % (url, platform['identifier']),
                    data=json.dumps(instrument), verify=False)
    r.raise_for_status()
    print(r.json())

    # add file
    file = {
        u'add_existing_file': u'/file/39e09ff4-de0b-411f-9b2e-d826a1c987db',
    }
    r = gcis.s.post("%s/platform/files/%s" % (url, platform['identifier']),
                    data=json.dumps(file), verify=False)
    r.raise_for_status()
    print(r.json())


if __name__ == "__main__":
    desc = "Test creation of platform."
    parser = argparse.ArgumentParser(description=desc)
    parser.add_argument('url', help="GCIS url")
    args = parser.parse_args()
    create_platform(args.url)
