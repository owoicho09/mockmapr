from django.contrib import admin
from .models import *


class HasEmailFilter(admin.SimpleListFilter):
    title = 'Has Email'
    parameter_name = 'has_email'

    def lookups(self, request, model_admin):
        return (
            ('yes', 'Has Email'),
            ('no', 'No Email'),
        )

    def queryset(self, request, queryset):
        value = self.value()
        if value == 'yes':
            return queryset.filter(email__isnull=False).exclude(email__exact='')
        elif value == 'no':
            return queryset.filter(email__isnull=True) | queryset.filter(email__exact='')
        return queryset




class LeadAdmin(admin.ModelAdmin):
    list_display = ('name', 'email','icp_match','icp_reason','email_sent')
    list_filter = ('icp_match','title', HasEmailFilter, 'source', 'email_sent')  # Use custom filter class here
    search_fields = ('email', 'name')


    def lead_email(self, obj):
        return obj.lead.email

class FollowupAdmin(admin.ModelAdmin):
    list_display = ('lead', 'ready_for_followup','template_type','followup_number')
    list_filter = ('template_type','ready_for_followup')  # Use custom filter class here




class TemplateAdmin(admin.ModelAdmin):
    list_display = ('name', 'content')


class OutreachTrackingAdmin(admin.ModelAdmin):
    list_display = ('lead_email', 'event', 'timestamp', 'opened_at')
    search_fields = ('lead__email',)

    def lead_email(self, obj):
        return obj.lead.email


class OutreachSequenceAdmin(admin.ModelAdmin):
    list_display = ('lead_email', 'status', 'email_subject', 'email_body')
    search_fields = ('lead__email',)

    def lead_email(self, obj):
        return obj.lead.email

    lead_email.short_description = "Lead Email"



admin.site.register(Lead,LeadAdmin)
admin.site.register(Template,TemplateAdmin)
admin.site.register(FollowUp,FollowupAdmin)

admin.site.register(OutreachSequence, OutreachSequenceAdmin)
admin.site.register(OutreachTracking, OutreachTrackingAdmin)
