from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import WorkflowViewSet, WorkflowExecutionViewSet, WorkflowExecutionStepViewSet

# Creiamo un router DRF per gestire le API in modo automatico
router = DefaultRouter()
router.register(r'', WorkflowViewSet, basename='workflow')
router.register(r'executions', WorkflowExecutionViewSet, basename='execution')
router.register(r'steps', WorkflowExecutionStepViewSet, basename='executionstep')

urlpatterns = [
    path('', include(router.urls)),  # Include automaticamente tutte le route del router
]
