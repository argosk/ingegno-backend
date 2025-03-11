import json
import time
from emails.models import EmailClickTracking, EmailLog, EmailOpenTracking
from leads.models import Lead
from workflows.models import WorkflowExecutionStep, WorkflowExecutionStepStatus
from django.utils.timezone import now


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

            print(f"Sending email to {lead.email}: {subject} - {body}")

            # Simuliamo l'invio della mail (sostituire con send_mail in produzione)
            # send_mail(subject, body, email_account, [lead.email])
            time.sleep(5)  # Simuliamo l'invio

            # Registriamo l'invio nel log
            email_log = EmailLog.objects.create(
                lead=lead,
                subject=subject,
                body=body,
                sender=email_account
            )

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
        
# def execute_step(step):
#     """
#     Esegue un nodo del workflow in base al suo tipo e imposta le condizioni.
#     """
#     try:
#         step.status = WorkflowExecutionStepStatus.RUNNING
#         step.started_at = now()
#         step.save()

#         node_data = step.node
#         if isinstance(node_data, str):
#             node_data = json.loads(node_data)

#         if node_data["type"] == "WAIT":
#             delay_hours = node_data["data"]["settings"]["delay_hours"]
#             print(f"Waiting for {delay_hours} hours...")
#             # time.sleep(delay_hours * 3600)  # Bloccante, ma viene eseguito dentro Celery
#             time.sleep(5)  # Simuliamo l'attesa

#         elif node_data["type"] == "SEND_EMAIL":
#             subject = node_data["data"]["settings"]["subject"]
#             body = node_data["data"]["settings"]["body"]
#             email_account = node_data["data"]["settings"]["email_account"]
#             print(f"Sending email: {subject} - {body} from {email_account}")

#         elif node_data["type"] == "CHECK_LINK_CLICKED":
#             email_id = node_data["data"]["settings"]["email_id"]
#             link_url = node_data["data"]["settings"]["link_url"]
#             print(f"Checking if {link_url} was clicked in email {email_id}")

#             # Simuliamo un controllo reale (dovrebbe essere gestito dal database o da un log)
#             link_clicked = True  # Se il link è stato cliccato, mettiamo True

#             if link_clicked:
#                 step.condition = "YES"
#             else:
#                 step.condition = "NO"

#             step.save()

#         step.status = WorkflowExecutionStepStatus.COMPLETED
#         step.completed_at = now()
#         step.save()

#     except Exception as e:
#         step.status = WorkflowExecutionStepStatus.FAILED
#         step.save()
#         print(f"Step execution failed: {e}")
