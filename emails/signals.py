import json
from django.db.models.signals import post_migrate
from django.dispatch import receiver
from django_celery_beat.models import PeriodicTask, IntervalSchedule

@receiver(post_migrate)
def setup_periodic_tasks(sender, **kwargs):
    """
    Eseguito dopo le migrazioni per configurare il task periodico.
    """
    if sender.name == "emails":  # Evita di eseguire il codice per ogni app
        print("Checking if periodic task exists...")

        schedule, created = IntervalSchedule.objects.get_or_create(
            every=5,
            period=IntervalSchedule.MINUTES,
        )

        PeriodicTask.objects.update_or_create(
            name="Check email replies",
            defaults={
                "interval": schedule,
                "task": "emails.tasks.check_email_replies",  # ✅ Nome corretto
                "args": json.dumps([]),
                "enabled": True,
            },
        )
        print("✅ Periodic task setup completed.")
