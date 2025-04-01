import base64
from django.http import Http404, HttpResponse, HttpResponseRedirect
from django.utils.timezone import now
from django.core import signing
from django.shortcuts import get_object_or_404
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
from rest_framework.viewsets import ViewSet
from rest_framework.decorators import action
from rest_framework import viewsets, permissions, generics
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from connected_accounts.models import ConnectedAccount, Provider
from leads.models import Lead
from .models import EmailClickTracking, EmailLog, EmailOpenTracking, EmailReplyTracking, EmailStatus
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

@csrf_exempt
def track_email_click(request, signed_data):
    try:
        data = signing.loads(signed_data)
        lead_id = data["lead_id"]
        email_log_id = data["email_log_id"]
        target_url = data["url"]
    except signing.BadSignature:
        raise Http404("Invalid or tampered tracking link.")

    try:
        lead = Lead.objects.get(id=lead_id)
        email_log = EmailLog.objects.get(id=email_log_id)
    except (Lead.DoesNotExist, EmailLog.DoesNotExist):
        raise Http404("Invalid tracking data")

    # Evita registrazioni duplicate
    tracking, created = EmailClickTracking.objects.get_or_create(
        lead=lead,
        email_log=email_log,
        link=target_url,
        defaults={"clicked": True, "clicked_at": now()}
    )

    if not created and not tracking.clicked:
        tracking.clicked = True
        tracking.clicked_at = now()
        tracking.save()

    return HttpResponseRedirect(target_url)

@csrf_exempt
def track_email_open(request, signed_data):
    try:
        data = signing.loads(signed_data)
        email_log_id = data["email_log_id"]
        lead_id = data["lead_id"]
    except signing.BadSignature:
        raise Http404("Invalid or tampered tracking link.")

    try:
        email_log = EmailLog.objects.get(id=email_log_id)
        lead = Lead.objects.get(id=lead_id)
    except (EmailLog.DoesNotExist, Lead.DoesNotExist):
        raise Http404("Invalid data.")

    tracking, created = EmailOpenTracking.objects.get_or_create(
        email_log=email_log,
        lead=lead,
        defaults={"opened": True, "opened_at": now()}
    )

    if not created and not tracking.opened:
        tracking.opened = True
        tracking.opened_at = now()
        tracking.save()

    # pixel 1x1 GIF trasparente
    pixel_gif = base64.b64decode(
        "R0lGODlhAQABAIAAAAAAAP///ywAAAAAAQABAAACAUwAOw=="
    )
    return HttpResponse(pixel_gif, content_type="image/gif")

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
    
    
