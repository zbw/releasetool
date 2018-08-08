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
Test the releasetool's API services, DB model, etc.
"""
__author__ = "Martin Toepfer"

import logging

from django.test import TestCase
from django.test import override_settings

from django.utils import timezone as tz
from django.core.exceptions import ObjectDoesNotExist

from django.contrib.auth.models import User

from collections import OrderedDict
import pandas as pd
import json

from .models import RtConfig, Document, Collection, ReleaseCandidate
from .models import ReviewerWrapper, Review, Guideline
from .models import SubjectAssignment, SubjectIndexer
from .online_configuration import CK_MAIN_AI
from .online_configuration import CK_CATALOG_API_PATTERN, CK_DOCUMENT_WEBLINK_PATTERN, CK_SUPPORT_EMAIL
from .online_configuration import CK_THES_DESCRIPTOR_TYPE, CK_THES_CATEGORY_TYPE, CK_THES_SPARQL_ENDPOINT
from .thesaurus_connection import ThesaurusApi

import os

# see:
# https://docs.djangoproject.com/en/2.0/intro/tutorial05/
# 

# TODO write tests that use: self.client, see: 
# https://docs.djangoproject.com/en/2.0/intro/tutorial05/#testing-the-detailview

DIR_TESTDATA = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'test_data')

#----# UTILITY | TEST CONTENT #----#

def _generate_dfj():
    """
    Synthesize several training examples.
    """
    dfj_data = OrderedDict()
    ## general structure:
    dfj_data["docid"] = None
    dfj_data["content"] = []
    dfj_data["cids"] = []
    ## generate arbitrary artificial entries:
    content_subjs = []
    patterns = [
            ("Agreement on fishery with %s", "10698-4 12964-6 %s"),
            ("Agreement on corn trading with %s", "10698-4 18008-1 %s"),
            ("Regulations on trade in fresh bovine from %s", "10698-4 18008-1 %s"),
            ("Trade Regulations ## bovine meat # %s", "10698-4 18008-1 %s"),
            ("Convention on cooperation to protect rivers in %s", "19708-3 15746-1 %s"),
            ("Veterinary matters in %s", "13374-1 19034-2 %s")
    ]
    #          = "Denmark Germany Ireland Iceland Italy  Norway  Spain   Sweden Tunisia".split()
    country_cids = "16995-3 18012-3 17413-4 16984-1 17039-2 16985-6 17161-5 16989-5 17754-6".split()
    country_names = "Denmark Germany Ireland Iceland Italy  Norway  Spain   Sweden Tunisia".split()
    n_countries = len(country_names)
    for i, country_cid in enumerate(country_cids):
        country_name = country_names[i]
        for pat_content, pat_concepts in patterns:
            content_subjs.append((pat_content % (country_name, ), pat_concepts % (country_cid, )))
    ## introduce some ARTIFICIAL NOISE:
    for i in range(len(country_cids) - 1):
        content_subjs.append(("Agreement between two states on banking regulation", 
                              "18707-3 %s %s" % (country_cids[i], country_cids[i+1])))
        content_subjs.append(("banking regulation between two EC states", 
                              "18707-3 %s %s" % (country_cids[i+1], country_cids[(i+3) % n_countries])))
    for i in range(len(country_cids) - 2):
        content_subjs.append(("Contract between three states on financial regulation", 
                              "19321-6 %s %s %s" % tuple(map(str.lower, country_cids[i:(i+3)]))))
    content_subjs += [
            ("Association agreement with Albania", "16184-5 17171-2"),
            ("Association agreement with Norway", "16184-5 16985-6"),
            ("Association agreement with Tunisia", "16184-5 17754-6"),
            ("Agreement of association with Iceland", "16184-5 16984-1"),
            ("Association between the EC and South Africa", "16184-5 17688-0"),
            ("Association between the EC Turkey", "16184-5 17638-1"),
    ]
    dfj_data["content"], dfj_data["cids"] = zip(*content_subjs)
    dfj_data["cids"] = list(map(str.split, dfj_data["cids"]))
    dfj_data["docid"] = list(map(lambda x: "doc_" + str(x), range(len(dfj_data["content"]))))
    return pd.DataFrame(dfj_data)
    
class TestContentManager(object):
    """
    Create data base content for testing.
    """
    
    def __init__(self):
        pass
    
    def clear(self):
        # clear the top level objects
        for clz in [RtConfig, Guideline, Collection, Document, Review, SubjectIndexer]:
            clz.objects.all().delete()
    
    def populate_db(self):
        logging.warning("RESET THE USER ACCOUNTS BEFORE LEAVING THE DEBUG MODE")
        try:
            user_x = User.objects.get(username='aaa')
        except ObjectDoesNotExist:
            user_x = User.objects.create_user('aaa', '', 'abcd1234', is_staff=True, is_superuser=True)
        try:
            user_x = User.objects.get(username='xxx')
        except ObjectDoesNotExist:
            user_x = User.objects.create_user('xxx', '', 'xyxy')
        try:
            user_y = User.objects.get(username='yyy')
        except ObjectDoesNotExist:
            user_y = User.objects.create_user('yyy', '', 'yxyx')
        revr = user_x # reviewer
        
        hi_xxxx = SubjectIndexer.objects.create(user=user_x)
        ai_main = SubjectIndexer.objects.create(ai_name="stwai_main")
        ai_lexical = SubjectIndexer.objects.create(ai_name="stwfsa_v0.1")
        
        confm = RtConfig.objects
        confm.create(key=CK_MAIN_AI, value=ai_main.ai_name)
        confm.create(key=CK_THES_SPARQL_ENDPOINT, value='http://zbw.eu/beta/sparql/stw/query')
        confm.create(key=CK_THES_DESCRIPTOR_TYPE, value="http://zbw.eu/namespaces/zbw-extensions/Descriptor")
        confm.create(key=CK_THES_CATEGORY_TYPE, value="http://zbw.eu/namespaces/zbw-extensions/Thsys")
        confm.create(key=CK_DOCUMENT_WEBLINK_PATTERN, value="""https://www.econbiz.de/record/{docid}""")
        confm.create(key=CK_CATALOG_API_PATTERN, value="""https://api.econbiz.de/v1/record/{docid}""")
        confm.create(key=CK_SUPPORT_EMAIL, value="""AutoIndex@zbw.eu""")
        
        help_link = "http://zbw.eu/"
        rlz = Guideline.objects.create(name="A1Rules_v1", pub_date=tz.now(), link=help_link)
        
        _tmplt_c = "http://zbw.eu/stw/descriptor/{cid}"
        _mk_c = lambda cid:_tmplt_c.format(cid=cid)
        
        doc1 = Document.objects.create(external_id="10011704735", title="Geography, search frictions and endogenous trade costs")
        doc2 = Document.objects.create(external_id="10011619528", title="Quality and Inequality", has_abstract=True)
        doc3 = Document.objects.create(external_id="10009639741", title="Chemicals in toys")
        # doc3 = Document.objects.create(external_id="10000000000", title="Investment's in R & D : <bold>test</bold>")
        
        subjects_doc1 = [("11613-5", 1.0), ("11540-6", .2)]
        ai_main.assign_scored(doc1, dict((_mk_c(cid), score) for cid, score in subjects_doc1))
        subjects_doc2 = [("11088-5", .05),]
        ai_main.assign_scored(doc2, dict((_mk_c(cid), score) for cid, score in subjects_doc2))
        
        
        col1 = Collection.objects.create(name="sample_1", description="arbitrary sample (#1)")
        col1.documents.add(doc1)
        col1.documents.add(doc2)
        col1.save()
        col2 = Collection.objects.create(name="sample_2", description="arbitrary sample (#2)")
        col2.documents.add(doc2)
        col2.documents.add(doc3)
        col2.save()
        
        # add a lot of artificial documents and organize into collections by even/odd
        col_even = Collection.objects.create(name="sample_even", description="artificial even")
        col_odd = Collection.objects.create(name="sample_odd", description="artificial odd")
        col_mod3 = Collection.objects.create(name="sample_mod3", description="artificial mod3")
        adf = _generate_dfj()
        for i in range(adf.shape[0]):
            _doc = Document.objects.create(external_id="%011d" % (i), title=adf.content[i])
            if i % 2 == 0:
                col_even.documents.add(_doc)
            else:
                col_odd.documents.add(_doc)
            if i % 3 == 0:
                col_mod3.documents.add(_doc)
            assignments = dict()
            for j, cid in enumerate(adf.cids[i]):
                score = (6+j)/(6+len(adf.cids[i]))
                assignments[_mk_c(cid)] = score
            ai_main.assign_scored(_doc, assignments)
            ## also, synthesize some concepts to be 
            ai_lexical.assign_scored(_doc, dict((c, score) for c, score in assignments.items() if c[-1:] in '02468'))
        for collection in [col_even, col_odd, col_mod3]:
            collection.save()
        
        # create a "parent" document and assign two child documents to it
        doc_parent = Document.objects.create(external_id="90000000001", 
                                             title="Journal 1",
                                             doc_type="journal")
        doc1.broader.add(doc_parent)
        doc1.save()
        doc2.broader.add(doc_parent)
        doc2.save()
        
        # create a review:
        # revu = revr.review_set.create(document=doc1, guideline=rlz, total_rating=)
        
        ## also, create a second guideline...
        rlz = Guideline.objects.create(name="A1Rules_v2", pub_date=tz.now(), link=help_link)
        
        ## and a release candidate
        rc1 = ReleaseCandidate.objects.create(name="RC1",
                                              pub_date=tz.now(),
                                              indexer=ai_main,
                                              file=os.path.join(DIR_TESTDATA, 'rc1.tsv'),
                                              concept_template=_tmplt_c
                                              )
        rc1.save()

