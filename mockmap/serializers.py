

from rest_framework import serializers
from .models import Lead, LeadStatus, OutreachSequence, OutreachTracking, OutreachTemplate


class LeadSerializer(serializers.ModelSerializer):
    class Meta:
        model = Lead
        fields = [
            'id',
            'name',
            'company_name',
            'website',
            'address',
            'email',
            'phone',
            'source',
            'rating',
            'reviews_count',
            'email_verified',
            'phone_verified',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class LeadStatusSerializer(serializers.ModelSerializer):
    lead = LeadSerializer(read_only=True)

    class Meta:
        model = LeadStatus
        fields = [
            'lead',
            'scraped',
            'verified',
            'enriched',
            'notes',
            'last_update',
        ]
        read_only_fields = ['last_update']


class OutreachSequenceSerializer(serializers.ModelSerializer):
    lead = serializers.PrimaryKeyRelatedField(queryset=Lead.objects.all())
    lead_name = serializers.CharField(source="lead.name", read_only=True)
    lead_email = serializers.CharField(source="lead.email", read_only=True)
    lead_business = serializers.CharField(source="lead.company_name", read_only=True)

    class Meta:
        model = OutreachSequence
        fields = [
            'id',
            'lead',
            "lead_name",
            "lead_email",
            "lead_business",
            'step',
            'status',
            'email_subject',
            'email_body',
            'sent_at',
            'response_at',
        ]
        read_only_fields = ['id', 'sent_at', 'response_at']


class OutreachTrackingSerializer(serializers.ModelSerializer):
    lead = LeadSerializer(read_only=True)

    class Meta:
        model = OutreachTracking
        fields = [
            'id',
            'lead',
            'sequence_step',
            'delivered',
            'opened',
            'clicked',
            'replied',
            'last_checked',
        ]
        read_only_fields = ['id', 'last_checked']


class OutreachTemplateSerializer(serializers.ModelSerializer):
    class Meta:
        model = OutreachTemplate
        fields = [
            'id',
            'name',
            'category',
            'body',
            'variables',
        ]
        read_only_fields = ['id']



class LeadFullSerializer(serializers.ModelSerializer):
    status = LeadStatusSerializer(read_only=True)
    outreach_sequences = OutreachSequenceSerializer(many=True, read_only=True, source='outreachsequence_set')

    class Meta:
        model = Lead
        fields = '__all__'


