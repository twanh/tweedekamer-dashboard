from urllib.parse import unquote

from flask import Flask
from flask import render_template
from SPARQLWrapper import JSON
from SPARQLWrapper import SPARQLWrapper

app = Flask(__name__)


def get_db_results(query):
    # Docker Compose setup (uncomment when using Docker)
    sparql = SPARQLWrapper('http://graphdb:7200/repositories/tk_kb')

    # Localhost for testing without Docker (comment when using Docker)
    # sparql = SPARQLWrapper('http://localhost:7200/repositories/tk_kb')

    sparql.setQuery(query)
    sparql.setReturnFormat(JSON)
    return sparql.query().convert()


@app.route('/')
def index():
    # Example Query: Get all parties and their number of seats
    query = """
    PREFIX tk: <http://www.semanticweb.org/twanh/ontologies/2025/9/tk/>
    SELECT ?fractieNaam ?aantalZetels ?fractieAfko
    WHERE {
        ?fractie a tk:Fractie ;
                 tk:naam ?fractieNaam ;
                 tk:aantalZetels ?aantalZetels ;
                 tk:afkorting ?fractieAfko .
    }
    ORDER BY DESC(?aantalZetels)
    """
    results = get_db_results(query)
    fracties = []
    for result in results['results']['bindings']:
        fracties.append({
            'name': result['fractieNaam']['value'],
            'seats': int(result['aantalZetels']['value']),
            'abbreviation': result['fractieAfko']['value'],
        })
    return render_template('index.html', fracties=fracties)


@app.route('/agreement')
def agreement():
    """This page will show all the agreements between the parties in a cross table."""

    query = """
    PREFIX tk: <http://www.semanticweb.org/twanh/ontologies/2025/9/tk/>

    SELECT
        ?partyA_ab                 # Abbreviation for Party A
        ?partyB_ab                 # Abbreviation for Party B
        (COUNT(?zaak) AS ?commonVotes)  # Total votes where both parties voted 'voor' or 'tegen'
        (SUM(IF(?voteA = ?voteB, 1, 0)) AS ?agreements) # Count of times they voted the same
        (((SUM(IF(?voteA = ?voteB, 1, 0))) * 100.0 / COUNT(?zaak)) AS ?agreementPercentage)
    WHERE {
        ?zaak a tk:Zaak .

        # Get Party A's vote
        { ?partyA tk:heeftVoorGestemd ?zaak . BIND("voor" AS ?voteA) }
        UNION
        { ?partyA tk:heeftTegenGestemd ?zaak . BIND("tegen" AS ?voteA) }
        # Get Party A's abbreviation
        ?partyA a tk:Fractie ;
                tk:afkorting ?partyA_ab .

        # Get Party B's vote on the SAME 'zaak'
        { ?partyB tk:heeftVoorGestemd ?zaak . BIND("voor" AS ?voteB) }
        UNION
        { ?partyB tk:heeftTegenGestemd ?zaak . BIND("tegen" AS ?voteB) }
        # Get Party B's abbreviation
        ?partyB a tk:Fractie ;
                tk:afkorting ?partyB_ab .

        # Filter for unique pairs to avoid calculating both A-B and B-A.
        FILTER(?partyA_ab < ?partyB_ab)
    }
    # Group the results for each unique party pair
    GROUP BY ?partyA_ab ?partyB_ab
    # Order the final list alphabetically
    ORDER BY ?partyA_ab ?partyB_ab
    """

    results = get_db_results(query)
    agreements = []

    for result in results['results']['bindings']:
        agreements.append({
            'partyA_ab': result['partyA_ab']['value'],
            'partyB_ab': result['partyB_ab']['value'],
            'commonVotes': result['commonVotes']['value'],
            'agreements': result['agreements']['value'],
            'agreementPercentage': result['agreementPercentage']['value'],
        })

    # Create a dictionary for quick lookup of agreement percentages
    agreement_dict = {}
    for agreement in agreements:
        key1 = (agreement['partyA_ab'], agreement['partyB_ab'])
        key2 = (agreement['partyB_ab'], agreement['partyA_ab'])
        pct = float(agreement['agreementPercentage'])
        agreement_dict[key1] = pct
        agreement_dict[key2] = pct

    # Get all unique parties
    parties = set()
    for agreement in agreements:
        parties.add(agreement['partyA_ab'])
        parties.add(agreement['partyB_ab'])
    parties = sorted(list(parties))

    # Create the agreement matrix
    agreement_matrix = {}
    for row_party in parties:
        agreement_matrix[row_party] = {}
        for col_party in parties:
            if row_party == col_party:
                agreement_matrix[row_party][col_party] = 100.0
            else:
                key = (row_party, col_party)
                agreement_matrix[row_party][col_party] = agreement_dict.get(
                    key, None,
                )

    return render_template('agreement.html', parties=parties, agreement_matrix=agreement_matrix)


