from rest_framework import serializers
from leads.models import Lead
from subscriptions.models import Subscription
from leads.serializers import LeadSerializer  # Use the LeadSerializer from the leads app
from .models import Campaign, EmailSequence


class EmailSequenceSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(required=False)  # Explicitly added to handle IDs correctly

    class Meta:
        model = EmailSequence
        fields = ['id', 'subject', 'body', 'order', 'send_after_days']

    def validate_order(self, value):
        if value <= 0:
            raise serializers.ValidationError("Order must be a positive number.")
        return value

    def validate_send_after_days(self, value):
        if value < 0:
            raise serializers.ValidationError("The 'send_after_days' field cannot be negative.")
        return value

class CampaignSerializer(serializers.ModelSerializer):
    # Nested email sequences
    email_sequences = EmailSequenceSerializer(many=True, required=False)
    # Accept only lead IDs instead of full objects
    leads = serializers.PrimaryKeyRelatedField(queryset=Lead.objects.all(), many=True, required=False)

    class Meta:
        model = Campaign
        fields = ['id', 'name', 'start_date', 'is_active', 'email_sequences', 'leads']
        extra_kwargs = {'start_date': {'required': False}}

    def validate(self, data):
        # Check if the user has an active subscription
        user = self.context['request'].user
        subscription = Subscription.objects.filter(user=user).first()

        if not subscription or subscription.status != 'active':
            raise serializers.ValidationError(
                "You must have an active subscription to create or modify a campaign."
            )
        return data

    def validate_leads(self, leads):
        user = self.context['request'].user
        lead_ids = [lead.id for lead in leads]

        # Check if all provided leads belong to the current user
        if not Lead.objects.filter(id__in=lead_ids, user=user).count() == len(lead_ids):
            raise serializers.ValidationError("One or more leads do not belong to the current user.")
        
        return leads    

    def create(self, validated_data):
        # Handle campaign creation with associated email sequences and leads
        email_sequences_data = validated_data.pop('email_sequences', [])
        leads = validated_data.pop('leads', [])
        campaign = Campaign.objects.create(**validated_data)

        # Create associated email sequences
        for sequence_data in email_sequences_data:
            EmailSequence.objects.create(campaign=campaign, **sequence_data)

        # Associate leads with the campaign
        campaign.leads.set(leads)

        return campaign

    def update(self, instance, validated_data):
        email_sequences_data = validated_data.pop('email_sequences', [])
        leads = validated_data.pop('leads', None)  # Change to None to avoid overwriting if not provided

        # Update campaign details
        instance.name = validated_data.get('name', instance.name)
        instance.start_date = validated_data.get('start_date', instance.start_date)
        instance.is_active = validated_data.get('is_active', instance.is_active)
        instance.save()

        # Update email sequences
        existing_sequences = {seq.id: seq for seq in instance.email_sequences.all()}
        updated_sequence_ids = []

        for sequence_data in email_sequences_data:
            sequence_id = sequence_data.get('id', None)
            if sequence_id and sequence_id in existing_sequences:
                sequence_instance = existing_sequences[sequence_id]
                for attr, value in sequence_data.items():
                    setattr(sequence_instance, attr, value)
                sequence_instance.save()
                updated_sequence_ids.append(sequence_instance.id)
            else:
                new_sequence = EmailSequence.objects.create(campaign=instance, **sequence_data)
                updated_sequence_ids.append(new_sequence.id)

        EmailSequence.objects.filter(campaign=instance).exclude(id__in=updated_sequence_ids).delete()

        # Update leads only if provided
        if leads is not None:
            instance.leads.set(leads)

        return instance


# from rest_framework import serializers
# from subscriptions.models import Subscription
# from .models import Campaign, EmailSequence

# class EmailSequenceSerializer(serializers.ModelSerializer):
#     id = serializers.IntegerField(required=False)  # Aggiunto esplicitamente per gestire correttamente gli ID

#     class Meta:
#         model = EmailSequence
#         fields = ['id', 'subject', 'body', 'order', 'send_after_days']

#     def validate_order(self, value):
#         if value <= 0:
#             raise serializers.ValidationError("Order must be a positive number.")
#         return value

#     def validate_send_after_days(self, value):
#         if value < 0:
#             raise serializers.ValidationError("The 'send_after_days' field cannot be negative.")
#         return value

# class CampaignSerializer(serializers.ModelSerializer):
#     # Nested email sequences
#     email_sequences = EmailSequenceSerializer(many=True, required=False)

#     class Meta:
#         model = Campaign
#         fields = ['id', 'name', 'start_date', 'is_active', 'email_sequences']

#     def validate(self, data):
#         # Check if the user has an active subscription
#         user = self.context['request'].user
#         subscription = Subscription.objects.filter(user=user).first()

#         if not subscription or subscription.status != 'active':
#             raise serializers.ValidationError(
#                 "You must have an active subscription to create or modify a campaign."
#             )
#         return data

#     def create(self, validated_data):
#         # Handle campaign creation with associated email sequences
#         email_sequences_data = validated_data.pop('email_sequences', [])
#         campaign = Campaign.objects.create(**validated_data)

#         # Create associated email sequences
#         for sequence_data in email_sequences_data:
#             EmailSequence.objects.create(campaign=campaign, **sequence_data)
        
#         return campaign

#     def update(self, instance, validated_data):
#         email_sequences_data = validated_data.pop('email_sequences', [])

#         # Update campaign details
#         instance.name = validated_data.get('name', instance.name)
#         instance.start_date = validated_data.get('start_date', instance.start_date)
#         instance.is_active = validated_data.get('is_active', instance.is_active)
#         instance.save()

#         # Create a mapping of existing sequences by ID
#         existing_sequences = {seq.id: seq for seq in instance.email_sequences.all()}
#         updated_sequence_ids = []

#         for sequence_data in email_sequences_data:
#             sequence_id = sequence_data.get('id', None)

#             if sequence_id and sequence_id in existing_sequences:
#                 # Update existing sequence using the nested serializer
#                 sequence_instance = existing_sequences[sequence_id]
#                 for attr, value in sequence_data.items():
#                     setattr(sequence_instance, attr, value)
#                 sequence_instance.save()
#                 updated_sequence_ids.append(sequence_instance.id)
#             else:
#                 # Create a new sequence if no valid ID is provided (handle new entries correctly)
#                 new_sequence = EmailSequence.objects.create(campaign=instance, **sequence_data)
#                 updated_sequence_ids.append(new_sequence.id)

#         # Optionally delete sequences not included in the update payload
#         EmailSequence.objects.filter(campaign=instance).exclude(id__in=updated_sequence_ids).delete()

#         return instance
