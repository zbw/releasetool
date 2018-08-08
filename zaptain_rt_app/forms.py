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
Specials forms, in particular for the reviewing view.
"""
__author__ = "Martin Toepfer"

from django import forms
from django.utils.encoding import smart_text
from django.utils.safestring import mark_safe

from django.forms import BaseFormSet, formset_factory

from .models import DOCLEVEL_CHOICES, SUBJLEVEL_CHOICES


# see:
# https://docs.djangoproject.com/en/2.0/ref/forms/
# https://docs.djangoproject.com/en/2.0/topics/forms/formsets/


# https://docs.djangoproject.com/en/2.0/ref/forms/widgets/#radioselect
# https://docs.djangoproject.com/en/2.0/ref/forms/fields/#django.forms.ChoiceField.choices

## DOC-LEVEL: ...

class DocumentRatingWidget(forms.RadioSelect):
    input_type = 'radio'
    template_name = 'django/forms/widgets/radio.html'
    option_template_name = 'zaptain_rt/widget_documentrating.html'
    # formerly: option_template_name = 'django/forms/widgets/radio_option.html'

class DocumentRatingForm(forms.Form):
    rating = forms.ChoiceField(widget=DocumentRatingWidget, 
                                  choices=DOCLEVEL_CHOICES, label="Conclusion")
    
    def disable(self):
        self.fields['rating'].disabled = True

## SUBJ-LEVEL: ...

class SubjectRatingWidget(forms.RadioSelect):
    input_type = 'radio'
    template_name = 'django/forms/widgets/radio.html'
    option_template_name = 'zaptain_rt/widget_subjectrating.html'

class SubjectRatingForm(forms.Form):
    uri = forms.CharField(widget=forms.HiddenInput())
    rating = forms.ChoiceField(widget=SubjectRatingWidget, 
                                  choices=SUBJLEVEL_CHOICES, label="Rating")
    
    def disable(self):
        self.fields['rating'].disabled = True

def subjrating_formsetfactory():
    return formset_factory(SubjectRatingForm, extra=0)


### MISSING SUBJECTS ###

class SubjectMissingForm(forms.Form):
    uri = forms.CharField(widget=forms.HiddenInput())

def missingsubj_formsetfactory():
    return formset_factory(SubjectMissingForm, extra=0)
