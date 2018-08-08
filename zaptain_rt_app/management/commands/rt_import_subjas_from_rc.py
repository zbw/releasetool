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
Import 
- specific documents and their subject indexing from a release candidate
- and put them in a collection, which will be cleaned in advance.

@author: Martin Toepfer, 2018
"""

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone as tz
from django.db.utils import OperationalError, IntegrityError

from django.contrib.auth.models import User
from zaptain_rt_app.models import RtConfig, Document, SubjectIndexer, SubjectAssignment, Collection, Guideline
from zaptain_rt_app.models import SubjectLevelReview, Review
from zaptain_rt_app.models import DOCLEVEL_CHOICES, SUBJLEVEL_CHOICES
from zaptain_rt_app.models import ReleaseCandidate

import pandas as pd

# see:
# https://docs.djangoproject.com/en/2.0/howto/custom-management-commands/

class Command(BaseCommand):
    help = 'Create controlled sample from a release candidate.'
    
    def add_arguments(self, parser):
        parser.add_argument('--f_whitelist', required=True, help="external document ids file")
        parser.add_argument('--collection', required=True, help="collection name")
        parser.add_argument('--rc', default=None, help="release candidate")
        # action=store_true

    def handle(self, *args, **options):
        f_whitelist = options['f_whitelist']
        collection_nm = options['collection']
        rc_nm = options['rc']
        
        rc = ReleaseCandidate.objects.get(name=rc_nm)
        col = Collection.objects.get(name=collection_nm)
        col.documents.all().delete()
        
        with open(f_whitelist) as fin:
            docids = [docid.strip() for docid in fin]
        rc.import_records(docids, collection=col)