@app.route('/leden')
def leden():
    # Example Query: Get all members and their parties
    query = """
    PREFIX tk: <http://www.semanticweb.org/twanh/ontologies/2025/9/tk/>
    PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>

    SELECT ?persoon ?persoonNaam ?fractieAfko
    WHERE {
      ?persoon a tk:Persoon .
      ?persoon tk:naam ?persoonNaam .
      OPTIONAL {
        ?persoon tk:isLidVan ?fractie .
        ?fractie tk:afkorting ?fractieAfko .
      }
    }
    ORDER BY ?fractieNaam ?persoonNaam
    """

    results = get_db_results(query)
    leden = []

    for result in results['results']['bindings']:
        leden.append({
            'name': result['persoonNaam']['value'],
            'party': result.get('fractieAfko', {}).get('value', 'Onbekend'),
        })
    return render_template('leden.html', leden=leden)


@app.route('/fractie/<path:fractie_naam>')
def fractie_detail(fractie_naam):
    # Decode the URL-encoded party name
    decoded_fractie_naam = unquote(fractie_naam)

    # SPARQL query to get members and voting statistics for a specific party
    query = f"""
    PREFIX tk: <http://www.semanticweb.org/twanh/ontologies/2025/9/tk/>

    SELECT ?persoonNaam (COUNT(DISTINCT ?zaakVoor) AS ?stemmenVoor) (COUNT(DISTINCT ?zaakTegen) AS ?stemmenTegen) (COUNT(DISTINCT ?zaakNietDeelgenomen) AS ?stemmenNietDeelgenomen)
    WHERE {{
      # Find the fractie by name
      ?fractie a tk:Fractie ;
               tk:naam "{decoded_fractie_naam}" .

      # Get all members of this fractie
      ?fractie tk:heeftLid ?persoon .
      ?persoon tk:naam ?persoonNaam .

      # OPTIONAL blocks to count votes in each category
      OPTIONAL {{ ?fractie tk:heeftVoorGestemd ?zaakVoor . }}
      OPTIONAL {{ ?fractie tk:heeftTegenGestemd ?zaakTegen . }}
      OPTIONAL {{ ?fractie tk:heeftNietDeelgenomen ?zaakNietDeelgenomen . }}
    }}
    GROUP BY ?persoonNaam
    ORDER BY ?persoonNaam
    """

    results = get_db_results(query)

    leden = []
    # Initialize vote_counts; we only need one set of counts for the whole party
    vote_counts = {
        'voor': 0,
        'tegen': 0,
        'niet_deelgenomen': 0,
    }

    bindings = results['results']['bindings']
    if bindings:
        # Since the vote counts are the same for every member of the party,
        # we can just take the counts from the first result.
        first_result = bindings[0]
        vote_counts['voor'] = int(first_result['stemmenVoor']['value'])
        vote_counts['tegen'] = int(first_result['stemmenTegen']['value'])
        vote_counts['niet_deelgenomen'] = int(
            first_result['stemmenNietDeelgenomen']['value'],
        )

        # Get the list of all members
        for result in bindings:
            leden.append(result['persoonNaam']['value'])

    return render_template(
        'fractie.html',
        fractie_naam=decoded_fractie_naam,
        leden=leden,
        vote_counts=vote_counts,  # Pass the vote counts to the template
    )


