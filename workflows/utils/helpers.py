from connected_accounts.models import ConnectedAccount
from workflows.models import LeadStepStatus, WorkflowExecutionStep


def find_previous_email_log(current_step, lead_id, workflow):
    step = current_step
    while step.parent_node_id:
        step = WorkflowExecutionStep.objects.get(id=step.parent_node_id)
        try:
            lead_status = LeadStepStatus.objects.get(
                lead_id=lead_id,
                workflow=workflow,
                step=step
            )
            if lead_status.email_log:
                return lead_status.email_log
        except LeadStepStatus.DoesNotExist:
            continue
    return None

def get_connected_account(email_address):
    """
    Recupera l'account connesso corrispondente all'indirizzo email fornito.
    """
    return ConnectedAccount.objects.filter(email_address=email_address, is_active=True).first()


def get_or_create_lead_step_status(lead, step):
    lead_step_status, _ = LeadStepStatus.objects.get_or_create(
        lead=lead,
        workflow=step.workflow_execution.workflow,
        step=step
    )
    return lead_step_status