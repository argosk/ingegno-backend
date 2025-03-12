import requests
import datetime
from celery import shared_task
from django.utils.timezone import make_aware, is_naive
from django.utils.timezone import now
from django.conf import settings
from django.db import IntegrityError
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from connected_accounts.models import ConnectedAccount, Provider
from emails.models import EmailLog
from leads.models import Lead
from .models import EmailReplyTracking
import imaplib
import json
import email

GMAIL_TOKEN_URL = "https://oauth2.googleapis.com/token"
GMAIL_API_URL = "https://www.googleapis.com/gmail/v1/users/me/messages"
MICROSOFT_TOKEN_URL = "https://login.microsoftonline.com/common/oauth2/v2.0/token"
OUTLOOK_API_URL = "https://graph.microsoft.com/v1.0/me/messages"

@shared_task
def check_email_replies():
    """
    Task Celery per controllare le risposte alle email inviate dal workflow.
    """
    connected_accounts = ConnectedAccount.objects.filter(is_active=True)

    for account in connected_accounts:
        if account.provider in [Provider.GMAIL, Provider.OUTLOOK]:
            check_oauth_replies(account)
        else:
            check_imap_replies(account)

def refresh_gmail_token(account):
    """ Aggiorna il token di accesso per Gmail. """
    if not account.refresh_token:
        print(f"No refresh token available for {account.email_address}. User must reconnect the account.")
        return None

    data = {
        "client_id": settings.GOOGLE_CLIENT_ID,
        "client_secret": settings.GOOGLE_CLIENT_SECRET,
        "refresh_token": account.refresh_token,
        "grant_type": "refresh_token",
    }

    response = requests.post(GMAIL_TOKEN_URL, data=data)
    if response.status_code == 200:
        token_data = response.json()
        account.access_token = token_data["access_token"]
        account.token_expires_at = now()
        account.save()
        print(f"Gmail token refreshed for {account.email_address}")
        return account.access_token
    else:
        print(f"Failed to refresh Gmail token for {account.email_address}. Error: {response.text}")
        return None

def refresh_outlook_token(account):
    """ Aggiorna il token di accesso per Outlook. """
    if not account.refresh_token:
        print(f"No refresh token available for {account.email_address}. User must reconnect the account.")
        return None

    data = {
        "client_id": settings.MICROSOFT_CLIENT_ID,
        "client_secret": settings.MICROSOFT_CLIENT_SECRET,
        "refresh_token": account.refresh_token,
        "grant_type": "refresh_token",
        "scope": "https://graph.microsoft.com/.default",
    }

    response = requests.post(MICROSOFT_TOKEN_URL, data=data)
    if response.status_code == 200:
        token_data = response.json()
        account.access_token = token_data["access_token"]
        account.token_expires_at = now()
        account.save()
        print(f"Outlook token refreshed for {account.email_address}")
        return account.access_token
    else:
        print(f"Failed to refresh Outlook token for {account.email_address}. Error: {response.text}")
        return None

def check_oauth_replies(account):
    """
    Controlla le risposte per account Gmail/Outlook con OAuth2, aggiornando il token se necessario.
    """
    print(f"Checking replies for {account.email_address} ({account.provider})")

    # Se il token è scaduto, aggiorniamolo
    if account.token_expires_at and now() > account.token_expires_at:
        print(f"Token expired for {account.email_address}, refreshing...")
        if account.provider == Provider.GMAIL:
            new_token = refresh_gmail_token(account)
        elif account.provider == Provider.OUTLOOK:
            new_token = refresh_outlook_token(account)

        if not new_token:
            print(f"Skipping {account.email_address}: unable to refresh token.")
            return

    if account.provider == Provider.GMAIL:
        check_gmail_replies(account)
    elif account.provider == Provider.OUTLOOK:
        check_outlook_replies(account)

def check_gmail_replies(account):
    """
    Recupera le risposte per un account Gmail utilizzando l'API di Gmail.
    """
    headers = {"Authorization": f"Bearer {account.access_token}"}
    params = {"q": "in:inbox newer_than:5d subject:Re:"}

    response = requests.get(GMAIL_API_URL, headers=headers, params=params)

    if response.status_code == 200:
        messages = response.json().get("messages", [])
        for msg in messages:
            msg_id = msg["id"]
            email_data = get_gmail_message_details(account, msg_id, account.access_token)
            if email_data:
                save_email_reply(email_data, account)

