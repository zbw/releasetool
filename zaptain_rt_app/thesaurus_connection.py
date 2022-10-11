# -*- coding: utf-8 -*-
#
#    releasetool - quality assessment for automatic subject indexing
#    Copyright (C) 2018 Martin Toepfer <m.toepfer@zbw.eu> | ZBW -- Leibniz Information Centre for Economics
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <https://www.gnu.org/licenses/>.
#
"""
Connection accessing thesaurus API services.
"""
__author__ = "Martin Toepfer"

import requests
from requests.exceptions import Timeout # ... ReadTimeout

#import json
try:
    from json import JSONDecodeError
except ImportError:
    JSONDecodeError = ValueError

import logging

from collections import defaultdict

from .models import RtConfig
from .online_configuration import RtConfigChoices
from .online_configuration import CK_THES_SPARQL_ENDPOINT, CK_THES_DESCRIPTOR_TYPE, CK_THES_CATEGORY_TYPE


_TIMEOUT_S = 5.000 ## TIMEOUT IN SECONDS


## TODO maybe use rdflib.plugins.sparql.prepareQuery instead...

# PREFIX stwd: <http://zbw.eu/stw/descriptor/>
# PREFIX zbwext: <http://zbw.eu/namespaces/zbw-extensions/>

#----# QUERY TEMPLATES #----#

QT_LABELS = """
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
PREFIX owl: <http://www.w3.org/2002/07/owl#>

SELECT ?c (GROUP_CONCAT(?prefLabel; SEPARATOR=" / ") as ?label) WHERE {
  SELECT * WHERE{
    values (?c) { %s } .
    ?c a skos:Concept ;
       skos:prefLabel ?prefLabel .
    }
    ORDER BY DESC(lang(?prefLabel))
}
GROUP BY ?c
"""

QT_CATEGORY_PATHS = """
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
PREFIX owl: <http://www.w3.org/2002/07/owl#>

SELECT DISTINCT ?t ?c WHERE {{
  values (?c) {{ {cs} }} .
  ?t a <{kat_type}> ;
     skos:narrower* ?k .
  ?k a <{kat_type}> ;
     skos:narrower ?c .
}}
"""

QT_CATEGORIES = """
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
PREFIX owl: <http://www.w3.org/2002/07/owl#>

SELECT ?c (GROUP_CONCAT(DISTINCT ?t; SEPARATOR=", ") AS ?kat_info)
WHERE {{
  values (?c) {{ {cs} }} .
  ?t a <{kat_type}> ;
     skos:topConceptOf ?x ;
     skos:narrower* ?y .
  ?y a <{kat_type}> ;
     skos:narrower ?c .
}}
GROUP BY ?c
"""

QT_CATEGORY_CODES = """
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
PREFIX owl: <http://www.w3.org/2002/07/owl#>

SELECT ?c (GROUP_CONCAT(DISTINCT ?code; SEPARATOR=", ") AS ?kat_info)
WHERE {{
  values (?c) {{ {cs} }} .
  ?t a <{kat_type}> ;
     skos:notation ?code ;
     skos:topConceptOf ?x ;
     skos:narrower* ?y .
  ?y a <{kat_type}> ;
     skos:narrower ?c .
}}
GROUP BY ?c
"""

Q_TOP_CATEGORIES = """
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
PREFIX owl: <http://www.w3.org/2002/07/owl#>

SELECT ?t ?code
WHERE {
  ?t a skos:Concept ;
     skos:topConceptOf ?c ;
     skos:notation ?code .
}
"""

Q_RELATIONS_BT = """
PREFIX skos: <http://www.w3.org/2004/02/skos/core#>

SELECT ?c ?relation ?c_other ?label
WHERE {{
  values (?c) {{ {cs} }} .
  values (?c_other) {{ {cs_other} }} .
  ?c (skos:broader)+ ?c_other .
  ?c_other a <{descriptor_type}> ;
           skos:prefLabel ?label .
  filter (lang(?label) = '{langstr}')
}}
"""

