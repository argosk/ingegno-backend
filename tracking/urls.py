from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import EmailTrackingViewSet

router = DefaultRouter()
router.register(r'email', EmailTrackingViewSet)

urlpatterns = [
    path('', include(router.urls)),
]
