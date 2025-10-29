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

    # Query to get number of zaken per month per zaak type
    zaken_per_type_query = """
    PREFIX tk: <http://www.semanticweb.org/twanh/ontologies/2025/9/tk/>
    PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
    PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
    PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>

    SELECT ?jaar ?maand ?zaakSoort (COUNT(DISTINCT ?zaak) AS ?aantal)
    WHERE {
      # Any subclass instance of Zaak
      ?zaak rdf:type ?zaakType .
      ?zaakType rdfs:subClassOf* tk:Zaak .

      # The data property representing the zaak type label
      ?zaak tk:zaakSoort ?zaakSoort .

      # Submission date
      ?zaak tk:indieningsDatum ?datum .

      # Extract year and month
      BIND(YEAR(?datum) AS ?jaar)
      BIND(MONTH(?datum) AS ?maand)
    }
    GROUP BY ?jaar ?maand ?zaakSoort
    ORDER BY ?jaar ?maand ?zaakSoort
    """

    zaken_per_type_results = get_db_results(zaken_per_type_query)
    zaken_per_type_per_month = []
    for result in zaken_per_type_results['results']['bindings']:
        jaar = int(result['jaar']['value'])
        maand = int(result['maand']['value'])
        soort = result['zaakSoort']['value']
        aantal = int(result['aantal']['value'])
        zaken_per_type_per_month.append({
            'jaar': jaar,
            'maand': maand,
            'type': soort,
            'aantal': aantal,
        })

    topics_over_time_query = """
    PREFIX tk: <http://www.semanticweb.org/twanh/ontologies/2025/9/tk/>
    PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
    PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>

    # Select the time (year, month), the category (topicName), and the value (aantalZaken)
    SELECT ?jaar ?maand ?topicName (COUNT(DISTINCT ?zaak) AS ?aantalZaken)
    WHERE {
    # Find a Zaak that is linked to a topic (Onderwerp)
    ?zaak tk:heeftOnderwerp ?onderwerp .

    # Get the human-readable name of that topic
    ?onderwerp tk:onderwerpType ?topicName .

    # Get the submission date of the Zaak
    ?zaak tk:indieningsDatum ?datum .

    # Extract Year and Month for grouping
    BIND(YEAR(?datum) AS ?jaar)
    BIND(MONTH(?datum) AS ?maand)
    }
    # Group by all three variables to get the count *per topic* *per month*
    GROUP BY ?jaar ?maand ?topicName

    # Order chronologically, then by topic name for a consistent stack order
    ORDER BY ?jaar ?maand ?topicName
    """

    # Execute the SPARQL query to get topics over time
    topics_results = get_db_results(topics_over_time_query)

    topics_per_month = []
    for result in topics_results['results']['bindings']:
        jaar = int(result['jaar']['value'])
        maand = int(result['maand']['value'])
        topic = result['topicName']['value']
        aantal = int(result['aantalZaken']['value'])
        topics_per_month.append({
            'jaar': jaar,
            'maand': maand,
            'topic': topic,
            'aantal': aantal,
        })

    return render_template(
        'index.html',
        topics_per_month=topics_per_month,
        zaken_per_type_per_month=zaken_per_type_per_month,
    )


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


@app.route('/fracties')
def fracties():
    # Get all parties and their number of seats
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
    return render_template('fracties.html', fracties=fracties)


