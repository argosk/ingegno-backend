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
    permission_classes = [IsAuthenticated]  # Solo utenti autenticati possono accedere

    def get_queryset(self):
        """ Mostra solo i workflow dell'utente autenticato """
        return self.queryset.filter(user=self.request.user)

    def perform_create(self, serializer):
        """ Associa il workflow all'utente autenticato durante la creazione """
        serializer.save(user=self.request.user)


class WorkflowExecutionViewSet(viewsets.ModelViewSet):
    queryset = WorkflowExecution.objects.all()
    serializer_class = WorkflowExecutionSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return self.queryset.filter(workflow__user=self.request.user)

    @action(detail=False, methods=['post'], url_path='create-with-steps')
    def create_with_steps(self, request):
        """ Crea un WorkflowExecution e i relativi WorkflowExecutionStep in un'unica chiamata """
        serializer = WorkflowExecutionWithStepsSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
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
