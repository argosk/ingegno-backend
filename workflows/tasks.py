import json
import time
from celery import shared_task
from django.utils.timezone import now
from django.db import connection
from workflows.models import WorkflowExecution, WorkflowExecutionStatus, WorkflowExecutionStep, WorkflowExecutionStepStatus
from emails.models import EmailLog, EmailStatus, ClickLog


def check_link_clicked(email_log_id) -> bool:
    """Verifica se il link di un'email è stato cliccato."""
    return ClickLog.objects.filter(email_log_id=email_log_id).exists()

def check_email_opened(email_log_id) -> bool:
    """Verifica se l'email è stata aperta."""
    return EmailLog.objects.filter(id=email_log_id, status=EmailStatus.OPENED).exists()

def propagate_email_log_id(parent_node_id, email_log_id):
    """Propaga l'email_log_id a tutti i nodi successivi nel workflow"""
    with connection.cursor() as cursor:
        cursor.execute(
            """
            WITH RECURSIVE next_steps AS (
                SELECT id, parent_node_id FROM workflows_workflowexecutionstep WHERE parent_node_id = %s
                UNION ALL
                SELECT w.id, w.parent_node_id
                FROM workflows_workflowexecutionstep w
                INNER JOIN next_steps ns ON w.parent_node_id = ns.id
            )
            UPDATE workflows_workflowexecutionstep
            SET email_log_id = %s
            WHERE id IN (SELECT id FROM next_steps)
            """,
            [parent_node_id, email_log_id]
        )
    print(f"@DEBUG: 🔄 Propagato email_log_id={email_log_id} a tutti i nodi successivi di {parent_node_id}")


@shared_task(bind=True)
def execute_workflow_task(self, workflow_execution_id):
    """Esegue un workflow step-by-step in modo asincrono con Celery"""

    execution = WorkflowExecution.objects.get(id=workflow_execution_id)
    if execution.status != WorkflowExecutionStepStatus.PENDING:
        return f"Workflow {execution.id} is already {execution.status}"

    execution.status = "RUNNING"
    execution.started_at = now()
    execution.save()


    def execute_step(step):
        """Esegue un singolo step del workflow"""
        print(f"\n@DEBUG: 🚀 Esecuzione step {step.id} - email_log_id PRIMA: {step.email_log_id}")

        step.status = WorkflowExecutionStepStatus.RUNNING
        step.started_at = now()
        WorkflowExecutionStep.objects.filter(id=step.id).update(
            status=step.status, started_at=step.started_at
        )

        node_data = json.loads(step.node) if isinstance(step.node, str) else step.node
        success = False
        next_condition = None

        if step.name == "SEND_EMAIL":
            email_log = EmailLog.objects.create(
                lead_id=1,
                subject=node_data.get("data", {}).get("settings", {}).get("subject", "Default Subject"),
                body=node_data.get("data", {}).get("settings", {}).get("body", "Default Body"),
                status=EmailStatus.SENT
            )

            # ✅ UPDATE DIRETTO NEL DATABASE PER EVITARE CACHE DJANGO
            with connection.cursor() as cursor:
                cursor.execute(
                    "UPDATE workflows_workflowexecutionstep SET email_log_id = %s WHERE parent_node_id = %s",
                    [email_log.id, node_data.get("id")]
                )
            
            propagate_email_log_id(node_data.get("id"), email_log.id)

            print(f"@DEBUG: ✅ Step aggiornato nel DB con email_log_id = {email_log.id}")

            time.sleep(2)  # Simula il ritardo di invio dell'email
            print("@DEBUG: ✅ Email inviata")
            success = True

        elif step.name == "WAIT":
            print("@DEBUG: ⏳ Attesa")
            wait_time = node_data.get("data", {}).get("settings", {}).get("delay_hours", 1)
            time.sleep(30)  # ⚠️ Simulazione temporanea, ripristinare `time.sleep(wait_time * 3600)`
            success = True

        elif step.name == "CHECK_LINK_CLICKED":
            # 🔄 Ricarichiamo lo step dal database per assicurarci che `email_log_id` sia aggiornato
            step.refresh_from_db()

            if step.email_log_id:
                response = check_link_clicked(step.email_log_id)
                next_condition = "YES" if response else "NO"
                print(f"@DEBUG: ✅ CHECK_LINK_CLICKED - Link cliccato: {response}")
                success = True
            else:
                print(f"@DEBUG: ❌ CHECK_LINK_CLICKED - Nessun email_log_id trovato per step {step.id}")
     

        step.status = WorkflowExecutionStepStatus.COMPLETED if success else WorkflowExecutionStepStatus.FAILED
        step.completed_at = now()
        WorkflowExecutionStep.objects.filter(id=step.id).update(
            status=step.status, completed_at=step.completed_at
        )

        return next_condition, node_data

    def process_steps(current_steps):
        """Esegue tutti gli step e continua il workflow"""
        for step in current_steps:
            print(f"\n@DEBUG: 📌 Prima dello step {step.id}, email_log_id = {step.email_log_id}")
            
            next_condition, node_data = execute_step(step)

            if next_condition is not None:
                next_steps = WorkflowExecutionStep.objects.filter(
                    workflow_execution=execution,
                    parent_node_id=node_data.get("id"),
                    condition=next_condition
                )

                print(f"@DEBUG: 📌 STEP SUCCESSIVO TROVATO: {next_steps}")
                process_steps(next_steps)

    steps = WorkflowExecutionStep.objects.filter(
        workflow_execution=execution,
        status=WorkflowExecutionStepStatus.CREATED
    ).order_by("number")

    if steps.exists():
        process_steps(steps)

    execution.status = WorkflowExecutionStepStatus.COMPLETED
    execution.completed_at = now()
    execution.save()

    return f"Workflow {execution.id} completed successfully"


