from django.db import models

from users.models import User
from campaigns.models import EmailSequence

# Create your models here.
from django.db import models
from leads.models import Lead
from campaigns.models import EmailSequence


class Email(models.Model):
    sequence = models.ForeignKey(EmailSequence, on_delete=models.CASCADE)
    lead = models.ForeignKey(Lead, on_delete=models.CASCADE, related_name='emails')  # Aggiunto related_name
    sender_email = models.EmailField()
    status = models.CharField(max_length=20, choices=[('pending', 'Pending'), ('sent', 'Sent'), ('failed', 'Failed')])
    sent_at = models.DateTimeField(null=True, blank=True)

    def get_recipient_email(self):
        # Retrieve the email directly from the associated lead
        return self.lead.email


class WarmUpTask(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    email_account = models.EmailField()  # Account connesso (Gmail/Outlook)
    start_date = models.DateTimeField()
    daily_limit = models.PositiveIntegerField(default=10)  # Numero giornaliero iniziale
    increase_rate = models.PositiveIntegerField(default=5)  # Incremento giornaliero
    max_limit = models.PositiveIntegerField(default=100)  # Limite massimo
    is_active = models.BooleanField(default=False)
