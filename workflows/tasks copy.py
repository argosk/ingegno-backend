import json
import time
from celery import shared_task
from django.utils.timezone import now
from workflows.models import WorkflowExecution, WorkflowExecutionStep, WorkflowExecutionStepStatus
from emails.models import EmailLog, EmailStatus, ClickLog


def check_link_clicked(email_log_id) -> bool:
    """Verifica se il link di un'email è stato cliccato."""
    return ClickLog.objects.filter(email_log_id=email_log_id).exists()


@shared_task(bind=True)
def execute_workflow_task(self, workflow_execution_id):
    """Esegue il workflow step-by-step in base all'ordine 'number'."""

    execution = WorkflowExecution.objects.get(id=workflow_execution_id)
    if execution.status != WorkflowExecutionStepStatus.PENDING:
        return f"Workflow {execution.id} is already {execution.status}"

    execution.status = "RUNNING"
    execution.started_at = now()
    execution.save()

    # Estrai tutti i passi in ordine
    steps = WorkflowExecutionStep.objects.filter(
        workflow_execution=execution
    ).order_by("number")

    # Manteniamo una mappa per il tracciamento di email_log_id
    email_log_mapping = {}

    for step in steps:
        step.refresh_from_db()
        node_data = json.loads(step.node) if isinstance(step.node, str) else step.node

        print(f"\n@DEBUG: 🚀 Esecuzione step {step.id} - {step.name} - email_log_id PRIMA: {step.email_log_id}")

        step.status = WorkflowExecutionStepStatus.RUNNING
        step.started_at = now()
        step.save(update_fields=["status", "started_at"])

        success = False
        next_condition = None
        email_log_id = None  # Per aggiornare il mapping se necessario

        if step.name == "SEND_EMAIL":
            email_log = EmailLog.objects.create(
                lead_id=1,
                subject=node_data.get("data", {}).get("settings", {}).get("subject", "Default Subject"),
                body=node_data.get("data", {}).get("settings", {}).get("body", "Default Body"),
                status=EmailStatus.SENT
            )

            email_log_mapping[step.id] = email_log.id
            step.email_log_id = email_log.id
            step.save(update_fields=["email_log_id"])

            print(f"@DEBUG: ✅ Email inviata con email_log_id={email_log.id}")

            time.sleep(2)  # Simula ritardo di invio
            success = True

        elif step.name == "WAIT":
            time.sleep(10)  # Simula attesa
            # Mantiene l'email_log_id del nodo precedente
            step.email_log_id = email_log_mapping.get(step.parent_node_id, None)
            step.save(update_fields=["email_log_id"])
            print(f"@DEBUG: ⏳ Attesa completata. email_log_id ereditato: {step.email_log_id}")
            success = True

        elif step.name == "CHECK_LINK_CLICKED":
            step.refresh_from_db()

            if not step.email_log_id:
                step.email_log_id = email_log_mapping.get(step.parent_node_id, None)
                step.save(update_fields=["email_log_id"])

            if step.email_log_id:
                response = check_link_clicked(step.email_log_id)
                next_condition = "YES" if response else "NO"
                print(f"@DEBUG: ✅ CHECK_LINK_CLICKED - Link cliccato: {response}")
                success = True
            else:
                print(f"@DEBUG: ❌ CHECK_LINK_CLICKED - Nessun email_log_id trovato per step {step.id}")

        step.status = WorkflowExecutionStepStatus.COMPLETED if success else WorkflowExecutionStepStatus.FAILED
        step.completed_at = now()
        step.save(update_fields=["status", "completed_at"])

        # Trova i passi successivi in base alla condizione (solo per CHECK_LINK_CLICKED)
        if next_condition:
            next_steps = WorkflowExecutionStep.objects.filter(
                workflow_execution=execution,
                parent_node_id=step.id,
                condition=next_condition
            )
            for next_step in next_steps:
                next_step.email_log_id = step.email_log_id
                next_step.save(update_fields=["email_log_id"])

    execution.status = WorkflowExecutionStepStatus.COMPLETED
    execution.completed_at = now()
    execution.save()

    return f"Workflow {execution.id} completed successfully"


# import json
# import time
# from django.utils.timezone import now
# from django.db import connection
# from workflows.models import WorkflowExecution, WorkflowExecutionStep, WorkflowExecutionStepStatus
# from emails.models import EmailLog, EmailStatus, ClickLog
# from celery import shared_task


# class WorkflowExecutor:
#     """Sistema per eseguire il workflow nodo per nodo."""

