Celery

celery -A ingegno worker --loglevel=info
celery -A ingegno beat --scheduler django_celery_beat.schedulers:DatabaseScheduler

---
Errore quando lancio il workflow su tutti i leads.