@app.route('/fractie/<path:fractie_naam>')
def fractie_detail(fractie_naam):
    # Decode the URL-encoded party name
    decoded_fractie_naam = unquote(fractie_naam)

    # This corrected query uses only the BIND method to define the count variables
    query = f"""
    PREFIX tk: <http://www.semanticweb.org/twanh/ontologies/2025/9/tk/>

    SELECT ?onderwerpType (COUNT(DISTINCT ?zaakVoor) AS ?stemmenVoor) (COUNT(DISTINCT ?zaakTegen) AS ?stemmenTegen) (COUNT(DISTINCT ?zaakNietDeelgenomen) AS ?stemmenNietDeelgenomen)
    WHERE {{
      # Find the fractie by name
      ?fractie a tk:Fractie ;
               tk:naam "{decoded_fractie_naam}" .

      # Use a VALUES block to define the vote types we are interested in
      VALUES ?voteProperty {{ tk:heeftVoorGestemd tk:heeftTegenGestemd tk:heeftNietDeelgenomen }}

      # Find all zaken the fractie has voted on
      ?fractie ?voteProperty ?zaak .

      # Get the onderwerp for each zaak
      ?zaak tk:heeftOnderwerp ?onderwerp .
      ?onderwerp tk:onderwerpType ?onderwerpType .

      # Use BIND to conditionally link zaken to vote types for counting.
      # This is the single, correct place to define these variables.
      BIND(IF(?voteProperty = tk:heeftVoorGestemd, ?zaak, 1/0) AS ?zaakVoor)
      BIND(IF(?voteProperty = tk:heeftTegenGestemd, ?zaak, 1/0) AS ?zaakTegen)
      BIND(IF(?voteProperty = tk:heeftNietDeelgenomen, ?zaak, 1/0) AS ?zaakNietDeelgenomen)
    }}
    GROUP BY ?onderwerpType
    ORDER BY ?onderwerpType
    """

    results = get_db_results(query)

    onderwerp_votes = {}
    total_votes = {'voor': 0, 'tegen': 0, 'niet_deelgenomen': 0}

    for result in results['results']['bindings']:
        onderwerp = result['onderwerpType']['value']
        voor = int(result['stemmenVoor']['value'])
        tegen = int(result['stemmenTegen']['value'])
        niet_deelgenomen = int(result['stemmenNietDeelgenomen']['value'])

        onderwerp_votes[onderwerp] = {
            'voor': voor,
            'tegen': tegen,
            'niet_deelgenomen': niet_deelgenomen,
        }

        total_votes['voor'] += voor
        total_votes['tegen'] += tegen
        total_votes['niet_deelgenomen'] += niet_deelgenomen

    leden_query = f"""
    PREFIX tk: <http://www.semanticweb.org/twanh/ontologies/2025/9/tk/>
    SELECT ?persoonNaam WHERE {{
      ?fractie tk:naam "{decoded_fractie_naam}" ;
               tk:heeftLid ?persoon .
      ?persoon tk:naam ?persoonNaam .
    }} ORDER BY ?persoonNaam
    """
    leden_results = get_db_results(leden_query)
    leden = [
        res['persoonNaam']['value']
        for res in leden_results['results']['bindings']
    ]

    return render_template(
        'fractie.html',
        fractie_naam=decoded_fractie_naam,
        leden=leden,
        total_votes=total_votes,
        onderwerp_votes=onderwerp_votes,
    )


@app.route('/zaken')
def zaken_lijst():
    # Query to get all zaken with their description and result
    query = """
    PREFIX tk: <http://www.semanticweb.org/twanh/ontologies/2025/9/tk/>
    SELECT ?zaakNummer ?beschrijving ?besluitResultaat
    WHERE {
        ?zaak a tk:Zaak ;
              tk:nummer ?zaakNummer ;
              tk:beschrijving ?beschrijving .
        OPTIONAL { ?zaak tk:besluitResultaat ?besluitResultaat . }
    }
    ORDER BY ?zaakNummer
    """
    results = get_db_results(query)
    zaken = []
    for result in results['results']['bindings']:
        zaken.append({
            'nummer': result['zaakNummer']['value'],
            'beschrijving': result['beschrijving']['value'],
            'resultaat': result.get('besluitResultaat', {}).get('value', 'Nog niet bekend'),
        })
    return render_template('zaken.html', zaken=zaken)


@app.route('/zaak/<path:zaak_nummer>')
def zaak_detail(zaak_nummer):
    # Decode the zaak nummer
    decoded_zaak_nummer = unquote(zaak_nummer)

    # Query to get the voting record of each party for a specific zaak
    query = f"""
    PREFIX tk: <http://www.semanticweb.org/twanh/ontologies/2025/9/tk/>
    SELECT ?fractieNaam (SUM(?voor) AS ?stemmenVoor) (SUM(?tegen) AS ?stemmenTegen) (SUM(?nietDeelgenomen) AS ?stemmenNietDeelgenomen) ?beschrijving ?besluitResultaat
    WHERE {{
      ?zaak tk:nummer "{decoded_zaak_nummer}" ;
            tk:beschrijving ?beschrijving .
      OPTIONAL {{ ?zaak tk:besluitResultaat ?besluitResultaat . }}

      ?fractie a tk:Fractie ;
               tk:naam ?fractieNaam .

      # Use BIND to check vote for each fractie and assign a 1 or 0
      BIND(IF(EXISTS {{ ?fractie tk:heeftVoorGestemd ?zaak }}, 1, 0) AS ?voor)
      BIND(IF(EXISTS {{ ?fractie tk:heeftTegenGestemd ?zaak }}, 1, 0) AS ?tegen)
      BIND(IF(EXISTS {{ ?fractie tk:heeftNietDeelgenomen ?zaak }}, 1, 0) AS ?nietDeelgenomen)
    }}
    GROUP BY ?fractieNaam ?beschrijving ?besluitResultaat
    ORDER BY ?fractieNaam
    """
    results = get_db_results(query)

    stemmingen = []
    zaak_info = {}
    bindings = results['results']['bindings']

    if bindings:
        # Get zaak info from the first result
        zaak_info = {
            'beschrijving': bindings[0]['beschrijving']['value'],
            'resultaat': bindings[0].get('besluitResultaat', {}).get('value', 'Nog niet bekend'),
        }
        # Get voting data for each party
        for result in bindings:
            stemmingen.append({
                'fractie': result['fractieNaam']['value'],
                'voor': int(result['stemmenVoor']['value']),
                'tegen': int(result['stemmenTegen']['value']),
                'niet_deelgenomen': int(result['stemmenNietDeelgenomen']['value']),
            })

    return render_template('zaak_detail.html', zaak_info=zaak_info, stemmingen=stemmingen)

