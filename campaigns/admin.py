from django.contrib import admin

# Register your models here.
from .models import Campaign, EmailSequence

admin.site.register(Campaign)
admin.site.register(EmailSequence)