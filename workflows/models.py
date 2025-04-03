import uuid
from django.db import models
from campaigns.models import Campaign
from emails.models import EmailLog
from leads.models import Lead
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


class WorkflowSettings(models.Model):
    workflow = models.OneToOneField(Workflow, on_delete=models.CASCADE, related_name="settings")
    
    # Start options
    start = models.CharField(max_length=10, choices=[('new', 'New Leads Only'), ('all', 'All Leads')], default='new')
    
    # Email sending settings
    max_emails_per_day = models.IntegerField(default=50)
    pause_between_emails = models.IntegerField(default=30)

    # Handling replies
    reply_action = models.CharField(max_length=10, choices=[('stop', 'Stop Workflow'), ('continue', 'Continue Workflow')], default='stop')

    # Sending Schedule
    sending_time_start = models.TimeField(default="08:00")
    sending_time_end = models.TimeField(default="18:00")
    sending_days = models.JSONField(default=list)  # ['monday', 'tuesday', ...]

    # Unsubscribe & Bounce Handling
    unsubscribe_handling = models.CharField(max_length=10, choices=[('remove', 'Remove'), ('exclude', 'Exclude')], default='remove')
    bounce_handling = models.CharField(max_length=10, choices=[('stop', 'Stop Workflow'), ('retry', 'Retry with Another Template'), ('continue', 'Continue Workflow')], default='stop')

    def __str__(self):
        return f"Settings for {self.workflow.name}"


# class WorkflowExecutionStatus(models.TextChoices):
#     PENDING = 'PENDING'
#     RUNNING = 'RUNNING'
#     COMPLETED = 'COMPLETED'
#     FAILED = 'FAILED'


class WorkflowExecution(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    workflow = models.OneToOneField(Workflow, on_delete=models.CASCADE, related_name='execution')
    trigger = models.CharField(max_length=50) # Manuale, programmato, evento cronjob, webhook, ecc.
    # status = models.CharField(max_length=50, choices=WorkflowExecutionStatus.choices, default=WorkflowExecutionStatus.PENDING)
    created_at = models.DateTimeField(auto_now_add=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    is_obsolete = models.BooleanField(default=False)  # Campo per contrassegnare esecuzioni vecchie

    def __str__(self):
        return f"{self.workflow.name}"
    

class WorkflowExecutionStepStatus(models.TextChoices):
    CREATED = 'CREATED'
    PENDING = 'PENDING'
    RUNNING = 'RUNNING'
    COMPLETED = 'COMPLETED'
    FAILED = 'FAILED'
    SKIPPED = 'SKIPPED'


class WorkflowExecutionStep(models.Model):
    id = models.UUIDField(primary_key=True, editable=False)
    workflow_execution = models.ForeignKey(WorkflowExecution, on_delete=models.CASCADE, related_name='steps')
    # status = models.CharField(max_length=50, choices=WorkflowExecutionStepStatus.choices, default=WorkflowExecutionStepStatus.CREATED)
    parent_node_id = models.UUIDField(null=True, blank=True)
    number = models.IntegerField()
    node = models.JSONField()
    name = models.CharField(max_length=50)
    condition = models.CharField(max_length=50, blank=True, null=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    credits_consumed = models.IntegerField(null=True, blank=True)
    # email_log = models.ForeignKey(EmailLog, null=True, blank=True, on_delete=models.SET_NULL)

    def __str__(self):
        return f"Step {self.number} - {self.name}"
    
class WorkflowQueue(models.Model):
    lead = models.ForeignKey(Lead, on_delete=models.CASCADE)
    workflow_execution = models.ForeignKey(WorkflowExecution, on_delete=models.CASCADE)
    settings = models.JSONField()

    processed = models.BooleanField(default=False)
    processing = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)
    processed_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"Queue: {self.lead.email} - {self.workflow_execution.workflow.name}"    

class LeadWorkflowStateStatus(models.TextChoices):
    RUNNING = 'RUNNING'
    COMPLETED = 'COMPLETED'
    FAILED = 'FAILED'

class LeadStepStatus(models.Model):
    lead = models.ForeignKey("leads.Lead", on_delete=models.CASCADE, related_name="step_statuses")
    workflow = models.ForeignKey(Workflow, on_delete=models.CASCADE)
    step = models.ForeignKey(WorkflowExecutionStep, on_delete=models.CASCADE)
    status = models.CharField(max_length=50, choices=WorkflowExecutionStepStatus.choices, default=WorkflowExecutionStepStatus.CREATED)
    condition = models.CharField(max_length=50, blank=True, null=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    email_log = models.ForeignKey(EmailLog, null=True, blank=True, on_delete=models.SET_NULL)


    class Meta:
        unique_together = ("lead", "workflow", "step")