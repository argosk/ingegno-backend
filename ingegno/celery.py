from __future__ import absolute_import, unicode_literals

import os
import ssl

from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "ingegno.settings")

app = Celery("ingegno")

# in production
# app = Celery('core',
#              broker_use_ssl={
#                  'ssl_cert_reqs': ssl.CERT_NONE
#              },
#              redis_backend_use_ssl={
#                  'ssl_cert_reqs': ssl.CERT_NONE
#              }
#              )

app.config_from_object("django.conf:settings", namespace="CELERY")

app.autodiscover_tasks()
