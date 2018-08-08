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
URL patterns provided by this app.
"""
__author__ = "Martin Toepfer"

from django.urls import path
#from django.views.generic import RedirectView
#from django.shortcuts import redirect

from . import views
from . import api

# reminder:
# path(
#    route, # url_pattern
#    view, # function to call with HttpRequest object as argument + captured values
#    kwargs, # arbitrary keyword attribute arguments passed as a dictionary
#    name, # name to refer to this URL, especially from templates
# )
# reminder: order is relevant! first match first served!
urlpatterns = [
    ## VIEWS
    path('', views.index, name='index'),
    path('about', views.about, name='about'),
    # login required:
    path('documents', views.DocumentListView.as_view(), name='documents'),
    path('collections', views.CollectionListView.as_view(), name='collections'),
    path('collection/analysis/<collection_id>', views.collection_analysis_view, name='collection_analysis'),
    path('collection/<collection_id>', views.collectionDocumentListView, name='collection'),
    path('review/compare/<external_id>', views.compare_review, name='compare_review'),
    path('review/<external_id>', views.review, name='review'), # views.ReviewView.as_view()
    
    ## DATA API
    # data api paths return json objects
    #
    path('api/document/<external_id>', api.document, name='api_document'),
    path('api/explain/<external_id>', api.explain, name='api_explain'),
    path('api/graph/<external_id>', api.subjects_graph, name='api_graph'),
    path('api/list/reviews/doc/<external_id>', api.list_reviews, name='api_list_reviews'),
    path('api/list/reviews/collection/<collection_id>/<ai_name>', api.export_collection_reviews, name='api_list_collection_reviews'),
    path('api/eval/collection/<collection_id>/<ai_name>', api.export_eval_collection, name='api_evaldata_collection'),
    path('api/eval/reviews/<collection_id>/<ai_name>', api.export_tbl_collection_reviews, name='api_list_evaldata'),
    path('api/compare/collection/<name>', api.compare_collection, name='api_compare_collection'),
    path('api/search_kos', api.search_kos, name='search_kos'),
    
    ## WIDGET API
    #

    ## REDIRECTS
    # path('sourcecode', RedirectView.as_view(url='NOT_IMPLEMENTED', permanent=True), name='sourcecode')
    # path('sourcecode', redirect('http://NOT_IMPLEMENTED'), name='sourcecode')
    path('doc/external/<external_id>', views.doc_redirect, name='doc_external'),

    # done: login, realized by middleware ...
    # done: admin sites, mostly realized by middleware, see:
    #           https://docs.djangoproject.com/en/2.0/ref/contrib/admin/#reversing-admin-urls
]
