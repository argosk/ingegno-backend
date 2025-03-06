from django.db import connection
from workflows.models import WorkflowExecutionStep
from emails.models import EmailLog

def test_update_email_log():
    """Testa un semplice aggiornamento di email_log_id in WorkflowExecutionStep"""

    # 🔹 Prendi un qualsiasi step esistente
    step = WorkflowExecutionStep.objects.filter(email_log_id__isnull=True).first()
    
    if not step:
        print("⚠️ Nessuno step trovato con email_log_id NULL. Aggiungi un nuovo record.")
        return

    # 🔹 Crea una nuova email log di test
    email_log = EmailLog.objects.create(
        lead_id=1,
        subject="Test Subject",
        body="Test Body",
        status="SENT"
    )

    print(f"🔹 STEP SELEZIONATO: {step.id}")
    print(f"🔹 EMAIL LOG CREATA: {email_log.id}")

    # 🔥 TEST 1: Update con QuerySet
    WorkflowExecutionStep.objects.filter(id=step.id).update(email_log_id=email_log.id)

    # 🔥 TEST 2: Update con Raw SQL
    with connection.cursor() as cursor:
        cursor.execute(
            "UPDATE workflows_workflowexecutionstep SET email_log_id = %s WHERE id = %s",
            [email_log.id, step.id]
        )

    # 🔹 Verifica se l'update è stato salvato
    step.refresh_from_db()
    print(f"🔹 DOPO UPDATE, email_log_id = {step.email_log_id}")

    # 🔥 TEST 3: Controllo diretto nel database
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT email_log_id FROM workflows_workflowexecutionstep WHERE id = %s",
            [step.id]
        )
        result = cursor.fetchone()
        print(f"🔹 QUERY DIRETTA DB, email_log_id = {result[0]}")

test_update_email_log()
