from django.contrib import admin
from .models import Workflow, WorkflowExecution, WorkflowExecutionStep

admin.site.register(Workflow)
admin.site.register(WorkflowExecution)
admin.site.register(WorkflowExecutionStep)
