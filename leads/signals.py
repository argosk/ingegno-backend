from django.db.models.signals import post_save
from django.dispatch import receiver
from workflows.models import Workflow, WorkflowExecution, WorkflowSettings, WorkflowStatus
from workflows.tasks.worker import execute_workflow
from .models import Lead, LeadStatus
from utils.utils import serialize_workflow_settings

@receiver(post_save, sender=Lead)
def process_new_lead(sender, instance, created, **kwargs):
    """
    Signal per gestire i nuovi lead con status='new'.
    Recupera la campagna ID e le impostazioni di workflow associate.
    """
    if created and instance.status == LeadStatus.NEW:
        print(f"👉 Nuovo lead aggiunto: {instance.name} ({instance.email})")
        # Ottenere l'ID della campagna
        campaign_id = instance.campaign.id
        print(f"Nuovo lead aggiunto: {instance.name} ({instance.email}), Campagna ID: {campaign_id}")

        # Trovare il workflow attivo associato alla campagna (se esiste)
        workflow = Workflow.objects.filter(campaign_id=campaign_id, status=WorkflowStatus.PUBLISHED).first()

        if workflow:
            # Ottenere le impostazioni del workflow
            workflow_settings = WorkflowSettings.objects.filter(workflow=workflow).first()
            settings_dict = serialize_workflow_settings(workflow_settings)
            # if workflow_settings and workflow_settings.start == "new":
            if workflow_settings:
                # Esegui il workflow in background sul lead aggiunto
                execution = WorkflowExecution.objects.filter(workflow=workflow).first()
                execute_workflow.delay(execution.id, instance.id, settings_dict)
        else:
            print("⚠️ Nessun Workflow trovato per questa campagna.")

        # Qui puoi aggiungere altre operazioni, ad esempio avviare un processo di email marketing
