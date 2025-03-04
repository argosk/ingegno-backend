from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import LeadViewSet

router = DefaultRouter()
router.register(r'', LeadViewSet, basename='lead')


"""
Available Endpoints:

GET /leads/: Retrieve all leads related to the authenticated user’s campaigns.
POST /leads/: Create a new lead (only if the user owns the campaign).
GET /leads/{id}/: Retrieve details of a specific lead.
PUT /leads/{id}/: Update an existing lead.
DELETE /leads/{id}/: Delete a lead.
POST /leads/{id}/update_status/: Update the status of a lead.
GET /leads/{id}/emails/: Retrieve email logs associated with a lead.
"""

urlpatterns = [
    path('', include(router.urls)),
]
