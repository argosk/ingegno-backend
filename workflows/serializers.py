import json
from rest_framework import serializers

from campaigns.models import Campaign
from .models import Workflow, WorkflowExecution, WorkflowExecutionStep, WorkflowSettings


class WorkflowSettingsSerializer(serializers.ModelSerializer):
    class Meta:
        model = WorkflowSettings
        fields = '__all__'

class WorkflowSerializer(serializers.ModelSerializer):
    campaign = serializers.PrimaryKeyRelatedField(queryset=Campaign.objects.all())
    campaign_name = serializers.CharField(source='campaign.name', read_only=True)
    settings = WorkflowSettingsSerializer(required=False)

    class Meta:
        model = Workflow
        fields = ['id', 'campaign', 'campaign_name', 'name', 'description', 'definition', 'status', 'created_at', 'updated_at', 'settings']
        read_only_fields = ['campaign_name', 'created_at', 'updated_at']

    def validate_campaign(self, value):
        """ Assicurati che la campagna appartenga all'utente autenticato. """
        request = self.context.get('request')
        if value.user != request.user:
            raise serializers.ValidationError("Non puoi associare un workflow a una campagna che non ti appartiene.")
        return value
    
    def create(self, validated_data):
        settings_data = validated_data.pop("settings", None)

        # Crea il workflow
        workflow = Workflow.objects.create(**validated_data)

        # Se non arrivano settings, crea quelli di default
        if settings_data:
            WorkflowSettings.objects.create(workflow=workflow, **settings_data)
        else:
            WorkflowSettings.objects.create(workflow=workflow)  # usa i default del modello

        return workflow

    def update(self, instance, validated_data):
        """ Permette di aggiornare le impostazioni del workflow insieme al workflow stesso """
        settings_data = validated_data.pop('settings', None)

        # Aggiorna i dati del Workflow
        instance = super().update(instance, validated_data)

        # Aggiorna i dati delle impostazioni se presenti
        if settings_data:
            settings_instance = instance.settings
            for key, value in settings_data.items():
                setattr(settings_instance, key, value)
            settings_instance.save()

        return instance

class WorkflowExecutionStepSerializer(serializers.ModelSerializer):
    class Meta:
        model = WorkflowExecutionStep
        fields = ['id', 'number', 'node', 'name', 'started_at', 'completed_at', 'credits_consumed', 'parent_node_id', 'condition']
        # fields = ['id', 'number', 'node', 'name', 'status', 'started_at', 'completed_at', 'credits_consumed', 'parent_node_id', 'condition']
        # read_only_fields = ['id']


class WorkflowExecutionWithStepsSerializer(serializers.ModelSerializer):
    steps = WorkflowExecutionStepSerializer(many=True)

    class Meta:
        model = WorkflowExecution
        # fields = ['id', 'workflow', 'trigger', 'status', 'created_at', 'started_at', 'completed_at', 'steps']
        fields = ['id', 'workflow', 'trigger', 'created_at', 'started_at', 'completed_at', 'steps']

    def create(self, validated_data):
        steps_data = validated_data.pop('steps')
        
        # Crea il WorkflowExecution
        workflow_execution = WorkflowExecution.objects.create(**validated_data)
        
        # Crea i WorkflowExecutionStep collegati al WorkflowExecution appena creato
        for step_data in steps_data:
            node_data = json.loads(step_data.get('node'))
            id = node_data.get('id')
            # print(step_data.get('node'))
            WorkflowExecutionStep.objects.create(
                workflow_execution=workflow_execution,
                id=id,
                **step_data
            )
        
        return workflow_execution
    

class WorkflowExecutionSerializer(serializers.ModelSerializer):
    workflow = WorkflowSerializer(read_only=True)  # Include i dettagli del workflow
    
    class Meta:
        model = WorkflowExecution
        fields = '__all__'


# class WorkflowExecutionStepSerializer(serializers.ModelSerializer):
#     workflow_execution = WorkflowExecutionSerializer(read_only=True)  # Include dettagli esecuzione

#     class Meta:
#         model = WorkflowExecutionStep
#         fields = '__all__'
