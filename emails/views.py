from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from .models import Email, WarmUpTask
from .serializers import EmailSerializer, WarmUpTaskSerializer


class EmailViewSet(viewsets.ModelViewSet):
    queryset = Email.objects.all()
    serializer_class = EmailSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        # Filter emails by the current user if necessary
        return Email.objects.filter(sequence__campaign__user=self.request.user)

    def perform_create(self, serializer):
        # Automatically link the email to the current user through the campaign/sequence
        serializer.save()


class WarmUpTaskViewSet(viewsets.ModelViewSet):
    queryset = WarmUpTask.objects.all()
    serializer_class = WarmUpTaskSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        # Filter warm-up tasks by the current authenticated user
        return WarmUpTask.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        # Automatically associate the task with the logged-in user
        serializer.save(user=self.request.user)