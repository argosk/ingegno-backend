from cryptography.fernet import Fernet
from django.conf import settings
import dns.resolver
import base64

# Crea la chiave Fernet a partire dalla chiave segreta nelle settings
FERNET_KEY = base64.urlsafe_b64encode(settings.FERNET_SECRET_KEY.encode())

def encrypt_password(password):
    cipher = Fernet(FERNET_KEY)
    return cipher.encrypt(password.encode()).decode()

def decrypt_password(encrypted_password):
    cipher = Fernet(FERNET_KEY)
    return cipher.decrypt(encrypted_password.encode()).decode()


def discover_email_servers(email_address):
    domain = email_address.split('@')[1]
    
    # Default configuration nel caso il lookup DNS fallisca
    imap_server = f"imap.{domain}"
    smtp_server = f"smtp.{domain}"

    try:
        # Prova a risolvere i record MX per il dominio
        mx_records = dns.resolver.resolve(domain, 'MX')
        if mx_records:
            # Utilizziamo il primo record per derivare i server
            mail_server = str(mx_records[0].exchange).rstrip('.')
            imap_server = f"imap.{mail_server}"
            smtp_server = f"smtp.{mail_server}"
    except Exception as e:
        print(f"Errore nel lookup dei server MX: {e}")

    return {
        "imap_host": imap_server,
        "imap_port": 993,  # Default SSL port
        "smtp_host": smtp_server,
        "smtp_port": 587   # Default TLS port
    }