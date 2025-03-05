import json
from celery import shared_task
from django.utils.timezone import now
from django.db import transaction
import time
from workflows.models import WorkflowExecution, WorkflowExecutionStep, WorkflowExecutionStepStatus
from emails.models import EmailLog, ClickLog, EmailStatus

def check_link_clicked(email_log_id) -> bool:
    """Verifica se il link di un'email è stato cliccato."""
    return ClickLog.objects.filter(email_log_id=email_log_id).exists()

def check_email_opened(email_log_id) -> bool:
    """Verifica se l'email è stata aperta."""
    return EmailLog.objects.filter(id=email_log_id, status=EmailStatus.OPENED).exists()

@shared_task(bind=True)
def execute_workflow_task(self, workflow_execution_id):
    """Esegue un workflow step-by-step in modo asincrono con Celery"""
    with transaction.atomic():
        execution = WorkflowExecution.objects.select_for_update().get(id=workflow_execution_id)
        if execution.status != WorkflowExecutionStepStatus.PENDING:
            return f"Workflow {execution.id} is already {execution.status}"

        execution.status = "RUNNING"
        execution.started_at = now()
        execution.save()

    def execute_step(step):
        """Esegue un singolo step del workflow"""
        step.status = WorkflowExecutionStepStatus.RUNNING
        step.started_at = now()
        step.save()

        node_data = json.loads(step.node) if isinstance(step.node, str) else step.node
        success = False
        next_condition = None

        if step.name == "SEND_EMAIL":
            email_log = EmailLog.objects.create(
                lead_id=14,  # TODO: Passare l'ID corretto
                subject=node_data.get("data", {}).get("settings", {}).get("subject", "Default Subject"),
                body=node_data.get("data", {}).get("settings", {}).get("body", "Default Body"),
                status=EmailStatus.SENT
            )

            # query =WorkflowExecutionStep.objects.filter(
            #     workflow_execution=execution,
            #     parent_node_id=node_data.get("id")
            #     # parent_node_id=step.id
            # )

            # print("@DEBUG: query:", query)


            # 🔹 Aggiorna i nodi successivi con l'email inviata
            WorkflowExecutionStep.objects.filter(
                workflow_execution=execution,
                parent_node_id=node_data.get("id")
                # parent_node_id=step.id
            ).update(email_log_id=email_log.id)

            time.sleep(2)  # Simula il ritardo di invio dell'email
            print("@DEBUG: email inviata")
            success = True

        elif step.name == "WAIT":
            print("@DEBUG: attesa")
            wait_time = node_data.get("data", {}).get("settings", {}).get("delay_hours", 1)
            execution.status = WorkflowExecutionStepStatus.PENDING
            execution.save()
            # time.sleep(wait_time * 3600)  # Simula il delay
            time.sleep(30)  # Simula il delay
            execution.status = WorkflowExecutionStepStatus.RUNNING
            execution.save()
            success = True

        elif step.name == "CHECK_EMAIL_OPENED":
            if step.email_log:
                response = check_email_opened(step.email_log.id)
                next_condition = "YES" if response else "NO"
                success = True

        elif step.name == "CHECK_LINK_CLICKED":
            if step.email_log:
                response = check_link_clicked(step.email_log.id)
                next_condition = "YES" if response else "NO"
                print("@DEBUG: CHECK_LINK_CLICKED:", response)
                success = True

        step.status = WorkflowExecutionStepStatus.COMPLETED if success else WorkflowExecutionStepStatus.FAILED
        step.completed_at = now()
        step.save()

        if step.status == WorkflowExecutionStepStatus.FAILED:
            execution.status = WorkflowExecutionStepStatus.FAILED
            execution.completed_at = now()
            execution.save()
            return None  # Interrompe l'esecuzione in caso di errore

        return next_condition  # Restituisce la condizione per determinare il nodo successivo

    def process_steps(current_steps):
        """Esegue tutti gli step e continua il workflow"""
        for step in current_steps:
            next_condition = execute_step(step)

            if next_condition is not None:
                next_steps = WorkflowExecutionStep.objects.filter(
                    workflow_execution=execution,
                    parent_node_id=step.id,
                    condition=next_condition
                )

                process_steps(next_steps)  # 🔥 **Esegue immediatamente i nodi successivi**

    with transaction.atomic():
        steps = WorkflowExecutionStep.objects.select_for_update().filter(
            workflow_execution=execution,
            status=WorkflowExecutionStepStatus.CREATED
        ).order_by("number")

        if steps.exists():
            process_steps(steps)  # 🔥 **Avvia il workflow processando tutti gli step**

    with transaction.atomic():
        execution.status = WorkflowExecutionStepStatus.COMPLETED
        execution.completed_at = now()
        execution.save()

    return f"Workflow {execution.id} completed successfully"

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

