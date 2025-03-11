import uuid
from django.db import models
from campaigns.models import Campaign
from emails.models import EmailLog
from users.models import User


class WorkflowStatus(models.TextChoices):
    DRAFT = 'DRAFT'
    PUBLISHED = 'PUBLISHED'


class Workflow(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    campaign = models.OneToOneField(Campaign, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='workflows')
    name = models.CharField(max_length=255)
    description = models.CharField(max_length=255, blank=True, null=True)
    definition = models.JSONField(blank=True, null=True)
    status = models.CharField(max_length=50, choices=WorkflowStatus.choices, default=WorkflowStatus.DRAFT)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ['user', 'name']

    def __str__(self):
        return self.name
    

class WorkflowExecutionStatus(models.TextChoices):
    PENDING = 'PENDING'
    RUNNING = 'RUNNING'
    COMPLETED = 'COMPLETED'
    FAILED = 'FAILED'


class WorkflowExecution(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    workflow = models.ForeignKey(Workflow, on_delete=models.CASCADE, related_name='executions')
    trigger = models.CharField(max_length=50) # Manuale, programmato, evento cronjob, webhook, ecc.
    status = models.CharField(max_length=50, choices=WorkflowExecutionStatus.choices, default=WorkflowExecutionStatus.PENDING)
    created_at = models.DateTimeField(auto_now_add=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    is_obsolete = models.BooleanField(default=False)  # Campo per contrassegnare esecuzioni vecchie

    def __str__(self):
        return f"{self.workflow.name} - {self.status}"
    

class WorkflowExecutionStepStatus(models.TextChoices):
    CREATED = 'CREATED'
    PENDING = 'PENDING'
    RUNNING = 'RUNNING'
    COMPLETED = 'COMPLETED'
    FAILED = 'FAILED'


class WorkflowExecutionStep(models.Model):
    id = models.UUIDField(primary_key=True, editable=False)
    workflow_execution = models.ForeignKey(WorkflowExecution, on_delete=models.CASCADE, related_name='steps')
    status = models.CharField(max_length=50, choices=WorkflowExecutionStepStatus.choices, default=WorkflowExecutionStepStatus.CREATED)
    parent_node_id = models.UUIDField(null=True, blank=True)
    number = models.IntegerField()
    node = models.JSONField()
    name = models.CharField(max_length=50)
    condition = models.CharField(max_length=50, blank=True, null=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    credits_consumed = models.IntegerField(null=True, blank=True)
    email_log = models.ForeignKey(EmailLog, null=True, blank=True, on_delete=models.SET_NULL)

    def __str__(self):
        return f"Step {self.number} - {self.name} ({self.status})"
