from django.db import models
from campaigns.models import Campaign


class LeadStatus(models.TextChoices):
    NEW = "new"
    CONTACTED = "contacted"
    CONVERTED = "converted"
    BOUNCED = "bounced"

class LeadWorkflowExecutionStatus(models.TextChoices):
    PENDING = 'PENDING'
    COMPLETED = 'COMPLETED'
    FAILED = 'FAILED'
    SKIPPED = 'SKIPPED'

class Lead(models.Model):
    campaign = models.ForeignKey(Campaign, on_delete=models.CASCADE, related_name="leads")
    name = models.CharField(max_length=255)
    email = models.EmailField()
    phone = models.CharField(max_length=20, blank=True, null=True)
    company = models.CharField(max_length=255, blank=True, null=True)
    sequence = models.IntegerField(default=0) # Numero di email inviate al lead
    status = models.CharField(max_length=50, choices=LeadStatus.choices, default=LeadStatus.NEW)
    unsubscribed = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    workflow_status = models.CharField(max_length=50, choices=LeadWorkflowExecutionStatus.choices, default=LeadWorkflowExecutionStatus.PENDING)