#     def __init__(self, workflow_execution_id):
#         self.execution = WorkflowExecution.objects.get(id=workflow_execution_id)
#         self.steps = self.load_steps()
#         self.current_step = None

#     def load_steps(self):
#         """Carica tutti gli step ordinati."""
#         return {
#             step.id: step
#             for step in WorkflowExecutionStep.objects.filter(
#                 workflow_execution=self.execution
#             ).order_by("number")
#         }

#     def get_next_steps(self, parent_node_id, condition=None):
#         """Trova i passi successivi a partire da un `parent_node_id`, filtrando per `condition` se presente."""
#         return [
#             step
#             for step in self.steps.values()
#             if step.parent_node_id == parent_node_id and (condition is None or step.condition == condition)
#         ]

#     def propagate_email_log_id(self, step_id, email_log_id):
#         """Propaga `email_log_id` a tutti i figli immediati."""
#         with connection.cursor() as cursor:
#             cursor.execute(
#                 """
#                 UPDATE workflows_workflowexecutionstep 
#                 SET email_log_id = %s 
#                 WHERE parent_node_id = %s
#                 """,
#                 [email_log_id, step_id]
#             )
#         print(f"@DEBUG: 🔄 Propagato email_log_id={email_log_id} ai figli di {step_id}")

#     def execute(self):
#         """Esegue il workflow partendo dal nodo di ingresso."""
#         entry_point = next((step for step in self.steps.values() if step.name == "WAIT" and step.parent_node_id is None), None)
#         if not entry_point:
#             print("@ERROR: Nessun nodo di ingresso trovato!")
#             return

#         self.execute_step(entry_point)

#     def execute_step(self, step):
#         """Esegue un singolo step e passa al successivo."""
#         self.current_step = step
#         print(f"\n@DEBUG: 🚀 Esecuzione step {step.id} - {step.name} - email_log_id PRIMA: {step.email_log_id}")

#         step.status = WorkflowExecutionStepStatus.RUNNING
#         step.started_at = now()
#         step.save(update_fields=["status", "started_at"])

#         node_data = json.loads(step.node) if isinstance(step.node, str) else step.node
#         success = False
#         next_condition = None

#         if step.name == "SEND_EMAIL":
#             email_log = EmailLog.objects.create(
#                 lead_id=1,
#                 subject=node_data["data"]["settings"]["subject"],
#                 body=node_data["data"]["settings"]["body"],
#                 status=EmailStatus.SENT
#             )
#             self.propagate_email_log_id(step.id, email_log.id)
#             print(f"@DEBUG: ✅ Email inviata con email_log_id = {email_log.id}")
#             time.sleep(2)
#             success = True

#         elif step.name == "WAIT":
#             print("@DEBUG: ⏳ Attesa...")
#             wait_time = node_data["data"]["settings"]["delay_hours"]
#             time.sleep(10)  # Simulazione, sostituire con `time.sleep(wait_time * 3600)`

#             if step.email_log_id:
#                 self.propagate_email_log_id(step.id, step.email_log_id)
#             else:
#                 print(f"@DEBUG: ❌ WAIT non ha email_log_id, impossibile propagare.")

#             success = True

#         elif step.name == "CHECK_LINK_CLICKED":
#             if step.email_log_id:
#                 response = ClickLog.objects.filter(email_log_id=step.email_log_id).exists()
#                 next_condition = "YES" if response else "NO"
#                 print(f"@DEBUG: ✅ CHECK_LINK_CLICKED - Link cliccato: {response}")
#                 success = True
#             else:
#                 print(f"@DEBUG: ❌ CHECK_LINK_CLICKED - Nessun email_log_id trovato!")
#                 success = False

#         step.status = WorkflowExecutionStepStatus.COMPLETED if success else WorkflowExecutionStepStatus.FAILED
#         step.completed_at = now()
#         step.save(update_fields=["status", "completed_at"])

#         if success:
#             self.process_next_steps(step, next_condition)

#     def process_next_steps(self, current_step, condition=None):
#         """Trova e avvia i prossimi step in base alla condizione."""
#         next_steps = self.get_next_steps(current_step.id, condition)

#         if not next_steps:
#             print(f"@DEBUG: ✅ Nessun altro step successivo per {current_step.id}. Workflow completato!")
#             return

#         for next_step in next_steps:
#             self.execute_step(next_step)


# # ESECUZIONE DEL WORKFLOW
# @shared_task(bind=True)
# def run_workflow(self, workflow_execution_id):
#     executor = WorkflowExecutor(workflow_execution_id)
#     executor.execute()



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

