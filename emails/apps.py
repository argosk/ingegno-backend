from django.apps import AppConfig

class EmailsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'emails'

    # def ready(self):
    #     """
    #     Importa i segnali quando Django è pronto.
    #     """
    #     import emails.signals  # Importiamo i segnali
