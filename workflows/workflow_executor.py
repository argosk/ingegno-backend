import json
from workflows.steps.send_email import execute_send_email
from workflows.steps.wait import execute_wait
from workflows.steps.check_link_clicked import execute_check_link_clicked


def execute_step(step, lead_id, settings, task):
    try:
        node_data = step.node
        if isinstance(node_data, str):
            node_data = json.loads(node_data)

        node_type = node_data.get("type")

        if node_type == "SEND_EMAIL":
            return execute_send_email(step, lead_id, settings, task, node_data)

        elif node_type == "WAIT":
            return execute_wait(step, lead_id, node_data)

        elif node_type == "CHECK_LINK_CLICKED":
            return execute_check_link_clicked(step, lead_id, node_data)

        else:
            print(f"⚠️ Nodo {node_type} non supportato.")
            return False

    except Exception as e:
        print(f"❌ Step execution failed: {e}")
        return False




# import re
# import json
# import time
# import pytz
# from datetime import time as dt_time
# from connected_accounts.models import ConnectedAccount, Provider
# from emails.models import EmailClickTracking, EmailLog, EmailReplyTracking, EmailStatus
# from emails.utils.throttling import is_account_throttled
# from leads.models import Lead, LeadStatus
# from emails.email_sender import send_email_gmail, send_email_outlook, send_email_smtp
# from workflows.models import LeadStepStatus, WorkflowExecutionStep, WorkflowExecutionStepStatus
# from django.conf import settings as ingegno_settings
# from django.core import signing
# from django.forms.models import model_to_dict
# from django.urls import reverse
# from django.utils.timezone import now, localtime
# from django.utils.http import urlsafe_base64_encode
# from django.utils.encoding import force_bytes


# MAX_RETRIES = 3


# # def get_unsubscribe_link(lead):
# #     uid = urlsafe_base64_encode(force_bytes(lead.id))
# #     return f"https://marketo.so/api/leads/unsubscribe/?uid={uid}"

# def get_unsubscribe_link(lead):
#     signed = signing.dumps({"lead_id": lead.id})
#     return f"https://{ingegno_settings.DOMAIN}/api/leads/unsubscribe/?token={signed}"

# def wrap_plain_links(text: str) -> str:
#     """
#     Wrappa i link nudi tipo http://example.com in <a href="...">...</a>
#     evitando quelli già presenti come href="..."
#     """
#     pattern = r'(?<!href=["\'])\bhttps?://[^\s<"]+'

#     def wrap(match):
#         url = match.group(0)
#         return f'<a href="{url}">{url}</a>'

#     return re.sub(pattern, wrap, text)


# def convert_links_to_trackable(body: str, lead_id: int, email_log_id: int, domain: str) -> str:
#     """
#     Sostituisce tutti gli href con URL firmati e tracciabili,
#     ignorando i link già tracciati (dominio tuo).
#     """
#     def replacer(match):
#         original_url = match.group(2)

#         # Ignora link già tracciati (con tuo dominio)
#         if domain in original_url:
#             return match.group(0)

#         signed_data = signing.dumps({
#             "lead_id": lead_id,
#             "email_log_id": email_log_id,
#             "url": original_url,
#         })
#         tracking_url = f"https://{domain}{reverse('track_email_click', args=[signed_data])}"
#         return f'{match.group(1)}="{tracking_url}"'

#     # Trova href = "..." o '...' con link http/https
#     pattern = r'(href)\s*=\s*["\'](https?://[^"\']+)["\']'
#     return re.sub(pattern, replacer, body)


# def prepare_email_body(body: str, lead_id: int, email_log_id: int, domain: str) -> str:
#     """
#     Wrappa link nudi e converte tutti i link in tracciabili.
#     """
#     # Step 1: Wrappa i link nudi
#     body = wrap_plain_links(body)

#     # Step 2: Converte i link wrappati in link tracciabili
#     body = convert_links_to_trackable(body, lead_id, email_log_id, domain)

#     return body

# def get_connected_account(email_address):
#     """
#     Recupera l'account connesso corrispondente all'indirizzo email fornito.
#     """
#     return ConnectedAccount.objects.filter(email_address=email_address, is_active=True).first()

# def find_previous_email_log(current_step, lead_id, workflow):
#     step = current_step
#     while step.parent_node_id:
#         step = WorkflowExecutionStep.objects.get(id=step.parent_node_id)
#         try:
#             lead_status = LeadStepStatus.objects.get(
#                 lead_id=lead_id,
#                 workflow=workflow,
#                 step=step
#             )
#             if lead_status.email_log:
#                 return lead_status.email_log
#         except LeadStepStatus.DoesNotExist:
#             continue
#     return None

# # Funzioni personalizzate disponibili nei template
# CUSTOM_PLACEHOLDER_FUNCTIONS = {
#     "current_date": lambda lead: now().strftime("%d/%m/%Y"),
#     "unsubscribe_link": get_unsubscribe_link,  
#     # aggiungi qui altre funzioni custom se vuoi
# }

