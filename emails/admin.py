from django.contrib import admin
from .models import Email, WarmUpTask

# Register your models here.
admin.site.register(Email)
admin.site.register(WarmUpTask)