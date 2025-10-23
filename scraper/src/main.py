import argparse
import datetime
import logging
import os

import requests
from models import Fractie
from models import Zaak
from models import ZaakSoort
from rdflib import Graph

from scraper import TkScraper


def create_arg_parser():

    parser = argparse.ArgumentParser(
        description='Scrape data from the TK API and upload it to GraphDB.',
    )
    parser.add_argument(
        '--graphdb-url',
        type=str,
        default=os.environ.get(
            'GRAPHDB_URL', 'http://localhost:7200/repositories/tk_main/statements',
        ),
        help='The URL of the GraphDB instance.',
    )

    parser.add_argument(
        '--start-date',
        type=str,
        help='The start date for fetching zaken (YYYY-MM-DD).',
        default='2025-01-01',
    )

    parser.add_argument(
        '--end-date',
        type=str,
        help='The end date for fetching zaken (YYYY-MM-DD).',
        default='2025-12-31',
    )

    return parser.parse_args()


def _upload_graph(g: Graph, url: str) -> None:
    logging.info('Uploading data to GraphDB...')
    data = g.serialize(format='turtle')
    headers = {'Content-Type': 'application/x-turtle'}

    try:
        response = requests.post(url, data=data, headers=headers)
        response.raise_for_status()
        logging.info('Data uploaded successfully to GraphDB.')
    except requests.exceptions.RequestException as e:
        logging.error(f'Error uploading data to GraphDB: {e}')


def _run_scraper(
    start_date: datetime.datetime,
    end_date: datetime.datetime,
) -> tuple[list[Fractie], list[Zaak]]:

    scraper = TkScraper(verbose=False)

    fracties = scraper.get_all_fracties(populate_members=True)
    logging.info('Fetching all zaken of type MOTIE in 2025...')

    zaken = scraper.get_all_zaken(
        # zaak_type=ZaakSoort.MOTIE,
        start_date=start_date,
        end_date=end_date,
    )

    return fracties, zaken


def main() -> int:

    logging.basicConfig(level=logging.INFO)

    args = create_arg_parser()

    start_date = datetime.datetime.strptime(args.start_date, '%Y-%m-%d')
    end_date = datetime.datetime.strptime(args.end_date, '%Y-%m-%d')

    # Run the scraper
    fracties, zaken = _run_scraper(start_date, end_date)

    # Create the graph
    g = Graph()
    g.bind('tk', 'http://www.semanticweb.org/twanh/ontologies/2025/9/tk/')

    for fractie in fracties:
        fractie.to_rdf(g)

    _upload_graph(g, args.graphdb_url)

    for zaak in zaken:
        zaak.to_rdf(g)

    _upload_graph(g, args.graphdb_url)

    return 0


if __name__ == '__main__':

    raise SystemExit(main())
