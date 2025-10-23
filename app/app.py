from flask import Flask
from flask import render_template
from SPARQLWrapper import JSON
from SPARQLWrapper import SPARQLWrapper

app = Flask(__name__)


def get_db_results(query):
    sparql = SPARQLWrapper('http://graphdb:7200/repositories/tk_repo')
    sparql.setQuery(query)
    sparql.setReturnFormat(JSON)
    return sparql.query().convert()


@app.route('/')
def index():
    # Example Query: Get all parties and their number of seats
    query = """
    PREFIX tk: <http://www.semanticweb.org/twanh/ontologies/2025/9/tk/>
    SELECT ?fractieNaam ?aantalZetels
    WHERE {
        ?fractie a tk:Fractie ;
                 tk:naam ?fractieNaam ;
                 tk:aantalZetels ?aantalZetels .
    }
    """
    results = get_db_results(query)
    fracties = []
    for result in results['results']['bindings']:
        fracties.append({
            'name': result['fractieNaam']['value'],
            'seats': int(result['aantalZetels']['value']),
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


if __name__ == '__main__':
    # app.run(host='0.0.0.0', debug=True)
    app.run(host='0.0.0.0', port=8000, debug=True)
