from rest_framework import serializers
from .models import EmailTracking

class EmailTrackingSerializer(serializers.ModelSerializer):
    class Meta:
        model = EmailTracking
        fields = ['id', 'email', 'opened_at', 'clicked_at', 'replied_at']

    def create(self, validated_data):
        # Custom logic if needed during the creation of tracking entries
        return EmailTracking.objects.create(**validated_data)

    def update(self, instance, validated_data):
        # Update tracking fields as needed
        instance.opened_at = validated_data.get('opened_at', instance.opened_at)
        instance.clicked_at = validated_data.get('clicked_at', instance.clicked_at)
        instance.replied_at = validated_data.get('replied_at', instance.replied_at)
        instance.save()
        return instance