#----# TEST CASES/CLASSES #----#

class GuidelineTests(TestCase):
    
    def testIterate(self):
        tcm = TestContentManager()
        tcm.populate_db()
        # test sorting of Guidelines
        self.assertEqual(Guideline.objects.latest().name, "A1Rules_v2")
        

class CollectionIterationTests(TestCase):
    
    def testIterate(self):
        """
        When a reviewer has completed the 1st document of a collection,
        the 2nd document should be presented next.
        """
        # TODO
        tcm = TestContentManager()
        tcm.populate_db()
        
        col1 = Collection.objects.get(name="sample_1")
        col2 = Collection.objects.get(name="sample_2")
#        revr = Reviewer.objects.first()
        revr = ReviewerWrapper(User.objects.first())
        
#        print("collection 1:", col1.documents.all())
        self.assertEqual(col1.compute_overlap(col2), 1)
#        print("progress info:", revr.get_progress_info(col1))
        
        next_doc = revr.get_next_document(col1)
#        print("next doc:", next_doc)
        self.assertEqual("10011619528", next_doc.external_id)


class SamplingTests(TestCase):
    
    @override_settings(MEDIA_ROOT=DIR_TESTDATA)
    def test_sample(self):
        tcm = TestContentManager()
        tcm.populate_db()
        #
        # TODO test sample releasecandidate
        rc1 = ReleaseCandidate.objects.get(name='RC1')
        rc1sz_expected = 12
        self.assertEqual(len(rc1.get_document_ids()),rc1sz_expected)
        ##
        jrl = Document.objects.filter(doc_type="journal").first()
        jrlsz_expected = 2
        self.assertEqual(jrl.narrower.count(), jrlsz_expected)
        ## test sampling
        ## test base
        docsz5 = rc1.sample(5)
        self.assertEqual(docsz5.shape[0], 5)
        ## test restrict by collection
        white_jrl = set(jrl.narrower.values_list("external_id", flat=True))
        self.assertEqual(rc1.sample(9, white_jrl).shape[0], jrlsz_expected)
        ## test restrict by collection
        white_jrlabstract = set(jrl.narrower.filter(has_abstract=True).values_list("external_id", flat=True))
        jrlabstractsz_expected = 1
        self.assertEqual(rc1.sample(9, white_jrlabstract).shape[0], jrlabstractsz_expected)
        
        
