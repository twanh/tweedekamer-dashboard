from flask import Flask, render_template
from SPARQLWrapper import JSON, SPARQLWrapper
from urllib.parse import unquote

app = Flask(__name__)


def get_db_results(query):
    # Docker Compose setup (uncomment when using Docker)
    sparql = SPARQLWrapper('http://graphdb:7200/repositories/tk_repo')

    # Localhost for testing without Docker (comment when using Docker)
    # sparql = SPARQLWrapper('http://localhost:7200/repositories/tk_repo')
    
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
            'abbreviation': result['fractieAfko']['value']
        })
    return render_template('index.html', fracties=fracties)


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
    
    # SPARQL query to get members of a specific party
    query = f"""
    PREFIX tk: <http://www.semanticweb.org/twanh/ontologies/2025/9/tk/>
    SELECT ?persoonNaam
    WHERE {{
      ?fractie a tk:Fractie ;
               tk:naam "{decoded_fractie_naam}" ;
               tk:heeftLid ?persoon .
      ?persoon tk:naam ?persoonNaam .
    }}
    ORDER BY ?persoonNaam
    """
    
    results = get_db_results(query)
    leden = [
        result['persoonNaam']['value'] 
        for result in results['results']['bindings']
    ]
    
    # You can also fetch the party details again if needed
    # For now, we'll just pass the name and the members
    return render_template(
        'fractie.html', 
        fractie_naam=decoded_fractie_naam,
        leden=leden
    )


if __name__ == '__main__':
    # Docker Compose setup (uncomment when using Docker)
    app.run(host='0.0.0.0', debug=True)

    # Localhost with specified port (for Macbook compatibility since port 5000 is sometimes in use), comment when using Docker
    # app.run(host='0.0.0.0', port=8000, debug=True)
