#!/usr/bin/python3
import requests
import json
_TIMEOUT_S = 16.0
QT_LABELS = """
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
PREFIX owl: <http://www.w3.org/2002/07/owl#>

SELECT * WHERE {
  values (?c) { %s } .
  ?c a skos:Concept ;
     skos:prefLabel ?label .
  FILTER (lang(?label) = "en")
}
"""
Q_AUTOCOMPLETE_FUZZY = """
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
PREFIX owl: <http://www.w3.org/2002/07/owl#>

PREFIX text: <http://jena.apache.org/text#>

SELECT DISTINCT ?c ?prefLabel ?literal ?score
WHERE {{
  (?c ?score ?literal)
     text:query ("{autocomplete_string}" ) .
  ?c a skos:Concept, <{descriptor_type}> ;
     skos:prefLabel ?prefLabel .
  FILTER (lang(?prefLabel) IN ( {languages} ))
}}
ORDER BY DESC(?score) DESC(lang(?prefLabel))
"""
c_uris = " ".join(
        [
            "(<http://zbw.eu/stw/descriptor/{}>)".format(i)
            for i
            in ["19317-4", "10465-6"]])
url = "http://127.0.0.1:5000/stw"
query = QT_LABELS % c_uris 
result = requests.post(url, data={"query": query}, timeout=_TIMEOUT_S)
if result.status_code == 200:
    result_json = json.loads(result.text)
    print(result_json)
    print(result.status_code, result.elapsed.total_seconds())
else:
    print(f"ERROR {result.status_code}: {result.text}")

query = Q_AUTOCOMPLETE_FUZZY.format(
    descriptor_type='http://zbw.eu/stw/descriptor', 
    autocomplete_string="Rente", 
    languages=", ".join(["\""+ lang +"\"" for lang in ["en", "de"]]))
result = requests.post(url, data={"query": query}, timeout=_TIMEOUT_S)
if result.status_code == 200:
    result_json = json.loads(result.text)
    print(result_json)
    print(result.status_code, result.elapsed.total_seconds())
else:
    print(f"ERROR {result.status_code}: {result.text}")
