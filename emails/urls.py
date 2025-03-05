from django.urls import path, include
from rest_framework.routers import DefaultRouter
from emails.views import EmailLogViewSet, track_link_click

router = DefaultRouter()
router.register(r'email-logs', EmailLogViewSet, basename="email-logs")

urlpatterns = [
    path('', include(router.urls)),
    path("track-click/<uuid:email_log_id>/", track_link_click, name="track_link_click"),
]
