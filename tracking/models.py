from django.db import models

from emails.models import Email


class EmailTracking(models.Model):
    email = models.OneToOneField(Email, on_delete=models.CASCADE)
    opened_at = models.DateTimeField(null=True, blank=True)
    clicked_at = models.DateTimeField(null=True, blank=True)
    replied_at = models.DateTimeField(null=True, blank=True)
    # unsubscribed_at = models.DateTimeField(null=True, blank=True)