# @app.route('/zaken')
# def zaken():
#     # Example Query: Get all zaken with their titles and onderwerpen
#     query = """
#     SELECT ?zaak ?titel ?beschrijving ?besluitResultaat ?besluitStemmingsoort ?dossierNummer ?indieningsDatum
#        ?isAfgedaan ?kabinetsappreciatie ?nummer ?termijn ?uuid ?volgnummer ?zaakSoort ?title
#     WHERE {
#     ?zaak a tk:Zaak .

#     OPTIONAL { ?zaak tk:titel ?titel . }
#     OPTIONAL { ?zaak tk:beschrijving ?beschrijving . }
#     OPTIONAL { ?zaak tk:besluitResultaat ?besluitResultaat . }
#     OPTIONAL { ?zaak tk:besluitStemmingsoort ?besluitStemmingsoort . }
#     OPTIONAL { ?zaak tk:dossierNummer ?dossierNummer . }
#     OPTIONAL { ?zaak tk:indieningsDatum ?indieningsDatum . }
#     OPTIONAL { ?zaak tk:isAfgedaan ?isAfgedaan . }
#     OPTIONAL { ?zaak tk:kabinetsappreciatie ?kabinetsappreciatie . }
#     OPTIONAL { ?zaak tk:nummer ?nummer . }
#     OPTIONAL { ?zaak tk:termijn ?termijn . }
#     OPTIONAL { ?zaak tk:uuid ?uuid . }
#     OPTIONAL { ?zaak tk:volgnummer ?volgnummer . }
#     OPTIONAL { ?zaak tk:zaakSoort ?zaakSoort . }
#     }

#     """

#     results = get_db_results(query)
#     zaken = []

#     for result in results['results']['bindings']:
#         zaken.append({
#             'titel': result.get('titel', {}).get('value', 'Geen titel gevonden.'),
#             'beschrijving': result.get('beschrijving', {}).get('value', 'Geen beschrijving gevonden.'),
#             'besluitResultaat': result.get('besluitResultaat', {}).get('value', 'Geen besluitResultaat gevonden.'),
#             'besluitStemmingsoort': result.get('besluitStemmingsoort', {}).get('value', 'Geen besluitStemmingsoort gevonden.'),
#             'dossierNummer': result.get('dossierNummer', {}).get('value', 'Geen dossierNummer gevonden.'),
#             'indieningsDatum': result.get('indieningsDatum', {}).get('value', 'Geen indieningsDatum gevonden.'),
#             'isAfgedaan': result.get('isAfgedaan', {}).get('value', 'Geen isAfgedaan gevonden.'),
#             'kabinetsappreciatie': result.get('kabinetsappreciatie', {}).get('value', 'Geen kabinetsappreciatie gevonden.'),
#             'nummer': result.get('nummer', {}).get('value', 'Geen nummer gevonden.'),
#             'termijn': result.get('termijn', {}).get('value', 'Geen termijn gevonden.'),
#             'uuid': result.get('uuid', {}).get('value', 'Geen uuid gevonden.'),
#             'volgnummer': result.get('volgnummer', {}).get('value', 'Geen volgnummer gevonden.'),
#             'zaakSoort': result.get('zaakSoort', {}).get('value', 'Geen zaakSoort gevonden.'),
#         })

#     return render_template('zaken.html', zaken=zaken)


if __name__ == '__main__':
    # Docker Compose setup (uncomment when using Docker)
    app.run(host='0.0.0.0', debug=True)

    # Localhost with specified port (for Macbook compatibility since port 5000 is sometimes in use), comment when using Docker
    # app.run(host='0.0.0.0', port=8000, debug=True)
