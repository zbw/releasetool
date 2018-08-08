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
Interface to existing catalog APIs, for instance,
ZBW's web api services, e.g., EconBiz, etc.
"""
__author__ = "Martin Toepfer"

import urllib
import urllib.request
from urllib.request import HTTPError
import json

import re

from .models import RtConfig, Document
from .online_configuration import CK_CATALOG_API_PATTERN

_UNAV_DESCRIPTION_ = "-unavailable-"

GROUP_FKS = ['isPartOf', 'series'] ## group field keys

class CatalogApi(object):
    """
    The CatalogApi accesses a library catalog service, 
    mainly in order to fetch document meta-data.
    """
    
    def __init__(self, pattern):
        """
        
        Example for ZBW environment:
            pattern = "https://api.econbiz.de/v1/record/{docid}"
            fam_pattern = "https://api.econbiz.de/v1/q=fam:{famid}"
        """
        self.pattern = pattern
    
    def fetch(self, external_id):
        try:
            return docjson_by_url(self.pattern.format(docid=external_id))
        except HTTPError as err:
#            logging.error(err)
            return {"title": "-HTTPError-", "description": _UNAV_DESCRIPTION_, "error": str(err)}

    def fetch_metadata(self, queryset):
        """
        Fetch metadata for Documents in queryset and create/update db objects accordingly.
        """
        for dbdoc in queryset:
            docid = dbdoc.external_id
            jdoc = self.fetch(docid)
            if not "error" in jdoc:
                title = jdoc["title"] # "xxx"
                dbdoc.title = title
                dbdoc.doc_type = jdoc['type']
                ## handle JOURNAL/SERIES relationships:
                for gk in GROUP_FKS:
                    if gk in jdoc:
                        for groupdoc in jdoc[gk]:
                            gid = groupdoc['external_id']
                            broader_doc, _created = Document.objects.get_or_create(external_id=gid)
                            if _created:
                                broader_doc.title = groupdoc['title']
                                broader_doc.doc_type = groupdoc['type']
                                broader_doc.save()
                            dbdoc.broader.add(broader_doc)
                dbdoc.save()
    
    @classmethod
    def create_from_db(Clz):
        return Clz(RtConfig.objects.get(key=CK_CATALOG_API_PATTERN).value)


    
#----# independent methods # ---- #

def _parse_description(description_text):
    """
    return keywords that have been parsed from description text field.
    """
    parse_match = re.search(r"( -- ).+? ; ", description_text)
    if parse_match:
        offset = parse_match.start()
        description_head = description_text[:offset]
        _x = description_text[parse_match.end(1):]
        _xs = re.findall(r"(?:^|; )([\w\s-]+)(?= ;|$)", _x)
        # TODO revisit heuristic: num. author keywords < 10 ?!
        if len(_xs) > 0 and all([len(p.split(" ")) < 10 for p in _xs]):
            keywords = list(map(str.strip, _xs))
            return description_head, keywords
    return description_text, []

def docjson_by_url(url):
    """
        Fetch document as JSON result by HTTP request from a url.
        
        arguments:
            docid: external document identifier, e.g., 10010392960
        
        returns:
            json object, some important fields 
                title,  # title of the record
                date, 
                description # 'abstract' of the record
                subject_byAuthor
                series, isPartOf
    """
    req = urllib.request.Request(url)
    opener = urllib.request.build_opener()
    with opener.open(req) as f:
        my_bytes = f.read()
        jsonrsp = json.loads(my_bytes.decode('utf-8'))
        if jsonrsp['status'] == 200:
            record = jsonrsp['record']
            ## TRANSFORM/EXTEND record instance >>>
            record = extend_record(record)
            # <<<
            return record
    raise Exception('unable to fetch url: ' + repr(req.full_url)) # TODO 404, not found?!

def extend_record(record):
    """
    extend several fields of record, e.g., ensure description field, etc.
    
    returns an extended/altered clone of record json obj
    """
#    recx = record
    recx = json.loads(json.dumps(record))
    ## ABSTRACT
    if not 'description' in recx:
        recx['description'] = _UNAV_DESCRIPTION_
    elif type(record['description']) is list:
        recx['description'] = recx['description'][0]
    ### SUBJECTs: highest prio: subject_byAuthor
    if 'subject_byAuthor' in recx:
        recx['subject'] = list(recx['subject_byAuthor'])
    if not 'subject' in recx:
        recx['subject'] = list() # empty list by default
    if len(recx['subject']) == 0:
        recx['description'], recx['subject'] = _parse_description(recx['description'])
    ###
    ### JOURNALS/SERIES : use first key that endswith '_id' per entries' lists
    for gk in GROUP_FKS:
        if gk in record:
            for broader_record in recx[gk]:
                id_keys = list(filter(lambda x: x.endswith('_id'), broader_record.keys()))
                ext_id = broader_record[id_keys[0]] if len(id_keys) > 0 else 'error'
                broader_record['external_id'] = ext_id
                if not 'type' in broader_record:
                    broader_record['type'] = 'unknown'
    return recx

    