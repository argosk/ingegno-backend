import requests
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from django.conf import settings
from django.utils.timezone import now
from emails.utils.throttling import is_account_throttled, update_throttle_status, reset_throttle_status


GMAIL_TOKEN_URL = "https://oauth2.googleapis.com/token"
GMAIL_SEND_API_URL = "https://www.googleapis.com/gmail/v1/users/me/messages/send"

MICROSOFT_TOKEN_URL = "https://login.microsoftonline.com/common/oauth2/v2.0/token"
OUTLOOK_SEND_API_URL = "https://graph.microsoft.com/v1.0/me/sendMail"

def refresh_outlook_token(account):
    """
    Aggiorna il token di accesso per un account Outlook se è scaduto.
    """
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
        account.token_expires_at = now()  # Aggiorna la data di scadenza
        account.save()
        print(f"Outlook token refreshed for {account.email_address}")
        return account.access_token
    else:
        print(f"Failed to refresh Outlook token for {account.email_address}. Error: {response.text}")
        return None

def refresh_gmail_token(account):
    """
    Aggiorna il token di accesso per un account Gmail se è scaduto.
    """
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
        account.token_expires_at = now()  # Aggiorniamo la data di scadenza
        account.save()
        print(f"Gmail token refreshed for {account.email_address}")
        return account.access_token
    else:
        print(f"Failed to refresh Gmail token for {account.email_address}. Error: {response.text}")
        return None

def send_email_gmail(account, recipient, subject, body):
    """
    Invia un'email usando l'API di Gmail, aggiornando il token se necessario.
    """
    # Verifica se l'account è in throttling
    if is_account_throttled(account):
        print(f"⛔ Gmail: {account.email_address} è in throttling. Invio annullato.")
        return

    # Se il token è scaduto, aggiorniamolo
    if account.token_expires_at and now() > account.token_expires_at:
        print(f"Gmail token expired for {account.email_address}, refreshing...")
        new_token = refresh_gmail_token(account)
        if not new_token:
            print(f"Cannot send email, no valid token for {account.email_address}")
            update_throttle_status(account)
            return

    headers = {"Authorization": f"Bearer {account.access_token}", "Content-Type": "application/json"}
    message = f"From: {account.email_address}\nTo: {recipient}\nSubject: {subject}\n\n{body}"
    encoded_message = {"raw": message.encode("utf-8").hex()}

    response = requests.post(GMAIL_SEND_API_URL, headers=headers, json=encoded_message)

    if response.status_code == 200:
        print(f"Gmail: Email sent successfully to {recipient}")
        reset_throttle_status(account)

    elif response.status_code == 401:  # Token scaduto, proviamo a rinnovarlo
        print(f"Gmail: Token expired for {account.email_address}. Refreshing token...")
        new_token = refresh_gmail_token(account)
        if new_token:
            send_email_gmail(account, recipient, subject, body)  # Riproviamo l'invio
        else:
            print(f"Gmail: Failed to refresh token. Email not sent to {recipient}.")
            update_throttle_status(account)

    else:
        print(f"Gmail: Failed to send email to {recipient}. Error: {response.text}")
        update_throttle_status(account)

def send_email_outlook(account, recipient, subject, body):
    """
    Invia un'email usando l'API di Microsoft Outlook, aggiornando il token se necessario.
    """
    if is_account_throttled(account):
        print(f"⛔ Outlook: {account.email_address} è in throttling. Invio annullato.")
        return

    if account.token_expires_at and now() > account.token_expires_at:
        print(f"Outlook token expired for {account.email_address}, refreshing...")
        new_token = refresh_outlook_token(account)
        if not new_token:
            print(f"Cannot send email, no valid token for {account.email_address}")
            update_throttle_status(account)
            return

    headers = {"Authorization": f"Bearer {account.access_token}", "Content-Type": "application/json"}
    email_data = {
        "message": {
            "subject": subject,
            "body": {"contentType": "Text", "content": body},
            "toRecipients": [{"emailAddress": {"address": recipient}}],
        },
        "saveToSentItems": "true",
    }

    response = requests.post(OUTLOOK_SEND_API_URL, headers=headers, json=email_data)

    if response.status_code == 202:
        print(f"Outlook: Email sent successfully to {recipient}")
        reset_throttle_status(account)

    elif response.status_code == 401:
        print(f"Outlook: Token expired for {account.email_address}. Refreshing token...")
        new_token = refresh_outlook_token(account)
        if new_token:
            send_email_outlook(account, recipient, subject, body)
        else:
            print(f"Outlook: Failed to refresh token. Email not sent to {recipient}.")
            update_throttle_status(account)
    else:
        print(f"Outlook: Failed to send email to {recipient}. Error: {response.text}")
        update_throttle_status(account)

# def send_email_outlook(account, recipient, subject, body):
#     """
#     Invia un'email usando l'API di Microsoft Outlook, aggiornando il token se necessario.
#     """
#     # Se il token è scaduto, aggiorniamolo
#     if account.token_expires_at and now() > account.token_expires_at:
#         print(f"Outlook token expired for {account.email_address}, refreshing...")
#         new_token = refresh_outlook_token(account)
#         if not new_token:
#             print(f"Cannot send email, no valid token for {account.email_address}")
#             return

#     headers = {"Authorization": f"Bearer {account.access_token}", "Content-Type": "application/json"}
#     email_data = {
#         "message": {
#             "subject": subject,
#             "body": {"contentType": "Text", "content": body},
#             "toRecipients": [{"emailAddress": {"address": recipient}}],
#         },
#         "saveToSentItems": "true",
#     }

#     response = requests.post(OUTLOOK_SEND_API_URL, headers=headers, json=email_data)

#     if response.status_code == 202:
#         print(f"Outlook: Email sent successfully to {recipient}")
#     elif response.status_code == 401:  # Token scaduto, proviamo a rinnovarlo
#         print(f"Outlook: Token expired for {account.email_address}. Refreshing token...")
#         new_token = refresh_outlook_token(account)
#         if new_token:
#             send_email_outlook(account, recipient, subject, body)  # Riproviamo l'invio
#         else:
#             print(f"Outlook: Failed to refresh token. Email not sent to {recipient}.")
#     else:
#         print(f"Outlook: Failed to send email to {recipient}. Error: {response.text}")

def send_email_smtp(account, recipient, subject, body):
    """
    Invia un'email usando SMTP per account IMAP personalizzati.
    """
    if is_account_throttled(account):
        print(f"⛔ SMTP: {account.email_address} è in throttling. Invio annullato.")
        return

    try:
        msg = MIMEMultipart()
        msg["From"] = account.email_address
        msg["To"] = recipient
        msg["Subject"] = subject
        msg.attach(MIMEText(body, "plain"))

        server = smtplib.SMTP(account.smtp_host, account.smtp_port)
        server.starttls()
        server.login(account.username, account.password)
        server.sendmail(account.email_address, recipient, msg.as_string())
        server.quit()

        print(f"SMTP: Email sent successfully to {recipient}")
        reset_throttle_status(account)

    except Exception as e:
        print(f"SMTP: Failed to send email to {recipient}. Error: {e}")
        update_throttle_status(account)
