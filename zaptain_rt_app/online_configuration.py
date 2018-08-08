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
Listing of online configuration keys.
"""
__author__ = "Martin Toepfer"

CK_MAIN_AI = "main_ai"

# for example: "m.toepfer@zbw.eu"
CK_SUPPORT_EMAIL = "support_email"

# for example: """https://api.econbiz.de/v1/{docid}"""
CK_CATALOG_API_PATTERN = "catalog_api_pattern"

# for example: """https://www.econbiz.de/Record/{docid}"""
CK_DOCUMENT_WEBLINK_PATTERN = "document_weblink_pattern"

CK_THES_DESCRIPTOR_TYPE = "thesaurus_descriptor_type"

# for example: "http://zbw.eu/namespaces/zbw-extensions/Thsys"
CK_THES_CATEGORY_TYPE = "thesaurus_category_type"

# for example: "http://zbw.eu/beta/sparql/stw/query"
CK_THES_SPARQL_ENDPOINT = "thesaurus_sparql_endpoint"

# TODO use it
CK_THES_SPARQL_QUERY = "thesaurus_sparql_query"

RtConfigKeys = [
        CK_MAIN_AI,
        CK_CATALOG_API_PATTERN,
        CK_DOCUMENT_WEBLINK_PATTERN,
        CK_THES_DESCRIPTOR_TYPE,
        CK_THES_CATEGORY_TYPE,
        CK_THES_SPARQL_ENDPOINT,
        CK_THES_SPARQL_QUERY]
RtConfigChoices = [
        (CK_MAIN_AI, "name of the main automatic indexing method"),
        (CK_SUPPORT_EMAIL, "support email"),
        (CK_CATALOG_API_PATTERN, "catalog API pattern"),
        (CK_DOCUMENT_WEBLINK_PATTERN, "document weblink pattern"), 
        (CK_THES_DESCRIPTOR_TYPE, "thesaurus descriptor type"),
        (CK_THES_CATEGORY_TYPE, "thesaurus category type"), 
        (CK_THES_SPARQL_ENDPOINT, "thesaurus sparql endpoint"), 
        (CK_THES_SPARQL_QUERY, "thesaurus sparql query")
]