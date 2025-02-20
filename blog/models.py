from django.db import models
from tinymce import models as tinymce_models


class Blog(models.Model):
    title = models.CharField(max_length=200)
    slug = models.SlugField(max_length=255, unique=True)
    content = tinymce_models.HTMLField()
    image = models.TextField(null=True, blank=True)
    seo_title = models.CharField(max_length=160)
    seo_description = models.CharField(max_length=160)
    seo_keywords = models.CharField(max_length=160, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.title