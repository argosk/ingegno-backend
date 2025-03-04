import uuid
from django.db import models
from users.models import User

class Campaign(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    name = models.CharField(max_length=255)
    start_date = models.DateTimeField(null=True, blank=True)
    end_date = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)


# class EmailSequence(models.Model):
#     campaign = models.ForeignKey(
#         Campaign, 
#         on_delete=models.CASCADE, 
#         related_name='email_sequences'  # Permette di accedere alle sequenze tramite campaign.email_sequences
#     )
#     subject = models.CharField(max_length=255)
#     body = models.TextField()
#     order = models.PositiveIntegerField()  # Ordine del follow-up
#     send_after_days = models.PositiveIntegerField(default=0)
