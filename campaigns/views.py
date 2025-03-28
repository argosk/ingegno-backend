from django.utils.timesince import timesince
from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework import status

from emails.models import EmailLog, EmailReplyTracking
from leads.models import Lead

from .models import Campaign
from .serializers import CampaignSerializer
from .pagination import CustomPageNumberPagination


class CampaignViewSet(viewsets.ModelViewSet):
    queryset = Campaign.objects.all()
    serializer_class = CampaignSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = CustomPageNumberPagination

    def get_queryset(self):
        # Mostra solo le campagne dell’utente autenticato
        return Campaign.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    # TOP PERFORMING CAMPAIGNS
    @action(detail=False, methods=["get"], url_path="top-campaigns")
    def top_campaigns(self, request):
        user = request.user

        # Trova le campagne dell'utente
        campaigns = Campaign.objects.filter(user=user)

        results = []

        for campaign in campaigns:
            sent = EmailLog.objects.filter(lead__campaign=campaign).count()
            replies = EmailReplyTracking.objects.filter(lead__campaign=campaign).count()

            if sent > 0:
                reply_rate = round((replies / sent) * 100, 2) if sent > 0 else 0.0
                results.append({
                    "id": str(campaign.id),
                    "name": campaign.name,
                    "sent": sent,
                    "replies": replies,
                    "reply_rate": reply_rate,
                })

        # Ordina per reply rate decrescente
        results.sort(key=lambda x: x["reply_rate"], reverse=True)

        return Response(results[:3], status=status.HTTP_200_OK)
    
    @action(detail=False, methods=["get"], url_path="recent-campaigns")
    def recent_campaigns(self, request):
        user = request.user

        campaigns = (
            Campaign.objects.filter(user=user)
            .order_by("-created_at")[:3]
        )

        results = []

        for campaign in campaigns:
            leads_count = Lead.objects.filter(campaign=campaign).count()
            sent_emails = EmailLog.objects.filter(lead__campaign=campaign).count()
            replies = EmailReplyTracking.objects.filter(lead__campaign=campaign).count()

            results.append({
                "id": str(campaign.id),
                "name": campaign.name,
                "created_ago": timesince(campaign.created_at) + " ago",
                "leads_count": leads_count,
                "sent_emails": sent_emails,
                "replies": replies,
            })

        return Response(results, status=status.HTTP_200_OK)    