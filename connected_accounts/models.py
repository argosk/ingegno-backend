from django.db import models
from connected_accounts.utils import encrypt_password
from users.models import User


class Provider(models.TextChoices):
    GMAIL = 'gmail', 'Gmail / G-Suite'
    OUTLOOK = 'outlook', 'Office 365 / Outlook'
    IMAP_SMTP = 'imap_smtp', 'IMAP / SMTP'

class ConnectedAccount(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='connected_accounts')
    provider = models.CharField(max_length=20, choices=Provider.choices)
    email_address = models.EmailField(unique=True)
    username = models.CharField(max_length=255, null=True, blank=True)  # Username per l'accesso IMAP/SMTP
    password = models.CharField(max_length=255, null=True, blank=True)  # Password (criptata!)    
    access_token = models.TextField(null=True, blank=True)  # Token per OAuth2 (se applicabile)
    refresh_token = models.TextField(null=True, blank=True)  # Per Gmail/Outlook
    token_expires_at = models.DateTimeField(null=True, blank=True)
    imap_host = models.CharField(max_length=255, null=True, blank=True)  # Solo per IMAP personalizzato
    imap_port = models.PositiveIntegerField(default=993)  # Default IMAP SSL port
    smtp_host = models.CharField(max_length=255, null=True, blank=True)
    smtp_port = models.PositiveIntegerField(default=587)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.email_address} ({self.get_provider_display()})"
    
    def save(self, *args, **kwargs):
        if self.password:
            self.password = encrypt_password(self.password)
        super().save(*args, **kwargs)

