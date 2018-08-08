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
This module implements the releasetool's custom admin site pages.
"""
__author__ = "Martin Toepfer"

from django.urls import reverse, re_path, path
from django.contrib import admin
from django.contrib import messages
from django.core.management import call_command
from django.http import HttpResponseRedirect
from django.template.response import TemplateResponse
from django.utils.html import format_html
from django.db.models import Count, Q
from django.db import transaction

from django import forms

from django_q.tasks import async

from urllib.parse import urlencode

from io import StringIO

from import_export import resources
from import_export.admin import ImportExportModelAdmin, ImportMixin, ExportMixin, ExportActionModelAdmin

from .exceptions import EmptyCollectionException, EmptySampleException, IllegalStateException
from .online_configuration import CK_MAIN_AI
from .models import RtConfig, Guideline, ReleaseCandidate
from .models import Collection, Document, SubjectAssignment, SubjectIndexer
from .models import Review, SubjectLevelReview

from .catalog_connection import CatalogApi
from .thesaurus_connection import ThesaurusApi

admin.site.site_header = "releasetool-admin"
admin.site.register([Guideline])

#-----# resources: #----#
##
# define resources for import-export features:
#
class DocumentResource(resources.ModelResource):
    class Meta:
        model = Document
        import_id_fields = ('external_id',)

class CollectionResource(resources.ModelResource):
    class Meta:
        model = Collection

#-----# special views and forms: #----#
        
class ParentRecordField(forms.CharField):
    
    def validate(self, value):
        super().validate(value)
        if len(value) > 0:
            try:
                parent_rec_dbo = Document.objects.get(external_id=value)
            except Document.DoesNotExist:
                raise forms.ValidationError("parent record does not exist!")

class SampleForm(forms.Form):
    """
    Form for sampling collections from release candidates.
    """
    rc = forms.ModelChoiceField(ReleaseCandidate.objects.all(), label="release candidate")
    parent_rec_id = ParentRecordField(label="parent record external_id (journal/series)", 
                                   required=False,
                                 max_length=50) # TODO max_length=Document.external_id.max_length)
    require_abstract = forms.BooleanField(required=False)
    size = forms.IntegerField(label="Size", min_value=1, max_value=1000)

# see: ReleaseCandidateAdmin.sample_view ## def sample_view_fun(request, rc_id, *args, **kwargs):
    

#-----# admin site classes: #----#
##
# define admin sites:
#
# see:
# - https://docs.djangoproject.com/en/2.0/ref/contrib/admin/#module-django.contrib.admin
# - https://docs.djangoproject.com/en/2.0/ref/contrib/admin/#django.contrib.admin.ModelAdmin.list_filter

@admin.register(ReleaseCandidate)
class ReleaseCandidateAdmin(admin.ModelAdmin):
    list_display = ('name', 'pub_date', 'file', 'indexer', 'num_documents', 'sample')
    actions = ['compute_info', 'compare', 'sample_action', 'create_stubs', 'fetch_metadata_complete']
        
    def get_urls(self):
        sample_url = path('sample/<rc_id>', self.admin_site.admin_view(self.sample_view), name='sample')
        return [sample_url] + super(ReleaseCandidateAdmin, self).get_urls()

    def sample(self, obj):
        """
        for **list_display**, return link to sample from this RC
        """
        url = reverse("admin:sample", kwargs={"rc_id": obj.name})
        return format_html('''<a href="{}">sample</a>''', url)
    sample.allow_tags = True
    
    def sample_action(self, request, queryset):
        """
        for **action_menu**, redirect to view to sample from this RC
        """
        if queryset.count() != 1:
            self.message_user(request, "Too many items selected!", messages.ERROR)
            return
        rc_id = queryset.first().name
        return HttpResponseRedirect(reverse("admin:sample" , kwargs={"rc_id": rc_id}))
    sample_action.short_description = "Sample"
    
    def sample_view(self, request, rc_id, *args, **kwargs):
        _iformdata = {"size": 200, "rc": rc_id}
        if "parent_rec_id" in request.GET:
            _iformdata["parent_rec_id"] = request.GET.get("parent_rec_id")
        form = SampleForm(initial=_iformdata)
        if request.POST:
            form = SampleForm(request.POST)
            if form.is_valid():
                try:
                    with transaction.atomic():
                        rc_selected = form.cleaned_data["rc"]
                        parent_rec_id = form.cleaned_data["parent_rec_id"]
                        
                        whiteset = None
                        white_queryset = None
                        parent_rec = None
                        if len(parent_rec_id) > 0:
                            parent_rec = Document.objects.get(external_id=parent_rec_id) 
                            white_queryset = parent_rec.narrower.all()
                        if form.cleaned_data["require_abstract"]:
                            white_queryset = (white_queryset if white_queryset else Document.objects.all()).filter(has_abstract=True)
                        if white_queryset:
                            whiteset = set(white_queryset.values_list("external_id", flat=True))
                        
                        rc = ReleaseCandidate.objects.get(name=rc_selected)
                        size = form.cleaned_data["size"]
                        docids = rc.sample(size, whiteset=whiteset).tolist()
                        if len(docids) == 0:
                            raise EmptyCollectionException("Empty collection.")
                        if whiteset is not None and len(docids) > len(whiteset):
                            raise IllegalStateException("collection size > whitelist size")
                        #
                        rc.import_records(docids)
                        #
                        new_name_prefix = "C"
                        if parent_rec:
                            new_name_prefix += "_" + parent_rec_id
                        name_regex = "^" + new_name_prefix + r"_\d+$"
                        _nr = Collection.objects.filter(name__regex=name_regex).order_by('name').last()
                        _nr = (int(_nr.name[(len(new_name_prefix)+1):]) + 1) if _nr else 0
                        new_name = "%s_%0002d" % (new_name_prefix, _nr, )
                        col = Collection.objects.create(name=new_name)
                        col.documents.add(*[Document.objects.get_or_create(external_id=docid)[0] for docid in docids])
                        col.description = "Sample from %s" % (rc.name,)
                        if parent_rec:
                            col.description += " | parent = " 
                            col.description += '"%s" (%s)' % (parent_rec.title, str(parent_rec_id),)
                        col.save()
                        ## then, redirect to the newly created collection
                        _cm = Collection._meta
                        url = reverse("admin:%s_%s_change" % (_cm.app_label, _cm.model_name), kwargs={"object_id": col.id})
                        return HttpResponseRedirect(url)
                except (EmptySampleException, IllegalStateException) as err:
                    msg = "Collection could not be created: %s." % (str(err),)
                    self.message_user(request, msg, messages.WARNING)
        sample_template_name = "admin/zaptain_rt_app/sample.html"
        context = dict()
        context["form"] = form
        context['title'] = "Sample"
        context['opts'] = self.model._meta
        context["app_label"] = "zaptain_rt_app" #self.model._meta.app_label' 
        request.current_app = self.admin_site.name
        return TemplateResponse(request, [sample_template_name],
                                context)
    
    def num_documents(self, obj):
        return len(obj.get_document_ids())
    
    def compute_info(self, request, queryset):
        msg = ""
        with StringIO() as out:
            call_command("rt_rc_list", *[rc.name for rc in queryset], stdout=out)
            msg = out.getvalue()
        msg = "<br/>".join(msg.splitlines())
        self.message_user(request, format_html(msg))
    
    def compare(self, request, queryset):
        if queryset.count() != 2:
            self.message_user(request, "Please select exactly two items!", messages.ERROR)
            return
        msg = ""
        with StringIO() as out:
            call_command("rt_rc_compare", *[rc.name for rc in queryset], stdout=out)
            msg = out.getvalue()
        msg = "<br/>".join(msg.splitlines())
        self.message_user(request, format_html(msg))
    
    def create_stubs(self, request, queryset):
        if queryset.count() != 1:
            self.message_user(request, "Too many items selected!", messages.ERROR)
            return
        rc = queryset.first()
        rc.create_document_stubs()
        self.message_user(request, "OK", messages.SUCCESS)
    create_stubs.short_description = "Create stubs"
    
    def _fetch_metadata_complete_task(self, rc):
        catapi = CatalogApi.create_from_db()
        rc.create_document_stubs()
        catapi.fetch_metadata(Document.objects.all()) # TODO: only fetch RC's documents rather than ALL
    
    def fetch_metadata_complete(self, request, queryset):
        if queryset.count() != 1:
            self.message_user(request, "Too many items selected!", messages.ERROR)
            return
        rc = queryset.first()
        task_id = async(self._fetch_metadata_complete_task, rc)
        tasks_url = reverse("admin:app_list", args=("django_q",))
        msg_tmplt = 'begin: gather meta-data asynchronously, <a href="{url}">task id = {id}</a>.'
        msg_data = {"url": tasks_url, "id": task_id}
        msg = format_html(msg_tmplt, **msg_data)
        self.message_user(request, msg, messages.WARNING)
    fetch_metadata_complete.short_description = "Fetch meta-data (complete!)"

class IsAiListFilter(admin.SimpleListFilter):
    title = ('Indexer Type')
    parameter_name = 'is_ai'
    
    def lookups(self, request, model_admin):
        return (('1', 'Automatic Method'), ('0', 'Human'))
    
    def queryset(self, request, queryset):
        if self.value() == '1':
            return queryset.filter(user__isnull=True)
        if self.value() == '0':
            return queryset.exclude(user__isnull=True)
    
@admin.register(SubjectIndexer)
class SubjectIndexerAdmin(admin.ModelAdmin):
    # optional fiels for list_display: ai_name, user
    list_display = ('id', 'label', 'is_human', 'is_main', 'set_as_main_link')
    list_filter = (IsAiListFilter,)
    actions = ["set_as_main_action"]
    
    def get_urls(self):
        sample_url = path('set_as_main/<indexer_id>', 
                          self.admin_site.admin_view(self.set_as_main_view), 
                          name='set_as_main')
        return [sample_url] + super(SubjectIndexerAdmin, self).get_urls()
    
    def label(self, obj):
        # TODO maybe rewrite, use and "annotate" instead
        return obj.ai_name if not obj.is_human() else obj.user.username
    
    def is_main(self, obj):
        return obj.ai_name == RtConfig.objects.get(key=CK_MAIN_AI).value
    
    def set_as_main_link(self, obj):
        if obj.is_human():
            return ""
        url = reverse("admin:set_as_main", kwargs={"indexer_id": obj.id})
        return format_html('''<a href="{}">set as main</a>''', url)
    set_as_main_link.allow_tags = True
    set_as_main_link.short_description = "set as main"
    
    def set_as_main_view(self, request, indexer_id, *kwarg, **kwargs):
        self.set_as_main_action(request, SubjectIndexer.objects.filter(id=indexer_id))
        _m = self.opts
        url = reverse("admin:%s_%s_changelist" % (_m.app_label, _m.model_name))
        return HttpResponseRedirect(url)
    
    def set_as_main_action(self, request, queryset):
        obj = queryset.first()
        if queryset.count() != 1 :
            self.message_user(request, "Too many items selected!", messages.ERROR)
            return
        if not obj.is_human():
            config = RtConfig.objects.get(key=CK_MAIN_AI)
            config.value = obj.ai_name
            config.save()
            self.message_user(request, "successfully set '%s' as main method." % (obj.ai_name,))
        else:
            self.message_user(request, "Illegal selection (human indexer), action aborted.", messages.ERROR)
    set_as_main_action.short_description = "set as main AI"


@admin.register(Collection)
class CollectionAdmin(ImportMixin, ExportActionModelAdmin, admin.ModelAdmin):
    resource_class = CollectionResource ## for import/export
    search_fields = ('name', 'description')
    list_display = ('name', 'description', 'size', 'analysis_link') # id
    exclude = ('documents',) # issue: page loading takes long when there are MANY documents !    
    actions = ["fetch_title_action", "merge_action"]
    # filter_horizontal = ('documents',)
    
    def get_queryset(self, request):
        qs = super(CollectionAdmin, self).get_queryset(request)
        qs = qs.annotate(size=Count("documents"))
        return qs
    
    def view_on_site(self, obj):
        return reverse("collection", kwargs={"collection_id": obj.id})
    
    def size(self, obj):
        return obj.size
    size.admin_order_field = 'size'
    
    def analysis_link(self, obj):
        url = reverse("collection_analysis", kwargs={"collection_id": obj.id})
        return format_html("""<a href="{}">analysis</a>""", url)
    analysis_link.allow_tags = True
    analysis_link.short_description = "analysis"
    
    def fetch_title_action(self, request, queryset):
        catapi = CatalogApi.create_from_db()
        for dbcollection in queryset:
            for dbdoc in dbcollection.documents.all():
                docid = dbdoc.external_id
                jdoc = catapi.fetch(docid)
                if not "error" in jdoc:
                    title = jdoc["title"] # "xxx"
                    dbdoc.title = title
                    dbdoc.save()
                    self.message_user(request, "successfully set %s's title." % (docid,))
                else:
                    self.message_user(request, "error @ " + docid, messages.ERROR)
                    break
    fetch_title_action.short_description = "fetch title"
    
    def merge_action(self, request, queryset):
        if queryset.count() < 2:
            self.message_user(request, "Too less items selected!", messages.ERROR)
            return
        with transaction.atomic():
            merge_names = [c.name for c in queryset]
            name_union = "C_" + "_".join(merge_names)
            col_union = Collection.objects.create(name=name_union)
            col_union.description = "Created as a union of collections: " + ", ".join(merge_names)
            col_union.documents.set([d for c in queryset for d in c.documents.all()])
            col_union.save()
            self.message_user(request, 
                              'successfully created new collection: "%s".' % (name_union,))
    merge_action.short_description = "merge"
    
# TODO delete confirmation shows too many related objects (#64) | does not work yet:
#    def render_delete_form(self, request, context):
#        context['deleted_objects'] = ['Object listing disabled']
#        return super(CollectionAdmin, self).render_delete_form(request, context)

@admin.register(RtConfig)
class RtConfigAdmin(admin.ModelAdmin):
    list_display = ('key', 'value')



@admin.register(Document)
class DocumentAdmin(ImportMixin, ExportActionModelAdmin, admin.ModelAdmin):
    exclude = ('broader',) # select field is slow for extensive num of choices # maybe later use filter_horizontal = ('authors',)
    list_display = ('external_id', 'title', 'has_abstract', 'doc_type', 'narrower_count', 'narrower_with_abstract_count', 'sample')
    search_fields = ('external_id', 'title')
    list_filter = ('doc_type', 'has_abstract')
    resource_class = DocumentResource
    actions = ["fetch_metadata_async"]
    
    def view_on_site(self, obj):
        # alternatively link to "api_document" or "review" ??
        return reverse("doc_external", kwargs={"external_id": obj.external_id})
    
    def get_queryset(self, request):
        qs = super(DocumentAdmin, self).get_queryset(request).annotate(
                _nsub = Count('narrower')
        ).annotate(
                _nsub_abstract = Count('narrower', filter=Q(narrower__has_abstract=True))
        )
        return qs
    
    def fetch_metadata_async(self, request, queryset):
        # see: http://django-q.readthedocs.io/en/latest/tasks.html#django_q.async
        catapi = CatalogApi.create_from_db()
        task_id = async(catapi.fetch_metadata, queryset)        
        tasks_url = reverse("admin:app_list", args=("django_q",))
        msg_tmplt = 'begin: gather meta-data asynchronously, <a href="{url}">task id = {id}</a>.'
        msg_data = {"url": tasks_url, "id": task_id}
        msg = format_html(msg_tmplt, **msg_data)
        self.message_user(request, msg, messages.WARNING)
    
    def narrower_count(self, obj):
        n = obj._nsub 
        return str(n) if n > 0 else ''
    narrower_count.short_description = '# doc'
    narrower_count.admin_order_field = '_nsub'
    
    def narrower_with_abstract_count(self, obj):
        n = obj._nsub_abstract
        return str(n) if n > 0 else ''
    narrower_with_abstract_count.short_description = '# doc [a]'
    narrower_with_abstract_count.admin_order_field = '_nsub_abstract'
    
    def sample(self, obj):
        """
        return link to sample from this parent ojb
        """
        rcs = list(ReleaseCandidate.objects.all())
        if len(rcs) < 1 or obj.narrower.all().count() < 1:
            return ''
        rc = ReleaseCandidate.objects.latest()
        url = reverse("admin:sample", kwargs={"rc_id": rc.name})
        url += "?" + urlencode({"parent_rec_id": obj.external_id})
        return format_html('''<a href="{}">sample</a>''', url)
    sample.allow_tags = True


@admin.register(SubjectAssignment)
class SubjectAssignmentAdmin(admin.ModelAdmin):
    list_display = ('id', 'document', 'subject', 'score', 'indexer')
    list_filter = ('indexer',)
    search_fields = ('document__external_id', 'subject')

@admin.register(Review)
class ReviewAdmin(ExportActionModelAdmin, admin.ModelAdmin):
    list_display = ('id', 'reviewer', 'document', 'guideline', 'ai', 'total_rating', 'review_link')
    list_filter = ('reviewer', 'total_rating', 'guideline', 'ai')
    search_fields = ('document__external_id',)
    
    def review_link(self, obj):
        url = reverse("compare_review", kwargs={"external_id": obj.document.external_id})
        return format_html("""<a href="{}">compare</a>""", url)
    review_link.allow_tags = True
    review_link.short_description = "see reviews"


# TODO use more sophisticated list_filter:
# - https://docs.djangoproject.com/en/2.0/ref/contrib/admin/#django.contrib.admin.ModelAdmin.list_filter
@admin.register(SubjectLevelReview)
class SubjectLevelReviewAdmin(ExportActionModelAdmin, admin.ModelAdmin):
    list_display = ('id', 'document', 'subject', 'reviewer', 'value')
    list_filter = ('value', 'review__reviewer')
    
    def reviewer(self, obj):
        return obj.review.reviewer

    def document(self, obj):
        return obj.subject_assignment.document
    
    def subject(self, obj):
        return obj.subject_assignment.subject
    