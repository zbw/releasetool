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

from django import template
from django.template.defaultfilters import stringfilter
from django.utils.html import conditional_escape
from django.utils.safestring import mark_safe
from django.urls import reverse

from ..models import Document

register = template.Library()

@register.filter(needs_autoescape=True)
def mk_link_external(doc, autoescape=True):
    """
    for a document, create a html link to the external resource
    
    usage example:
        {{ dbdoc | mk_link_external }}
    """
    if not isinstance(doc, Document):
        # raise AttributeError("argument of wrong type passed to mk_link_external filter")
        raise TypeError("mk_link_external filter expected Document type, but was " + str(type(doc)))
    mapfun = conditional_escape if autoescape else lambda z: z
    url = mapfun (doc.format_weblink())
    extid = mapfun (doc.external_id)
    linkelem = '''<a href="{}">{}</a>'''.format(url, extid)
    return mark_safe(linkelem)

@register.filter(needs_autoescape=True)
def mk_link_internal(doc, autoescape=True):
    """
    for a document, create a html link to the internal reviewing interface.
    
    usage example:
        {{ dbdoc | mk_link_internal }}
    """
    if not isinstance(doc, Document):
        raise TypeError("mk_link_internal filter expected Document type, but was " + str(type(doc)))
    mapfun = conditional_escape if autoescape else lambda z: z
    url = mapfun (reverse("review", kwargs={"external_id": doc.external_id}))
    extid = mapfun (doc.external_id)
    linkelem = '''<a href="{}">{}</a>'''.format(url, extid)
    return mark_safe(linkelem)