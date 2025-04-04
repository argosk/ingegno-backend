from rest_framework import serializers
from .models import EmailLog, EmailReplyTracking

class EmailLogSerializer(serializers.ModelSerializer):
    lead_email = serializers.EmailField(source='lead.email', read_only=True)

    class Meta:
        model = EmailLog
        fields = ['id', 'lead', 'lead_email', 'subject', 'body', 'sent_at', 'status', 'response_received', 'sender']
        read_only_fields = ['id', 'sent_at']

class EmailReplyTrackingSerializer(serializers.ModelSerializer):
    email = serializers.EmailField(source='lead.email', read_only=True)
    first_name = serializers.CharField(source='lead.first_name', read_only=True)
    last_name = serializers.CharField(source='lead.last_name', read_only=True)
    label = serializers.CharField(source='lead.campaign.name', read_only=True)



    class Meta:
        model = EmailReplyTracking
        fields = ['id', 'lead', 'label', 'email', 'first_name', 'last_name', 'subject', 'body', 'received_at', 'read']
        read_only_fields = ['id', 'lead', 'label', 'email', 'first_name', 'last_name', 'subject', 'body', 'received_at']