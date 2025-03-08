from django.db import models
from leads.models import Lead

class EmailStatus(models.TextChoices):
    SENT = "sent", "Sent"
    OPENED = "opened", "Opened"
    CLICKED = "clicked", "Clicked"
    REPLIED = "replied", "Replied"
    BOUNCED = "bounced", "Bounced"

class EmailLog(models.Model):
    lead = models.ForeignKey(Lead, on_delete=models.CASCADE, related_name="emails")
    subject = models.CharField(max_length=255)
    body = models.TextField()
    sent_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=50, choices=EmailStatus.choices, default=EmailStatus.SENT)
    response_received = models.BooleanField(default=False)

    def __str__(self):
        return f"Email to {self.lead.email} - {self.get_status_display()}"


class ClickLog(models.Model):
    email_log = models.ForeignKey(EmailLog, on_delete=models.CASCADE, related_name="clicks")
    link = models.URLField()
    clicked_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Click on {self.link} by {self.email_log.lead.email}"