@app.route('/zaken')
def zaken():
    # Example Query: Get all zaken with their titles and onderwerpen
    query = """
    SELECT ?zaak ?titel ?beschrijving ?besluitResultaat ?besluitStemmingsoort ?dossierNummer ?indieningsDatum
       ?isAfgedaan ?kabinetsappreciatie ?nummer ?termijn ?uuid ?volgnummer ?zaakSoort ?title
    WHERE {
    ?zaak a tk:Zaak .

    OPTIONAL { ?zaak tk:titel ?titel . }
    OPTIONAL { ?zaak tk:beschrijving ?beschrijving . }
    OPTIONAL { ?zaak tk:besluitResultaat ?besluitResultaat . }
    OPTIONAL { ?zaak tk:besluitStemmingsoort ?besluitStemmingsoort . }
    OPTIONAL { ?zaak tk:dossierNummer ?dossierNummer . }
    OPTIONAL { ?zaak tk:indieningsDatum ?indieningsDatum . }
    OPTIONAL { ?zaak tk:isAfgedaan ?isAfgedaan . }
    OPTIONAL { ?zaak tk:kabinetsappreciatie ?kabinetsappreciatie . }
    OPTIONAL { ?zaak tk:nummer ?nummer . }
    OPTIONAL { ?zaak tk:termijn ?termijn . }
    OPTIONAL { ?zaak tk:uuid ?uuid . }
    OPTIONAL { ?zaak tk:volgnummer ?volgnummer . }
    OPTIONAL { ?zaak tk:zaakSoort ?zaakSoort . }
    }

    """

    results = get_db_results(query)
    zaken = []

    for result in results['results']['bindings']:
        zaken.append({
            'titel': result.get('titel', {}).get('value', 'Geen titel gevonden.'),
            'beschrijving': result.get('beschrijving', {}).get('value', 'Geen beschrijving gevonden.'),
            'besluitResultaat': result.get('besluitResultaat', {}).get('value', 'Geen besluitResultaat gevonden.'),
            'besluitStemmingsoort': result.get('besluitStemmingsoort', {}).get('value', 'Geen besluitStemmingsoort gevonden.'),
            'dossierNummer': result.get('dossierNummer', {}).get('value', 'Geen dossierNummer gevonden.'),
            'indieningsDatum': result.get('indieningsDatum', {}).get('value', 'Geen indieningsDatum gevonden.'),
            'isAfgedaan': result.get('isAfgedaan', {}).get('value', 'Geen isAfgedaan gevonden.'),
            'kabinetsappreciatie': result.get('kabinetsappreciatie', {}).get('value', 'Geen kabinetsappreciatie gevonden.'),
            'nummer': result.get('nummer', {}).get('value', 'Geen nummer gevonden.'),
            'termijn': result.get('termijn', {}).get('value', 'Geen termijn gevonden.'),
            'uuid': result.get('uuid', {}).get('value', 'Geen uuid gevonden.'),
            'volgnummer': result.get('volgnummer', {}).get('value', 'Geen volgnummer gevonden.'),
            'zaakSoort': result.get('zaakSoort', {}).get('value', 'Geen zaakSoort gevonden.'),
        })

    return render_template('zaken.html', zaken=zaken)


if __name__ == '__main__':
    # Docker Compose setup (uncomment when using Docker)
    app.run(host='0.0.0.0', debug=True)

    # Localhost with specified port (for Macbook compatibility since port 5000 is sometimes in use), comment when using Docker
    # app.run(host='0.0.0.0', port=8000, debug=True)
