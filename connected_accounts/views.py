import requests
import imaplib
import smtplib
from datetime import datetime, timedelta
from django.conf import settings
from rest_framework import viewsets, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from rest_framework.response import Response
from google_auth_oauthlib.flow import Flow
from .utils import discover_email_servers, encrypt_password, decrypt_password
from .models import ConnectedAccount
from .serializers import ConnectedAccountSerializer


class ConnectedAccountViewSet(viewsets.ModelViewSet):
    queryset = ConnectedAccount.objects.all()
    serializer_class = ConnectedAccountSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        # Visualizza solo gli account associati all'utente corrente
        return ConnectedAccount.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        # Salva l'account con l'utente autenticato
        serializer.save(user=self.request.user)


class OAuth2InitView(APIView):
    def get(self, request):
        oauth_provider = settings.OAUTH2_PROVIDERS['gmail']
        flow = Flow.from_client_config(
            {
                "web": {
                    "client_id": oauth_provider['client_id'],
                    "client_secret": oauth_provider['client_secret'],
                    "redirect_uris": [oauth_provider['redirect_uri']],
                    "auth_uri": oauth_provider['auth_uri'],
                    "token_uri": oauth_provider['token_uri'],
                }
            },
            scopes=[
                'https://www.googleapis.com/auth/gmail.send',
                'https://www.googleapis.com/auth/gmail.readonly',
                'https://www.googleapis.com/auth/userinfo.email',
                'https://www.googleapis.com/auth/userinfo.profile',
                'openid']
        )

        # Imposta esplicitamente la redirect URI
        flow.redirect_uri = oauth_provider['redirect_uri']

        # Genera l'URL di autorizzazione con il redirect URI manualmente
        auth_url, _ = flow.authorization_url(
            access_type='offline',
            include_granted_scopes='true',
            prompt='consent',
        )
        return Response({'auth_url': auth_url})
    

class OAuth2CallbackView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        code = request.GET.get('code')
        if not code:
            return Response({"error": "Authorization code is missing"}, status=status.HTTP_400_BAD_REQUEST)

        oauth_provider = settings.OAUTH2_PROVIDERS['gmail']
        flow = Flow.from_client_config(
            {
                "web": {
                    "client_id": oauth_provider['client_id'],
                    "client_secret": oauth_provider['client_secret'],
                    "redirect_uris": [oauth_provider['redirect_uri']],
                    "auth_uri": oauth_provider['auth_uri'],
                    "token_uri": oauth_provider['token_uri'],
                }
            },
            scopes=[
                'https://www.googleapis.com/auth/gmail.send',
                'https://www.googleapis.com/auth/gmail.readonly',
                'https://www.googleapis.com/auth/userinfo.email',
                'https://www.googleapis.com/auth/userinfo.profile',
                'openid']            
        )

        # Imposta esplicitamente la redirect URI
        flow.redirect_uri = oauth_provider['redirect_uri']

        # Scambia il codice con i token
        flow.fetch_token(code=code)

        # Ottieni le credenziali
        credentials = flow.credentials

        # Ottieni l'indirizzo email dell'utente dal token
        email_address = self.get_user_email(credentials)

        # Salva i token e l'account connesso
        ConnectedAccount.objects.create(
            user=request.user,
            provider='gmail',
            email_address=email_address,
            access_token=credentials.token,
            refresh_token=credentials.refresh_token,
            token_expires_at=credentials.expiry
        )

        return Response({"message": "Gmail account connected successfully"})

    def get_user_email(self, credentials):
        response = requests.get(
            'https://www.googleapis.com/oauth2/v1/userinfo',
            headers={'Authorization': f'Bearer {credentials.token}'}
        )
        return response.json().get('email')
    

class OutlookOAuth2InitView(APIView):
    def get(self, request):
        oauth_provider = settings.OAUTH2_PROVIDERS['outlook']

        # Costruzione dell'URL di autorizzazione
        auth_url = (
            f"{oauth_provider['auth_uri']}?"
            f"client_id={oauth_provider['client_id']}&"
            f"response_type=code&"
            f"redirect_uri={oauth_provider['redirect_uri']}&"
            f"scope={' '.join(oauth_provider['scopes'])}&"
            f"response_mode=query&"
            f"prompt=consent"
        )

        return Response({'auth_url': auth_url})


class OutlookOAuth2CallbackView(APIView):
    def get(self, request):
        code = request.GET.get('code')
        if not code:
            return Response({"error": "Authorization code is missing"}, status=status.HTTP_400_BAD_REQUEST)

        oauth_provider = settings.OAUTH2_PROVIDERS['outlook']
        token_url = oauth_provider['token_uri']
        redirect_uri = oauth_provider['redirect_uri']

        data = {
            'client_id': oauth_provider['client_id'],
            'client_secret': oauth_provider['client_secret'],
            'code': code,
            'redirect_uri': redirect_uri,
            'grant_type': 'authorization_code',
        }

        token_response = requests.post(token_url, data=data).json()

        access_token = token_response.get('access_token')
        refresh_token = token_response.get('refresh_token')  # Salviamo anche questo

        expires_in = token_response.get('expires_in')
        user_info = self.get_user_email(access_token)

        ConnectedAccount.objects.create(
            user=request.user,
            provider='outlook',
            email_address=user_info['userPrincipalName'],
            access_token=access_token,
            refresh_token=refresh_token,
            token_expires_at=datetime.now() + timedelta(seconds=expires_in)
        )

        return Response({"message": "Outlook account connected successfully"})

    def get_user_email(self, access_token):
        response = requests.get(
            'https://graph.microsoft.com/v1.0/me',
            headers={'Authorization': f'Bearer {access_token}'}
        )
        return response.json()


class IMAPSMTPAccountView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        data = request.data
        user = request.user

        email_address = data.get('email_address')
        username = data.get('username', email_address)  # Default: email come username
        password = data.get('password')

        # Scopriamo i server IMAP/SMTP automaticamente se non forniti
        server_info = discover_email_servers(email_address)
        imap_host = server_info['imap_host']
        imap_port = server_info['imap_port']
        smtp_host = server_info['smtp_host']
        smtp_port = server_info['smtp_port']

        # Test della connessione IMAP
        if not self.test_imap_connection(imap_host, imap_port, username, password):
            return Response({"error": "IMAP connection failed"}, status=status.HTTP_400_BAD_REQUEST)

        # Test della connessione SMTP
        if not self.test_smtp_connection(smtp_host, smtp_port, username, password):
            return Response({"error": "SMTP connection failed"}, status=status.HTTP_400_BAD_REQUEST)

        # Salviamo l'account con la password crittografata
        encrypted_password = encrypt_password(password)
        ConnectedAccount.objects.create(
            user=user,
            provider='imap_smtp',
            email_address=email_address,
            username=username,
            password=encrypted_password,
            imap_host=imap_host,
            imap_port=imap_port,
            smtp_host=smtp_host,
            smtp_port=smtp_port,
            is_active=True
        )

        return Response({"message": "IMAP/SMTP account connected successfully"})

    def test_imap_connection(self, imap_host, imap_port, username, password):
        try:
            connection = imaplib.IMAP4_SSL(imap_host, imap_port)
            connection.login(username, password)
            connection.logout()
            return True
        except Exception as e:
            print(f"IMAP Connection Error: {e}")
            return False

    def test_smtp_connection(self, smtp_host, smtp_port, username, password):
        try:
            server = smtplib.SMTP(smtp_host, smtp_port)
            server.starttls()
            server.login(username, password)
            server.quit()
            return True
        except Exception as e:
            print(f"SMTP Connection Error: {e}")
            return False