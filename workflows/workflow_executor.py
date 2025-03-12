import json
import time
from connected_accounts.models import ConnectedAccount, Provider
from emails.models import EmailClickTracking, EmailLog, EmailOpenTracking, EmailReplyTracking
from leads.models import Lead, LeadStatus
from workflows.email_sender import send_email_gmail, send_email_outlook, send_email_smtp
from workflows.models import WorkflowExecutionStep, WorkflowExecutionStepStatus
from django.utils.timezone import now

def get_connected_account(email_address):
    """
    Recupera l'account connesso corrispondente all'indirizzo email fornito.
    """
    return ConnectedAccount.objects.filter(email_address=email_address, is_active=True).first()


def find_previous_email_log(current_step):
    """
    Risale a ritroso nel workflow per trovare il primo nodo `SEND_EMAIL` con un `email_log_id` valido.
    """
    step = current_step
    while step.parent_node_id:
        step = WorkflowExecutionStep.objects.get(id=step.parent_node_id)
        if step.email_log:
            return step.email_log  # Abbiamo trovato l'email corretta
    return None  # Nessun `SEND_EMAIL` trovato


def execute_step(step, lead_id):
    """
    Esegue un nodo del workflow in base al suo tipo e al lead.
    """
    try:
        # Controlliamo se il lead ha risposto a un'email del workflow
        if EmailReplyTracking.objects.filter(lead_id=lead_id).exists():
            print(f"Lead {lead_id} has replied to an email. Stopping execution for this lead.")
            return  # Non eseguiamo il nodo
                
        step.status = WorkflowExecutionStepStatus.RUNNING
        step.started_at = now()
        step.save()

        node_data = step.node
        if isinstance(node_data, str):
            node_data = json.loads(node_data)

        # Recuperiamo il lead specifico
        lead = Lead.objects.get(id=lead_id)

        if node_data["type"] == "WAIT":
            delay_hours = node_data["data"]["settings"]["delay_hours"]
            print(f"Waiting for {delay_hours} hours...")
            # time.sleep(delay_hours * 3600)
            time.sleep(5)  # Simuliamo l'attesa

        elif node_data["type"] == "SEND_EMAIL":
            subject = node_data["data"]["settings"]["subject"]
            body = node_data["data"]["settings"]["body"].replace("{name}", lead.name)  # Personalizziamo il nome
            email_account = node_data["data"]["settings"]["email_account"]

            # Generiamo il tracking pixel
            # tracking_pixel_url = f"https://yourdomain.com{reverse('track_email_open', args=[lead.id])}"
            # body += f'<img src="{tracking_pixel_url}" width="1" height="1" style="display:none;" />'

            # Simuliamo l'invio della mail (sostituire con send_mail in produzione)
            # send_mail(subject, body, email_account, [lead.email])
            # time.sleep(5)  # Simuliamo l'invio

                        # Recuperiamo l'account email connesso
            connected_account = get_connected_account(email_account)
            if not connected_account:
                print(f"No connected email account found for {email_account}. Skipping SEND_EMAIL.")
                step.status = WorkflowExecutionStepStatus.FAILED
                step.save()
                return

            print(f"Sending email from {connected_account.provider} ({email_account}) to {lead.email}: {subject}")

            if connected_account.provider == Provider.GMAIL:
                send_email_gmail(connected_account, lead.email, subject, body)
            elif connected_account.provider == Provider.OUTLOOK:
                send_email_outlook(connected_account, lead.email, subject, body)
            else:
                send_email_smtp(connected_account, lead.email, subject, body)

            # Registriamo l'invio nel log
            email_log = EmailLog.objects.create(
                lead=lead,
                subject=subject,
                body=body,
                sender=email_account
            )

            # Segniamo il lead come contattato
            lead.status = LeadStatus.CONTACTED
            lead.save()

            # Salviamo il riferimento all'email log nel nodo del workflow
            step.email_log = email_log
            step.save()

        elif node_data["type"] == "CHECK_LINK_CLICKED":
            print(f"Checking if {lead.email} clicked the link")

            # Troviamo il corretto `email_log_id` cercando a ritroso il primo `SEND_EMAIL`
            email_log = find_previous_email_log(step)

            print(f"► Found email_log: {email_log.id}")

            if not email_log:
                print("No email_log found, skipping CHECK_LINK_CLICKED")
                step.status = WorkflowExecutionStepStatus.FAILED
                step.save()
                return

            # Controlliamo se il lead ha cliccato su un link nell'email specifica
            clicked = EmailClickTracking.objects.filter(lead=lead, email_log=email_log, clicked=True).exists()

            if clicked:
                step.condition = "YES"
            else:
                step.condition = "NO"

            step.save()

        # elif node_data["type"] == "CHECK_EMAIL_OPENED":
        #     print(f"Checking if {lead.email} opened the email")

        #     # Controlliamo se il lead ha aperto l'email
        #     opened = EmailOpenTracking.objects.filter(lead=lead, opened=True).exists()

        #     if opened:
        #         step.condition = "YES"
        #     else:
        #         step.condition = "NO"

        #     step.save()            

        step.status = WorkflowExecutionStepStatus.COMPLETED
        step.completed_at = now()
        step.save()

    except Exception as e:
        step.status = WorkflowExecutionStepStatus.FAILED
        step.save()
        print(f"Step execution failed: {e}")
