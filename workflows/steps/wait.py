import time
from django.utils.timezone import now
from workflows.models import WorkflowExecutionStepStatus
from workflows.utils.helpers import get_or_create_lead_step_status
from leads.models import Lead


def execute_wait(step, lead_id, node_data):
    lead = Lead.objects.get(id=lead_id)

    lead_step_status = get_or_create_lead_step_status(lead, step)

    lead_step_status.status = WorkflowExecutionStepStatus.RUNNING
    lead_step_status.started_at = now()
    lead_step_status.save()

    delay = node_data["data"]["settings"].get("delay", 0)
    format = node_data["data"]["settings"].get("format", "Minutes")
    print(f"Waiting for {delay} {format}")

    if format == "Minutes":
        time.sleep(delay * 60)
    elif format == "Hours":
        time.sleep(delay * 3600)
    elif format == "Days":
        time.sleep(delay * 86400)

    lead_step_status.status = WorkflowExecutionStepStatus.COMPLETED
    lead_step_status.completed_at = now()
    lead_step_status.save()

    return True