# import json
# import time
# from celery import shared_task
# from django.utils.timezone import now
# from django.db import connection
# from workflows.models import WorkflowExecution, WorkflowExecutionStatus, WorkflowExecutionStep, WorkflowExecutionStepStatus
# from emails.models import EmailLog, EmailStatus, ClickLog


# def check_link_clicked(email_log_id) -> bool:
#     """Verifica se il link di un'email è stato cliccato."""
#     return ClickLog.objects.filter(email_log_id=email_log_id).exists()

# def check_email_opened(email_log_id) -> bool:
#     """Verifica se l'email è stata aperta."""
#     return EmailLog.objects.filter(id=email_log_id, status=EmailStatus.OPENED).exists()

# @shared_task(bind=True)
# def execute_workflow_task(self, workflow_execution_id):
#     """Esegue un workflow step-by-step in modo asincrono con Celery"""

#     execution = WorkflowExecution.objects.get(id=workflow_execution_id)
#     if execution.status != WorkflowExecutionStepStatus.PENDING:
#         return f"Workflow {execution.id} is already {execution.status}"

#     execution.status = "RUNNING"
#     execution.started_at = now()
#     execution.save()

#     def execute_step(step):
#         """Esegue un singolo step del workflow"""
#         print(f"\n@DEBUG: 🚀 Esecuzione step {step.id} - email_log_id PRIMA: {step.email_log_id}")

#         step.status = WorkflowExecutionStepStatus.RUNNING
#         step.started_at = now()
#         WorkflowExecutionStep.objects.filter(id=step.id).update(
#             status=step.status, started_at=step.started_at
#         )

#         node_data = json.loads(step.node) if isinstance(step.node, str) else step.node
#         success = False

#         if step.name == "SEND_EMAIL":
#             email_log = EmailLog.objects.create(
#                 lead_id=1,
#                 subject=node_data.get("data", {}).get("settings", {}).get("subject", "Default Subject"),
#                 body=node_data.get("data", {}).get("settings", {}).get("body", "Default Body"),
#                 status=EmailStatus.SENT
#             )

#             # ✅ UPDATE DIRETTO NEL DATABASE PER EVITARE CACHE DJANGO
#             with connection.cursor() as cursor:
#                 cursor.execute(
#                     "UPDATE workflows_workflowexecutionstep SET email_log_id = %s WHERE parent_node_id = %s",
#                     [email_log.id, node_data.get("id")]
#                 )

#             print(f"@DEBUG: ✅ Step aggiornato nel DB con email_log_id = {email_log.id}")

#             time.sleep(2)  # Simula il ritardo di invio dell'email
#             print("@DEBUG: ✅ Email inviata")
#             success = True

