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

# see:
# https://docs.djangoproject.com/en/2.0/howto/custom-management-commands/

class Command(BaseCommand):
    help = 'List and compute infos for uploaded ReleaseCandidates.'
    
    def add_arguments(self, parser):
        parser.add_argument('rc_ID', nargs='*', help="ids of ")

    def handle(self, *args, **options):
        _LNL = 40
        _LN_STRONG = "=" * _LNL
        _LN = "-" * _LNL
        self.stdout.write(_LN_STRONG)
        self.stdout.write("release candidate:")
        rcs = ReleaseCandidate.objects.all()
        if len(options['rc_ID']) > 0:
            # print("OPTION IDS", options['rc_ID'])
            rcs = ReleaseCandidate.objects.filter(name__in=options['rc_ID'])
        for dbrc in rcs:
            self.stdout.write(_LN)
            self.stdout.write("name = %s" % (dbrc.name,))
            self.stdout.write("file = %s" % (dbrc.file,))
            self.stdout.write("url  = %s" % (dbrc.file.url,))
            
            docids = dbrc.get_document_ids()
            self.stdout.write("# lns= %s" % (len(docids),))
        
        self.stdout.write(_LN_STRONG)
        self.stdout.write(self.style.SUCCESS('Done.'))
    