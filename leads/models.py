from django.db import models
from users.models import User

class Lead(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='leads')
    email = models.EmailField()
    name = models.CharField(max_length=255, blank=True)
    company = models.CharField(max_length=255, blank=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} - {self.email}"