def check_outlook_replies(account):
    """
    Recupera le risposte per un account Outlook utilizzando Microsoft Graph API.
    """
    headers = {"Authorization": f"Bearer {account.access_token}"}
    params = {"$filter": "isRead eq false and startswith(subject, 'Re:')"}

    response = requests.get(OUTLOOK_API_URL, headers=headers, params=params)

    if response.status_code == 200:
        messages = response.json().get("value", [])
        for msg in messages:
            email_data = {
                "lead_email": msg["from"]["emailAddress"]["address"],
                "subject": msg["subject"],
                "body": msg["body"]["content"],
                "received_at": msg["receivedDateTime"]
            }
            save_email_reply(email_data, account)

def check_imap_replies(account):
    """
    Controlla le risposte via IMAP per account personalizzati.
    """
    try:
        mail = imaplib.IMAP4_SSL(account.imap_host, account.imap_port)
        mail.login(account.username, account.password)
        mail.select("INBOX")

        result, data = mail.search(None, '(UNSEEN SUBJECT "Re:")')

        if result == "OK":
            for num in data[0].split():
                result, msg_data = mail.fetch(num, "(RFC822)")
                if result == "OK":
                    raw_email = msg_data[0][1]
                    msg = email.message_from_bytes(raw_email)
                    sender = msg["From"]
                    subject = msg["Subject"]
                    body = msg.get_payload(decode=True).decode() if not msg.is_multipart() else ""

                    lead = Lead.objects.filter(email=sender).first()
                    if lead:
                        email_log = EmailLog.objects.filter(lead=lead).order_by("-id").first()
                        if email_log:
                            EmailReplyTracking.objects.create(
                                lead=lead,
                                email_log=email_log,
                                subject=subject,
                                body=body,
                                received_at=now()
                            )
                            print(f"Reply recorded for {lead.email}")

        mail.logout()
    except Exception as e:
        print(f"IMAP error for {account.email_address}: {e}")

def get_email_body(msg_data):
    """
    Estrae il corpo dell'email dal payload.
    """
    if "parts" in msg_data["payload"]:
        for part in msg_data["payload"]["parts"]:
            if part["mimeType"] == "text/plain":
                return part["body"]["data"]
    return ""  

def get_gmail_message_details(account, msg_id, access_token):
    """
    Recupera i dettagli di un'email specifica tramite l'API di Gmail.
    """
    url = f"{GMAIL_API_URL}/{msg_id}"
    headers = {"Authorization": f"Bearer {access_token}"}
    
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        msg_data = response.json()
        headers = {h["name"]: h["value"] for h in msg_data["payload"]["headers"]}

        return {
            "lead_email": headers.get("From"),
            "subject": headers.get("Subject"),
            "body": get_email_body(msg_data),
            "received_at": msg_data["internalDate"]
        }
    return None

def save_email_reply(email_data, account):
    """
    Salva la risposta solo se proviene da un lead a cui abbiamo inviato un'email e non è già stata salvata.
    """
    lead = Lead.objects.filter(email=email_data["lead_email"]).first()
    if not lead:
        print(f"No lead found for {email_data['lead_email']}. Skipping.")
        return

    email_log = EmailLog.objects.filter(lead=lead).order_by("-sent_at").first()
    if not email_log:
        print(f"No email log found for {lead.email}. Skipping.")
        return

    if email_log.subject not in email_data["subject"]:
        print(f"Email reply subject does not match sent email for {lead.email}. Skipping.")
        return

    # **Gestione della conversione della data**
    received_at_str = email_data["received_at"]
    
    if received_at_str.isdigit():  
        received_at = datetime.datetime.fromtimestamp(int(received_at_str) / 1000)
    else:
        received_at = datetime.datetime.fromisoformat(received_at_str.replace("Z", "+00:00"))

    if is_naive(received_at):
        received_at = make_aware(received_at)

    # **Verifica se la risposta è già stata salvata con un controllo più rigoroso**
    try:
        EmailReplyTracking.objects.create(
            lead=lead,
            email_log=email_log,
            subject=email_data["subject"],
            body=email_data["body"],
            received_at=received_at
        )
        print(f"✅ Valid reply recorded for {lead.email}. Workflow will stop for this lead.")
    except IntegrityError:
        print(f"⚠️ Duplicate reply detected for {lead.email}. Skipping save.")