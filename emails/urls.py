from django.urls import path, include
from rest_framework.routers import DefaultRouter
from emails.views import EmailLogViewSet

router = DefaultRouter()
router.register(r'email-logs', EmailLogViewSet, basename="email-logs")

urlpatterns = [
    path('', include(router.urls)),
]
