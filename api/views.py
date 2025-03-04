import os
import requests
import secrets
import certifi
from django.conf import settings
from django.http import JsonResponse
from django.contrib.auth.tokens import PasswordResetTokenGenerator
from django.contrib.auth.hashers import make_password
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes
from django.core.mail import get_connection, EmailMultiAlternatives, send_mail
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenRefreshView, TokenObtainPairView
from rest_framework import status

from api.serializers import CustomTokenObtainPairSerializer, ForgotPasswordSerializer, ResetPasswordSerializer
from subscriptions.models import StripeStatus, Subscription
from users.models import User

os.environ['SSL_CERT_FILE'] = certifi.where()

def index(request):
    return JsonResponse({
        'version': '1.0.0',
        'name': 'API',
        })

class CustomTokenObtainPairView(TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer

class CustomTokenRefreshView(TokenRefreshView):
    def post(self, request, *args, **kwargs):
        
        # print("Tutti i cookie ricevuti:", request.COOKIES)  # Verifica cosa arriva

        # Ottieni il token di refresh dal cookie
        refresh_token = request.COOKIES.get("auth-refresh-token")
        # print('refresh_token', refresh_token) # è nullo!!!
        
        if not refresh_token:
            return Response({"detail": "Refresh token is missing or invalid."}, status=400)

        try:
            # Decodifica il refresh token e genera un nuovo access token
            token = RefreshToken(refresh_token)
            new_access_token = str(token.access_token)
        except Exception:
            return Response({"detail": "Invalid refresh token."}, status=400)

        # Recupera l'utente associato al refresh token
        user = self.get_user_from_refresh_token(refresh_token)
        if user:
            # Verifica se l'utente ha un abbonamento attivo
            subscription = Subscription.objects.filter(user=user, status=StripeStatus.ACTIVE).first()
            has_active_subscription = subscription is not None

            # Costruisci la risposta finale con i dati extra
            data = {
                "access": new_access_token,
                "has_active_subscription": has_active_subscription,
                "first_name": user.first_name,
                "last_name": user.last_name,
                "email": user.email,
                "credits": user.credits,
            }

            if has_active_subscription:
                data["subscription_plan"] = subscription.plan
                data["subscription_status"] = subscription.status

            return Response(data)

        return Response({"detail": "User not found."}, status=400)

    def get_user_from_refresh_token(self, refresh_token):
        try:
            # Decodifica il token di refresh
            token = RefreshToken(refresh_token)
            user_id = token["user_id"]
            return User.objects.get(id=user_id)
        except Exception:
            return None

# class CustomTokenRefreshView(TokenRefreshView):
#     def post(self, request, *args, **kwargs):
#         response = super().post(request, *args, **kwargs)  # Chiamata al metodo originale
        
#         if response.status_code == 200:
#             # Ottieni l'utente dal token di refresh
#             user = self.get_user_from_refresh_token(request.data.get("refresh"))
#             if user:

#                 # Check if the user has an active subscription
#                 subscription = Subscription.objects.filter(user=user, status=StripeStatus.ACTIVE).first()
#                 has_active_subscription = subscription is not None
#                 data = response.data
                
#                 data['has_active_subscription'] = has_active_subscription
#                 if has_active_subscription:
#                     data['subscription_plan'] = subscription.plan
#                     data['subscription_status'] = subscription.status

#                 # Aggiungi i dati extra alla risposta
#                 data.update({
#                     "first_name": user.first_name,
#                     "last_name": user.last_name,
#                     "email": user.email,
#                     "credits": user.credits,
#                 })

#         return response

#     def get_user_from_refresh_token(self, refresh_token):
#         try:
#             # Decodifica il token di refresh
#             token = RefreshToken(refresh_token)
#             user_id = token["user_id"]
#             return User.objects.get(id=user_id)
#         except Exception:
#             return None

class ForgotPasswordView(APIView):
    def post(self, request):
        serializer = ForgotPasswordSerializer(data=request.data)
        if serializer.is_valid():
            email = serializer.validated_data['email']
            user = User.objects.get(email=email)
            
            # Genera token
            token_generator = PasswordResetTokenGenerator()
            token = token_generator.make_token(user)
            uid = urlsafe_base64_encode(force_bytes(user.pk))

            # Costruisci il link di reset
            # reset_url = f"{request.build_absolute_uri('/reset-password/')}?uid={uid}&token={token}"
            reset_url = f"{settings.FRONTEND_URL}/auth/reset-password?uid={uid}&token={token}"

            try:
                # Configura la connessione SMTP
                connection = get_connection(
                    use_tls=True,
                    host='smtp.office365.com',
                    port=587,
                    username=settings.EMAIL_HOST_USER,
                    password=settings.EMAIL_HOST_PASSWORD,
                    fail_silently=False,
                )

                # Contenuto dell'email (HTML + Plain Text)
                subject = "Reset your password"
                text_content = f"Click the link below to reset your password:\n{reset_url}"
                html_content = """
                    <html>
                        <body>
                            <h1>Reset your password</h1>
                            <p>Click the link below to reset your password: <a href="{reset_url}">{reset_url}</a></p>
                            <br>
                            <p style="color: gray;">Carouselly Team</p>
                        </body>
                    </html>
                """.format(reset_url=reset_url)

                # Configura l'email come multipart
                email = EmailMultiAlternatives(
                    subject=subject,
                    body=text_content,
                    from_email=settings.EMAIL_HOST_USER,
                    to=["venezia.emilio@gmail.com"],
                    connection=connection,
                    headers={"Reply-To": settings.EMAIL_HOST_USER},
                )
                email.attach_alternative(html_content, "text/html")

                # Invia l'email
                email.send()
                
                return Response({"message": "If an account with this email exists, a password reset link has been sent."}, status=200)

            except Exception as e:
                # Log dell'errore
                print(f"Errore durante l'invio dell'email: {e}")
                return Response({"error": "An error occurred. Please try again later."}, status=500)            
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    

class ResetPasswordView(APIView):
    def post(self, request):
        serializer = ResetPasswordSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response({"message": "Password has been reset successfully."}, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    

class GoogleAuthURLView(APIView):
    def get(self, request):
        google_auth_url = (
            "https://accounts.google.com/o/oauth2/v2/auth"
            "?client_id={client_id}"
            "&redirect_uri={redirect_uri}"
            "&response_type=code"
            "&scope=openid email profile"
        ).format(
            client_id=settings.GOOGLE_CLIENT_ID,
            redirect_uri=settings.GOOGLE_REDIRECT_URI,
        )
        return Response({"auth_url": google_auth_url}, status=status.HTTP_200_OK)    
    

class GoogleCallbackView(APIView):
    def post(self, request):
        code = request.data.get("code")

        if not code:
            return Response({"error": "Authorization code is required."}, status=status.HTTP_400_BAD_REQUEST)

        # Scambia il codice con il token
        token_request_url = "https://oauth2.googleapis.com/token"
        token_request_data = {
            "code": code,
            "client_id": settings.GOOGLE_CLIENT_ID,
            "client_secret": settings.GOOGLE_CLIENT_SECRET,
            "redirect_uri": settings.GOOGLE_REDIRECT_URI,
            "grant_type": "authorization_code",
        }

        token_response = requests.post(token_request_url, data=token_request_data)
        if token_response.status_code != 200:
            return Response({"error": "Failed to retrieve token."}, status=status.HTTP_400_BAD_REQUEST)

        token_data = token_response.json()
        id_token = token_data.get("id_token")

        if not id_token:
            return Response({"error": "ID token is missing."}, status=status.HTTP_400_BAD_REQUEST)

        # Verifica l'ID token e ottieni i dati dell'utente
        user_info_url = "https://oauth2.googleapis.com/tokeninfo"
        user_info_response = requests.get(user_info_url, params={"id_token": id_token})

        if user_info_response.status_code != 200:
            return Response({"error": "Failed to retrieve user info."}, status=status.HTTP_400_BAD_REQUEST)

        user_info = user_info_response.json()
        email = user_info.get("email")
        first_name = user_info.get("given_name", "")
        last_name = user_info.get("family_name", "")
        profile_image_url = user_info.get("picture", "")

        # Autentica o registra l'utente
        user, created = User.objects.get_or_create(email=email, defaults={
            "email": email,
            "first_name": first_name,
            "last_name": last_name,
            "password": make_password(secrets.token_urlsafe(16)),  # Genera una password casuale
            "profile_image_url": profile_image_url,
            "is_google_user": True,
        })

        # Genera JWT
        refresh = RefreshToken.for_user(user)
        print('refresh', str(refresh))
        print('access', str(refresh.access_token))

        return Response({
            "refresh": str(refresh),
            "access": str(refresh.access_token),
        }, status=status.HTTP_200_OK)
    

class TestEmailView(APIView):
    def get(self, request):
        try:
            # Configura la connessione SMTP
            connection = get_connection(
                use_tls=True,
                host='smtp.office365.com',
                port=587,
                username=settings.EMAIL_HOST_USER,
                password=settings.EMAIL_HOST_PASSWORD,
                fail_silently=False,
            )

            # Contenuto dell'email (HTML + Plain Text)
            subject = "Test Email da Carouselly"
            text_content = "Questa è una email di test inviata da Carouselly."
            html_content = """
                <html>
                    <body>
                        <h1 style="color: #4CAF50;">Carouselly Test Email</h1>
                        <p>Questa è una <strong>email di test</strong> inviata da Django tramite il server SMTP di Office365.</p>
                        <br>
                        <p style="color: gray;">Grazie, il team Carouselly.</p>
                    </body>
                </html>
            """

            # Configura l'email come multipart
            email = EmailMultiAlternatives(
                subject=subject,
                body=text_content,
                from_email=settings.EMAIL_HOST_USER,
                to=["venezia.emilio@gmail.com"],
                connection=connection,
                headers={"Reply-To": settings.EMAIL_HOST_USER},
            )
            email.attach_alternative(html_content, "text/html")

            # Invia l'email
            email.send()

            return Response({"message": "Test email inviata con successo."}, status=200)

        except Exception as e:
            # Log dell'errore
            print(f"Errore durante l'invio dell'email: {e}")
            return Response({"error": f"Errore nell'invio dell'email: {str(e)}"}, status=500)