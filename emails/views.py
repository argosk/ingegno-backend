from django.http import JsonResponse
from django.utils.timezone import now
from django.shortcuts import get_object_or_404
from rest_framework.viewsets import ViewSet
from rest_framework.decorators import action
from rest_framework import viewsets, permissions, generics
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from connected_accounts.models import ConnectedAccount, Provider
from .models import EmailClickTracking, EmailLog, EmailReplyTracking, EmailStatus
from .serializers import EmailLogSerializer, EmailReplyTrackingSerializer
from .email_sender import send_email_gmail, send_email_outlook, send_email_smtp

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

class UniboxView(ViewSet):
    permission_classes = [IsAuthenticated]
    
    @action(detail=False, methods=['post'], url_path='email-reply')
    def email_reply(self, request):
        """Risponde a un'email ricevuta"""
        email_id= request.data.get('email_id')
        reply_body = request.data.get('body')

        if not email_id or not reply_body:
            return Response({"error": "Missing email_id or body"}, status=400)

        try:
            mail = EmailReplyTracking.objects.get(id=email_id, lead__campaign__user=request.user)
        except EmailReplyTracking.DoesNotExist:
            return Response({"error": "Email not found"}, status=404)        

        sender_email = mail.email_log.sender
        lead_email = mail.lead.email
        original_message = mail.body
        subject = mail.subject

        # Formattazione della risposta includendo il messaggio originale
        full_reply = f"""{reply_body}

---

{original_message}"""

        # Controllo che l'email risulti ancora connessa al sistema
        connected_account = ConnectedAccount.objects.filter(
            email_address=sender_email, is_active=True
        ).first()

        if not connected_account:
            return Response({"error": "Sender email is not connected"}, status=400)
        
        if connected_account.provider == Provider.GMAIL:
            send_email_gmail(connected_account, lead_email, subject, full_reply)
        elif connected_account.provider == Provider.OUTLOOK:
            send_email_outlook(connected_account, lead_email, subject, full_reply)
        else:
            send_email_smtp(connected_account, lead_email, subject, full_reply)   

        return Response({"message": "Email sent successfully"})
    
    @action(detail=False, methods=['delete'], url_path='email-delete')
    def email_delete(self, request):
        """Elimina un'email ricevuta"""
        email_id = request.data.get('email_id')

        if not email_id:
            return Response({"error": "Missing email_id"}, status=400)

        try:
            mail = EmailReplyTracking.objects.get(id=email_id, lead__campaign__user=request.user)
        except EmailReplyTracking.DoesNotExist:
            return Response({"error": "Email not found"}, status=404)

        mail.delete()
        return Response({"message": "Email deleted successfully"})
    
    @action(detail=False, methods=['post'], url_path='email-as-unread')
    def mark_as_unread(self, request):
        """Imposta un'email come non letta"""
        email_id = request.data.get('email_id')

        if not email_id:
            return Response({"error": "Missing email_id"}, status=400)

        try:
            mail = EmailReplyTracking.objects.get(id=email_id, lead__campaign__user=request.user)
        except EmailReplyTracking.DoesNotExist:
            return Response({"error": "Email not found"}, status=404)

        mail.read = False
        mail.save()
        return Response({"message": "Email marked as unread"})
    
    
