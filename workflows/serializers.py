import json
from rest_framework import serializers

from campaigns.models import Campaign
from .models import Workflow, WorkflowExecution, WorkflowExecutionStep


# class WorkflowSerializer(serializers.ModelSerializer):
#     class Meta:
#         model = Workflow
#         fields = ['id', 'name', 'description', 'definition', 'status', 'created_at', 'updated_at']

class WorkflowSerializer(serializers.ModelSerializer):
    campaign = serializers.PrimaryKeyRelatedField(queryset=Campaign.objects.all())

    class Meta:
        model = Workflow
        fields = ['id', 'campaign', 'name', 'description', 'definition', 'status', 'created_at', 'updated_at']

    def validate_campaign(self, value):
        """ Assicurati che la campagna appartenga all'utente autenticato. """
        request = self.context.get('request')
        if value.user != request.user:
            raise serializers.ValidationError("Non puoi associare un workflow a una campagna che non ti appartiene.")
        return value

class WorkflowExecutionStepSerializer(serializers.ModelSerializer):
    class Meta:
        model = WorkflowExecutionStep
        fields = ['id', 'number', 'node', 'name', 'status', 'started_at', 'completed_at', 'credits_consumed', 'parent_node_id', 'condition']
        # read_only_fields = ['id']


class WorkflowExecutionWithStepsSerializer(serializers.ModelSerializer):
    steps = WorkflowExecutionStepSerializer(many=True)

    class Meta:
        model = WorkflowExecution
        fields = ['id', 'workflow', 'trigger', 'status', 'created_at', 'started_at', 'completed_at', 'steps']

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