Q_RELATIONS_RT = """
PREFIX skos: <http://www.w3.org/2004/02/skos/core#>

SELECT ?c ?relation ?c_other ?label
WHERE {{
  values (?c) {{ {cs} }} .
  values (?c_other) {{ {cs_other} }} .
  ?c skos:related ?c_other .
  ?c_other a <{descriptor_type}> ;
           skos:prefLabel ?label .
  filter (lang(?label) = '{langstr}')
}}
"""

# see: https://jena.apache.org/documentation/query/text-query.html#syntax
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
Q_AUTOCOMPLETE_EXACT = """
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
PREFIX owl: <http://www.w3.org/2002/07/owl#>

PREFIX text: <http://jena.apache.org/text#>

SELECT ?c ?prefLabel ?literal ?score
WHERE {{
  (?c ?score ?literal)
     text:query ("{autocomplete_string}" ) .
  ?c a skos:Concept, <{descriptor_type}> ;
     skos:prefLabel ?prefLabel .
  FILTER (lang(?prefLabel) IN ( {languages} ))
  FILTER (regex(str(?literal), "(?i)^{regex_string}.*"))
}}
ORDER BY DESC(?score) DESC(lang(?prefLabel))
"""

#----# CLASSES #----#

class ThesaurusApi(object):
    
    def __init__(self, endpoint, descriptor_type, category_type, languages=["de", "en"]):
        """
        examples:
            see tests.py
        """
        self.endpoint = endpoint
        self.Dtype = descriptor_type
        self.Ktype = category_type
        self.languages = languages
    
    def autocomplete(self, autocomplete_string, limit=-1, exact_begin=False):
        template = Q_AUTOCOMPLETE_EXACT if exact_begin else Q_AUTOCOMPLETE_FUZZY
        _qs = template.format(
                descriptor_type=self.Dtype, 
                autocomplete_string=autocomplete_string, 
                regex_string=autocomplete_string.strip("*"),
                languages=", ".join(["\""+ lang +"\"" for lang in self.languages]))
        if type(limit) is int and limit > -1:
            _qs = _qs + "LIMIT %d" % (limit, )
        rsp = self._q(_qs)
        if rsp.status_code != 200:
            logging.error(rsp)
            return {}
        return rsp.json()
    
    def labels(self, concept_uris, prefix=None):
        """
        return a dictionary of concept_id --> prefLabel items
        """
        _fallback_rsp = dict((c, c) for c in concept_uris)
        try:
            rsp = self._q(QT_LABELS, concept_uris=concept_uris) # , prefix=prefix) # , accept="application/sparql-results+json")
        except Timeout as err:
            logging.error(err)
            return _fallback_rsp
        if rsp.status_code != 200:
            logging.error("error querying labels... %s" % (repr(rsp), ))
            # logging.error(query)
            logging.error("Querying labels for concepts failed.")
            logging.error(rsp.content)
            return _fallback_rsp
        thelabels = defaultdict(list)
        for e in rsp.json()["results"]["bindings"]:
            key = e['c']['value']
            value = e['label']['value']
            thelabels[key].append(value)
        joinedlabels = {
                cncpt_id: ' / '.join(labels)
                for cncpt_id, labels
                in thelabels.items()}
        return joinedlabels
    
    def top_categories(self):
        """
        Query the top categories of the thesaurus.
        
        returns a dictionary that maps top-level category URIs to corresponding names.
        """
        try:
            rsp = self._q(Q_TOP_CATEGORIES)
            if rsp.status_code != 200:
                logging.error("error querying top categories... %s" % (repr(rsp), ))
                logging.error(rsp.content)
                return dict()
            rsp_bindings = rsp.json()["results"]["bindings"]
            return dict((e['code']['value'], e['t']['value']) for e in rsp_bindings)
        except ReadTimeoutError:
            logging.error("Querying top categories timed out.")
            return dict()
    
    def categories(self, concept_uris, return_type='code'):
        """
        Query the categories (k) that concepts (c) belong to, for instance:
            c1 => k2, k7
            c2 => k1, k2, k5
            ...
        
        returns a dictionary, return_type may be 'code' or 'uri'.
        """
        if type(concept_uris) is str:
            concept_uris = [concept_uris,]
        if len(concept_uris) < 1:
            return dict()
        cidsstr = ThesaurusApi._curis_to_valueliststr(concept_uris)
        qtmplt = None
        if return_type == 'code':
            qtmplt = QT_CATEGORY_CODES
        elif return_type == 'uri':
            qtmplt = QT_CATEGORIES
        else:
            raise Exception('illegal return_type parameter given')
        thecks = dict((c_uri, []) for c_uri in concept_uris) # map to thesaurus categories
        query = qtmplt.format(cs=cidsstr, kat_type=self.Ktype)
        try:
            rsp = self._q(query)
        except Timeout as err:
            logging.error(err)
            return thecks
        jsonresult = rsp.json()["results"]["bindings"]
        for e in jsonresult:
            if not 'c' in e:
                logging.error(e)
            else:
                c = e["c"]["value"]
                kats = e["kat_info"]["value"].split(", ")
                # add your special endpoint extensions for ordering of categories here:
                if self.endpoint == "http://zbw.eu/beta/sparql/stw/query":
                    _order = "VBWPNGA"
                    _orderfun = lambda k: _order.index(k) if k in _order else 0
                    kats = sorted(kats, key=_orderfun)
                thecks[c] = kats
        return thecks
    
