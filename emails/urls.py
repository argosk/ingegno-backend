from django.urls import path, include
from rest_framework.routers import DefaultRouter
from emails.views import (
    EmailLogViewSet,
    UnreadRepliesCountView,
    track_link_click,
    LeadEmailRepliesListView,
    MarkReplyAsReadView,
    UniboxView,
    track_email_open
)

router = DefaultRouter()
router.register(r'', EmailLogViewSet, basename="emails")  # ok: è un ViewSet
router.register(r'unibox', UniboxView, basename="unibox")


urlpatterns = [
    # Le altre view si registrano manualmente:
    path("track-click/<uuid:email_log_id>/", track_link_click, name="track_link_click"),
    path("track-email-open/<str:signed_data>/", track_email_open, name="track_email_open"),
    path("replies/", LeadEmailRepliesListView.as_view(), name="lead-email-replies"),
    path("replies/unread-count/", UnreadRepliesCountView.as_view(), name="unread-replies-count"),
    path("replies/<uuid:pk>/mark-read/", MarkReplyAsReadView.as_view(), name="mark-reply-read"),
    path('', include(router.urls)),  # Include le rotte del ViewSet
]
