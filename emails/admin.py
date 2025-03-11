from django.contrib import admin
from .models import EmailLog, EmailClickTracking

admin.site.register(EmailLog)
admin.site.register(EmailClickTracking)
