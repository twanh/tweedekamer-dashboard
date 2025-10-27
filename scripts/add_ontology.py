import argparse
import logging
import os

import requests
from rdflib import Graph
from requests.exceptions import RequestException

# Set up basic logging
logging.basicConfig(level=logging.INFO)


def upload_ontology(graphdb_url: str, ontology_file: str) -> int:

    if not os.path.exists(ontology_file):
        logging.error(
            f'Error: Ontology file not found at path: {ontology_file}',
        )
        return 1

    logging.info(f'Loading ontology from {ontology_file}...')
    g_ontology = Graph()

    try:
        g_ontology.parse(ontology_file, format='turtle')
        logging.info(
            f'Successfully loaded {len(g_ontology)} triples from ontology.',
        )
    except Exception as e:
        logging.error(f'Error parsing ontology file: {e}')
        return 1

    # Ensure the URL is the /statements endpoint
    if not graphdb_url.endswith('/statements'):
        if graphdb_url.endswith('/'):
            graphdb_url = graphdb_url[:-1]  # Remove trailing slash
        graphdb_url += '/statements'
        logging.info(
            f'Appended /statements to URL. Uploading to: {graphdb_url}',
        )

    try:
        data = g_ontology.serialize(format='turtle')
        headers = {'Content-Type': 'application/x-turtle'}

        logging.info(f'Uploading {len(g_ontology)} triples to GraphDB...')

        response = requests.post(graphdb_url, data=data, headers=headers)
        # Check for HTTP errors (4xx or 5xx)
        response.raise_for_status()

    except RequestException as e:
        logging.error(f'HTTP Error uploading data to GraphDB: {e}')
        if e.response is not None:
            logging.error(f'Response body: {e.response.text}')
        return 1
    except Exception as e:
        logging.error(f'An unexpected error occurred: {e}')
        return 1

    logging.info('Ontology uploaded successfully to GraphDB.')
    return 0


def main() -> int:
    # Set up the command-line argument parser
    parser = argparse.ArgumentParser(
        description='Upload a Turtle ontology file to a GraphDB repository.',
    )

    parser.add_argument(
        'graphdb_url',
        type=str,
        help="The URL of the GraphDB repository (e.g., 'http://localhost:7200/repositories/tk_kb')",
    )

    parser.add_argument(
        'ontology_file',
        type=str,
        help="The file path to the .ttl ontology file (e.g., './tweedekamer-ontology.ttl')",
    )

    args = parser.parse_args()

    # Run the upload function with the provided arguments
    return upload_ontology(args.graphdb_url, args.ontology_file)


if __name__ == '__main__':
    raise SystemExit(main())
