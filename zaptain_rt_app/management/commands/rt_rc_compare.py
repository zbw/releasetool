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

@author: Martin Toepfer, 2018
"""

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone as tz
from django.db.utils import OperationalError

from zaptain_rt_app.models import ReleaseCandidate

import pandas as pd

# see:
# https://docs.djangoproject.com/en/2.0/howto/custom-management-commands/

class Command(BaseCommand):
    help = 'Very basic comparison of release candidates.'
    
    def add_arguments(self, parser):
        parser.add_argument('rc_ID', nargs=2, help="exactly two ids of release candidates")

    def handle(self, *args, **options):
        _LNL = 40
        _LN_STRONG = "=" * _LNL
        _LN = "-" * _LNL
        
        rcs = ReleaseCandidate.objects.filter(name__in=options['rc_ID'])
        rc1, rc2 = rcs.first(), rcs.last()
        ids1 = rc1.get_document_ids()
        ids2 = rc2.get_document_ids()
        
        
        self.stdout.write(_LN_STRONG)
        self.stdout.write("#docs %s = %d" % (rc1.name, len(ids1)))
        self.stdout.write("#docs %s = %d" % (rc2.name, len(ids2)))
        self.stdout.write("overlap = %d" % (len(set(ids1).intersection(ids2))))
        self.stdout.write(_LN)
        ser1 = pd.Series(map(lambda t: len(t["subjects"]), rc1.iter_statements()))
        ser2 = pd.Series(map(lambda t: len(t["subjects"]), rc2.iter_statements()))
        # avg_n_subjs = .mean()
        self.stdout.write("avg. num. of subjects '%s' = %.3f" % (rc1.name, ser1.mean()))
        self.stdout.write("avg. num. of subjects '%s' = %.3f" % (rc2.name, ser2.mean()))
        self.stdout.write(_LN_STRONG)
    