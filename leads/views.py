from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from .models import Lead
from .serializers import LeadSerializer


class LeadViewSet(viewsets.ModelViewSet):
    queryset = Lead.objects.all()
    serializer_class = LeadSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        # Filter leads by the logged-in user
        return Lead.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        # Associate the lead with the logged-in user
        serializer.save(user=self.request.user)
