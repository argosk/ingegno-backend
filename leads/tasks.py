import csv
import io
from celery import shared_task
from django.core.cache import cache
from .models import Lead, LeadStatus
from campaigns.models import Campaign

@shared_task(bind=True)
def process_csv_leads(self, file_data, campaign_id, user_id):
    """
    Task Celery per elaborare il CSV e salvare i lead in modo asincrono.
    """
    from django.contrib.auth import get_user_model
    User = get_user_model()

    try:
        campaign = Campaign.objects.get(id=campaign_id, user_id=user_id)
    except Campaign.DoesNotExist:
        return {"error": "Campaign not found or unauthorized."}

    csv_reader = csv.DictReader(io.StringIO(file_data))
    total_rows = sum(1 for row in csv_reader)  # Conta il numero di righe
    csv_reader = csv.DictReader(io.StringIO(file_data))  # Rilegge dall'inizio

    leads = []
    errors = []
    processed_count = 0

    for row in csv_reader:
        # status_value = row.get('status', LeadStatus.NEW).strip().lower()
        # if status_value not in dict(LeadStatus.choices):
        #     errors.append(f"Invalid status '{status_value}' for lead {row.get('email')}")
        #     continue

        lead = Lead(
            campaign=campaign,
            name=row.get('name', '').strip(),
            email=row.get('email', '').strip(),
            phone=row.get('phone', '').strip() if 'phone' in row else None,
            company=row.get('company', '').strip() if 'company' in row else None,
        )
        leads.append(lead)
        processed_count += 1

        # Aggiorna la cache con la percentuale di avanzamento
        cache.set(f"csv_progress_{self.request.id}", int((processed_count / total_rows) * 100), timeout=600)

        # Salvataggio ogni 500 leads per evitare memory overflow
        if processed_count % 500 == 0:
            Lead.objects.bulk_create(leads)
            leads = []

    if leads:
        Lead.objects.bulk_create(leads)

    return {"status": "completed", "processed": processed_count, "errors": errors}
