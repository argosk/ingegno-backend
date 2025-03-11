from django.http import JsonResponse
from django.utils.timezone import now
from django.shortcuts import get_object_or_404
from rest_framework import viewsets, permissions
from .models import EmailClickTracking, EmailLog, EmailStatus
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


def track_link_click(request, email_log_id):
    """Registra il clic su un link da un'email"""
    email_log = get_object_or_404(EmailLog, id=email_log_id)
    link = request.GET.get("link")

    if not link:
        return JsonResponse({"error": "Missing link parameter"}, status=400)

    EmailClickTracking.objects.create(email_log=email_log, link=link, clicked_at=now())

    # Aggiorna lo stato dell'email se non era già "CLICKED"
    if email_log.status != EmailStatus.CLICKED:
        email_log.status = EmailStatus.CLICKED
        email_log.save()

    return JsonResponse({"success": True})


def generate_tracked_link(email_log: EmailLog, original_link: str) -> str:
    """Genera un link tracciato che passa da Django prima di reindirizzare l'utente"""
    base_tracking_url = "http://localhost:8000/api/emails/track-click/"
    return f"{base_tracking_url}{email_log.id}/?link={original_link}"
