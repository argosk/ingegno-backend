from django.db import models
from campaigns.models import Campaign


class LeadStatus(models.TextChoices):
    NEW = "new"
    CONTACTED = "contacted"
    CONVERTED = "converted"


class Lead(models.Model):
    campaign = models.ForeignKey(Campaign, on_delete=models.CASCADE, related_name="leads")
    name = models.CharField(max_length=255)
    email = models.EmailField()
    phone = models.CharField(max_length=20, blank=True, null=True)
    company = models.CharField(max_length=255, blank=True, null=True)
    # source = models.CharField(max_length=100, help_text="Origine del lead, es. sito web, social")
    # lead_score = models.IntegerField(default=0)
    status = models.CharField(max_length=50, choices=LeadStatus.choices, default=LeadStatus.NEW)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

# class Lead(models.Model):
#     # campaign = models.ForeignKey(Campaign, on_delete=models.CASCADE, related_name="leads")
#     user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='leads')
#     email = models.EmailField()
#     name = models.CharField(max_length=255, blank=True)
#     company = models.CharField(max_length=255, blank=True)
#     uploaded_at = models.DateTimeField(auto_now_add=True)

#     def __str__(self):
#         return f"{self.name} - {self.email}"
