import uuid
from django.db import models
from django.utils.timezone import now
from datetime import timedelta
from leads.models import Lead
from connected_accounts.models import ConnectedAccount

class EmailStatus(models.TextChoices):
    SENT = "sent", "Sent"
    PENDING = "pending", "Pending"
    OPENED = "opened", "Opened"
    CLICKED = "clicked", "Clicked"
    REPLIED = "replied", "Replied"
    BOUNCED = "bounced", "Bounced"

class EmailLog(models.Model):
    lead = models.ForeignKey(Lead, on_delete=models.CASCADE, related_name="emails")
    subject = models.CharField(max_length=255)
    body = models.TextField(blank=True)  # inizialmente vuoto
    sent_at = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=50, choices=EmailStatus.choices, default=EmailStatus.PENDING)
    sender = models.EmailField()

    def mark_sent(self):
        self.status = EmailStatus.SENT
        self.sent_at = now()
        self.save()

    def mark_failed(self):
        self.status = EmailStatus.FAILED
        self.save()

    def __str__(self):
        return f"Email to {self.lead.email} - {self.get_status_display()}"


class EmailClickTracking(models.Model):
    lead = models.ForeignKey(Lead, on_delete=models.CASCADE, related_name="clicks")
    email_log = models.ForeignKey(EmailLog, on_delete=models.CASCADE, related_name="clicks")
    link = models.URLField()
    clicked = models.BooleanField(default=False)  # Se il lead ha cliccato il link
    clicked_at = models.DateTimeField(null=True, blank=True)  # Data del click
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Lead {self.lead.email} - Clicked: {self.clicked}"


class EmailOpenTracking(models.Model):
    lead = models.ForeignKey(Lead, on_delete=models.CASCADE, related_name="email_opens")
    email_log = models.ForeignKey(EmailLog, on_delete=models.CASCADE, related_name="email_opens")
    opened = models.BooleanField(default=False)  # True se l'email è stata aperta
    opened_at = models.DateTimeField(null=True, blank=True)  # Data di apertura
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Lead {self.lead.email} - Opened: {self.opened}"
    
    class Meta:
        unique_together = ("lead", "email_log")
        # Evita duplicati per lead + email_log
        # Se un lead apre più volte la stessa email, non creerà più record
    
    
class EmailReplyTracking(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    lead = models.ForeignKey(Lead, on_delete=models.CASCADE, related_name="replies")
    email_log = models.ForeignKey(EmailLog, on_delete=models.CASCADE, related_name="replies")
    subject = models.CharField(max_length=255)
    body = models.TextField()
    received_at = models.DateTimeField(auto_now_add=True)
    read = models.BooleanField(default=False)

    class Meta:
        unique_together = ("lead", "email_log", "subject")  # Evita duplicati per lead + email_log + subject    

    def __str__(self):
        return f"Reply from {self.lead.email} - {self.subject}"    


class ThrottleStatus(models.Model):
    account = models.OneToOneField(ConnectedAccount, on_delete=models.CASCADE)
    consecutive_failures = models.IntegerField(default=0)
    last_error_at = models.DateTimeField(null=True, blank=True)
    paused_until = models.DateTimeField(null=True, blank=True)

    def is_throttled(self):
        return self.paused_until and now() < self.paused_until

    def reset(self):
        self.consecutive_failures = 0
        self.paused_until = None
        self.last_error_at = None
        self.save()

    def increase(self):
        self.consecutive_failures += 1
        self.last_error_at = now()
        if self.consecutive_failures >= 3:
            self.paused_until = now() + timedelta(minutes=10)
        self.save()