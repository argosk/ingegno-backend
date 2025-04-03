from django.db.models.signals import post_save
from django.dispatch import receiver
from workflows.models import Workflow, WorkflowExecution, WorkflowQueue, WorkflowSettings, WorkflowStatus
from utils.utils import serialize_workflow_settings

@receiver(post_save, sender=Workflow)
def process_workflow(sender, instance, **kwargs):
    """
    Signal per gestire i workflow.
    """
    if instance.status == WorkflowStatus.PUBLISHED:
        print(f"Workflow pubblicato: {instance.name}")
        # Ottengo le impostazioni del workflow
        workflow_settings = WorkflowSettings.objects.filter(workflow=instance).first()
        settings_dict = serialize_workflow_settings(workflow_settings)
        if workflow_settings and workflow_settings.start == "all":
            # Avvia il workflow per tutti i lead che sono presenti nella campagna e per i futuri nuovi leads
            leads = instance.campaign.leads.all()

            try:
                workflow_execution = instance.execution
            except WorkflowExecution.DoesNotExist:
                print("❌ Nessuna WorkflowExecution trovata per questo Workflow.")
                return

            for lead in leads:
                # execute_workflow.delay(workflow_execution.id, lead.id, settings_dict)
                WorkflowQueue.objects.create(
                    lead=lead,
                    workflow_execution=workflow_execution,
                    settings=settings_dict
                )
                
                