#    def groups(self, concept_ids):
#        """
#        oriented at ASPECTS of the subject matter of a document.
#        
#        TODO return groups (may be computed in a sophisticated fashion) of concepts
#        """
#        pass
    
    def relations(self, concept_uris, include_RT=True):
        """
        Check which relations are specified between concepts.
        """
        relations_ = [] # return obj
        relations_ += self._fetch_relations(Q_RELATIONS_BT, concept_uris, "BT")
        if include_RT:
            relations_ += self._fetch_relations(Q_RELATIONS_RT, concept_uris, "RT")
        return relations_

    def _fetch_relations(self, template, concept_uris, relation_name):
        relations_ = [] # return obj
        cs = ThesaurusApi._curis_to_valueliststr(concept_uris)
        qq = template.format(cs=cs, cs_other=cs, langstr='en', 
                                 descriptor_type=self.Dtype)
        rsp = self._q(qq)
        if rsp.status_code != 200:
            logging.error("error querying top categories... %s" % (repr(rsp), ))
            logging.error(qq)
            logging.error(rsp.content)
        else:
            jobj = rsp.json()['results']['bindings']
            for el_ in jobj:
                if all(k in el_ for k in ['c_other', 'label']):
                    cid = el_['c']['value']
                    cid_other = el_['c_other']['value']
                    relations_.append({"source": cid, "target": cid_other, "relation": relation_name })
                else:
                    logging.warning(el_)
        return relations_
    
    def _q(self, query, concept_uris=None, timeout=_TIMEOUT_S):
        """
        perform a POST http requests action,
        please handle TIMEOUTs, --> ReadTimeoutError
        """
        if not concept_uris is None:
            query = query % (ThesaurusApi._curis_to_valueliststr(concept_uris))
        return requests.post(self.endpoint, data={"query": query}, timeout=timeout)
    
    @staticmethod
    def _curis_to_valueliststr(concept_uris):
        return " ".join(["(<" + curi + ">)" for curi in concept_uris])
    

    @classmethod
    def create_from_db(Clz):
        ctx = dict()
        for k, k_hum in RtConfigChoices:
            try:
                ctx[k] = RtConfig.objects.get(key=k).value
            except RtConfig.DoesNotExist:
                pass
        return Clz(ctx[CK_THES_SPARQL_ENDPOINT], ctx[CK_THES_DESCRIPTOR_TYPE], ctx[CK_THES_CATEGORY_TYPE])


    
