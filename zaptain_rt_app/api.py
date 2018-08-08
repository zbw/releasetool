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
The releasetool api for access to db models, partly delegating to external services, etc.
"""
__author__ = "Martin Toepfer"

from collections import Counter
from collections import defaultdict

import re

from django.shortcuts import get_object_or_404
from django.http import HttpResponse, Http404
from django.http import JsonResponse

from django.contrib.auth.decorators import login_required
from django.contrib.admin.views.decorators import staff_member_required
from django.core.exceptions import ObjectDoesNotExist

from django.db import models
from django.db.models import Q, F, Count

from django.contrib.auth.models import User

from .models import RtConfig
from .models import Collection, Document
from .models import SubjectAssignment
from .models import ReviewerWrapper, SubjectIndexer, Review, SubjectLevelReview

from .thesaurus_connection import ThesaurusApi
from .catalog_connection import CatalogApi
from .online_configuration import RtConfigChoices
from .online_configuration import CK_CATALOG_API_PATTERN
from .online_configuration import CK_THES_SPARQL_ENDPOINT, CK_THES_DESCRIPTOR_TYPE, CK_THES_CATEGORY_TYPE

import pandas as pd

# see:
# https://docs.djangoproject.com/en/2.0/intro/tutorial04/
# https://docs.djangoproject.com/en/2.0/ref/request-response/#jsonresponse-objects
#    response = JsonResponse({'foo': 'bar'})

def basecontext(request, external_id=None):
    """
    Provide data and objects useful for templates.
    """
    ctx = dict()
    ctx["rt_collections"] = Collection.objects.all()
    ctx["url_sourcecode"] = 'https://github.com/zbw/releasetool'
    for k, k_hum in RtConfigChoices:
        try:
            ctx[k] = RtConfig.objects.get(key=k).value
        except ObjectDoesNotExist:
            pass
    ctx["kos"] = ThesaurusApi(ctx[CK_THES_SPARQL_ENDPOINT], ctx[CK_THES_DESCRIPTOR_TYPE], ctx[CK_THES_CATEGORY_TYPE])
    ctx["catalog"] = CatalogApi(ctx[CK_CATALOG_API_PATTERN]) # .create_from_db()
    if request.user.is_authenticated:
        ctx["reviewer"] = ReviewerWrapper(request.user)
    if not external_id is None:
        ctx["dbdoc"] = get_object_or_404(Document, external_id=external_id)
        ctx["jsondoc"] = ctx['catalog'].fetch(external_id)
    return ctx

@login_required
def search_kos(request):
    """
    Search for descriptors which match a search string.
    """
    kos = basecontext(request)["kos"]
    q = request.GET.get("q", None)
    if not q:
        return JsonResponse(dict())
    q = q.strip()
    exact_begin = q.startswith("^")
    exact_end = False # TODO q.endswith("$")
    q = re.sub(r"\W+", " ", q).strip()
    if not exact_begin:
        q = "*" + q
        q = q.replace(" ", " AND ")
    if not exact_end:
        q += '*'
    return JsonResponse(data=kos.autocomplete(q, limit=100, exact_begin=exact_begin))


@login_required
def document(request, external_id):
    try:
        document = Document.objects.get(external_id=external_id)
    except Document.DoesNotExist:
        raise Http404("Document does not exist")
    return JsonResponse({"external_id": document.external_id, "title": document.title})
#    return get_object_or_404(Document, ...)


@login_required
def explain(request, external_id):
    ctx = dict()
    for k, k_hum in RtConfigChoices:
        try:
            ctx[k] = RtConfig.objects.get(key=k).value
        except ObjectDoesNotExist:
            pass
    ctx["kos"] = ThesaurusApi(ctx[CK_THES_SPARQL_ENDPOINT], ctx[CK_THES_DESCRIPTOR_TYPE], ctx[CK_THES_CATEGORY_TYPE])
    try:
        document = Document.objects.get(external_id=external_id)
    except Document.DoesNotExist:
        raise Http404("Document does not exist")
    assignments = defaultdict(list)
    for sa in SubjectAssignment.objects.filter(document=document): # TODO is_ai?
        assignments[sa.subject].append({"indexer": sa.indexer.ai_name, "score": sa.score})
    subj_labels = ctx['kos'].labels(list(assignments.keys()))
    assignments = dict((k, {"support": v}) for k, v in assignments.items())
    for k in subj_labels:
        assignments[k]["label"] = subj_labels[k]
    assignments = list(assignments.items())
    return JsonResponse({"external_id": document.external_id, "title": document.title, 
                         "assignments": assignments}, json_dumps_params={"indent": 4})

@login_required
def subjects_graph(request, external_id):
    """
    for document with specific external_id,
    return information about 
    - concept-concept relations 
    - concept-category relations
    
    node prototype:
        {"group": 0, "id": ..., "type": "concept" }
    
    link prototype:
        {}
    """
    nodes = []
    links = []
    kb = ThesaurusApi.create_from_db()
    try:
        document = Document.objects.get(external_id=external_id)
    except Document.DoesNotExist:
        raise Http404("Document does not exist")
    assignments = defaultdict(list)
    for sa in SubjectAssignment.objects.filter(document=document): # TODO is_ai?
        assignments[sa.subject].append({"indexer": sa.indexer.ai_name, "score": sa.score})

    subj_ = list(assignments.keys())
    
    # TODO fix later
    topkats = kb.top_categories()
    topkats_inv = dict((v,k) for k, v in topkats.items())
    subj_labels = kb.labels(subj_)
    categories = kb.categories(subj_, return_type='uri')
    relations_ = kb.relations(subj_)
    
    _links_by_target = dict((rel["target"], rel) for rel in relations_ if rel["relation"] == "BT")
    
    # >>>
    _topkats_active = set(k for ks in categories.values() for k in ks)
    for katuri in _topkats_active:
        code = topkats_inv[katuri]
        nodes.append({"group": code, "id": katuri, "type": "thsys"})
    for curi in subj_:
        nodes.append({"group": 0, "id": curi, "type": "descriptor"})
        for k in categories[curi]:
            if curi in _links_by_target:
                _rel = _links_by_target[curi]
                # if _rel["type"] == "BT":
                links.append({"source": _rel["source"], "target": curi})
            else:
                links.append({"source": k, "target": curi})
    # <<<
    
    jdata = {
        "external_id": document.external_id,
        "nodes": nodes,
        "links": links,
        "topkats": topkats,
        "labels": subj_labels,
        "categories": categories,
        "relations": relations_,
        "status": 'OK'
    }
    return JsonResponse(jdata)
    

# ---- STAFF STUFF -------------------------- #

def j_list_reviews(external_id, ai=None):
    document = get_object_or_404(Document, external_id=external_id)
    dbrevs = Review.objects.filter(document=document)
    if ai:
        dbrevs = dbrevs.filter(ai=ai)
    revdict = dict((r.id, {
            "id": r.id, 
            "by": r.reviewer.username,
            "ai": r.ai.ai_name,
            "total_rating": r.total_rating
    }) for r in dbrevs)
    # reviewers = [r.by for rid, r in revdict.items()]
    ratdict = defaultdict(dict)
    for rev in dbrevs:
        for rat in SubjectLevelReview.objects.filter(review=rev): # rev.ratings.all():
            _rattup = (rev.reviewer.username, rat.value)
            sa = rat.subject_assignment
            _ratdata = ratdict[sa.subject]
            _ratdata["subject_ref"] = sa.subject
            _ratdata["rating"] = _ratdata.get("rating", []) + [_rattup]
            _ratdata["is_added"] = sa.indexer.is_human()
    kos = ThesaurusApi.create_from_db()
    for k, v in kos.labels(ratdict.keys()).items():
        ratdict[k]["label"] = v
    jdata = {
        "external_id": document.external_id,
        "reviews": revdict,
        "ratings": ratdict
    }
    return jdata

@staff_member_required
def list_reviews(request, external_id):
    """
    list all reviews available for a single document.
    
    return json data
    """
    # TODO HANDLE multiple AIs !
    jdata = j_list_reviews(external_id)
    return JsonResponse(jdata)

@staff_member_required
def export_collection_reviews(request, collection_id, ai_name):
    if ai_name == None:
        ai_name = request.GET.get('ai_name', SubjectIndexer.get_main_ai().ai_name)
    ai = SubjectIndexer.objects.get(ai_name=ai_name) # TODO optionally pass ai via request.GET
    collection = get_object_or_404(Collection, id=collection_id)
    qs_revws = Review.objects.filter(document__in=collection.documents.all(), ai=ai)
    
    o_format = request.GET.get('export', 'json').lower()
    if o_format == 'json':
#        jdata = gather_analysis_data(qs_revws)
        docs_unique = set(rev.document.external_id for rev in qs_revws)
        jdata = dict((extid, j_list_reviews(extid, ai)) for extid in docs_unique)
        json_data = {"analyis_metadata": {
                        "collection": collection_id, "collection_name": collection.name, "ai": ai_name
                     }, "payload": jdata
         }
        response = JsonResponse(json_data, json_dumps_params={"indent": 2})
        fnm = "export-reviews.json"
        response['Content-Disposition'] = 'attachment; filename="%s"' % (fnm,)
        return response
    raise Http404("illegal export format")

@staff_member_required
def export_eval_collection(request, collection_id, ai_name):
    ai = SubjectIndexer.get_main_ai()
    collection = get_object_or_404(Collection, id=collection_id)
    rvws = Review.objects.filter(document__in=collection.documents.all(), ai=ai)
    tbl = tbl_collection_reviews(rvws)
    tblagg = aggregate_tbl_collection_reviews(tbl)
    df = tblagg
    o_format = request.GET.get('export', 'json').lower()
    if o_format == 'csv':
        response = HttpResponse(content_type="text/csv")
        fnm = "export-reviews-aggregated_level_2.csv"
        response['Content-Disposition'] = 'attachment; filename="%s"' % (fnm,)
        df.loc["collection"] = collection.name
        df.loc["ai"] = ai.ai_name
        df.to_csv(response)
        return response
    elif o_format == 'json':
        pass
    else:
        raise Http404("illegal export format")
    df_data = df.to_dict(orient="records")
    json_data = {"collection": collection_id,
                 "ai": ai_name,
                 "tbl": df_data
     }
    return JsonResponse(json_data, json_dumps_params={"indent": 2})

def aggregate_tbl_collection_reviews(df):
    """
    compute means for evaluation,
    by aggregating a result of tbl_collection_reviews
    """
    dfagg = df.drop(labels=["reviewer"], axis=1).groupby(["external_id"], axis=0).mean()
    dfagg = dfagg
    dfagg_agg = dfagg.mean(axis=0)
#        df.rename(lambda si: 'avg_' + str(si), axis='index') ## newer PANDAS
    dfagg_agg = dfagg_agg.rename_axis(lambda si: 'avg_' + str(si), axis='index') ## older PANDAS
    dfagg_agg.loc["n_rev"] = df.shape[0]
    dfagg_agg.loc["n_doc"] = df.external_id.unique().shape[0]
    dfagg_agg.columns = ['key', 'value']
    return dfagg_agg

@staff_member_required
def export_tbl_collection_reviews(request, collection_id, ai_name):
    if ai_name == None:
        ai_name = request.GET.get('ai_name', SubjectIndexer.get_main_ai().ai_name)
    ai = SubjectIndexer.objects.get(ai_name=ai_name) # TODO optionally pass ai via request.GET
    collection = get_object_or_404(Collection, id=collection_id)
    qs_revws = Review.objects.filter(document__in=collection.documents.all(), ai=ai)
    df = tbl_collection_reviews(qs_revws)
    o_format = request.GET.get('export', 'json').lower()
    if o_format == 'csv':
        response = HttpResponse(content_type="text/csv")
        fnm = "export-reviews-aggregated_level_1.csv"
        response['Content-Disposition'] = 'attachment; filename="%s"' % (fnm,)
        df.to_csv(response, index=False)
        return response
    elif o_format == 'json':
        pass
    else:
        raise Http404("illegal export format")
    df_data = df.to_dict(orient="records")
    json_data = {"collection": collection_id,
                 "ai": ai_name,
                 "tbl": df_data
     }
    return JsonResponse(json_data, json_dumps_params={"indent": 2})

def tbl_collection_reviews(qs_revws):
    """
    Create a dataframe that enables evaluations like precision/recall (similar to TPs, FPs, etc.)
    
    > columns, in that order:
        external_id ~ document id
        reviewer
        total_rating ~ document-level rating
        [total_numeric ~ document-level rating, mapped to a numerical value]
        n_p2 ~ really helpful
        n_p1 ~        helpful 
        n_0  ~        fair
        n_n1 ~        harmful
        n_miss ~      missing
        precision_...
        precision_...
        recall
    
    return a table that lists these figures for each review from queryset qs_revws
    """
    qset = qs_revws # Review.objects.filter(id=14)
    qset = qset.annotate(np2=Count("ratings", filter=
                                   Q(subjectlevelreview__value="reallyhelpful",
                                     ratings__indexer=models.F("ai"))))
    qset = qset.annotate(np1=Count("ratings", filter=Q(subjectlevelreview__value="helpful")))
    qset = qset.annotate(n0=Count("ratings", filter=Q(subjectlevelreview__value="fair")))
    qset = qset.annotate(nharm=Count("ratings", filter=Q(subjectlevelreview__value="harmful")))
    qset = qset.annotate(nai=Count("ratings", filter=Q(ratings__indexer=models.F("ai"))))
    qset = qset.annotate(nadded=Count("ratings", filter=Q(ratings__indexer__user=models.F("reviewer"))))
#    print(qset.query)
#    r1 = qset.first()
#    print("%s, p=%d n=%d m=%d" % (str(r1), r1.np1 + r1.np2, r1.nharm, r1.nadded))
    df = pd.DataFrame.from_records(
            [(row.document.external_id, 
              row.reviewer.id,
              row.total_rating,
              row.np2, 
              row.np1, 
              row.n0, 
              row.nharm, 
              row.nadded) for row in qset],
            columns=("external_id", "reviewer", "total_rating", "n_p2", "n_p1", "n_0", "n_n1", "n_miss")
            )
    df["precision_012"] = df.eval("(n_p2 + n_p1 + n_0) / (n_p2 + n_p1 + n_0 + n_n1)")
    df["precision_12"] = df.eval("(n_p2 + n_p1) / (n_p2 + n_p1 + n_0 + n_n1)")
    df["recall"] = df.eval("(n_p2 + n_p1) / (n_p2 + n_p1 + n_miss)")
    return df.sort_values(by=["external_id", "reviewer"])


@staff_member_required
def compare_collection(request, name):
    """
    compare all document-level reviews for each document of a collection.
    
    consistency/agreement measure:
    very basic implementation, it makes sense that more sophisticated analysis 
    should be performed externally, offline, which allows more flexibility and
    customization.
    """
    # TODO need to restrict to specific AI !
    coldbo = get_object_or_404(Collection, name=name)
    reviews = Review.objects.filter(document__in=coldbo.documents.all()) # .filter(reviewer=user)
    do_pairwise = request.GET.get("pairwise", "False").lower() not in ["false", "0"]
    jdata = gather_analysis_data(reviews, do_pairwise=do_pairwise)
    jdata["collection"] = name
    return JsonResponse(jdata)

def gather_analysis_data(reviews, ai=None, do_pairwise=False):
    ## TODO NOTE: maybe better apporach: create pandas dataframe from simple query, then merge...
    revdocs = Document.objects.filter(external_id__in=reviews.values_list("document", flat=True))
    actrevr = list(set(reviews.values_list("reviewer__id", flat=True)))
    agreement = defaultdict(dict)    
    if do_pairwise:
        agreement = _compare_reviewers_reviews_pairwise(actrevr, reviews)
    else:
        for doc in revdocs:
            _revs = reviews.filter(document=doc)
            n_reviews = _revs.count()
            _rats = _revs.values_list("total_rating", flat=True)
            n_disagreement = len(set(_rats)) - 1
            total_ratings = Counter(_rats)
            agreement[doc.external_id] = {
                    "n_reviews": n_reviews, 
                    "n_disagreement": n_disagreement,
                    "total_ratings": total_ratings
            }
    jdata = {
#        "collection": name,
        "active_reviewers": actrevr,
        "n_reviews": reviews.count(),
        "n_doc_unique": revdocs.count(),
        "agreement": agreement
    }
    return jdata
    

def _compare_reviewers_reviews_pairwise(actrevr, reviews):
    """
    for given active reviewers (actrevr) and a set of reviews,
    compute agreement,
    only considering documents that both reviewers have reviewed.
    """
    agreement = defaultdict(dict)
    _mapdoc = lambda docid: Document.objects.get(external_id=docid)
    ## fetch pair-wise reviews
    for hid1 in actrevr:
        for hid2 in actrevr:
            revs1 = reviews.filter(reviewer=User.objects.get(id=hid1))
            revs2 = reviews.filter(reviewer=User.objects.get(id=hid2))
            docs_share = revs1.values_list("document", flat=True).intersection(revs2.values_list("document", flat=True))
            docs_share = list(map(_mapdoc, docs_share))
            _cmp = [(doc.external_id, revs1.get(document=doc).total_rating, revs2.get(document=doc).total_rating) for doc in docs_share]
            evidence = len(_cmp)
            _agreement = sum([it[1] == it[2] for it in _cmp]) / evidence if evidence > 0 else -1
            agreement[hid1][hid2] = {"agreement": _agreement, "n_reviews": evidence, "documents": _cmp}
    return agreement

