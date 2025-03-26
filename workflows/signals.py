from django.db.models.signals import post_save
from django.dispatch import receiver
from workflows.models import Workflow, WorkflowExecution, WorkflowSettings, WorkflowStatus
from workflows.tasks import execute_workflow

@receiver(post_save, sender=Workflow)
def process_workflow(sender, instance, **kwargs):
    """
    Signal per gestire i workflow.
    """
    if instance.status == WorkflowStatus.PUBLISHED:
        print(f"Workflow pubblicato: {instance.name}")
        # Ottengo le impostazioni del workflow
        workflow_settings = WorkflowSettings.objects.filter(workflow=instance).first()
        if workflow_settings and workflow_settings.start == "all":
            # Avvia il workflow per tutti i lead che sono presenti nella campagna e per i futuri nuovi leads
            leads = instance.campaign.leads.all()

            try:
                workflow_execution = instance.execution
            except WorkflowExecution.DoesNotExist:
                print("❌ Nessuna WorkflowExecution trovata per questo Workflow.")
                return

            for lead in leads:
                # TODO: Passare i settings
                execute_workflow.delay(workflow_execution.id, lead.id, None)
                
