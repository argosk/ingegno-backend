from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import EmailViewSet, WarmUpTaskViewSet

# Crea un router per registrare gli endpoint
router = DefaultRouter()
router.register(r'emails', EmailViewSet)
router.register(r'warmup-tasks', WarmUpTaskViewSet)

urlpatterns = [
    path('', include(router.urls)),
]
