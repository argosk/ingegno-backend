from django.http import JsonResponse
from django.utils.timezone import now
from django.shortcuts import get_object_or_404
from rest_framework import viewsets, permissions, generics
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from .models import EmailClickTracking, EmailLog, EmailReplyTracking, EmailStatus
from .serializers import EmailLogSerializer, EmailReplyTrackingSerializer

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

class StandardPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = 'page_size'
    max_page_size = 100

class LeadEmailRepliesListView(generics.ListAPIView):
    serializer_class = EmailReplyTrackingSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = StandardPagination

    def get_queryset(self):
        return EmailReplyTracking.objects.filter(
            lead__campaign__user=self.request.user
        ).order_by('-received_at')
    

class MarkReplyAsReadView(generics.UpdateAPIView):
    serializer_class = EmailReplyTrackingSerializer
    permission_classes = [IsAuthenticated]
    queryset = EmailReplyTracking.objects.all()

    def patch(self, request, *args, **kwargs):
        reply = self.get_object()
        read = request.data.get('read')
        if read is not None:
            reply.read = read
            reply.save()
            return Response({'status': 'updated', 'read': reply.read})
        return Response({'error': 'Missing "read" parameter'}, status=status.HTTP_400_BAD_REQUEST)
    

class UnreadRepliesCountView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        count = EmailReplyTracking.objects.filter(
            lead__campaign__user=request.user,
            read=False
        ).count()
        return Response({"unread_count": count})