from django.contrib import admin
from .models import EmailLog, ClickLog

admin.site.register(EmailLog)
admin.site.register(ClickLog)
