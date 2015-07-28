# gcis-nasa_airborne-scraper
Scraper for airbornescience.nasa.gov.

## Installation

```bash
virtualenv env
source env/bin/activate
pip install lxml requests[security] beautifulsoup4
```

## Examples

#### Usage

```bash
./crawl.py -h
```

#### Scrape and dump info to JSON documents in "output" directory

```bash
./crawl.py output
```
