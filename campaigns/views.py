from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated

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