# def replace_placeholders(text: str, lead: Lead) -> str:
#     """
#     Sostituisce {placeholder} nel testo con:
#     - Campi del modello Lead (solo quelli del DB)
#     - Funzioni personalizzate definite in CUSTOM_PLACEHOLDER_FUNCTIONS
#     """
#     lead_data = model_to_dict(lead)

#     def replacer(match):
#         key = match.group(1)

#         # 1. Se è una funzione personalizzata, la eseguo
#         if key in CUSTOM_PLACEHOLDER_FUNCTIONS:
#             try:
#                 return str(CUSTOM_PLACEHOLDER_FUNCTIONS[key](lead))
#             except Exception as e:
#                 return f"[Errore: {e}]"

#         # 2. Se è un campo del modello Lead
#         if key in lead_data:
#             return str(lead_data[key])

#         # 3. Altrimenti lo lascio così com'è
#         return match.group(0)

#     return re.sub(r"\{([a-zA-Z0-9_]+)\}", replacer, text)

# def execute_step(step, lead_id, settings, task):
#     """
#     Esegue un nodo del workflow in base al suo tipo e al lead.
#     """
#     try:
#         # Recuperiamo il lead specifico
#         lead = Lead.objects.get(id=lead_id, unsubscribed=False)

#         # # Controlliamo se l'utente ha fatto l'unsubscribe
#         # if lead.unsubscribed:
#         #     print(f"Lead {lead_id} si è disiscritto. Interrompiamo il workflow.")
#         #     if settings.get("unsubscribe_handling") == "exclude":
#         #         print("Rimuovo l'utente da tutti i workflow")
#         #         return            
#         #     if settings.get("unsubscribe_handling") == "remove":
#         #         print("Unsubscribe handling: stop")
#         #         return


#         # Recuperiamo o creiamo lo stato dello step per questo lead
#         lead_step_status, _ = LeadStepStatus.objects.get_or_create(
#             lead=lead,
#             workflow=step.workflow_execution.workflow,
#             step=step
#         )    

#         # User timezone    
#         timezone = step.workflow_execution.workflow.user.timezone
#         # Applichiamo la timezone dell'utente
#         user_timezone = pytz.timezone(timezone)
#         local_now = localtime(now(), user_timezone)

#         # Giorno attuale (es: "monday", "tuesday", ecc.)
#         current_day = local_now.strftime("%A").lower()

#         # Convertiamo le stringhe in oggetti `time`
#         start_time = dt_time.fromisoformat(settings.get("sending_time_start"))
#         end_time = dt_time.fromisoformat(settings.get("sending_time_end"))

#         # Calcoliamo l'inizio della giornata (mezzanotte) per oggi
#         start_of_day = now().replace(hour=0, minute=0, second=0, microsecond=0)

#         current_time = local_now.time()

#         # Controllo "reply_action" -  Controlliamo se il lead ha risposto a un'email del workflow, in tal caso fermiamo il workflow
#         if settings.get("reply_action") == 'stop':
#             if EmailReplyTracking.objects.filter(lead_id=lead_id).exists():
#                 print(f"Lead {lead_id} has replied to an email. Stopping execution for this lead.")
#                 lead_step_status.status = WorkflowExecutionStepStatus.COMPLETED
#                 lead_step_status.save()
#                 return  # Non eseguiamo il nodo
                                 
#         lead_step_status.status = WorkflowExecutionStepStatus.RUNNING
#         lead_step_status.started_at = now()
#         lead_step_status.save()

#         node_data = step.node
#         if isinstance(node_data, str):
#             node_data = json.loads(node_data)

#         # Recuperiamo il lead specifico
#         lead = Lead.objects.get(id=lead_id)

#         if node_data["type"] == "WAIT":
#             delay = node_data["data"]["settings"]["delay"]
#             format = node_data["data"]["settings"]["format"]
#             print(f"Waiting for {delay} {format}")

#             if format == "Minutes":
#                 # TODO: Testare workflow con almeno 2 utenti
#                 time.sleep(delay * 60)
#             elif format == "Hours":
#                 time.sleep(delay * 3600)
#             elif format == "Days":
#                 time.sleep(delay * 86400)

#         elif node_data["type"] == "SEND_EMAIL":

#             subject = replace_placeholders(node_data["data"]["settings"]["subject"], lead)
#             body = replace_placeholders(node_data["data"]["settings"]["body"], lead)
#             email_account = node_data["data"]["settings"]["email_account"]

#             # Crea EmailLog PENDING
#             email_log = EmailLog.objects.create(
#                 lead=lead,
#                 subject=subject,
#                 sender=email_account,
#                 status=EmailStatus.PENDING
#             )

#             signed_data = signing.dumps({
#                 "lead_id": lead.id,
#                 "email_log_id": email_log.id,
#             })

#             # Genera l'URL del pixel di tracciamento
#             tracking_pixel_url = f"https://{ingegno_settings.DOMAIN}{reverse('track_email_open', args=[signed_data])}"
#             # TODO: Abilitare il pixel di tracciamento
#             # body += f'<img src="{tracking_pixel_url}" width="1" height="1" style="display:none;" alt="" />'
#             print(f"Tracking pixel URL: {tracking_pixel_url}")