#         elif step.name == "WAIT":
#             print("@DEBUG: attesa")
#             wait_time = node_data.get("data", {}).get("settings", {}).get("delay_hours", 1)
#             # time.sleep(wait_time * 3600)  # Simula il delay
#             time.sleep(30)  # TODO:  Simula il delay non reale per test - ripristinare quello sopra
#             success = True

#         # elif step.name == "CHECK_LINK_CLICKED":
#         #     if step.email_log:
#         #         response = check_link_clicked(step.email_log.id)
#         #         next_condition = "YES" if response else "NO"
#         #         print("@DEBUG: CHECK_LINK_CLICKED:", response)
#         #         success = True            

#         step.status = WorkflowExecutionStepStatus.COMPLETED if success else WorkflowExecutionStepStatus.FAILED
#         step.completed_at = now()
#         WorkflowExecutionStep.objects.filter(id=step.id).update(
#             status=step.status, completed_at=step.completed_at
#         )

#         return node_data.get("next_condition"), node_data

#     def process_steps(current_steps):
#         """Esegue tutti gli step e continua il workflow"""
#         for step in current_steps:
#             print(f"\n@DEBUG: 📌 Prima dello step {step.id}, email_log_id = {step.email_log_id}")
            
#             next_condition, node_data = execute_step(step)

#             if next_condition is not None:
#                 next_steps = WorkflowExecutionStep.objects.filter(
#                     workflow_execution=execution,
#                     parent_node_id=node_data.get("id"),
#                     condition=next_condition
#                 )

#                 print(f"@DEBUG: 📌 STEP SUCCESSIVO TROVATO: {next_steps}")
#                 process_steps(next_steps)

#     steps = WorkflowExecutionStep.objects.filter(
#         workflow_execution=execution,
#         status=WorkflowExecutionStepStatus.CREATED
#     ).order_by("number")

#     if steps.exists():
#         process_steps(steps)

#     execution.status = WorkflowExecutionStepStatus.COMPLETED
#     execution.completed_at = now()
#     execution.save()

#     return f"Workflow {execution.id} completed successfully"



# import json
# from celery import shared_task
# from django.utils.timezone import now
# from django.db import connection, transaction
# import time
# from workflows.models import WorkflowExecution, WorkflowExecutionStep, WorkflowExecutionStepStatus
# from emails.models import EmailLog, ClickLog, EmailStatus


# @shared_task(bind=True)
# def execute_workflow_task(self, workflow_execution_id):
#     """Esegue un workflow step-by-step in modo asincrono con Celery"""

#     execution = WorkflowExecution.objects.get(id=workflow_execution_id)
#     if execution.status != WorkflowExecutionStepStatus.PENDING:
#         return f"Workflow {execution.id} is already {execution.status}"

#     execution.status = "RUNNING"
#     execution.started_at = now()
#     execution.save()

#     def execute_step(step):
#         """Esegue un singolo step del workflow"""
#         print(f"\n@DEBUG: 🚀 Esecuzione dello step {step.id} - email_log_id PRIMA dell'update: {step.email_log_id}")

#         step.status = WorkflowExecutionStepStatus.RUNNING
#         step.started_at = now()
#         step.save()

#         node_data = json.loads(step.node) if isinstance(step.node, str) else step.node
#         success = False
#         next_condition = None

#         if step.name == "SEND_EMAIL":
#             email_log = EmailLog.objects.create(
#                 lead_id=1,
#                 subject=node_data.get("data", {}).get("settings", {}).get("subject", "Default Subject"),
#                 body=node_data.get("data", {}).get("settings", {}).get("body", "Default Body"),
#                 status=EmailStatus.SENT
#             )

#             queryset = WorkflowExecutionStep.objects.filter(
#                 workflow_execution=execution,
#                 parent_node_id=node_data.get("id")
#             )

#             print("@DEBUG: email_log.id =", email_log.id)
#             print("@DEBUG: Nodi trovati per aggiornamento:", queryset)

#             if queryset.exists():
#                 print("@DEBUG: 🚀 Tentativo di aggiornamento con SQL")

#                 # ✅ UPDATE DIRETTO NEL DATABASE
#                 with connection.cursor() as cursor:
#                     cursor.execute(
#                         "UPDATE workflows_workflowexecutionstep SET email_log_id = %s WHERE parent_node_id = %s",
#                         [email_log.id, node_data.get("id")]
#                     )

