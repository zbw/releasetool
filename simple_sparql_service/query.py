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
c_uris = " ".join(
        [
            "(<http://zbw.eu/stw/descriptor/{}>)".format(i)
            for i
            in ["19317-4", "10465-6"]])
url = "http://127.0.0.1:5000/"
query = QT_LABELS % c_uris 
result = requests.post(url, data={"query": query}, timeout=_TIMEOUT_S)
result_json = json.loads(result.text)
print(result_json)
print(result.status_code, result.elapsed.total_seconds())