#             # Converte link in link tracciabili
#             body = prepare_email_body(body, lead.id, email_log.id, ingegno_settings.DOMAIN)

#             if current_day not in settings.get("sending_days", []):
#                 print(f"❌ Today ({current_day}) is not allowed for sending.")
#                 raise task.retry(countdown=18000)  # Riprova tra 5 ore

#             if not (start_time <= current_time <= end_time):
#                 print(f"❌ Current time ({current_time}) is outside of allowed sending window ({start_time} - {end_time})")
#                 raise task.retry(countdown=3600)  # Riprova tra un'ora

#             # Controllo "max_emails_per_day" - Contiamo le email inviate da questo sender a partire da mezzanotte
#             count_email_logs = EmailLog.objects.filter(
#                 sender=email_account,
#                 sent_at__gte=start_of_day
#             ).count()
    
#             if count_email_logs >= settings.get("max_emails_per_day"):
#                 print(f"⚠️ Maximum emails per day reached for {email_account}. Skipping SEND_EMAIL.")
#                 raise task.retry(
#                     countdown=86400, # 24h
#                     max_retries=MAX_RETRIES, 
#                     exc=Exception("Max emails reached for today.")
#                 )

#             # Recuperiamo l'account email connesso
#             connected_account = get_connected_account(email_account)
#             if not connected_account:
#                 print(f"No connected email account found for {email_account}. Skipping SEND_EMAIL.")
#                 lead_step_status.status = WorkflowExecutionStepStatus.FAILED
#                 lead_step_status.save()
#                 return False

#             print(f"Sending email from {connected_account.provider} ({email_account}) to {lead.email}: {subject}")

#             # if connected_account.provider == Provider.GMAIL:
#             #     send_email_gmail(connected_account, lead.email, subject, body)
#             # elif connected_account.provider == Provider.OUTLOOK:
#             #     send_email_outlook(connected_account, lead.email, subject, body)
#             # else:
#             #     send_email_smtp(connected_account, lead.email, subject, body)
            
#             if connected_account.provider == Provider.GMAIL:
#                 if is_account_throttled(connected_account):
#                     print(f"🔁 Skip Gmail: {connected_account.email_address} è in throttling.")
#                     lead_step_status.status = WorkflowExecutionStepStatus.SKIPPED
#                     lead_step_status.completed_at = now()
#                     lead_step_status.save()
#                     return False
#                 send_email_gmail(connected_account, lead.email, subject, body)

#             elif connected_account.provider == Provider.OUTLOOK:
#                 if is_account_throttled(connected_account):
#                     print(f"🔁 Skip Outlook: {connected_account.email_address} è in throttling.")
#                     lead_step_status.status = WorkflowExecutionStepStatus.SKIPPED
#                     lead_step_status.completed_at = now()
#                     lead_step_status.save()
#                     return False
#                 send_email_outlook(connected_account, lead.email, subject, body)

#             else:
#                 if is_account_throttled(connected_account):
#                     print(f"🔁 Skip SMTP: {connected_account.email_address} è in throttling.")
#                     lead_step_status.status = WorkflowExecutionStepStatus.SKIPPED
#                     lead_step_status.completed_at = now()
#                     lead_step_status.save()
#                     return False
#                 send_email_smtp(connected_account, lead.email, subject, body)

        
#             # Aggiorniamo lo stato dell'email log
#             email_log.body = body
#             email_log.mark_sent()

#             # Segniamo il lead come contattato
#             lead.status = LeadStatus.CONTACTED
#             lead.save()

#             lead_step_status.email_log = email_log
#             lead_step_status.save()

#         elif node_data["type"] == "CHECK_LINK_CLICKED":
#             print(f"Checking if {lead.email} clicked the link")

#             # Troviamo il corretto `email_log_id` cercando a ritroso il primo `SEND_EMAIL`
#             email_log = find_previous_email_log(step, lead_id, workflow=step.workflow_execution.workflow)

#             if not email_log:
#                 print("No email_log found, skipping CHECK_LINK_CLICKED")
#                 lead_step_status.status = WorkflowExecutionStepStatus.FAILED
#                 lead_step_status.save()                
#                 return False

#             # Controlliamo se il lead ha cliccato su un link nell'email specifica
#             link_url = node_data["data"]["settings"]["link_url"]

#             # Controllo se il lead ha cliccato su un link specifico
#             clicked = EmailClickTracking.objects.filter(lead=lead, email_log=email_log, link=link_url, clicked=True).exists()

#             if clicked:
#                 lead_step_status.condition = "YES"
#             else:
#                 lead_step_status.condition = "NO"

#             # step.save()
#             lead_step_status.save()

#         lead_step_status.status = WorkflowExecutionStepStatus.COMPLETED
#         lead_step_status.completed_at = now()
#         lead_step_status.save()
#         return True

#     except Exception as e:
#         lead_step_status.status = WorkflowExecutionStepStatus.FAILED
#         lead_step_status.save()
#         print(f"Step execution failed: {e}")
#         return False
 