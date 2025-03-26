# from django.apps import AppConfig


# class WorkflowsConfig(AppConfig):
#     default_auto_field = 'django.db.models.BigAutoField'
#     name = 'workflows'
from django.apps import AppConfig

class WorkflowsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "workflows"

    def ready(self):
        import workflows.signals  # ✅ Importa i segnali quando l'app è pronta
