from django.db.models.signals import post_save
from django.dispatch import receiver
from workflows.models import Workflow, WorkflowSettings, WorkflowStatus
from .models import Lead, LeadStatus

@receiver(post_save, sender=Lead)
def process_new_lead(sender, instance, created, **kwargs):
    """
    Signal per gestire i nuovi lead con status='new'.
    Recupera la campagna ID e le impostazioni di workflow associate.
    """
    if created and instance.status == LeadStatus.NEW:
        # Ottenere l'ID della campagna
        campaign_id = instance.campaign.id
        print(f"Nuovo lead aggiunto: {instance.name} ({instance.email}), Campagna ID: {campaign_id}")

        # Trovare il workflow attivo associato alla campagna (se esiste)
        workflow = Workflow.objects.filter(campaign_id=campaign_id, status=WorkflowStatus.PUBLISHED).first()

        if workflow:
            # Ottenere le impostazioni del workflow
            workflow_settings = WorkflowSettings.objects.filter(workflow=workflow).first()
            if workflow_settings and workflow_settings.start == "new":
                print(f"Workflow trovato: {workflow.id}")
                print(f"Settings: Max Emails per Day: {workflow_settings.max_emails_per_day}")
                print(f"Pause tra email: {workflow_settings.pause_between_emails} secondi")
                print(f"Gestione risposte: {workflow_settings.reply_action}")
                print(f"Orario di invio: {workflow_settings.sending_time_start} - {workflow_settings.sending_time_end}")
                print(f"Giorni di invio: {workflow_settings.sending_days}")
                print(f"Gestione Unsubscribe: {workflow_settings.unsubscribe_handling}")
                print(f"Gestione Bounce: {workflow_settings.bounce_handling}")

                    # Esegui il workflow in background sul lead aggiunto
                    # execute_workflow.delay(workflow.id, instance.id, workflow_settings)
        else:
            print("⚠️ Nessun Workflow trovato per questa campagna.")

        # Qui puoi aggiungere altre operazioni, ad esempio avviare un processo di email marketing
