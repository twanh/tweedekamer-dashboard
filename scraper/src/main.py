import datetime
import logging

import requests
from models import ZaakSoort
from rdflib import Graph

from scraper import TkScraper


def _upload_graph(g: Graph, url: str) -> None:
    logging.info('Uploading data to GraphDB...')
    data = g.serialize(format='turtle')
    headers = {'Content-Type': 'application/x-turtle'}
    # url = f"{os.environ.get('GRAPHDB_URL')}/repositories/tk_repo/statements"

    try:
        response = requests.post(url, data=data, headers=headers)
        response.raise_for_status()
        logging.info('Data uploaded successfully to GraphDB.')
    except requests.exceptions.RequestException as e:
        logging.error(f'Error uploading data to GraphDB: {e}')


def main() -> int:

    logging.basicConfig(level=logging.INFO)

    scraper = TkScraper(verbose=False)

    # Create the graph
    g = Graph()
    g.bind('tk', 'http://www.semanticweb.org/twanh/ontologies/2025/9/tk/')

    # TODO: Scrape everything
    fracties = scraper.get_all_fracties(populate_members=True)

    print(fracties)

    # Get zaken
    logging.info('Fetching all zaken of type MOTIE in 2025...')

    zaken = scraper.get_all_zaken(
        zaak_type=ZaakSoort.MOTIE,
        start_date=datetime.datetime(2025, 1, 14),
        end_date=datetime.datetime(2025, 1, 15),
    )

    print(zaken)

    # _upload_graph(
    #     g,
    #     f'{os.environ.get("GRAPHDB_URL")}/repositories/tk_repo/statements',
    # )

    return 0


if __name__ == '__main__':

    raise SystemExit(main())
