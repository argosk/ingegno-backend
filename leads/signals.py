from django.db.models.signals import post_save
from django.dispatch import receiver
from workflows.models import Workflow, WorkflowExecution, WorkflowSettings, WorkflowStatus
from workflows.tasks import execute_workflow
from .models import Lead, LeadStatus

def serialize_workflow_settings(settings):
    if not settings:
        return None

    return {
        "max_emails_per_day": settings.max_emails_per_day,
        "pause_between_emails": settings.pause_between_emails,
        "reply_action": settings.reply_action,
        "sending_time_start": str(settings.sending_time_start),  # orario in formato stringa
        "sending_time_end": str(settings.sending_time_end),
        "sending_days": settings.sending_days,
        "unsubscribe_handling": settings.unsubscribe_handling,
        "bounce_handling": settings.bounce_handling,
    }


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
                # print(f"Workflow trovato: {workflow.id}")
                # print(f"Settings: Max Emails per Day: {workflow_settings.max_emails_per_day}")
                # print(f"Pause tra email: {workflow_settings.pause_between_emails} secondi")
                # print(f"Gestione risposte: {workflow_settings.reply_action}")
                # print(f"Orario di invio: {workflow_settings.sending_time_start} - {workflow_settings.sending_time_end}")
                # print(f"Giorni di invio: {workflow_settings.sending_days}")
                # print(f"Gestione Unsubscribe: {workflow_settings.unsubscribe_handling}")
                # print(f"Gestione Bounce: {workflow_settings.bounce_handling}")

                # Esegui il workflow in background sul lead aggiunto
                execution = WorkflowExecution.objects.filter(workflow=workflow).first()
                # print(f"Workflow Execution: {execution.id}")

                execute_workflow.delay(execution.id, instance.id, settings_dict)
        else:
            print("⚠️ Nessun Workflow trovato per questa campagna.")

        # Qui puoi aggiungere altre operazioni, ad esempio avviare un processo di email marketing
