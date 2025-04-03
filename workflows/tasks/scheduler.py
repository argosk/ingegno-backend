from celery import shared_task
from django.utils.timezone import now
from django.db import transaction
from workflows.models import WorkflowExecution, WorkflowQueue
from workflows.tasks.worker import execute_workflow


BATCH_SIZE = 200  # Numero di lead da processare per ciclo

@shared_task(name="workflows.tasks.scheduler.schedule_workflow_batch")
def schedule_workflow_batch():
    """
    Task periodico che preleva un batch di lead dalla WorkflowQueue con lock pessimista
    e lancia i workflow senza rischi di concorrenza.
    """
    with transaction.atomic():
        queue_items = (
            WorkflowQueue.objects
            .select_for_update(skip_locked=True)
            .filter(processed=False, processing=False)
            .order_by("created_at")[:BATCH_SIZE]
        )

        if not queue_items:
            print("🎯 Nessun lead da processare.")
            return

        for item in queue_items:
            item.processing = True
            item.save(update_fields=["processing"])

    # 🔁 Ora fuori dalla transazione: eseguiamo i workflow in async
    for item in queue_items:
        lead = item.lead
        execution = WorkflowExecution.objects.get(id=item.workflow_execution_id)
        settings = item.settings

        execute_workflow.apply_async(
            args=[execution.id, lead.id, settings]
        )

        item.processed = True
        item.processing = False
        item.processed_at = now()
        item.save()

    print(f"🚀 Processati {len(queue_items)} lead dal batch.")