from django.core.cache import cache
from rest_framework import viewsets, permissions, status, serializers
from rest_framework.response import Response
from rest_framework.decorators import action
from .models import Lead, LeadStatus
from .serializers import LeadSerializer
from campaigns.models import Campaign
from campaigns.pagination import CustomPageNumberPagination
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter
from django.db.models import Q
from emails.models import EmailLog, EmailReplyTracking, EmailStatus
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

        opened_emails = EmailLog.objects.filter(lead__campaign=campaign, status=EmailStatus.OPENED).count()
        # replied_emails = EmailLog.objects.filter(lead__campaign=campaign, response_received=True).count()
        replied_emails = EmailReplyTracking.objects.filter(lead__campaign=campaign).count()

        return Response({
            "leads": total_leads,
            "contacted": contacted_leads,
            "opened": opened_emails,
            "replied": replied_emails
        })


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