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
The database model of the releasetool app.

Notes on implementation:
- "missing subjects", subject terms that reviewers added because they were missing

"""
__author__ = "Martin Toepfer"

from django.db import models
from django.db import transaction
from django.db.models import Q, F
from django.contrib.auth.models import User
from django.core.validators import URLValidator
from django.core.paginator import Paginator
from django import forms

from django.core.exceptions import ObjectDoesNotExist

from .exceptions import EmptySampleException

from .online_configuration import RtConfigKeys, RtConfigChoices
from .online_configuration import CK_MAIN_AI
from .online_configuration import CK_DOCUMENT_WEBLINK_PATTERN
from .online_configuration import CK_CATALOG_API_PATTERN

import pandas as pd

#
# see also:
#   https://docs.djangoproject.com/en/2.0/ref/models/fields/#foreignkey
#   https://docs.djangoproject.com/en/2.0/ref/models/fields/#manytomanyfield
#   https://docs.djangoproject.com/en/2.0/topics/db/models/#intermediary-manytomany
#
# 
# https://docs.djangoproject.com/en/2.0/topics/db/queries/
#

class PermissiveUrlForm(forms.URLField):
    pat_scheme = r"http[s]?"
    custom_urlpat = pat_scheme + ":" + r"\S+"
    default_validators=[URLValidator(regex=custom_urlpat)]

class PermissiveUrlField(models.URLField):
    pat_scheme = r"http[s]?"
    custom_urlpat = pat_scheme + ":" + r"\S+"
    default_validators=[URLValidator(regex=custom_urlpat)]
    
    def formfield(self, **kwargs):
        defaults = {
            'form_class': PermissiveUrlForm, # forms.URLField,
        }
        defaults.update(kwargs)
        return super().formfield(**defaults)


###############################################################################
###############################################################################
## CONFIGURATION 
###############################################################################


class RtConfig(models.Model):
    """
    releasetool configuration key-value pairs.
    
    See: .online_configuration.RtConfigChoices
    """
    key = models.CharField(max_length=50, choices=RtConfigChoices, primary_key=True)
    value = models.CharField(max_length=200)
    
    help_text = """Keys: %s""" % (repr(RtConfigKeys))
    
    def __str__(self):
        return str({self.key: self.value})
    
    class Meta:
        ordering = ('key',)

###############################################################################
###############################################################################

class SubjectIndexer(models.Model):
    """
    Either a
        * __human__ professional indexer, resembling a specific request.user, or
        * __automaton__, method that automatically assigns subject terms to documents.
    """
    ai_name = models.CharField(max_length=500)
    user = models.ForeignKey(User, on_delete=models.CASCADE, blank=True, null=True)
    
    def is_human(self):
        return not self.user is None
    
    def is_ai(self):
        # SubjectIndexer.objects.exclude(ai_name='')
        return not self.ai_name is None
    
    def assign_scored(self, doc, assignments, review=None, commit=True):
        """
        assign subjects with score to documents for ai_s (automatic subject indexers)
        
        ARGUMENTS
        =========
            assignments: dictionary, subject => score
        """
        if review is None and self.is_human():
            raise Exception() # TODO create new exception type
        sas = list()
        for subj, score in assignments.items():
            kwargs = {"document": doc, "subject": subj, "indexer": self, 
                      "score": score, "review_binding": review}
            if commit:
                sa = SubjectAssignment.objects.create(**kwargs)
            else:
                sa = SubjectAssignment(**kwargs)
            sas.append(sa)
        return sas
    
    def __str__(self):
        if self.is_human():
            return "human:" + self.user.username
        elif self.is_ai():
            return "ai:" + self.ai_name
        return "(AI:%s:%s|H:%s:%s)" % tuple(map(repr, [self.is_ai(), self.ai_name, self.is_human(), self.user]))

    @classmethod
    def get_main_ai(clz):
        ai_main_name = RtConfig.objects.get(key=CK_MAIN_AI).value
        ai_main = clz.objects.get(ai_name=ai_main_name)
        return ai_main


class Guideline(models.Model):
    """
    Instructions for reviewers on how to judge quality.
    
    Typically, this object only represents a specific guideline version,
    and links to external sources for the actual textual content of the guideline.
    
    The releasetool will always use the latest guideline according to pub_data
    to display views, that is, Guideline.objects.latest().
    """
    name = models.CharField(max_length=200)
    pub_date = models.DateTimeField('date published')
    description = models.CharField(max_length=500, blank=True)
    link = PermissiveUrlField(max_length=200, blank=True) # for example, point to corporate wiki
    ## note: maybe provide opportunity to upload a file (PDF) as instructions?! # file = FileField 
    
    def __str__(self):
        return "%s.%s" % (self.name, self.pub_date.strftime("%Y%m%d"))
    
    class Meta:
        ordering = ('name',)
        get_latest_by = "pub_date"


class Document(models.Model):
    """
    A 'Document' typically represents a record of a library catalog, for instance,
    a book, a conference paper, a discussion paper or a journal article, ...
    In the database, it may also refer to a journal or working paper series.
    
    Document records only require an external id, yet at least the title should
    be provided, too.
    Further information (abstract, keywords, etc.) about a 'Document' is requested from a catalog API.
    In fact, titles are also requested from the catalog API, so they are only part of the db for convenience.
    
    has_abstract: 'False' no or unknown availability of an abstract/summary of the resource.
    """
    # choices/constants:
#    AVAILABILITY_YES = 'Y'
#    AVAILABILITY_NO = 'N'
#    AVAILABILITY_UNKNOWN = 'U'
#    CHOICES_AVAILABILITY = ((AVAILABILITY_YES, 'Yes'), (AVAILABILITY_NO, 'No'), (AVAILABILITY_UNKNOWN, 'Unknown'))
    # fields:
    external_id = models.CharField(max_length=50, unique=True, primary_key=True)
    title = models.CharField(max_length=500)
    has_abstract = models.BooleanField(default=False) # models.CharField(max_length=1, choices=AVAILABILITY_YES, default=AVAILABILITY_UNKNOWN)
    doc_type = models.CharField(max_length=50, blank=True)
    broader = models.ManyToManyField("Document", blank=True, related_name='narrower')
    
    def format_weblink(self):
        """
        based on the dynamic configuration, return a link to an external location
        that represents the document.
        """
        try:
            pattern = RtConfig.objects.get(key=CK_DOCUMENT_WEBLINK_PATTERN).value
            return pattern.format(docid=self.external_id)
        except ObjectDoesNotExist:
            return "" # TODO return link to internal error page | use messages middleware?
    
    def format_api_link(self):
        try:
            pattern = RtConfig.objects.get(key=CK_CATALOG_API_PATTERN).value
            return pattern.format(docid=self.external_id)
        except RtConfig.DoesNotExist:
            return "" # TODO return link to internal error page | use messages middleware?
    
    def __str__(self):
        return self.external_id
    
    class Meta:
        ordering = ('external_id',)

class Collection(models.Model):
    """
    A collection of documents.
    
    Collections can overlap.
    """
    name = models.CharField(max_length=300, unique=True)
    description = models.CharField(max_length=500)
    documents = models.ManyToManyField(Document)
    
    def compute_overlap(self, other):
        return self.documents.filter(external_id__in=other.documents.values("external_id")).count()
    
    def count_reviews(self):
        return Review.objects.filter(document__in=self.documents.all()).count()
    
    def __str__(self):
        return self.name


class SubjectAssignment(models.Model):
    """
    Assignment of relevance of a subject to a document.
    
    'Subject' typically refers to a SKOS concept, examples:
        subject = "http://zbw.eu/stw/descriptor/10503-3"
    
    free text can be supported as well in a later version, example:
        subject = "http://mycustomdomain/keyword/Kiel"
    """
    document = models.ForeignKey(Document, on_delete=models.CASCADE)
    subject = models.URLField(max_length=300)
    score = models.DecimalField(max_digits=3, decimal_places=2) # TODO limit 0 <= x <= 1
    indexer = models.ForeignKey(SubjectIndexer, on_delete=models.CASCADE)
    ## add the possibility of binding the assignment to a specific review:
    # in this case, the subject assignment will be deleted when the review is deleted
    # which is useful for "missing" subjects
    review_binding = models.ForeignKey("Review", on_delete=models.CASCADE,
               blank=True, null=True,
               related_name='missing_subjects')
    
    def __str__(self):
        return "%s^%0.2f#%s" % (self.document.external_id, self.score, self.subject)
    
    class Meta:
        unique_together = ("document", "subject", "indexer")

class ReviewerWrapper(object):
    """
    Actually, this is not a real model class. It's just a wrapper around user,
    providing some methods for convenience.
    """
    
    def __init__(self, user):
        self.user = user
    
    def as_indexer(self):
        """
        in order to assign subjects to a document, you need to wrap this user with
        a subjectindexer object.
        """
        try:
            subjidx = SubjectIndexer.objects.get(user=self.user)
        except ObjectDoesNotExist:
            subjidx = SubjectIndexer.objects.create(user=self.user)
        return subjidx
    
    def get_progress_info(self, collection):
        """
        Tell the progress of the reviewer on a given collection.
        
        return dict { "n_review": n_review, "n_total": n_total }
        """
        user = self.user
        if collection is None:
            return {"n_review": -1, "n_total": -1}
        n_total = collection.documents.count()
        n_review = Review.objects.filter(reviewer=user).filter(document__in=collection.documents.all()).count()
        return {"n_review": n_review, "n_total": n_total}
    
    def get_next_document(self, collection=None):
        """
        Return the document that this reviewer should see next from the given collection.
        That is, a document without review.
        """
        # TODO implemented
        user = self.user
        # TODO exclude the current document
        doctodo = Document.objects
        if not collection is None:
            doctodo = collection.documents
        doctodo = doctodo.exclude(review__in=Review.objects.filter(reviewer=user))
        return doctodo.first()


#class ReviewManager(models.Manager):
#    def get_queryset(self):
#        _a_nall = models.Count("ratings")
##        _a_nai = models.Count("ratings", filter=Q(ratings__indexer=F("ai")))
#        _a_nai = models.Count("ratings", filter=Q(ratings__indexer=F("ai")))
#        _a_harmful = models.Count("ratings", filter=Q(subjectlevelreview__value="harmful"))
#        #
#        #
#        qs = super(ReviewManager, self).get_queryset()
##        qs = qs.annotate(n_all=_a_nall)
##        qs = qs.annotate(n_ai=_a_nai)
##        qs = qs.annotate(n_harmful=_a_harmful)
#        return qs

DOCLEVEL_CHOICES = (
    ("skip", "skip"),
    ("reject", "reject"), 
    ("fair", "fair"),
    ("good", "good"))
class Review(models.Model):
    """
    Representation of a complete review that comprises 
      - a total, as well as 
      - subject-level quality judgements.
    
    Reviews are automatically deleted when either 
    their corresponding
    - guideline,
    - document,
    - or reviewer is deleted.
    """
    ai = models.ForeignKey(SubjectIndexer, on_delete=models.CASCADE)
    reviewer = models.ForeignKey(User, on_delete=models.CASCADE)
    document = models.ForeignKey(Document, on_delete=models.CASCADE)
    guideline = models.ForeignKey(Guideline, on_delete=models.CASCADE)
    total_rating = models.CharField(max_length=20, choices=DOCLEVEL_CHOICES)
    ratings = models.ManyToManyField(to=SubjectAssignment, through="SubjectLevelReview")
    
#    objects = ReviewManager()
#    
    def __str__(self):
        return "%s-reviewed-%s" % (self.reviewer, self.document.external_id)
    
    class Meta:
        unique_together = ("reviewer", "document", "ai") # guideline ?


SUBJLEVEL_CHOICES = (("harmful", "harmful"), ("fair", "fair"), ("helpful", "helpful"), ("reallyhelpful", "really helpful"))
class SubjectLevelReview(models.Model):
    """
    Relevancy assessment of a particular subject for a document.
    """
    subject_assignment = models.ForeignKey(SubjectAssignment, on_delete=models.CASCADE)
    review = models.ForeignKey(Review, on_delete=models.CASCADE)
    value = models.CharField(max_length=20, choices=SUBJLEVEL_CHOICES)
    
    class Meta:
        unique_together = ("review", "subject_assignment")


_parse_cell = lambda cell: (cell if ':' in cell else cell + ':1.0').split(':') 

def _sample(docids, size, whiteset=None):
    if whiteset is not None:
        docids = list(whiteset.intersection(docids))
    else:
        docids = docids
    pdser = pd.Series(docids)
    n = min(size, pdser.size)
    if n == 0:
        raise EmptySampleException()
    return pdser.sample(n)

class ReleaseCandidate(models.Model):
    """
    A releasecandidate comprises the complete subject assignments data
    that are tested for usage in opeartive IR.
    
    The data is stored as a file on disk.
    """
    name = models.CharField(max_length=50, primary_key=True)
    description = models.CharField(max_length=500, blank=True)
    pub_date = models.DateTimeField('date published', help_text="""Published means, e.g., upload into releasetool, not published to operative IR system.""")
    file = models.FileField(upload_to='releasecandidates/', help_text="""File content:
        tab-separated values; for each row: first cell = document external id, then subjects""")
    indexer = models.ForeignKey(SubjectIndexer, on_delete=models.CASCADE)
    concept_template = models.CharField(max_length=300, blank=True, null=True, help_text="""str.format template with concept id inserted as named argument "cid", e.g., http://zbw.eu/stw/descriptor/{cid}""")
    
    def get_document_ids(self):
        """
        returns: LIST of all document ids comprised by this RC
        """
        with self.file.open(mode="r") as fi:
            return [row.split('\t')[0] for row in fi.read().splitlines()]
    
    def get_content(self):
        with self.file.open(mode="r") as fi:
            return fi.read()
    
    def iter_statements(self):
        _ctmplt = self.concept_template
        with self.file.open(mode="r") as fi:
            for ln in fi:
                _cells = ln.strip().split("\t")
                docid = _cells[0]
                crefs = dict((_ctmplt.format(cid=cid), float(score)) for cid, score in map(_parse_cell, _cells[1:]))
                yield {"external_id": docid, "subjects": crefs}
    
    def sample(self, n=200, whiteset=None):
        """
        Simple method that can be used to create new collections.
        If you want to create collections in a more sophicsticated way,
        please write custom code that fits to your needs.
        
        return a random sample (pd.Series) of $n document ids from this release candidate.
        """
        return _sample(self.get_document_ids(), n, whiteset)
    
    @transaction.atomic
    def create_document_stubs(self):
        """
        create Document object stubs (only external_id, empty title) for ALL
        records of this RC.
        """
        for lni, row in enumerate(self.get_content().splitlines()):
            _cells = row.strip().split("\t")
            docid = _cells[0]
            dbdoc, _ = Document.objects.get_or_create(external_id=docid)
    
    def import_records(self, docids, create_emptydoc=True, skip_docfail=False, 
                         collection=None, limit=-1):
        """
        if necessary, create document stubs and subj assignments for all docids.
        
        note: docids for which subj assignments with INDEXER are already in the DB will be EXCLUDED
        """
        rc = self
        _ctmplt = self.concept_template
        indexer = self.indexer
        ## determine already available assignments
        # these documents are excluded
        # convert to set! > https://wiki.python.org/moin/TimeComplexity
        exclude = set(SubjectAssignment.objects.filter(
                document__external_id__in=docids, indexer=rc.indexer).values_list("document__external_id", flat=True))
        for lni, row in enumerate(rc.get_content().splitlines()):
            _cells = row.strip().split("\t")
            docid = _cells[0]
            doci = 0
            if docid in docids:
                if not docid in exclude:
                    doc = None
                    try:
                        doc = Document.objects.get(external_id=docid)
                    except Document.DoesNotExist as err:
                        if create_emptydoc:
                            doc = Document.objects.create(external_id=docid, title='-')
                        else:
                            if skip_docfail:
                                pass
                                # self.stderr.write("illegal document reference to %s" % (str(docid,)))
                            else:
                                raise err
                    if not doc is None:
                        crefs = dict((_ctmplt.format(cid=cid), float(score)) for cid, score in map(_parse_cell, _cells[1:]))
                        indexer.assign_scored(doc, crefs)          
                        if not collection is None:
                            collection.documents.add(doc)
                        if limit > -1 and doci >= limit:
                            break
                    doci += 1
        # TODO need to call collection.save() ?!
    
    def __str__(self):
        return self.name
    
    class Meta:
        ordering = ('pub_date', 'name',)
        get_latest_by = "pub_date"