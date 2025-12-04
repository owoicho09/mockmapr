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
    list_display = ('name', 'email','icp_match','icp_reason','icp_match')
    list_filter = ('icp_match','title', HasEmailFilter)  # Use custom filter class here


class FollowupAdmin(admin.ModelAdmin):
    list_display = ('lead', 'ready_for_followup','template_type','followup_number')
    list_filter = ('template_type','ready_for_followup')  # Use custom filter class here




class TemplateAdmin(admin.ModelAdmin):
    list_display = ('name', 'content')


class OutreachTrackingAdmin(admin.ModelAdmin):
    list_display = ('lead', 'event','timestamp','opened_at')


class OutreachSequenceAdmin(admin.ModelAdmin):
    list_display = ('lead', 'status','email_subject','email_body')




admin.site.register(Lead,LeadAdmin)
admin.site.register(Template,TemplateAdmin)
admin.site.register(FollowUp,FollowupAdmin)

admin.site.register(OutreachSequence, OutreachSequenceAdmin)
admin.site.register(OutreachTracking, OutreachTrackingAdmin)
