from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from .models import EmailTracking
from .serializers import EmailTrackingSerializer

class EmailTrackingViewSet(viewsets.ModelViewSet):
    queryset = EmailTracking.objects.all()
    serializer_class = EmailTrackingSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        # Filtro per visualizzare solo le email tracking legate alle email dell'utente attuale
        return EmailTracking.objects.filter(email__sequence__campaign__user=self.request.user)
