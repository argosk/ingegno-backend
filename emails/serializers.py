from rest_framework import serializers
from .models import EmailLog

class EmailLogSerializer(serializers.ModelSerializer):
    lead_email = serializers.EmailField(source='lead.email', read_only=True)

    class Meta:
        model = EmailLog
        fields = ['id', 'lead', 'lead_email', 'subject', 'body', 'sent_at', 'status', 'response_received', 'sender']
        read_only_fields = ['id', 'sent_at']
