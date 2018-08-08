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
Created on Sat Mar 17 13:19:35 2018

@author: Martin Toepfer
"""

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone as tz
from django.db.utils import OperationalError

from zaptain_rt_app.models import RtConfig, Document, Collection, Review, Guideline, SubjectIndexer
from zaptain_rt_app.tests import TestContentManager

# see:
# https://docs.djangoproject.com/en/2.0/howto/custom-management-commands/

class Command(BaseCommand):
    help = 'Reset the db to a specific test state.'

    def handle(self, *args, **options):
        tcm = TestContentManager()
        tcm.clear()
        self.stdout.write(self.style.SUCCESS('Deleted objects.'))
        tcm.populate_db()
        
        self.stdout.write(self.style.SUCCESS('Successfully reset the db to the test state.'))