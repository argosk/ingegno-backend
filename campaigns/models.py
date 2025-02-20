from django.db import models
from leads.models import Lead
from users.models import User

class Campaign(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    name = models.CharField(max_length=255)
    start_date = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    leads = models.ManyToManyField(Lead)  # Leads associati alla campagna


class EmailSequence(models.Model):
    campaign = models.ForeignKey(
        Campaign, 
        on_delete=models.CASCADE, 
        related_name='email_sequences'  # Permette di accedere alle sequenze tramite campaign.email_sequences
    )
    subject = models.CharField(max_length=255)
    body = models.TextField()
    order = models.PositiveIntegerField()  # Ordine del follow-up
    send_after_days = models.PositiveIntegerField(default=0)
