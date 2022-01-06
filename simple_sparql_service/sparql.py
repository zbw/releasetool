#!/usr/bin/python3
from flask import Flask, request
import rdflib
from rdflib.plugins.sparql.results.jsonresults import termToJSON
from waitress import serve
from argparse import ArgumentParser
import logging

app = Flask(__name__)

_key_graph = 'graph'

def mk_arg_parser():
    p = ArgumentParser(
        description='Simple service providing a SPARQL endpoint'
        'from a rdf file.')
    p.add_argument(
        '-f', '--rdf-file',
        help='Path to the rdffile to be served.')
    p.add_argument(
        '-p', '--port',
        help='Port the service should listen on')
    return p

def load_graph(path: str):
    g = rdflib.Graph()
    g.parse(path, format='xml')
    return g


@app.route('/', methods=["POST"])
def query_fn():
    json = request.form
    query = json["query"]
    result = app.config[_key_graph].query(query)
    res_vars = [var.toPython()[1:] for var in result.vars]
    bindings = [
            {
                var: termToJSON(None, binding[var])
                for var in res_vars}
            for binding
            in result.bindings]
    return {"results": {"bindings": bindings, "head": {"vars": res_vars}}}


if __name__ == "__main__":
    args = mk_arg_parser().parse_args()
    g = load_graph(args.rdf_file)
    app.config[_key_graph] = g
    logging.warning('Graph loaded')
    serve(app, listen=f"*:{args.port}")
