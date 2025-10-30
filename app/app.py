from urllib.parse import unquote

from flask import Flask
from flask import render_template
from flask import request
from SPARQLWrapper import JSON
from SPARQLWrapper import SPARQLWrapper

app = Flask(__name__)


def get_db_results(query):
    """Get results from the GraphDB database."""

    # Docker Compose setup (uncomment when using Docker)
    sparql = SPARQLWrapper('http://graphdb:7200/repositories/tk_kb')

    sparql.setQuery(query)
    sparql.setReturnFormat(JSON)

    return sparql.query().convert()


def get_wikidata_results(query):
    """Get results from the Wikidata SPARQL endpoint."""

    sparql = SPARQLWrapper('https://query.wikidata.org/sparql')

    sparql.setQuery(query)
    sparql.setReturnFormat(JSON)

    return sparql.query().convert()


@app.route('/')
def index():
    """Render the index page.

    Index page shows: 
        - Number of zaken per month per zaak type
        - Number of zaken per month per topic
        - Stemgedrag per party (Voor/Tegen/Niet Deelgenomen)
        - Aangenomen vs Verworpen per topic
    """

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
    # We transform the results from the queries to a better format for the frontend
    zaken_per_type_per_month = []
    # For each result, add a new entry to the zaken_per_type_per_month list

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

    # Query to get number of zaken per month per topic
    topics_over_time_query = """
    PREFIX tk: <http://www.semanticweb.org/twanh/ontologies/2025/9/tk/>
    PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
    PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>

    SELECT ?jaar ?maand ?topicName (COUNT(DISTINCT ?zaak) AS ?aantalZaken)
    WHERE {

    ?zaak tk:heeftOnderwerp ?onderwerp .
    ?onderwerp tk:onderwerpType ?topicName .
    ?zaak tk:indieningsDatum ?datum .

    BIND(YEAR(?datum) AS ?jaar)
    BIND(MONTH(?datum) AS ?maand)
    }
    GROUP BY ?jaar ?maand ?topicName
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

    # Stemgedrag partijen voor/tegen/onthouden
    vote_behaviour_parties_qeury = """
    PREFIX tk: <http://www.semanticweb.org/twanh/ontologies/2025/9/tk/>
    PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>

    SELECT ?partijNaam ?stemSoort (COUNT(?zaak) AS ?aantalStemmen)
    WHERE {
    {
        ?partij rdf:type tk:Fractie ;
                tk:heeftVoorGestemd ?zaak .
        BIND("Voor" AS ?stemSoort)
    }
    UNION
    {
        ?partij rdf:type tk:Fractie ;
                tk:heeftTegenGestemd ?zaak .
        BIND("Tegen" AS ?stemSoort)
    }
    UNION
    {
        ?partij rdf:type tk:Fractie ;
                tk:heeftNietDeelgenomen ?zaak .
        BIND("Niet Deelgenomen" AS ?stemSoort)
    }

    # Get the party's afkorting for the label
    ?partij tk:afkorting ?partijNaam .
    }
    GROUP BY ?partijNaam ?stemSoort
    ORDER BY ?partijNaam ?stemSoort
    """
    vote_behaviour_parties_results = get_db_results(
        vote_behaviour_parties_qeury,
    )

    partijen_votes = {}
    for result in vote_behaviour_parties_results['results']['bindings']:
        partij = result['partijNaam']['value']
        stem_soort = result['stemSoort']['value']
        aantal = int(result['aantalStemmen']['value'])
        if partij not in partijen_votes:
            partijen_votes[partij] = {
                'Voor': 0,
                'Tegen': 0,
                'Niet Deelgenomen': 0,
            }
        partijen_votes[partij][stem_soort] = aantal

    # Flatten the data to make the rendring on the frontend easier
    partij_vote_behaviour = []
    for partij, stem_gedrag in partijen_votes.items():
        entry = {
            'partij': partij,
            'Voor': stem_gedrag.get('Voor', 0),
            'Tegen': stem_gedrag.get('Tegen', 0),
            'Niet Deelgenomen': stem_gedrag.get('Niet Deelgenomen', 0),
        }
        partij_vote_behaviour.append(entry)

    zaak_acceptance_per_topic_query = """
    PREFIX tk: <http://www.semanticweb.org/twanh/ontologies/2025/9/tk/>
    PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>

    # For each topic: count how many were 'Stemmen - aangenomen' vs 'Stemmen - verworpen'
    SELECT ?topicName ?resultaat (COUNT(DISTINCT ?zaak) AS ?aantalZaken)
    WHERE {
        ?zaak tk:besluitResultaat ?resultaat ;
              tk:heeftOnderwerp ?onderwerp .
        ?onderwerp tk:onderwerpType ?topicName .
        FILTER(?resultaat IN ("Stemmen - aangenomen", "Stemmen - verworpen"))
    }
    GROUP BY ?topicName ?resultaat
    ORDER BY ?topicName ?resultaat
    """

    zaak_acceptance_per_topic_results = get_db_results(
        zaak_acceptance_per_topic_query,
    )

    # Transform results for frontend: normalize raw labels and aggregate per topic
    acceptance_by_topic = {}
    for result in zaak_acceptance_per_topic_results['results']['bindings']:
        topic = result['topicName']['value']
        raw_result = result['resultaat']['value']
        aantal = int(result['aantalZaken']['value'])

        if raw_result == 'Stemmen - aangenomen':
            norm_label = 'Aangenomen'
        elif raw_result == 'Stemmen - verworpen':
            norm_label = 'Verworpen'
        else:
            # Skip any other outcomes
            continue

        if topic not in acceptance_by_topic:
            acceptance_by_topic[topic] = {
                'topic': topic, 'Aangenomen': 0, 'Verworpen': 0,
            }
        acceptance_by_topic[topic][norm_label] += aantal

    zaak_acceptance = list(acceptance_by_topic.values())

    return render_template(
        'index.html',
        topics_per_month=topics_per_month,
        zaken_per_type_per_month=zaken_per_type_per_month,
        partij_vote_behaviour=partij_vote_behaviour,
        zaak_topic_acceptance=zaak_acceptance,
    )


@app.route('/agreement')
def agreement():
    """This page will show all the agreements between the parties in a cross table, and adds crosstables per topic."""

    # Get global cross-table for all zaken
    query = """
    PREFIX tk: <http://www.semanticweb.org/twanh/ontologies/2025/9/tk/>

    SELECT
        ?partyA_ab
        ?partyB_ab
        (COUNT(?zaak) AS ?commonVotes)
        (SUM(IF(?voteA = ?voteB, 1, 0)) AS ?agreements)
        (((SUM(IF(?voteA = ?voteB, 1, 0))) * 100.0 / COUNT(?zaak)) AS ?agreementPercentage)
    WHERE {
        ?zaak a tk:Zaak .

        { ?partyA tk:heeftVoorGestemd ?zaak . BIND("voor" AS ?voteA) }
        UNION
        { ?partyA tk:heeftTegenGestemd ?zaak . BIND("tegen" AS ?voteA) }
        ?partyA a tk:Fractie ;
                tk:afkorting ?partyA_ab .

        { ?partyB tk:heeftVoorGestemd ?zaak . BIND("voor" AS ?voteB) }
        UNION
        { ?partyB tk:heeftTegenGestemd ?zaak . BIND("tegen" AS ?voteB) }
        ?partyB a tk:Fractie ;
                tk:afkorting ?partyB_ab .

        FILTER(?partyA_ab < ?partyB_ab)
    }
    GROUP BY ?partyA_ab ?partyB_ab
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

    agreement_dict = {}
    for agreement in agreements:
        key1 = (agreement['partyA_ab'], agreement['partyB_ab'])
        key2 = (agreement['partyB_ab'], agreement['partyA_ab'])
        pct = float(agreement['agreementPercentage'])
        agreement_dict[key1] = pct
        agreement_dict[key2] = pct

    parties = set()
    for agreement in agreements:
        parties.add(agreement['partyA_ab'])
        parties.add(agreement['partyB_ab'])
    parties = sorted(list(parties))

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

    # Get cross-table for each topic
    topic_query = """
    PREFIX tk: <http://www.semanticweb.org/twanh/ontologies/2025/9/tk/>
    SELECT ?topic ?partyA_ab ?partyB_ab (COUNT(?zaak) AS ?commonVotes) (SUM(IF(?voteA = ?voteB, 1, 0)) AS ?agreements)
           (((SUM(IF(?voteA = ?voteB, 1, 0))) * 100.0 / COUNT(?zaak)) AS ?agreementPercentage)
    WHERE {
      ?zaak a tk:Zaak ;
            tk:heeftOnderwerp ?onderwerp .
      ?onderwerp tk:onderwerpType ?topic .
      { ?partyA tk:heeftVoorGestemd ?zaak . BIND("voor" AS ?voteA) }
      UNION
      { ?partyA tk:heeftTegenGestemd ?zaak . BIND("tegen" AS ?voteA) }
      ?partyA a tk:Fractie ; tk:afkorting ?partyA_ab .
      { ?partyB tk:heeftVoorGestemd ?zaak . BIND("voor" AS ?voteB) }
      UNION
      { ?partyB tk:heeftTegenGestemd ?zaak . BIND("tegen" AS ?voteB) }
      ?partyB a tk:Fractie ; tk:afkorting ?partyB_ab .
      FILTER(?partyA_ab < ?partyB_ab)
    }
    GROUP BY ?topic ?partyA_ab ?partyB_ab
    ORDER BY ?topic ?partyA_ab ?partyB_ab
    """
    topic_results = get_db_results(topic_query)

    # We transform the results from the queries to a better format for the frontend
    topic_agreement = {}
    all_topics = set()
    for res in topic_results['results']['bindings']:
        topic = res['topic']['value']
        partyA = res['partyA_ab']['value']
        partyB = res['partyB_ab']['value']
        pct = float(res['agreementPercentage']['value'])
        all_topics.add(topic)
        if topic not in topic_agreement:
            topic_agreement[topic] = {}
        topic_agreement[topic][(partyA, partyB)] = pct
        topic_agreement[topic][(partyB, partyA)] = pct
    all_topics = sorted(list(all_topics))

    topic_agreement_tables = {}
    for topic in all_topics:
        topic_matrix = {}
        for row_party in parties:
            topic_matrix[row_party] = {}
            for col_party in parties:
                if row_party == col_party:
                    topic_matrix[row_party][col_party] = 100.0
                else:
                    pct = topic_agreement.get(topic, {}).get(
                        (row_party, col_party), None,
                    )
                    topic_matrix[row_party][col_party] = pct
        topic_agreement_tables[topic] = topic_matrix

    return render_template(
        'agreement.html',
        parties=parties,
        agreement_matrix=agreement_matrix,
        topic_agreement_tables=topic_agreement_tables,
        all_topics=all_topics,
    )


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

    decoded_fractie_naam = unquote(fractie_naam)

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

    # Fetch Wikidata info for this fractie by Dutch label
    wikidata_query = f"""
    PREFIX wd: <http://www.wikidata.org/entity/>
    PREFIX wdt: <http://www.wikidata.org/prop/direct/>
    PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
    PREFIX wikibase: <http://wikiba.se/ontology#>
    PREFIX bd: <http://www.bigdata.com/rdf#>

    SELECT ?item ?itemLabel ?shortName ?website ?inception ?memberCount ?ideology ?ideologyLabel WHERE {{
      ?item wdt:P31 wd:Q7278 ;  # instance of political party
            rdfs:label "{decoded_fractie_naam}"@nl .
      OPTIONAL {{ ?item wdt:P1813 ?shortName . }}
      OPTIONAL {{ ?item wdt:P856 ?website . }}
      OPTIONAL {{ ?item wdt:P571 ?inception . }}
      OPTIONAL {{ ?item wdt:P2124 ?memberCount . }}
      OPTIONAL {{
        ?item wdt:P1142 ?ideology .
      }}
      SERVICE wikibase:label {{
        bd:serviceParam wikibase:language "nl,en" .
      }}
    }}
    LIMIT 1
    """

    wikidata_res = get_wikidata_results(wikidata_query)
    wikidata_info = None
    if wikidata_res and wikidata_res.get('results', {}).get('bindings'):
        b = wikidata_res['results']['bindings'][0]
        inception_raw = b.get('inception', {}).get('value')
        inception_display = None
        if inception_raw:
            try:
                # Expected format: YYYY-MM-DD or full xsd:dateTime
                inception_display = inception_raw[:10]
            except Exception:
                inception_display = inception_raw

        ideology_label = None
        ideology_raw = b.get('ideologyLabel', {}).get('value')
        if ideology_raw:
            ideology_label = ideology_raw

        wikidata_info = {
            'label': b.get('itemLabel', {}).get('value'),
            'shortName': b.get('shortName', {}).get('value'),
            'website': b.get('website', {}).get('value'),
            'inception': inception_display,
            'memberCount': b.get('memberCount', {}).get('value'),
            'ideology': ideology_label,
        }

    # Recent zaken the fractie voted on (with their vote)
    recent_zaken_query = f"""
    PREFIX tk: <http://www.semanticweb.org/twanh/ontologies/2025/9/tk/>
    SELECT ?zaakNummer ?beschrijving ?datum (SUM(?voor) AS ?stemmenVoor) (SUM(?tegen) AS ?stemmenTegen) (SUM(?nietDeelgenomen) AS ?stemmenNietDeelgenomen)
    WHERE {{
      ?fractie a tk:Fractie ;
               tk:naam "{decoded_fractie_naam}" .

      ?zaak a tk:Zaak ;
            tk:nummer ?zaakNummer ;
            tk:beschrijving ?beschrijving .
      OPTIONAL {{ ?zaak tk:indieningsDatum ?datum . }}

      BIND(IF(EXISTS {{ ?fractie tk:heeftVoorGestemd ?zaak }}, 1, 0) AS ?voor)
      BIND(IF(EXISTS {{ ?fractie tk:heeftTegenGestemd ?zaak }}, 1, 0) AS ?tegen)
      BIND(IF(EXISTS {{ ?fractie tk:heeftNietDeelgenomen ?zaak }}, 1, 0) AS ?nietDeelgenomen)
    }}
    GROUP BY ?zaakNummer ?beschrijving ?datum
    ORDER BY DESC(?datum) ?zaakNummer
    LIMIT 10
    """

    recent_results = get_db_results(recent_zaken_query)

    recent_zaken = []
    for res in recent_results['results']['bindings']:
        vote_label = 'Onbekend'
        stemmen_voor = int(res.get('stemmenVoor', {}).get('value', '0'))
        stemmen_tegen = int(res.get('stemmenTegen', {}).get('value', '0'))
        stemmen_niet = int(
            res.get('stemmenNietDeelgenomen', {}).get('value', '0'),
        )
        if stemmen_voor == 1:
            vote_label = 'Voor'
        elif stemmen_tegen == 1:
            vote_label = 'Tegen'
        elif stemmen_niet == 1:
            vote_label = 'Niet Deelgenomen'

        recent_zaken.append({
            'nummer': res['zaakNummer']['value'],
            'beschrijving': res['beschrijving']['value'],
            'datum': res.get('datum', {}).get('value'),
            'vote': vote_label,
        })

    return render_template(
        'fractie.html',
        fractie_naam=decoded_fractie_naam,
        leden=leden,
        total_votes=total_votes,
        onderwerp_votes=onderwerp_votes,
        recent_zaken=recent_zaken,
        wikidata=wikidata_info,
        member_count=len(leden),
    )


