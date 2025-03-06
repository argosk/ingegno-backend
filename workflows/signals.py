from django.db.models.signals import pre_save
from django.dispatch import receiver
from workflows.models import WorkflowExecutionStep  # ✅ Importa il modello corretto

@receiver(pre_save, sender=WorkflowExecutionStep)
def debug_workflow_step_update(sender, instance, **kwargs):
    """ Stampa un debug ogni volta che viene modificato un WorkflowExecutionStep """
    print(f"@DEBUG: 🛑 Prima di salvare Step {instance.id}, email_log_id = {instance.email_log_id}")
