# gcis-nasa_airborne-scraper
Scraper for airbornescience.nasa.gov.

## Installation

```bash
virtualenv env
source env/bin/activate
pip install lxml requests[security] beautifulsoup4
```

## Examples

#### Scrape and dump EOL landing page/DOI/EZID info to JSON document

```bash
./crawl_eol.py eol.json
```

#### Scrape and dump airborne info to JSON documents in "output" directory

```bash
./crawl.py --eol=eol.json output
```
