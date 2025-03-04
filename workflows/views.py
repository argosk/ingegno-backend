from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from .models import Workflow, WorkflowExecution, WorkflowExecutionStep
from .serializers import WorkflowExecutionWithStepsSerializer, WorkflowExecutionSerializer, WorkflowSerializer, WorkflowExecutionStepSerializer


class WorkflowViewSet(viewsets.ModelViewSet):
    """ API ViewSet per il modello Workflow """
    queryset = Workflow.objects.all()
    serializer_class = WorkflowSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """ Mostra solo i workflow dell'utente autenticato """
        return self.queryset.filter(user=self.request.user)

    def perform_create(self, serializer):
        """ Associa il workflow all'utente autenticato e alla campagna selezionata """
        serializer.save(user=self.request.user)

    # get workflows by campaign id
    @action(detail=False, methods=['get'], url_path='campaign/(?P<campaign_id>[^/.]+)')
    def get_by_campaign_id(self, request, campaign_id):
        """ Restituisce il workflow di una specifica campagna appartenente all'utente autenticato """
        try:
            workflow = self.get_queryset().get(campaign_id=campaign_id)
            serializer = self.get_serializer(workflow)
            return Response(serializer.data)
        except Workflow.DoesNotExist:
            return Response({"error": "Workflow not found"}, status=status.HTTP_404_NOT_FOUND)


class WorkflowExecutionViewSet(viewsets.ModelViewSet):
    queryset = WorkflowExecution.objects.all()
    serializer_class = WorkflowExecutionSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return self.queryset.filter(workflow__user=self.request.user)

    @action(detail=False, methods=['post'], url_path='create-with-steps')
    def create_with_steps(self, request):
        """ Cancella le esecuzioni precedenti e crea una nuova WorkflowExecution con relativi WorkflowExecutionStep """
        serializer = WorkflowExecutionWithStepsSerializer(data=request.data)
        
        if serializer.is_valid():
            workflow_id = request.data.get("workflow")
            
            if not workflow_id:
                return Response({"error": "workflow field is required"}, status=status.HTTP_400_BAD_REQUEST)

            # Recupera il workflow
            try:
                workflow = Workflow.objects.get(id=workflow_id, user=request.user)
            except Workflow.DoesNotExist:
                return Response({"error": "Workflow not found"}, status=status.HTTP_404_NOT_FOUND)

            # Elimina tutte le esecuzioni precedenti collegate al workflow e i relativi step
            WorkflowExecution.objects.filter(workflow=workflow).delete()

            # Ora crea una nuova esecuzione e gli step associati
            workflow_execution = serializer.save()
            return Response(WorkflowExecutionWithStepsSerializer(workflow_execution).data, status=status.HTTP_201_CREATED)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# class WorkflowExecutionViewSet(viewsets.ModelViewSet):
#     """ API ViewSet per le esecuzioni dei workflow """
#     queryset = WorkflowExecution.objects.all()
#     serializer_class = WorkflowExecutionSerializer
#     permission_classes = [IsAuthenticated]

#     def get_queryset(self):
#         """ Mostra solo le esecuzioni di workflow appartenenti all'utente autenticato """
#         return self.queryset.filter(workflow__user=self.request.user)


class WorkflowExecutionStepViewSet(viewsets.ModelViewSet):
    """ API ViewSet per i passi di esecuzione di un workflow """
    queryset = WorkflowExecutionStep.objects.all()
    serializer_class = WorkflowExecutionStepSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """ Mostra solo i passi di esecuzione relativi ai workflow dell'utente """
        return self.queryset.filter(workflow_execution__workflow__user=self.request.user)