def _mk_ThesStw():
    endpoint = "http://zbw.eu/beta/sparql/stw/query"
    d_type = "http://zbw.eu/namespaces/zbw-extensions/Descriptor"
    k_type = "http://zbw.eu/namespaces/zbw-extensions/Thsys"
    thes = ThesaurusApi(endpoint, d_type, k_type)
    return thes
    

class ThesaurusApiTests(TestCase):
    
    def test_labels(self):
        thes = _mk_ThesStw()
        curi_prefix = "http://zbw.eu/stw/descriptor/"
        
        cid = "11540-6"
        curi = curi_prefix + cid
        labels = thes.labels([curi])
        self.assertDictEqual(labels, {curi: "Public finance"})
        
        cref = curi_prefix + "11268-3"# migrant workers
        self.assertDictEqual(thes.categories(cref), {cref: ['V', 'B', 'N']})
    
    def test_categories(self):
        thes = _mk_ThesStw()
        
        curi_prefix = "http://zbw.eu/stw/descriptor/"
        
        cref = curi_prefix + "11268-3"# migrant workers
        self.assertDictEqual(thes.categories(cref), {cref: ['V', 'B', 'N']})
    
    def test_graph(self):
        thes = _mk_ThesStw()
        # http://zbw.eu/stw/descriptor/10000-1 : Supply
        # http://zbw.eu/stw/descriptor/10169-3 : Labour supply
        # http://zbw.eu/stw/descriptor/11187-3 : Working time
        # 10000-1 >BT> 10169-3
        # 10169-3 ~RT~ 11187-3
        cids = ["10000-1", "10169-3", "11187-3"]
        curis = ["http://zbw.eu/stw/descriptor/" + cid for cid in cids]
        relations = thes.relations(curis)
        print("test-graph:")
        print("=" * 80)
        print("RELATIONS:", json.dumps(relations, indent=4))
        # TODO make assertions
        
    
    def test_autocomplete(self):
        thes = _mk_ThesStw()
        _parse = lambda jsonrsp: [e['c']['value'] for e in jsonrsp['results']['bindings']]
        self.assertIn("http://zbw.eu/stw/descriptor/18012-3", _parse(thes.autocomplete("Germany")))
        self.assertIn("http://zbw.eu/stw/descriptor/18012-3", _parse(thes.autocomplete("German*")))
        



