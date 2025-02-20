from django.contrib import admin
from .models import Blog

class BlogAdmin(admin.ModelAdmin):
    prepopulated_fields = {"slug": ("title",)}  # Precompila lo slug basandosi sul titolo

admin.site.register(Blog, BlogAdmin)
