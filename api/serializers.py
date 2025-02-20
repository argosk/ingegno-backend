from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework.exceptions import AuthenticationFailed
from django.core.exceptions import ValidationError
from django.contrib.auth.tokens import PasswordResetTokenGenerator
from django.utils.http import urlsafe_base64_decode
from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from subscriptions.models import StripeStatus, Subscription
from users.models import User


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    def validate(self, attrs):
        # Convertiamo l'email in minuscolo
        attrs['email'] = attrs['email'].lower()

        # Autenticazione dell'utente (se usi l'email come identificativo)
        user = authenticate(
            username=attrs.get('email'),
            password=attrs.get('password')
        )

        if user is None:
            raise AuthenticationFailed({"detail": "Invalid email or password."})  # Output personalizzato

        data = super().validate(attrs)  # Ottiene i token (access e refresh)
        
        # Aggiunge i dati dell'utente
        user = self.user
        # Check if the user has an active subscription
        subscription = Subscription.objects.filter(user=user, status=StripeStatus.ACTIVE).first()
        has_active_subscription = subscription is not None
        
        data['has_active_subscription'] = has_active_subscription
        if has_active_subscription:
            data['subscription_plan'] = subscription.plan
            data['subscription_status'] = subscription.status

        # Aggiungi i dati extra alla risposta
        data.update({
            "first_name": user.first_name,
            "last_name": user.last_name,
            "email": user.email,
            "credits": user.credits,
        })
        
        return data


class ForgotPasswordSerializer(serializers.Serializer):
    email = serializers.EmailField()

    def validate_email(self, value):
        if not User.objects.filter(email=value).exists():
            raise ValidationError("No user is associated with this email.")
        return value


class ResetPasswordSerializer(serializers.Serializer):
    uid = serializers.CharField()
    token = serializers.CharField()
    new_password = serializers.CharField(write_only=True)
    confirm_password = serializers.CharField(write_only=True)

    def validate(self, data):
        # Verifica UID
        try:
            uid = urlsafe_base64_decode(data['uid']).decode()
            self.user = User.objects.get(pk=uid)
        except (User.DoesNotExist, ValueError, TypeError):
            raise ValidationError("Invalid UID or user does not exist.")

        # Verifica Token
        token_generator = PasswordResetTokenGenerator()
        if not token_generator.check_token(self.user, data['token']):
            raise ValidationError("Invalid or expired token.")

        # Verifica corrispondenza password
        if data['new_password'] != data['confirm_password']:
            raise ValidationError("Passwords do not match.")

        # Validazione password con regole di Django
        try:
            validate_password(data['new_password'], self.user)
        except ValidationError as e:
            raise ValidationError({'new_password': e.messages})
        
        return data

    def save(self):
        self.user.set_password(self.validated_data['new_password'])
        self.user.save()
        return self.user        

