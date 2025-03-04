from rest_framework import viewsets, permissions
from .models import EmailLog
from .serializers import EmailLogSerializer

class EmailLogViewSet(viewsets.ModelViewSet):
    queryset = EmailLog.objects.all()
    serializer_class = EmailLogSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        """
        Restituisce solo le email relative ai lead dell'utente autenticato.
        """
        user = self.request.user
        return EmailLog.objects.filter(lead__campaign__user=user)