#     while True:
#         with transaction.atomic():
#             steps = WorkflowExecutionStep.objects.select_for_update().filter(
#                 workflow_execution=execution,
#                 status=WorkflowExecutionStepStatus.CREATED
#             ).order_by("number")

#             if not steps.exists():
#                 break  # Fine del workflow

#             for step in steps:
#                 step.status = WorkflowExecutionStepStatus.RUNNING
#                 step.started_at = now()
#                 step.save()

#                 node_data = json.loads(step.node) if isinstance(step.node, str) else step.node

#                 print('node_data:', node_data)

#                 success = False  # Determina se il nodo ha completato il suo compito con successo
#                 next_condition = None  # Per determinare il prossimo nodo in base alla condizione

#                 if step.type == "SEND_EMAIL":
#                     # Simula l'invio dell'email

#                     email_log = EmailLog.objects.create(
#                         lead_id=14, # TODO: Passare l'ID del lead corretto
#                         subject=node_data.get("data", {}).get("settings", {}).get("subject", "Default Subject"),
#                         body=node_data.get("data", {}).get("settings", {}).get("body", "Default Body"),
#                         status=EmailStatus.SENT
#                     )
#                     # email_log = EmailLog.objects.create(
#                     #     lead_id=node_data["data"].get("lead_id"),
#                     #     subject=node_data["data"].get("subject", "Default Subject"),
#                     #     body=node_data["data"].get("body", "Default Body"),
#                     #     status="sent"
#                     # )

#                     # Aggiorna tutti i nodi successivi (`CHECK_LINK_CLICKED`, `CHECK_EMAIL_OPENED`)
#                     WorkflowExecutionStep.objects.filter(
#                         workflow_execution=execution,
#                         parent_node_id=step.id  # 🔹 Qualunque nodo che dipende da questa email inviata
#                     ).update(email_log=email_log)

#                     print("@DEBUG: email inviata")
#                     time.sleep(2)
#                     success = True

#                 elif step.type == "WAIT":
#                     wait_time = node_data.get("data", {}).get("settings", {}).get("delay_hours", 1)
#                     execution.status = WorkflowExecutionStepStatus.PENDING
#                     execution.save()
#                     # time.sleep(wait_time * 3600)  # Attende il tempo specificato in ore
#                     time.sleep(30)  # DEBUG SOLO 30 SECONDI
#                     execution.status = WorkflowExecutionStepStatus.RUNNING
#                     execution.save()
#                     success = True

#                 elif step.type == "CHECK_EMAIL_OPENED":
#                     if step.email_log:
#                         # success = check_email_opened(step.email_log.id)
#                         response = check_email_opened(step.email_log.id)
#                         next_condition = "YES" if success else "NO"

#                 elif step.type == "CHECK_LINK_CLICKED":
#                     if step.email_log:
#                         # success = check_link_clicked(step.email_log.id)
#                         response = check_link_clicked(step.email_log.id)
#                         next_condition = "YES" if response else "NO"

#                 step.status = "COMPLETED" if success else "FAILED"
#                 step.completed_at = now()
#                 step.save()

#                 if step.status == "FAILED":
#                     execution.status = "FAILED"
#                     execution.completed_at = now()
#                     execution.save()
#                     return f"Workflow {execution.id} failed at step {step.id}"

#         time.sleep(1)  # Piccola pausa per evitare carico eccessivo sul database

#     with transaction.atomic():
#         execution.status = "COMPLETED"
#         execution.completed_at = now()
#         execution.save()

#     return f"Workflow {execution.id} completed successfully"
