import pytz
from datetime import time as dt_time
from django.utils.timezone import now, localtime
from django.conf import settings as ingegno_settings
from django.core import signing
from django.urls import reverse

from workflows.models import WorkflowExecutionStepStatus, LeadStepStatus
from leads.models import Lead, LeadStatus
from emails.models import EmailLog, EmailStatus
from emails.utils.throttling import is_account_throttled
from emails.email_sender import send_email_gmail, send_email_outlook, send_email_smtp
from connected_accounts.models import Provider

from workflows.utils.email_placeholders import replace_placeholders
from workflows.utils.email_tracking import prepare_email_body
from workflows.utils.helpers import get_connected_account

MAX_RETRIES = 3

def execute_send_email(step, lead_id, settings, task, node_data):
    lead = Lead.objects.get(id=lead_id, unsubscribed=False)

    lead_step_status, _ = LeadStepStatus.objects.get_or_create(
        lead=lead,
        workflow=step.workflow_execution.workflow,
        step=step
    )

    timezone = step.workflow_execution.workflow.user.timezone
    user_timezone = pytz.timezone(timezone)
    local_now = localtime(now(), user_timezone)

    current_day = local_now.strftime("%A").lower()
    start_time = dt_time.fromisoformat(settings.get("sending_time_start"))
    end_time = dt_time.fromisoformat(settings.get("sending_time_end"))
    start_of_day = now().replace(hour=0, minute=0, second=0, microsecond=0)
    current_time = local_now.time()

    if settings.get("reply_action") == 'stop':
        from emails.models import EmailReplyTracking
        if EmailReplyTracking.objects.filter(lead_id=lead_id).exists():
            print(f"Lead {lead_id} has replied to an email. Stopping execution.")
            lead_step_status.status = WorkflowExecutionStepStatus.COMPLETED
            lead_step_status.save()
            return True

    lead_step_status.status = WorkflowExecutionStepStatus.RUNNING
    lead_step_status.started_at = now()
    lead_step_status.save()

    subject = replace_placeholders(node_data["data"]["settings"]["subject"], lead)
    body = replace_placeholders(node_data["data"]["settings"]["body"], lead)
    email_account = node_data["data"]["settings"]["email_account"]

    email_log = EmailLog.objects.create(
        lead=lead,
        subject=subject,
        sender=email_account,
        status=EmailStatus.PENDING
    )

    signed_data = signing.dumps({"lead_id": lead.id, "email_log_id": email_log.id})
    tracking_pixel_url = f"https://{ingegno_settings.DOMAIN}{reverse('track_email_open', args=[signed_data])}"
    print(f"Tracking pixel URL: {tracking_pixel_url}")

    body = prepare_email_body(body, lead.id, email_log.id, ingegno_settings.DOMAIN)

    if current_day not in settings.get("sending_days", []):
        print(f"❌ Today ({current_day}) is not allowed for sending.")
        raise task.retry(countdown=18000)

    if not (start_time <= current_time <= end_time):
        print(f"❌ Current time ({current_time}) is outside allowed window ({start_time} - {end_time})")
        raise task.retry(countdown=3600)

    count_email_logs = EmailLog.objects.filter(sender=email_account, sent_at__gte=start_of_day).count()
    if count_email_logs >= settings.get("max_emails_per_day"):
        print(f"⚠️ Max emails/day reached for {email_account}.")
        raise task.retry(countdown=86400, max_retries=MAX_RETRIES, exc=Exception("Max emails reached"))

    connected_account = get_connected_account(email_account)
    if not connected_account:
        print(f"No connected account for {email_account}")
        lead_step_status.status = WorkflowExecutionStepStatus.FAILED
        lead_step_status.save()
        return False

    if is_account_throttled(connected_account):
        print(f"🔁 {connected_account.email_address} in throttling.")
        lead_step_status.status = WorkflowExecutionStepStatus.SKIPPED
        lead_step_status.completed_at = now()
        lead_step_status.save()
        return False

    print(f"Sending email via {connected_account.provider} to {lead.email}: {subject}")

    if connected_account.provider == Provider.GMAIL:
        send_email_gmail(connected_account, lead.email, subject, body)
    elif connected_account.provider == Provider.OUTLOOK:
        send_email_outlook(connected_account, lead.email, subject, body)
    else:
        send_email_smtp(connected_account, lead.email, subject, body)

    email_log.body = body
    email_log.mark_sent()

    lead.status = LeadStatus.CONTACTED
    lead.save()

    lead_step_status.email_log = email_log
    lead_step_status.status = WorkflowExecutionStepStatus.COMPLETED
    lead_step_status.completed_at = now()
    lead_step_status.save()

    return True
