from celery import shared_task
from django.utils.timezone import now
from workflows.models import WorkflowExecution, WorkflowExecutionStep, WorkflowExecutionStatus, WorkflowExecutionStepStatus
import json

from workflows.workflow_executor import execute_step

@shared_task
def execute_workflow(workflow_execution_id, lead_id, settings):
    """
    Task Celery per eseguire un intero workflow in background, rispettando le condizioni e applicandolo a un lead specifico.
    """
    try:
        workflow_execution = WorkflowExecution.objects.get(id=workflow_execution_id)
        workflow_execution.status = WorkflowExecutionStatus.RUNNING
        workflow_execution.started_at = now()
        workflow_execution.save()

        # Ordiniamo i nodi
        steps = WorkflowExecutionStep.objects.filter(workflow_execution=workflow_execution).order_by("number")
        executed_steps = {}

        for step in steps:
            # Se il nodo ha un parent, controlliamo che sia completato
            if step.parent_node_id:
                parent_step = WorkflowExecutionStep.objects.get(id=step.parent_node_id)

                if parent_step.status != WorkflowExecutionStepStatus.COMPLETED:
                    continue
                
                # Se il nodo padre è un CHECK_LINK_CLICKED, verificare la condizione
                if parent_step.node:
                    parent_node_data = parent_step.node
                    if isinstance(parent_node_data, str):
                        parent_node_data = json.loads(parent_node_data)

                    if parent_node_data["type"] == "CHECK_LINK_CLICKED":
                        if step.condition == "YES" and parent_step.condition != "YES":
                            continue
                        if step.condition == "NO" and parent_step.condition != "NO":
                            continue

            # Eseguiamo il nodo passando il `lead_id`
            execute_step(step, lead_id)
            executed_steps[step.id] = step

        # Segniamo il workflow come completato
        workflow_execution.status = WorkflowExecutionStatus.COMPLETED
        workflow_execution.completed_at = now()
        workflow_execution.save()

    except Exception as e:
        workflow_execution.status = WorkflowExecutionStatus.FAILED
        workflow_execution.save()
        print(f"Workflow execution failed: {e}")