#                 # 🔄 Verifica diretta nel DB
#                 with connection.cursor() as cursor:
#                     cursor.execute(
#                         "SELECT id, email_log_id FROM workflows_workflowexecutionstep WHERE parent_node_id = %s",
#                         [node_data.get("id")]
#                     )
#                     rows = cursor.fetchall()
#                     for row in rows:
#                         print(f"@DEBUG: ✅ Confermato nel DB step {row[0]} con email_log_id = {row[1]}")

#                 # 🔄 Aggiornamento forzato per Django
#                 queryset.update(email_log_id=email_log.id)

#             time.sleep(2)  # Simula il ritardo di invio dell'email
#             print("@DEBUG: ✅ email inviata")
#             success = True

#         step.status = WorkflowExecutionStepStatus.COMPLETED if success else WorkflowExecutionStepStatus.FAILED
#         step.completed_at = now()

#         # 🚀 ✅ Evitiamo `save()`, usiamo `.update()` per assicurare che Django non perda i dati
#         WorkflowExecutionStep.objects.filter(id=step.id).update(
#             status=step.status,
#             completed_at=step.completed_at
#         )

#         # 🔄 Forziamo il reload dal database
#         step.refresh_from_db()
#         print(f"@DEBUG: 🔄 Dopo refresh, step {step.id} ha email_log_id = {step.email_log_id}")

#         return next_condition, node_data

#     def process_steps(current_steps):
#         """Esegue tutti gli step e continua il workflow"""
#         for step in current_steps:
#             # 🔄 Prima di eseguire ogni step, ricarichiamo dal DB
#             step = WorkflowExecutionStep.objects.get(id=step.id)
#             print(f"\n@DEBUG: 📌 Prima dell'esecuzione dello step {step.id}, email_log_id = {step.email_log_id}")

#             next_condition, node_data = execute_step(step)

#             # 🔄 Dopo l'update, ricarichiamo di nuovo dal database
#             step.refresh_from_db()
#             print(f"@DEBUG: 🔄 Dopo refresh_from_db(), step {step.id} ha email_log_id = {step.email_log_id}")

#             if next_condition is not None:
#                 next_steps = WorkflowExecutionStep.objects.filter(
#                     workflow_execution=execution,
#                     parent_node_id=node_data.get("id"),
#                     condition=next_condition
#                 ).select_related('email_log')  # 🔥 Evita lazy loading, forza il fetch dei dati

#                 print(f"@DEBUG: 📌 STEP SUCCESSIVO TROVATO: {next_steps}")

#                 process_steps(next_steps)

#     steps = WorkflowExecutionStep.objects.filter(
#         workflow_execution=execution,
#         status=WorkflowExecutionStepStatus.CREATED
#     ).order_by("number").select_related('email_log')

#     if steps.exists():
#         process_steps(steps)

#     execution.status = WorkflowExecutionStepStatus.COMPLETED
#     execution.completed_at = now()
#     execution.save()

#     return f"Workflow {execution.id} completed successfully"


# @shared_task(bind=True)
# def cleanup_old_executions(self):
    """Elimina i WorkflowExecution completati e obsoleti dopo 5 minuti."""
    time.sleep(300)  # ⏳ Attendere 5 minuti per garantire che il workflow sia completato
    deleted_count, _ = WorkflowExecution.objects.filter(
        is_obsolete=True, 
        status=WorkflowExecutionStepStatus.COMPLETED
    ).delete()
    print(f"@DEBUG: ❌ Eliminati {deleted_count} vecchi workflow completati")

# @shared_task(bind=True)
# def execute_workflow_task(self, workflow_execution_id):
#     """Esegue un workflow step-by-step in modo asincrono con Celery"""
#     with transaction.atomic():
#         execution = WorkflowExecution.objects.select_for_update().get(id=workflow_execution_id)
#         if execution.status != WorkflowExecutionStepStatus.PENDING:
#             return f"Workflow {execution.id} is already {execution.status}"

#         execution.status = "RUNNING"
#         execution.started_at = now()
#         execution.save()

#     def execute_step(step):
#         """Esegue un singolo step del workflow"""
#         step.status = WorkflowExecutionStepStatus.RUNNING
#         step.started_at = now()
#         step.save()

