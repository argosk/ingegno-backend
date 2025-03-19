from django.db.models.signals import post_save
from django.dispatch import receiver
from workflows.models import Workflow, WorkflowSettings, WorkflowStatus

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
            for lead in leads:
                # execute_workflow.delay(instance.id, lead.id, workflow_settings)
                pass
