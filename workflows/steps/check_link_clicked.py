from django.utils.timezone import now
from workflows.utils.helpers import get_or_create_lead_step_status
from workflows.models import WorkflowExecutionStepStatus
from emails.models import EmailClickTracking
from leads.models import Lead
from workflows.utils.helpers import find_previous_email_log


def execute_check_link_clicked(step, lead_id, node_data):
    lead = Lead.objects.get(id=lead_id)
    lead_step_status = get_or_create_lead_step_status(lead, step)

    lead_step_status.status = WorkflowExecutionStepStatus.RUNNING
    lead_step_status.started_at = now()
    lead_step_status.save()

    email_log = find_previous_email_log(step, lead_id, workflow=step.workflow_execution.workflow)
    if not email_log:
        print("No email_log found, skipping CHECK_LINK_CLICKED")
        lead_step_status.status = WorkflowExecutionStepStatus.FAILED
        lead_step_status.save()
        return False

    link_url = node_data["data"]["settings"].get("link_url")
    clicked = EmailClickTracking.objects.filter(
        lead=lead,
        email_log=email_log,
        link=link_url,
        clicked=True
    ).exists()

    lead_step_status.condition = "YES" if clicked else "NO"
    lead_step_status.status = WorkflowExecutionStepStatus.COMPLETED
    lead_step_status.completed_at = now()
    lead_step_status.save()

    print(f"Link clicked: {clicked} for lead {lead_id}")
    return True
