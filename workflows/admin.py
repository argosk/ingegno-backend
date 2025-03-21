from django.contrib import admin
from .models import Workflow, WorkflowExecution, WorkflowExecutionStep, WorkflowSettings

@admin.register(WorkflowExecutionStep)
class WorkflowExecutionStepAdmin(admin.ModelAdmin):
    list_display = (
        "id", "workflow_execution", "number", "name", 
        "condition", "parent_node_id", "started_at", "completed_at", "credits_consumed"
    )
    list_filter = ("condition", "workflow_execution")
    search_fields = ("id", "name", "workflow_execution__workflow__name")
    ordering = ("workflow_execution", "number")

@admin.register(WorkflowExecution)
class WorkflowExecutionAdmin(admin.ModelAdmin):
    list_display = ("id", "workflow", "trigger", "created_at", "started_at", "completed_at")
    list_filter = ("trigger",)
    search_fields = ("id", "workflow__name")
    ordering = ("created_at",)

@admin.register(Workflow)
class WorkflowAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "user", "created_at", "updated_at")
    list_filter = ("user",)
    search_fields = ("id", "name", "user__username")
    ordering = ("created_at",)

@admin.register(WorkflowSettings)
class WorkflowSettingsAdmin(admin.ModelAdmin):
    list_display = (
        "workflow", "start", "max_emails_per_day", "pause_between_emails",
        "reply_action", "sending_time_start", "sending_time_end",
        "unsubscribe_handling", "bounce_handling"
    )
    list_filter = ("start", "reply_action", "unsubscribe_handling", "bounce_handling")
    search_fields = ("workflow__name", "workflow__user__username")
    ordering = ("workflow",)