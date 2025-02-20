from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from subscriptions.models import Subscription, StripeStatus
from .serializers import RegisterSerializer, UserSerializer, ChangePasswordSerializer, UpdateUserSerializer


class MeView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        # Get the currently authenticated user
        user = request.user
        
        # Serialize the user data
        serializer = UserSerializer(user)

        # Check if the user has an active subscription
        subscription = Subscription.objects.filter(user=user, status=StripeStatus.ACTIVE).first()
        has_active_subscription = subscription is not None

        # Add subscription data to the response
        data = serializer.data
        data['has_active_subscription'] = has_active_subscription
        if has_active_subscription:
            data['subscription_plan'] = subscription.plan
            data['subscription_status'] = subscription.status

        # Return the user data with subscription information
        return Response(data)
    

class RegisterView(APIView):
    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response({"message": "User registered successfully"}, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ChangePasswordView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = ChangePasswordSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            serializer.save()
            return Response({"message": "Password changed successfully"}, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    

class UpdateUserView(APIView):
    permission_classes = [IsAuthenticated]

    def put(self, request):
        serializer = UpdateUserSerializer(instance=request.user, data=request.data, context={'request': request})
        if serializer.is_valid():
            user = serializer.save()
            return Response({
                "message": "User updated successfully",
                "first_name": user.first_name,
                "last_name": user.last_name,
                "email": user.email
            }, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    # def put(self, request):
    #     serializer = UpdateUserSerializer(instance=request.user, data=request.data, context={'request': request})
    #     if serializer.is_valid():
    #         serializer.save()
    #         return Response({"message": "User updated successfully"}, status=status.HTTP_200_OK)
    #     return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)