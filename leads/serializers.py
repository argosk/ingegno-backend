from rest_framework import serializers
from .models import Lead
from campaigns.models import Campaign


class LeadSerializer(serializers.ModelSerializer):
    campaign = serializers.PrimaryKeyRelatedField(queryset=Campaign.objects.all())
    status_display = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        model = Lead
        fields = [
            'id', 'campaign', 'name', 'email', 'phone', 'company', 
            'status', 'status_display', 
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']