#         node_data = json.loads(step.node) if isinstance(step.node, str) else step.node
#         success = False
#         next_condition = None

#         if step.name == "SEND_EMAIL":
#             email_log = EmailLog.objects.create(
#                 lead_id=1,  # TODO: Passare l'ID corretto
#                 subject=node_data.get("data", {}).get("settings", {}).get("subject", "Default Subject"),
#                 body=node_data.get("data", {}).get("settings", {}).get("body", "Default Body"),
#                 status=EmailStatus.SENT
#             )

#             queryset = WorkflowExecutionStep.objects.filter(
#                 workflow_execution=execution,
#                 parent_node_id=node_data.get("id")
#             )

#             print("@DEBUG: Nodi trovati per aggiornamento:", queryset)
#             print("@DEBUG: email_log.id =", email_log.id)

#             if queryset.exists():
#                 with transaction.atomic():  # 🔥 Assicura il commit atomico
#                     for next_step in queryset:
#                         next_step.email_log = email_log  # ✅ Assegna direttamente l'oggetto EmailLog
#                         next_step.save()
#                         print(f"@DEBUG: Dopo save(), email_log_id = {next_step.email_log_id}")

#                 # 🔥 Verifica immediata con SQL per controllare il valore salvato
#                 with connection.cursor() as cursor:
#                     cursor.execute(
#                         "SELECT id, email_log_id FROM workflows_workflowexecutionstep WHERE parent_node_id = %s",
#                         [node_data.get("id")]
#                     )
#                     rows = cursor.fetchall()
#                     print("@DEBUG: Verifica nel DB dopo salvataggio diretto:", rows)

#             time.sleep(2)  # Simula il ritardo di invio dell'email
#             print("@DEBUG: email inviata")
#             success = True

#         elif step.name == "WAIT":
#             print("@DEBUG: attesa")
#             wait_time = node_data.get("data", {}).get("settings", {}).get("delay_hours", 1)
#             execution.status = WorkflowExecutionStepStatus.PENDING
#             execution.save()
#             time.sleep(30)  # Simula il delay
#             execution.status = WorkflowExecutionStepStatus.RUNNING
#             execution.save()
#             success = True

#         elif step.name == "CHECK_EMAIL_OPENED":
#             if step.email_log:
#                 response = check_email_opened(step.email_log.id)
#                 next_condition = "YES" if response else "NO"
#                 success = True

#         elif step.name == "CHECK_LINK_CLICKED":
#             if step.email_log:
#                 response = check_link_clicked(step.email_log.id)
#                 next_condition = "YES" if response else "NO"
#                 print("@DEBUG: CHECK_LINK_CLICKED:", response)
#                 success = True

#         step.status = WorkflowExecutionStepStatus.COMPLETED if success else WorkflowExecutionStepStatus.FAILED
#         step.completed_at = now()
#         step.save()

#         if step.status == WorkflowExecutionStepStatus.FAILED:
#             execution.status = WorkflowExecutionStepStatus.FAILED
#             execution.completed_at = now()
#             execution.save()
#             return None  # Interrompe l'esecuzione in caso di errore

#         return next_condition  # Restituisce la condizione per determinare il nodo successivo

#     def process_steps(current_steps):
#         """Esegue tutti gli step e continua il workflow"""
#         for step in current_steps:
#             next_condition = execute_step(step)

#             if next_condition is not None:
#                 next_steps = WorkflowExecutionStep.objects.filter(
#                     workflow_execution=execution,
#                     parent_node_id=step.id,
#                     condition=next_condition
#                 )

#                 process_steps(next_steps)  # 🔥 **Esegue immediatamente i nodi successivi**

#     with transaction.atomic():
#         steps = WorkflowExecutionStep.objects.select_for_update().filter(
#             workflow_execution=execution,
#             status=WorkflowExecutionStepStatus.CREATED
#         ).order_by("number")

#         if steps.exists():
#             process_steps(steps)  # 🔥 **Avvia il workflow processando tutti gli step**

#     with transaction.atomic():
#         execution.status = WorkflowExecutionStepStatus.COMPLETED
#         execution.completed_at = now()
#         execution.save()

#     return f"Workflow {execution.id} completed successfully"

