from celery import shared_task
from django.utils.timezone import now
from leads.models import Lead, LeadWorkflowExecutionStatus
from workflows.models import WorkflowExecution, WorkflowExecutionStep, WorkflowExecutionStepStatus, LeadStepStatus, WorkflowStatus
import json

from workflows.workflow_executor import execute_step

def check_and_complete_workflow_for_lead(workflow_execution, lead_id):
    incomplete_steps = LeadStepStatus.objects.filter(
        lead_id=lead_id,
        workflow=workflow_execution.workflow
    ).exclude(status=WorkflowExecutionStepStatus.COMPLETED)

    if not incomplete_steps.exists():
        # Tutti gli step avviati sono completati, aggiorniamo lo stato del lead
        Lead.objects.filter(id=lead_id).update(workflow_status=LeadWorkflowExecutionStatus.COMPLETED)
        print(f"✅ Lead {lead_id}: workflow completato")
    else:
        print(f"⏳ Lead {lead_id}: workflow ancora in esecuzione ({incomplete_steps.count()} step incompleti)")

@shared_task(bind=True)
def execute_workflow(self, workflow_execution_id, lead_id, settings):
    """
    Task Celery per eseguire un intero workflow in background, rispettando le condizioni e applicandolo a un lead specifico.
    """
    try:

        workflow_execution = WorkflowExecution.objects.get(id=workflow_execution_id)

        # Il seguente controllo non è necessario in quanto se si mette in DRAFT un workflow, non verrà eseguito
        # poiché 
        
        # Controllo se lo stato del workflow si trova in DRAFT, se è così non eseguo il workflow
        # workflow_status = workflow_execution.workflow.status
        # if workflow_status == WorkflowStatus.DRAFT:
        #     print(f"Workflow {workflow_execution.workflow.id} in stato DRAFT, non eseguito.")
        #     return

        
        # print(f"--SETTINGS: {settings.get('max_emails_per_day')}")
        # workflow_execution.status = WorkflowExecutionStatus.RUNNING
        # workflow_execution.started_at = now()
        # workflow_execution.save()


        # TODO: Gestire la pausa tra l'invio delle email se l'utente ha scelto come opzione di inviare le emails a tutti i contatti della lista già presenti. 
        # Probabilmente è meglio gestire una pausa tra l'eseuzione del workflow tra leads
        # in quanto il workflow potrebbe essere eseguito per più leads contemporaneamente

        # TODO: Implementare lo stop del workflow per il lead se ha risposto a un'email
        # TODO: Implementare lo stop del workflow per il lead se richiede l'unsubscribe
        # TODO: Implementare lo stop del workflow per il lead se la prima email va in bounce - se richiesto nelle impostazioni
        # TODO: Gestire l'orario e il giorno di invio delle email 


        # Ordiniamo i nodi
        steps = WorkflowExecutionStep.objects.filter(workflow_execution=workflow_execution).order_by("number")
        executed_steps = {}

        for step in steps:
            # Se il nodo ha un parent, controlliamo che sia completato
            if step.parent_node_id:
                parent_step = WorkflowExecutionStep.objects.get(id=step.parent_node_id)

                # if parent_step.status != WorkflowExecutionStepStatus.COMPLETED:
                #     continue
                try:
                    parent_status = LeadStepStatus.objects.get(
                        lead_id=lead_id,
                        workflow=workflow_execution.workflow,
                        step=parent_step
                    )
                except LeadStepStatus.DoesNotExist:
                    continue  # Non è stato ancora eseguito

                if parent_status.status != WorkflowExecutionStepStatus.COMPLETED:
                    continue                
                
                # Se il nodo padre è un CHECK_LINK_CLICKED, verificare la condizione
                if parent_step.node:
                    parent_node_data = parent_step.node
                    if isinstance(parent_node_data, str):
                        parent_node_data = json.loads(parent_node_data)

                    if parent_node_data["type"] == "CHECK_LINK_CLICKED":
                        if step.condition == "YES" and parent_status.condition != "YES":
                            continue
                        if step.condition == "NO" and parent_status.condition != "NO":
                            continue

            # Eseguiamo il nodo passando il `lead_id`
            execute_step(step, lead_id, settings, task=self)
            executed_steps[step.id] = step

        # NON POSSIAMO IMPOSTARE IL WORKFLOW COME COMPLETATO
        # Segniamo il workflow come completato
        # workflow_execution.status = WorkflowExecutionStatus.COMPLETED
        # workflow_execution.completed_at = now()
        # workflow_execution.save()

        check_and_complete_workflow_for_lead(workflow_execution, lead_id)
        

    except Exception as e:
        # workflow_execution.status = WorkflowExecutionStatus.FAILED
        # workflow_execution.save()
        Lead.objects.filter(id=lead_id).update(workflow_status=LeadWorkflowExecutionStatus.FAILED)
        print(f"Workflow execution failed: {e}")