from django.contrib import admin
from .models import Workflow, WorkflowExecution, WorkflowExecutionStep

@admin.register(WorkflowExecutionStep)
class WorkflowExecutionStepAdmin(admin.ModelAdmin):
    list_display = (
        "id", "workflow_execution", "number", "name", "status", 
        "condition", "parent_node_id", "started_at", "completed_at", "credits_consumed"
    )
    list_filter = ("status", "condition", "workflow_execution")
    search_fields = ("id", "name", "workflow_execution__workflow__name")
    ordering = ("workflow_execution", "number")

@admin.register(WorkflowExecution)
class WorkflowExecutionAdmin(admin.ModelAdmin):
    list_display = ("id", "workflow", "trigger", "status", "created_at", "started_at", "completed_at")
    list_filter = ("status", "trigger")
    search_fields = ("id", "workflow__name")
    ordering = ("created_at",)

@admin.register(Workflow)
class WorkflowAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "user", "status", "created_at", "updated_at")
    list_filter = ("status", "user")
    search_fields = ("id", "name", "user__username")
    ordering = ("created_at",)
