from django.core.cache import cache
from django.db.models import Count
from django.utils.timezone import now, timedelta
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str
from django.db.models import Q
from rest_framework import viewsets, permissions, status, serializers
from rest_framework.response import Response
from rest_framework.decorators import action
from django_filters.rest_framework import DjangoFilterBackend
from .models import Lead, LeadStatus
from .serializers import LeadSerializer
from campaigns.models import Campaign
from campaigns.pagination import CustomPageNumberPagination
from rest_framework.filters import SearchFilter, OrderingFilter
from emails.models import EmailLog, EmailReplyTracking, EmailOpenTracking, EmailStatus
from .tasks import process_csv_leads


class LeadViewSet(viewsets.ModelViewSet):
    queryset = Lead.objects.all()
    serializer_class = LeadSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = CustomPageNumberPagination
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['status', 'campaign']
    search_fields = ['name', 'email']
    ordering_fields = ['created_at', 'name']

    def get_queryset(self):
        """
        Return leads related to the provided campaign_id, only if the campaign belongs to the authenticated user.
        """
        user = self.request.user
        campaign_id = self.request.query_params.get('campaign_id')

        if not campaign_id:
            return Lead.objects.none()

        try:
            campaign = Campaign.objects.get(id=campaign_id, user=user)
        except Campaign.DoesNotExist:
            return Lead.objects.none()

        return Lead.objects.filter(campaign=campaign)

    def perform_create(self, serializer):
        """
        Requires 'campaign_id' in the request data to associate the lead with the correct campaign.
        """
        campaign_id = self.request.data.get('campaign')
        if not campaign_id:
            raise serializers.ValidationError({"error": "Missing 'campaign' in request."})

        try:
            campaign = Campaign.objects.get(id=campaign_id, user=self.request.user)
        except Campaign.DoesNotExist:
            raise serializers.ValidationError({"error": "You are not authorized to add leads to this campaign."}, code=status.HTTP_403_FORBIDDEN)

        serializer.save(campaign=campaign)

    @action(detail=False, methods=['get'], url_path='unsubscribe', permission_classes=[permissions.AllowAny])
    def unsubscribe(self, request):
        """
        Public endpoint to unsubscribe a lead using a base64 encoded ID.
        Example: /api/leads/unsubscribe/?uid=Mg==
        """
        uid = request.query_params.get('uid')
        if not uid:
            return Response({'error': 'Missing uid parameter.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            lead_id = force_str(urlsafe_base64_decode(uid))
            lead = Lead.objects.get(id=lead_id)
        except (Lead.DoesNotExist, ValueError, TypeError):
            return Response({'error': 'Invalid or non-existent lead.'}, status=status.HTTP_404_NOT_FOUND)

        lead.unsubscribed = True
        lead.save()

        return Response({'message': 'Successfully unsubscribed.'}, status=status.HTTP_200_OK)

       
    @action(detail=False, methods=['post'], url_path='delete-leads', permission_classes=[permissions.IsAuthenticated])
    def delete_leads(self, request):
        """
        Elimina uno o più Lead in base agli ID forniti.
        """
        lead_ids = request.data.get('lead_ids', [])

        if not isinstance(lead_ids, list) or not lead_ids:
            raise serializers.ValidationError({"error": "Invalid or missing 'lead_ids'. Provide a list of IDs."}, code=status.HTTP_400_BAD_REQUEST)

        user = request.user
        leads_to_delete = Lead.objects.filter(Q(id__in=lead_ids) & Q(campaign__user=user))

        if not leads_to_delete.exists():
            raise serializers.ValidationError({"error": "No valid leads found to delete."}, code=status.HTTP_404_NOT_FOUND)

        deleted_count, _ = leads_to_delete.delete()

        return Response({"message": f"{deleted_count} leads deleted successfully."}, status=status.HTTP_200_OK)
    
    # @action(detail=True, methods=['post'], permission_classes=[permissions.IsAuthenticated])
    # def update_status(self, request, pk=None):
    #     """
    #     Custom endpoint to update the lead's status.
    #     """
    #     lead = self.get_object()
    #     new_status = request.data.get('status')

    #     if new_status not in dict(lead._meta.get_field('status').choices):
    #         # return Response({'error': 'Invalid status.'}, status=status.HTTP_400_BAD_REQUEST)
    #         raise serializers.ValidationError({'error': 'Invalid status.'}, code=status.HTTP_400_BAD_REQUEST)

    #     lead.status = new_status
    #     lead.save()

    #     return Response({'message': 'Status updated successfully', 'new_status': lead.get_status_display()})


    @action(detail=False, methods=['get'], url_path='campaign-stats', permission_classes=[permissions.IsAuthenticated])
    def campaign_stats(self, request):
        """
        Returns stats for a specific campaign, including total leads, contacted, opened emails, and replied.
        """
        campaign_id = request.query_params.get('campaign_id')        
        if not campaign_id:
            # return Response({'error': "Missing 'campaign_id' parameter."}, status=status.HTTP_400_BAD_REQUEST)
            raise serializers.ValidationError({'error': "Missing 'campaign_id' parameter."}, code=status.HTTP_400_BAD_REQUEST)

        user = request.user
        try:
            campaign = Campaign.objects.get(id=campaign_id, user=user)
        except Campaign.DoesNotExist:
            # return Response({'error': "Campaign not found or not authorized."}, status=status.HTTP_403_FORBIDDEN)
            raise serializers.ValidationError({'error': "Campaign not found or not authorized."}, code=status.HTTP_403_FORBIDDEN)

        # Aggregazione dati
        total_leads = Lead.objects.filter(campaign=campaign).count()
        contacted_leads = Lead.objects.filter(campaign=campaign, status=LeadStatus.CONTACTED).count()

        opened_emails = EmailOpenTracking.objects.filter(lead__campaign=campaign, opened=True).count()
        replied_emails = EmailReplyTracking.objects.filter(lead__campaign=campaign).count()

        return Response({
            "leads": total_leads,
            "contacted": contacted_leads,
            "opened": opened_emails,
            "replied": replied_emails
        })

    @action(detail=False, methods=['get'], url_path='campaign-analytics')
    def campaign_analytics(self, request):
        """
        Returns analytics data for a campaign, ensuring all days in the requested period are included.
        """
        campaign_id = request.query_params.get('campaign_id')
        period = request.query_params.get('period', '90')  # Default: Last 3 months

        if not campaign_id:
            raise serializers.ValidationError({'error': "Missing 'campaign_id' parameter."})

        user = request.user
        try:
            campaign = Campaign.objects.get(id=campaign_id, user=user)
        except Campaign.DoesNotExist:
            raise serializers.ValidationError({'error': "Campaign not found or not authorized."})

        # Determina l'intervallo di date
        period_days = int(period)
        start_date = (now() - timedelta(days=period_days)).date()
        end_date = now().date()

        # Generiamo tutte le date del periodo
        date_range = [(start_date + timedelta(days=i)).isoformat() for i in range((end_date - start_date).days + 1)]
        
        # Creiamo un dizionario con tutte le date inizializzate a zero
        analytics_data = {date: {"date": date, "contacted": 0, "opened": 0, "replied": 0} for date in date_range}

        # Aggrega i dati per giorno
        contacted = Lead.objects.filter(campaign=campaign, status=LeadStatus.CONTACTED, created_at__date__gte=start_date) \
            .values('created_at__date') \
            .annotate(count=Count('id'))
        
        opened = EmailOpenTracking.objects.filter(lead__campaign=campaign, opened_at__date__gte=start_date) \
            .values('opened_at__date') \
            .annotate(count=Count('id'))
        
        replied = EmailReplyTracking.objects.filter(lead__campaign=campaign, received_at__date__gte=start_date) \
            .values('received_at__date') \
            .annotate(count=Count('id'))

        # Inseriamo i valori nei dati già inizializzati
        for entry in contacted:
            date_str = entry['created_at__date'].isoformat()
            analytics_data[date_str]['contacted'] = entry['count']
        
        for entry in opened:
            date_str = entry['opened_at__date'].isoformat()
            analytics_data[date_str]['opened'] = entry['count']
        
        for entry in replied:
            date_str = entry['received_at__date'].isoformat()
            analytics_data[date_str]['replied'] = entry['count']

        # Convertiamo il dizionario in lista ordinata
        return Response(list(analytics_data.values()))    

    @action(detail=False, methods=['post'], url_path='upload-csv', permission_classes=[permissions.IsAuthenticated])
    def upload_csv(self, request):
        file = request.FILES.get('file')
        campaign_id = request.data.get('campaign')

        if not file or not campaign_id:
            # return Response({'error': "File or campaign_id missing."}, status=status.HTTP_400_BAD_REQUEST)
            raise serializers.ValidationError({'error': "File or campaign_id missing."}, code=status.HTTP_400_BAD_REQUEST)

        # Leggi il file come stringa
        file_data = file.read().decode('utf-8')

        # Avvia il task Celery
        task = process_csv_leads.delay(file_data, campaign_id, request.user.id)

        return Response({"task_id": task.id, "message": "CSV processing started."}, status=status.HTTP_202_ACCEPTED)

    @action(detail=False, methods=['get'], url_path='upload-progress', permission_classes=[permissions.IsAuthenticated])
    def upload_progress(self, request):
        task_id = request.query_params.get("task_id")
        if not task_id:
            # return Response({'error': "Task ID missing."}, status=status.HTTP_400_BAD_REQUEST)
            raise serializers.ValidationError({'error': "Task ID missing."}, code=status.HTTP_400_BAD_REQUEST)

        progress = cache.get(f"csv_progress_{task_id}", 0)
        return Response({"progress": progress})