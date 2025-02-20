from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import LeadViewSet

# Crea un router per registrare gli endpoint
router = DefaultRouter()
router.register(r'', LeadViewSet)

urlpatterns = [
    path('', include(router.urls)),
]
