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
The releasetool's views
"""
__author__ = "Martin Toepfer"

from django.urls import reverse
from django.shortcuts import render, get_object_or_404
from django.shortcuts import redirect
from django.http import HttpResponse, HttpResponseRedirect, JsonResponse
from django.template import RequestContext
from django.core.exceptions import ObjectDoesNotExist

from django.views import generic
# from django.forms import formset_factory

from django.db import models
from django.db import IntegrityError
from django.db.models import Q, Count

from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator

from django.db import transaction

from django.contrib import messages

import json
from urllib.parse import urlencode

from collections import defaultdict
import re

from .models import RtConfig, Collection, Document, Guideline
from .models import ReviewerWrapper, Review, SubjectIndexer, SubjectLevelReview # ...
from .online_configuration import RtConfigChoices
from .online_configuration import CK_MAIN_AI
from .online_configuration import CK_CATALOG_API_PATTERN
from .online_configuration import CK_THES_DESCRIPTOR_TYPE, CK_THES_CATEGORY_TYPE, CK_THES_SPARQL_ENDPOINT
from .catalog_connection import CatalogApi
from .thesaurus_connection import ThesaurusApi

from .forms import DocumentRatingForm, SubjectRatingForm, subjrating_formsetfactory, missingsubj_formsetfactory, DOCLEVEL_CHOICES
from .forms import SubjectMissingForm

from .api import basecontext
from .api import list_reviews
from .api import compare_collection
from .api import tbl_collection_reviews, aggregate_tbl_collection_reviews, gather_analysis_data

class HttpResponseNotImplementedError(HttpResponse):
    status_code = 501

# see:
# https://docs.djangoproject.com/en/2.0/intro/tutorial03/
# https://docs.djangoproject.com/en/2.0/topics/templates/

#
# Views:
#
def index(request):
    """
    The __welcome__ page of the project.
    """
    context = dict()
    return render(request, 'zaptain_rt/index.html', context)

def about(request):
    """
    Information __about__ the webtool.
    """
    context = dict()
    return render(request, 'zaptain_rt/about.html', context)

def doc_redirect(request, external_id):
    rqctx = basecontext(request, external_id=external_id)
    dbdoc = rqctx["dbdoc"]
    url = dbdoc.format_weblink()
    return redirect(url)

# use generic views, see:
# https://docs.djangoproject.com/en/2.0/intro/tutorial04/#amend-views
# https://developer.mozilla.org/en-US/docs/Learn/Server-side/Django/Generic_views
@method_decorator(login_required, name='dispatch')
class CollectionListView(generic.ListView):
    model = Collection
    template_name = 'zaptain_rt/collection_list.html'
    
    def get_queryset(self):
        user = self.request.user
        collections = Collection.objects.annotate(
                Count('documents'), 
                myreviews=Count('documents__review', filter=Q(documents__review__reviewer=user)))
        return collections

@method_decorator(login_required, name='dispatch')
class DocumentListView(generic.ListView):
    model = Document
    template_name = 'zaptain_rt/document_list.html'

@login_required
def collectionDocumentListView(request, collection_id):
    template_name = 'zaptain_rt/collection_document_list.html'
    collection = get_object_or_404(Collection, id=collection_id)
    user = request.user
    
    reviews = Review.objects.filter(reviewer=user).filter(document__in=collection.documents.all())
    todo_list = collection.documents.exclude(review__in=Review.objects.filter(reviewer=user))
    context = {
        "collection": collection,
        "todo_documents": todo_list,
        "reviews": reviews,
    }
    return render(request, template_name, context)


# see: https://docs.djangoproject.com/en/2.0/intro/tutorial04/
@login_required
def review(request, external_id):
    """
    Essential view that document subject indexing reviewing
    service.
    """
    rqctx = basecontext(request, external_id=external_id)
    dbdoc = rqctx["dbdoc"]
    collection_id = request.GET.get('collection')
    try:
        collection = Collection.objects.get(id=collection_id)
    except ObjectDoesNotExist:
        # TODO fix quick fix
        collection = dbdoc.collection_set.first()
    
    _predecessor = None
    _successor = None
    if collection is not None:
        _predecessor = collection.documents.filter(external_id__lt=dbdoc.external_id).last()
        _successor = collection.documents.filter(external_id__gt=dbdoc.external_id).first()
    
    ## DETERMINE MAIN AI:
    ai_main = SubjectIndexer.get_main_ai()
    
    dbreview = None
    try:
        dbreview = Review.objects.get(reviewer=request.user, document=dbdoc, ai=ai_main)
    except Review.DoesNotExist:
        pass
    
    SubjectRatingFormset = subjrating_formsetfactory()
    SubjectMissingFormset = missingsubj_formsetfactory()
    
    hi = rqctx['reviewer'].as_indexer()
    assignments = dbdoc.subjectassignment_set.filter(indexer=ai_main)
    subjs_infodemanded = set(sa.subject for sa in dbdoc.subjectassignment_set.filter(indexer__user__isnull=True))
    
    subjratings_form = None
    subjmissing_form = None
    if request.method == 'POST':
        # POST REQUEST, JSON >> SAVE REVIEW
        docrating_form = DocumentRatingForm(request.POST, request.FILES, prefix='dor')
        subjratings_form = SubjectRatingFormset(request.POST, request.FILES, prefix='sar')
        subjmissing_form = SubjectMissingFormset(request.POST, request.FILES, prefix="smis")
        
        if docrating_form.is_valid():
            doclevel_choice = docrating_form['rating'].value()
            _revargs = {"ai": ai_main,
                        "reviewer": request.user, 
                        "document": dbdoc, 
                        "total_rating": doclevel_choice, # doclevel_idx,
                        "guideline": Guideline.objects.latest()}
            ## ONLY SAVE IF SKIP OR ALL VALID
            _success = False
            
            try:
                with transaction.atomic():
                    if doclevel_choice.startswith('skip'):
                        ##
                        #
                        # for SKIP: DO NOT CREATE ANY SUBJ-LEVEL RATINGs!
                        Review.objects.create(**_revargs)
                        _success = True
                    else:
                        if subjratings_form.is_valid(): # already checked: docrating_form.is_valid()
                            # create review object:
                            revnew = Review.objects.create(**_revargs)
                            # create subject rating objects:
                            for srf in subjratings_form:
                                subject = srf['uri'].value()
                                value = srf['rating'].value()
                                sa = dbdoc.subjectassignment_set.get(subject=subject, indexer=ai_main)
                                SubjectLevelReview.objects.create(
                                        subject_assignment=sa,
                                        review=revnew,
                                        value=value
                                )
                            # create missing subject objects:
                            hi.assign_scored(dbdoc, 
                                             dict((smf['uri'].value(), 1.0) for smf in subjmissing_form),
                                             review=revnew)
                            for smf in subjmissing_form:
                                sa = dbdoc.subjectassignment_set.get(
                                        subject=smf['uri'].value(), indexer=hi)
                                SubjectLevelReview.objects.create(
                                        subject_assignment=sa,
                                        review=revnew,
                                        value='reallyhelpful'
                                )
                            _success = True
            except IntegrityError as err:
                messages.error(request, 'DB integrity error! Have you already reviewed this document?')
            
            if _success:
                # redirect >> review next document for user for collection
                if _successor:
                    _nexturl = reverse("review", kwargs={"external_id": _successor.external_id})
                    return HttpResponseRedirect(_nexturl + "?" + urlencode({"collection_id": collection.id}))
                # if next document not available, redirect to collection overview
                return HttpResponseRedirect(reverse("collection", kwargs={"collection_id": collection.id}))
    else:
        # in particular: GET REQUEST
        _initial_doc_level = ""
        _initial_subjrating = []
        _initial_subjmissing = []
        if dbreview:
            ## try to recover data for form widgets:
            _initial_doc_level = dbreview.total_rating
            _initial_subjrating = []
            _initial_subjmissing = [{"uri": sa.subject} for sa in dbdoc.subjectassignment_set.filter(indexer=hi)]
            for sa in assignments:
                try:
                    subjrating = SubjectLevelReview.objects.get(review=dbreview, subject_assignment=sa)
                    _initial_subjrating.append({"uri": sa.subject, "rating": subjrating.value})
                except ObjectDoesNotExist:
                    _initial_subjrating.append({"uri": sa.subject})
        else:
            # not reviewed before...
            for sa in assignments:
                _initial_subjrating.append({"uri": sa.subject})
        
        subjratings_form = SubjectRatingFormset(initial=_initial_subjrating, prefix='sar')
        subjmissing_form = SubjectMissingFormset(initial=_initial_subjmissing, prefix="smis")
        docrating_form = DocumentRatingForm(initial={"rating": _initial_doc_level}, prefix='dor')
        if dbreview:
            # DISABLE INPUT:
            docrating_form.disable()
            for form in subjratings_form:
                form.disable()
    
    for sf in subjmissing_form:
        subjs_infodemanded.add(sf['uri'].value())
    
    # ENHANCE subj forms with subj infos:
    subj_rowdata = []
    subjmissing_rowdata = []
    subj_labels = rqctx['kos'].labels(list(subjs_infodemanded))
    subj_categories = rqctx['kos'].categories(list(subjs_infodemanded))
    for sf in subjratings_form:
        k = sf['uri'].value()
        info = {"uri": k, "label": subj_labels[k], "kats": subj_categories[k]}
        subj_rowdata.append({"form": sf, "info": info})
    for sf in subjmissing_form:
        k = sf['uri'].value()
        info = {"uri": k, "label": subj_labels[k], "kats": subj_categories[k]}
        subjmissing_rowdata.append({"form": sf, "info": info})
    
    guideline_link = "" # TODO provide default guideline msg in static folder
    try:
        guideline_link = Guideline.objects.latest().link
    except ObjectDoesNotExist:
        pass
    
    explanation = dict((subj, {"support": [], "label": subj_labels[subj]}) for subj in subjs_infodemanded)
    for sa in dbdoc.subjectassignment_set.filter(indexer__user__isnull=True):
        explanation[sa.subject]["support"].append({"indexer": sa.indexer.ai_name, "score": sa.score})
    explanation = list(explanation.items())
    
    show_graph = request.GET.get('graph', False) or True # TODO introduce admin online param?!
    
    context = {
            "guideline": guideline_link, # latest guideline
            
            "collection": collection,
            "document": dbdoc,
            "docjson": rqctx["jsondoc"],
            "docjson_str": json.dumps(rqctx["jsondoc"], indent=2),
            "collection_slice": (_predecessor, _successor), # paginator_page,
            "progress": rqctx['reviewer'].get_progress_info(collection),
            "explanation": explanation,
            
            "review": dbreview,
            "docrating_form": docrating_form,
            "subjratings_form": subjratings_form,
            "subj_rowdata": subj_rowdata,
            "subjmissing_form": subjmissing_form,
            "subjmissing_rowdata": subjmissing_rowdata,

            "extended_form": request.GET.get('extended_form', False),
            "debug": request.GET.get('debug', False),
            
            "show_graph": show_graph
    }
    return render(request, 'zaptain_rt/review.html', context)

#----# admin views: #----#
    
_print_obj = lambda d: print("=" * 80, d, "=" * 80) # for debugging

@staff_member_required
def collection_analysis_view(request, collection_id):
    ## !!
    ## >> Analysis depends on RC ==> MAIN-AI !!!
    ## !!
    ai_name = request.GET.get('ai_name', None)
    ai = SubjectIndexer.get_main_ai() if ai_name is None else get_object_or_404(SubjectIndexer, ai_name=ai_name)
    collection = get_object_or_404(Collection, id=collection_id)
    rvws = Review.objects.filter(document__in=collection.documents.all(), ai=ai)
    
    jr = json.dumps(gather_analysis_data(rvws, ai=ai))
    jrj = json.loads(jr)
    
    for k, v in jrj["agreement"].items():
        v["dbdoc"] = get_object_or_404(Document, external_id=k)
    n_rejected = sum(["reject" in x["total_ratings"] for x in jrj["agreement"].values()])
    docs_todo = collection.documents.exclude(external_id__in=jrj["agreement"].keys())
    
    ## compute recall etc.!
    tbl = None
    tblagg = None
    if rvws.count() > 0:
        tbl = tbl_collection_reviews(rvws)
        tblagg = aggregate_tbl_collection_reviews(tbl)
    
    context = {
        "ai": ai,
        "collection": collection,
        "docls_data": jrj,
        "without_review": docs_todo,
        "n_rejected": n_rejected,
        "df_aggagg": tblagg
    }
    return render(request, "zaptain_rt/collection_analysis.html", context)

@staff_member_required
def compare_review(request, external_id):
    """
    Show a comparison of all available reviews for a specific document.
    """
    context = basecontext(request, external_id=external_id)
    jr = list_reviews(request, external_id)
    context["compare_data"] = json.loads(jr.content.decode('utf-8'))
    # TODO HANDLE multiple AIs !
    return render(request, 'zaptain_rt/compare_review.html', context)