@app.route('/zaken')
def zaken_lijst():
    start_date = request.args.get('start_date', '')
    end_date = request.args.get('end_date', '')
    onderwerp_filter = request.args.get('onderwerp_type', '')
    resultaat_filter = request.args.get('resultaat', '')
    zaak_type_filter = request.args.get('zaak_type', '')

    # Pagination parameters
    page = request.args.get('page', 1, type=int)
    per_page = 20
    offset = (page - 1) * per_page

    besluit_query = """
    PREFIX tk: <http://www.semanticweb.org/twanh/ontologies/2025/9/tk/>
    SELECT DISTINCT ?besluitResultaat WHERE {
        ?zaak a tk:Zaak ;
              tk:besluitResultaat ?besluitResultaat .
    }
    ORDER BY ?besluitResultaat
    """

    zaak_soort_query = """
    PREFIX tk: <http://www.semanticweb.org/twanh/ontologies/2025/9/tk/>
    SELECT DISTINCT ?zaakSoort WHERE {
        ?zaak a tk:Zaak ;
              tk:zaakSoort ?zaakSoort .
    }
    ORDER BY ?zaakSoort
    """

    besluit_results = get_db_results(besluit_query)
    zaak_soort_results = get_db_results(zaak_soort_query)

    besluit_opties = [
        res['besluitResultaat']['value']
        for res in besluit_results['results']['bindings']
    ]
    zaak_type_opties = [
        res['zaakSoort']['value']
        for res in zaak_soort_results['results']['bindings']
    ]

    onderwerp_opties = [
        'Binnenlandse Zaken en Koninkrijksrelaties',
        'Buitenlandse Zaken en Defensie',
        'Economie en Financien',
        'Infrastructuur en Waterstaat',
        'Justitie en Veiligheid',
        'Klimaat en Energie',
        'Landbouw en Natuur',
        'Onderwijs Cultuur en Wetenschap',
        'Sociale Zaken en Werkgelegenheid',
        'Volksgezondheid en Zorg',
        'Other',
    ]

    # Note: We build the query step by step, because this way we can optimize the
    # query a bit more. In early testing this page took over 10seconds to load because 
    # of the large amount of data and the query that did a lot of heavy lifting.

    base_patterns = [
        '?zaak a tk:Zaak',
        '?zaak tk:nummer ?zaakNummer',
        '?zaak tk:beschrijving ?beschrijving',
        '?zaak tk:indieningsDatum ?indieningsDatum',
    ]

    # Apply date filters early (before optional clauses)
    early_filters = []
    if start_date:
        early_filters.append(
            f'FILTER (?indieningsDatum >= "{start_date}"^^xsd:date)',
        )
    if end_date:
        early_filters.append(
            f'FILTER (?indieningsDatum <= "{end_date}"^^xsd:date)',
        )

    onderwerp_pattern = ''
    if onderwerp_filter:
        base_patterns.append('?zaak tk:heeftOnderwerp ?onderwerp')
        base_patterns.append('?onderwerp tk:onderwerpType ?onderwerpType')
        early_filters.append(f'FILTER (?onderwerpType = "{onderwerp_filter}")')
    else:
        onderwerp_pattern = 'OPTIONAL { ?zaak tk:heeftOnderwerp ?onderwerp . ?onderwerp tk:onderwerpType ?onderwerpType . }'

    optional_patterns = []
    if not resultaat_filter:
        optional_patterns.append('?zaak tk:besluitResultaat ?besluitResultaat')
    else:
        base_patterns.append('?zaak tk:besluitResultaat ?besluitResultaat')
        early_filters.append(
            f'FILTER (?besluitResultaat = "{resultaat_filter}")',
        )

    if not zaak_type_filter:
        optional_patterns.append('?zaak tk:zaakSoort ?zaakSoort')
    else:
        base_patterns.append('?zaak tk:zaakSoort ?zaakSoort')
        early_filters.append(f'FILTER (?zaakSoort = "{zaak_type_filter}")')

    # We join the base patterns, early filters and optional patterns 
    where_clause = ' .\n        '.join(base_patterns) + ' .'
    if early_filters:
        where_clause += '\n        ' + '\n        '.join(early_filters)
    if optional_patterns:
        where_clause += '\n        OPTIONAL { ' + \
            ' . '.join(optional_patterns) + ' . }'
    if onderwerp_pattern and not onderwerp_filter:
        where_clause += '\n        ' + onderwerp_pattern

    limit = per_page + 1
    if not onderwerp_filter:
        limit = per_page + 5

    # We build the final query
    query = f"""
    PREFIX tk: <http://www.semanticweb.org/twanh/ontologies/2025/9/tk/>
    PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
    SELECT DISTINCT ?zaakNummer ?beschrijving ?besluitResultaat ?indieningsDatum ?zaakSoort ?onderwerpType
    WHERE {{
        {where_clause}
    }} ORDER BY DESC(?indieningsDatum)
    LIMIT {limit} OFFSET {offset}
    """

    results = get_db_results(query)
    bindings = results['results']['bindings']

    seen_zaken = set()
    unique_bindings = []
    for result in bindings:
        zaak_nummer = result['zaakNummer']['value']
        if zaak_nummer not in seen_zaken:
            seen_zaken.add(zaak_nummer)
            unique_bindings.append(result)

    # Determine if there is a next page
    has_next = len(unique_bindings) > per_page
    if has_next or (len(bindings) == limit and len(unique_bindings) == per_page):
        # If we fetched the full limit and still got a full page after dedup, likely more exist
        has_next = True
    unique_bindings = unique_bindings[:per_page]

    zaken = []
    for result in unique_bindings:
        raw_date = result['indieningsDatum']['value'].split('T')[0]

        zaken.append({
            'nummer': result['zaakNummer']['value'],
            'beschrijving': result['beschrijving']['value'],
            'resultaat': result.get('besluitResultaat', {}).get('value', 'Nog niet bekend'),
            'datum': raw_date,
            'type': result.get('zaakSoort', {}).get('value', 'Onbekend'),
            'onderwerp': result.get('onderwerpType', {}).get('value', 'Geen onderwerp'),
        })

    # Calculate pagination info without running a heavy COUNT query
    has_prev = page > 1
    total_zaken = None
    total_pages = None

    return render_template(
        'zaken.html',
        zaken=zaken,
        aantal_zaken=total_zaken,
        page=page,
        per_page=per_page,
        total_pages=total_pages,
        has_prev=has_prev,
        has_next=has_next,
        filters={
            'start_date': start_date,
            'end_date': end_date,
            'onderwerp_type': onderwerp_filter,
            'resultaat': resultaat_filter,
            'zaak_type': zaak_type_filter,
        },
        onderwerp_opties=onderwerp_opties,
        besluit_opties=besluit_opties,
        zaak_type_opties=zaak_type_opties,
    )


