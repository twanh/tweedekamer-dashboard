import argparse
import datetime
import logging
import os
import time

import requests
from models import Zaak
from models import ZaakSoort
from rdflib import Graph
from requests.exceptions import JSONDecodeError

from scraper import TkScraper

# RETRY CONFIG
MAX_RETRIES = 3
RETRY_DELAY = 5  # seconds


def create_arg_parser():
    """
    Create the argument parser for the script.
    """

    parser = argparse.ArgumentParser(
        description='Scrape data from the TK API and upload it to GraphDB.',
    )
    parser.add_argument(
        '--graphdb-url',
        type=str,
        default=os.environ.get(
            'GRAPHDB_URL',
            'http://localhost:7200/repositories/tk_kb/statements',
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

    parser.add_argument(
        '--disable-topic-classification',
        action='store_true',
        help='Disable topic classification for zaken.',
    )

    return parser.parse_args()


def _upload_graph(g: Graph, url: str) -> None:
    """Upload the RDF graph to the GraphDB instance."""

    logging.info('Uploading data to GraphDB...')
    data = g.serialize(format='turtle')
    headers = {'Content-Type': 'application/x-turtle'}

    try:
        response = requests.post(url, data=data, headers=headers)
        response.raise_for_status()
        logging.info('Data uploaded successfully to GraphDB.')
    except requests.exceptions.RequestException as e:
        logging.error(f'Error uploading data to GraphDB: {e}')


def _scrape_zaken(
    scraper: TkScraper,
    start_date: datetime.datetime,
    end_date: datetime.datetime,
    zaak_soort: ZaakSoort = ZaakSoort.MOTIE,
    classify_topics: bool = True,
) -> list[Zaak]:
    """
    Scrape zaken of a specific type within a date range,
    with retries on failure.
    """

    logging.info(
        f'Scraping zaken ({zaak_soort}) from {start_date} to {end_date}',
    )

    for attempt in range(MAX_RETRIES):
        try:

            logging.info(f'Fetching zaken (Attempt {attempt + 1})...')

            zaken = scraper.get_all_zaken(
                zaak_type=zaak_soort,
                start_date=start_date,
                end_date=end_date,
                classify_topics=classify_topics,
            )
            return zaken

        except JSONDecodeError as e:
            logging.error(f'JSON decode error fetching zaken: {e}')
            logging.info(f'Retrying in {RETRY_DELAY} seconds...')
            time.sleep(RETRY_DELAY)

        except Exception as e:
            logging.error(f'Error fetching zaken: {e}')
            logging.info(f'Retrying in {RETRY_DELAY} seconds...')
            time.sleep(RETRY_DELAY)

    logging.error('Failed to fetch zaken after multiple attempts.')
    return []


def main() -> int:

    logging.basicConfig(level=logging.INFO)

    args = create_arg_parser()

    start_date = datetime.datetime.strptime(args.start_date, '%Y-%m-%d')
    end_date = datetime.datetime.strptime(args.end_date, '%Y-%m-%d')

    # Initialize the scraper and the graph
    scraper = TkScraper(verbose=False)
    g = Graph()
    g.bind('tk', 'http://www.semanticweb.org/twanh/ontologies/2025/9/tk/')

    # Run the scraper

    # First scrape all the fracties
    fracties = []
    for attempt in range(MAX_RETRIES):
        try:
            logging.info(f'Fetching all fracties (Attempt {attempt + 1})...')
            fracties = scraper.get_all_fracties(populate_members=True)
            break
        except Exception as e:
            logging.error(f'Error fetching fracties: {e}')
            logging.info(f'Retrying in {RETRY_DELAY} seconds...')
            time.sleep(RETRY_DELAY)

    if not fracties:
        logging.error('Failed to fetch fracties after multiple attempts.')
        return 1

    # Add fracties to the graph
    for fractie in fracties:
        fractie.to_rdf(g)

    # Update the graphdb
    _upload_graph(g, args.graphdb_url)

    # Scrape zaken day by day based on the start and end date
    current_date = start_date
    n_zaken = 0
    while current_date <= end_date:

        logging.info(f'Scraping zaken for date: {current_date.date()}')
        next_date = current_date + datetime.timedelta(days=1)

        zaak_types = [
            ZaakSoort.MOTIE,
            ZaakSoort.AMENDEMENT,
            ZaakSoort.WETSVOORSTEL,
            ZaakSoort.INITIATIEF_WETGEVING,
        ]

        for zaak_type in zaak_types:
            logging.info(f'Scraping zaken of type: {zaak_type}')

            zaken = _scrape_zaken(
                scraper,
                current_date,
                next_date,
                zaak_type,
                classify_topics=not args.disable_topic_classification,
            )

            n_zaken += len(zaken)

            for zaak in zaken:
                zaak.to_rdf(g)

        # Upload the graph after each day's scraping
        _upload_graph(g, args.graphdb_url)

        # Move to the next date
        current_date = next_date

    logging.info('Scraping and uploading completed successfully.')
    logging.info(f'Total fracties scraped: {len(fracties)}')
    logging.info(f'Total zaken scraped: {n_zaken}')

    return 0


if __name__ == '__main__':

    raise SystemExit(main())
