from rest_framework import serializers
from .models import Email, WarmUpTask

class EmailSerializer(serializers.ModelSerializer):
    class Meta:
        model = Email
        fields = ['id', 'sequence', 'lead', 'sender_email', 'status', 'sent_at']

    def validate_sender_email(self, value):
        if not value or "@" not in value:
            raise serializers.ValidationError("A valid sender email address is required.")
        return value

    def create(self, validated_data):
        # Create the email entry with the lead's email automatically retrieved
        lead = validated_data.pop('lead')
        recipient_email = lead.email  # Automatically get the email from the lead
        email = Email.objects.create(recipient_email=recipient_email, lead=lead, **validated_data)
        return email

    def update(self, instance, validated_data):
        # Update email details
        lead = validated_data.get('lead', instance.lead)
        instance.lead = lead
        instance.sender_email = validated_data.get('sender_email', instance.sender_email)
        instance.status = validated_data.get('status', instance.status)
        instance.sent_at = validated_data.get('sent_at', instance.sent_at)
        instance.save()
        return instance


class WarmUpTaskSerializer(serializers.ModelSerializer):
    class Meta:
        model = WarmUpTask
        fields = ['id', 'user', 'email_account', 'start_date', 'daily_limit', 'increase_rate', 'max_limit', 'is_active']

    def validate_daily_limit(self, value):
        if value <= 0:
            raise serializers.ValidationError("Daily limit must be a positive integer.")
        return value

    def validate_increase_rate(self, value):
        if value < 0:
            raise serializers.ValidationError("Increase rate cannot be negative.")
        return value

    def validate_max_limit(self, value):
        if value <= 0:
            raise serializers.ValidationError("Max limit must be greater than zero.")
        return value

    def create(self, validated_data):
        # Custom logic during task creation (if needed)
        warmup_task = WarmUpTask.objects.create(**validated_data)
        return warmup_task

    def update(self, instance, validated_data):
        # Update warm-up task details
        instance.email_account = validated_data.get('email_account', instance.email_account)
        instance.start_date = validated_data.get('start_date', instance.start_date)
        instance.daily_limit = validated_data.get('daily_limit', instance.daily_limit)
        instance.increase_rate = validated_data.get('increase_rate', instance.increase_rate)
        instance.max_limit = validated_data.get('max_limit', instance.max_limit)
        instance.is_active = validated_data.get('is_active', instance.is_active)
        instance.save()
        return instance