@app.route('/zaak/<path:zaak_nummer>')
def zaak_detail(zaak_nummer):

    decoded_zaak_nummer = unquote(zaak_nummer)

    query = f"""
    PREFIX tk: <http://www.semanticweb.org/twanh/ontologies/2025/9/tk/>
    SELECT ?fractieNaam
           (SUM(?voor) AS ?stemmenVoor)
           (SUM(?tegen) AS ?stemmenTegen)
           (SUM(?nietDeelgenomen) AS ?stemmenNietDeelgenomen)
           ?beschrijving ?onderwerp ?besluitResultaat
           ?volgnummer ?indieningsDatum ?besluitStemmingsoort ?dossierNummer
    WHERE {{
      ?zaak tk:nummer "{decoded_zaak_nummer}" ;
            tk:beschrijving ?beschrijving .
      OPTIONAL {{ ?zaak tk:besluitResultaat ?besluitResultaat . }}
      OPTIONAL {{ ?zaak tk:volgnummer ?volgnummer . }}
      OPTIONAL {{ ?zaak tk:indieningsDatum ?indieningsDatum . }}
      OPTIONAL {{ ?zaak tk:besluitStemmingsoort ?besluitStemmingsoort . }}
      OPTIONAL {{ ?zaak tk:dossierNummer ?dossierNummer . }}
      OPTIONAL {{
        ?zaak tk:heeftOnderwerp ?onderwerpInst .
        ?onderwerpInst tk:onderwerpType ?onderwerp .
      }}

      ?fractie a tk:Fractie ;
               tk:naam ?fractieNaam .

      # Use BIND to check vote for each fractie and assign a 1 or 0
      BIND(IF(EXISTS {{ ?fractie tk:heeftVoorGestemd ?zaak }}, 1, 0) AS ?voor)
      BIND(IF(EXISTS {{ ?fractie tk:heeftTegenGestemd ?zaak }}, 1, 0) AS ?tegen)
      BIND(IF(EXISTS {{ ?fractie tk:heeftNietDeelgenomen ?zaak }}, 1, 0) AS ?nietDeelgenomen)
    }}
    GROUP BY ?fractieNaam ?beschrijving ?onderwerp ?besluitResultaat
             ?volgnummer ?indieningsDatum ?besluitStemmingsoort ?dossierNummer
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
            'onderwerp': bindings[0].get('onderwerp', {}).get('value', 'Niet bekend'),
            'volgnummer': bindings[0].get('volgnummer', {}).get('value', 'Niet bekend'),
            'indieningsDatum': bindings[0].get('indieningsDatum', {}).get('value', 'Niet bekend'),
            'besluitStemmingsoort': bindings[0].get('besluitStemmingsoort', {}).get('value', 'Niet bekend'),
            'dossierNummer': bindings[0].get('dossierNummer', {}).get('value', 'Niet bekend'),
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


@app.route('/persoon/<path:persoon_naam>')
def persoon_detail(persoon_naam):
    decoded_persoon_naam = unquote(persoon_naam)

    person_topic_query = f"""
    PREFIX tk: <http://www.semanticweb.org/twanh/ontologies/2025/9/tk/>

    SELECT ?onderwerpType (COUNT(DISTINCT ?zaakVoor) AS ?stemmenVoor) (COUNT(DISTINCT ?zaakTegen) AS ?stemmenTegen) (COUNT(DISTINCT ?zaakNietDeelgenomen) AS ?stemmenNietDeelgenomen)
    WHERE {{
      ?persoon a tk:Persoon ;
               tk:naam "{decoded_persoon_naam}" .

      VALUES ?voteProperty {{ tk:heeftVoorGestemd tk:heeftTegenGestemd tk:heeftNietDeelgenomen }}

      ?persoon ?voteProperty ?zaak .

      ?zaak tk:heeftOnderwerp ?onderwerp .
      ?onderwerp tk:onderwerpType ?onderwerpType .

      BIND(IF(?voteProperty = tk:heeftVoorGestemd, ?zaak, 1/0) AS ?zaakVoor)
      BIND(IF(?voteProperty = tk:heeftTegenGestemd, ?zaak, 1/0) AS ?zaakTegen)
      BIND(IF(?voteProperty = tk:heeftNietDeelgenomen, ?zaak, 1/0) AS ?zaakNietDeelgenomen)
    }}
    GROUP BY ?onderwerpType
    ORDER BY ?onderwerpType
    """

    topic_results = get_db_results(person_topic_query)

    onderwerp_votes = {}
    total_votes = {'voor': 0, 'tegen': 0, 'niet_deelgenomen': 0}

    for result in topic_results['results']['bindings']:
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

    recent_person_zaken_query = f"""
    PREFIX tk: <http://www.semanticweb.org/twanh/ontologies/2025/9/tk/>
    SELECT ?zaakNummer ?beschrijving ?datum (SUM(?voor) AS ?stemmenVoor) (SUM(?tegen) AS ?stemmenTegen) (SUM(?nietDeelgenomen) AS ?stemmenNietDeelgenomen)
    WHERE {{
      ?persoon a tk:Persoon ;
               tk:naam "{decoded_persoon_naam}" .

      ?zaak a tk:Zaak ;
            tk:nummer ?zaakNummer ;
            tk:beschrijving ?beschrijving .
      OPTIONAL {{ ?zaak tk:indieningsDatum ?datum . }}

      BIND(IF(EXISTS {{ ?persoon tk:heeftVoorGestemd ?zaak }}, 1, 0) AS ?voor)
      BIND(IF(EXISTS {{ ?persoon tk:heeftTegenGestemd ?zaak }}, 1, 0) AS ?tegen)
      BIND(IF(EXISTS {{ ?persoon tk:heeftNietDeelgenomen ?zaak }}, 1, 0) AS ?nietDeelgenomen)
    }}
    GROUP BY ?zaakNummer ?beschrijving ?datum
    ORDER BY DESC(?datum) ?zaakNummer
    LIMIT 10
    """

    recent_results = get_db_results(recent_person_zaken_query)

    recent_zaken = []
    for res in recent_results['results']['bindings']:
        vote_label = 'Onbekend'
        stemmen_voor = int(res.get('stemmenVoor', {}).get('value', '0'))
        stemmen_tegen = int(res.get('stemmenTegen', {}).get('value', '0'))
        stemmen_niet = int(
            res.get('stemmenNietDeelgenomen', {}).get('value', '0'),
        )
        if stemmen_voor == 1:
            vote_label = 'Voor'
        elif stemmen_tegen == 1:
            vote_label = 'Tegen'
        elif stemmen_niet == 1:
            vote_label = 'Niet Deelgenomen'

        recent_zaken.append({
            'nummer': res['zaakNummer']['value'],
            'beschrijving': res['beschrijving']['value'],
            'datum': res.get('datum', {}).get('value'),
            'vote': vote_label,
        })

    return render_template(
        'persoon.html',
        persoon_naam=decoded_persoon_naam,
        total_votes=total_votes,
        onderwerp_votes=onderwerp_votes,
        recent_zaken=recent_zaken,
    )


if __name__ == '__main__':
    app.run(host='0.0.0.0', debug=True)
