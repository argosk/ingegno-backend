import json
import time
import pytz
from datetime import time as dt_time
from connected_accounts.models import ConnectedAccount, Provider
from emails.models import EmailClickTracking, EmailLog, EmailReplyTracking, EmailStatus
from leads.models import Lead, LeadStatus
from emails.email_sender import send_email_gmail, send_email_outlook, send_email_smtp
from workflows.models import LeadStepStatus, WorkflowExecutionStep, WorkflowExecutionStepStatus
from django.conf import settings as ingegno_settings
from django.core import signing
from django.urls import reverse
from django.utils.timezone import now, localtime
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes

MAX_RETRIES = 3


def get_unsubscribe_link(lead):
    uid = urlsafe_base64_encode(force_bytes(lead.id))
    return f"https://marketo.so/api/leads/unsubscribe/?uid={uid}"

def get_connected_account(email_address):
    """
    Recupera l'account connesso corrispondente all'indirizzo email fornito.
    """
    return ConnectedAccount.objects.filter(email_address=email_address, is_active=True).first()

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


def execute_step(step, lead_id, settings, task):
    """
    Esegue un nodo del workflow in base al suo tipo e al lead.
    """
    try:
        # Recuperiamo il lead specifico
        lead = Lead.objects.get(id=lead_id, unsubscribed=False)

        # # Controlliamo se l'utente ha fatto l'unsubscribe
        # if lead.unsubscribed:
        #     print(f"Lead {lead_id} si è disiscritto. Interrompiamo il workflow.")
        #     if settings.get("unsubscribe_handling") == "exclude":
        #         print("Rimuovo l'utente da tutti i workflow")
        #         return            
        #     if settings.get("unsubscribe_handling") == "remove":
        #         print("Unsubscribe handling: stop")
        #         return


        # Recuperiamo o creiamo lo stato dello step per questo lead
        lead_step_status, _ = LeadStepStatus.objects.get_or_create(
            lead=lead,
            workflow=step.workflow_execution.workflow,
            step=step
        )    

        # User timezone    
        timezone = step.workflow_execution.workflow.user.timezone
        # Applichiamo la timezone dell'utente
        user_timezone = pytz.timezone(timezone)
        local_now = localtime(now(), user_timezone)

        # Giorno attuale (es: "monday", "tuesday", ecc.)
        current_day = local_now.strftime("%A").lower()

        # Convertiamo le stringhe in oggetti `time`
        start_time = dt_time.fromisoformat(settings.get("sending_time_start"))
        end_time = dt_time.fromisoformat(settings.get("sending_time_end"))

        # Calcoliamo l'inizio della giornata (mezzanotte) per oggi
        start_of_day = now().replace(hour=0, minute=0, second=0, microsecond=0)

        current_time = local_now.time()

        # Controllo "reply_action" -  Controlliamo se il lead ha risposto a un'email del workflow, in tal caso fermiamo il workflow
        if settings.get("reply_action") == 'stop':
            if EmailReplyTracking.objects.filter(lead_id=lead_id).exists():
                print(f"Lead {lead_id} has replied to an email. Stopping execution for this lead.")
                lead_step_status.status = WorkflowExecutionStepStatus.COMPLETED
                lead_step_status.save()
                return  # Non eseguiamo il nodo
                 
                
        # step.status = WorkflowExecutionStepStatus.RUNNING
        # step.started_at = now()
        # step.save()
        lead_step_status.status = WorkflowExecutionStepStatus.RUNNING
        lead_step_status.started_at = now()
        lead_step_status.save()

        node_data = step.node
        if isinstance(node_data, str):
            node_data = json.loads(node_data)

        # Recuperiamo il lead specifico
        lead = Lead.objects.get(id=lead_id)

        if node_data["type"] == "WAIT":
            delay = node_data["data"]["settings"]["delay"]
            format = node_data["data"]["settings"]["format"]
            print(f"Waiting for {delay} {format}")

            if format == "Minutes":
                # TODO: Testare workflow con almeno 2 utenti
                time.sleep(delay * 60)
            elif format == "Hours":
                time.sleep(delay * 3600)
            elif format == "Days":
                time.sleep(delay * 86400)

        elif node_data["type"] == "SEND_EMAIL":

            subject = node_data["data"]["settings"]["subject"]
            body = node_data["data"]["settings"]["body"].replace("{name}", lead.name)  # Personalizziamo il nome
            email_account = node_data["data"]["settings"]["email_account"]

            # Crea EmailLog PENDING
            email_log = EmailLog.objects.create(
                lead=lead,
                subject=subject,
                sender=email_account,
                status=EmailStatus.PENDING
            )

            # Generiamo il tracking pixel
            # tracking_pixel_url = f"https://yourdomain.com{reverse('track_email_open', args=[email_log.id, lead.id])}"
            # body += f'<img src="{tracking_pixel_url}" width="1" height="1" style="display:none;" alt="" />'

            signed_data = signing.dumps({
                "lead_id": lead.id,
                "email_log_id": email_log.id,
            })

            tracking_pixel_url = f"https://{ingegno_settings.DOMAIN}{reverse('track_email_open', args=[signed_data])}"
            print(f"Tracking pixel URL: {tracking_pixel_url}")

            if current_day not in settings.get("sending_days", []):
                print(f"❌ Today ({current_day}) is not allowed for sending.")
                raise task.retry(countdown=18000)  # Riprova tra 5 ore

            if not (start_time <= current_time <= end_time):
                print(f"❌ Current time ({current_time}) is outside of allowed sending window ({start_time} - {end_time})")
                raise task.retry(countdown=3600)  # Riprova tra un'ora

            # Controllo "max_emails_per_day" - Contiamo le email inviate da questo sender a partire da mezzanotte
            count_email_logs = EmailLog.objects.filter(
                sender=email_account,
                sent_at__gte=start_of_day
            ).count()
    
            if count_email_logs >= settings.get("max_emails_per_day"):
                print(f"⚠️ Maximum emails per day reached for {email_account}. Skipping SEND_EMAIL.")
                raise task.retry(
                    countdown=86400, # 24h
                    max_retries=MAX_RETRIES, 
                    exc=Exception("Max emails reached for today.")
                )

            # Recuperiamo l'account email connesso
            connected_account = get_connected_account(email_account)
            if not connected_account:
                print(f"No connected email account found for {email_account}. Skipping SEND_EMAIL.")
                # step.status = WorkflowExecutionStepStatus.FAILED
                # step.save()
                lead_step_status.status = WorkflowExecutionStepStatus.FAILED
                lead_step_status.save()
                return

            print(f"Sending email from {connected_account.provider} ({email_account}) to {lead.email}: {subject}")

            if connected_account.provider == Provider.GMAIL:
                send_email_gmail(connected_account, lead.email, subject, body)
            elif connected_account.provider == Provider.OUTLOOK:
                send_email_outlook(connected_account, lead.email, subject, body)
            else:
                send_email_smtp(connected_account, lead.email, subject, body)
            # print(f"Email sent to {lead.email} - Subject: {subject}")

            # Registriamo l'invio nel log
            # email_log = EmailLog.objects.create(
            #     lead=lead,
            #     subject=subject,
            #     body=body,
            #     sender=email_account
            # )

            # Aggiorniamo lo stato dell'email log
            email_log.body = body
            email_log.mark_sent()

            # Segniamo il lead come contattato
            lead.status = LeadStatus.CONTACTED
            lead.save()

            # Salviamo il riferimento all'email log nel nodo del workflow
            # step.email_log = email_log
            # step.save()
            lead_step_status.email_log = email_log
            lead_step_status.save()

        elif node_data["type"] == "CHECK_LINK_CLICKED":
            print(f"Checking if {lead.email} clicked the link")

            # Troviamo il corretto `email_log_id` cercando a ritroso il primo `SEND_EMAIL`
            email_log = find_previous_email_log(step, lead_id, workflow=step.workflow_execution.workflow)

            # print(f"► Found email_log: {email_log.id}")

            if not email_log:
                print("No email_log found, skipping CHECK_LINK_CLICKED")
                # step.status = WorkflowExecutionStepStatus.FAILED
                # step.save()
                lead_step_status.status = WorkflowExecutionStepStatus.FAILED
                lead_step_status.save()                
                return

            # Controlliamo se il lead ha cliccato su un link nell'email specifica
            # clicked = EmailClickTracking.objects.filter(lead=lead, email_log=email_log, clicked=True).exists()
            link_url = node_data["data"]["settings"]["link_url"]

            # Controllo se il lead ha cliccato su un link specifico
            clicked = EmailClickTracking.objects.filter(lead=lead, email_log=email_log, link=link_url, clicked=True).exists()

            if clicked:
                lead_step_status.condition = "YES"
            else:
                lead_step_status.condition = "NO"

            # step.save()
            lead_step_status.save()

        lead_step_status.status = WorkflowExecutionStepStatus.COMPLETED
        lead_step_status.completed_at = now()
        lead_step_status.save()
 
        # step.status = WorkflowExecutionStepStatus.COMPLETED
        # step.completed_at = now()
        # step.save()

    except Exception as e:
        # step.status = WorkflowExecutionStepStatus.FAILED
        # step.save()
        lead_step_status.status = WorkflowExecutionStepStatus.FAILED
        lead_step_status.save()
        print(f"Step execution failed: {e}")
 