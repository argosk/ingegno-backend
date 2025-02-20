from rest_framework import serializers

from connected_accounts.utils import encrypt_password
from .models import ConnectedAccount

class ConnectedAccountSerializer(serializers.ModelSerializer):
    class Meta:
        model = ConnectedAccount
        fields = [
            'id', 'user', 'provider', 'email_address', 'username', 'password', 'access_token', 'refresh_token',
            'token_expires_at', 'imap_host', 'imap_port', 'smtp_host', 'smtp_port', 'is_active'
        ]
        read_only_fields = ['user', 'access_token', 'refresh_token']
        
    def create(self, validated_data):
        # Crittografa la password prima di salvarla
        if 'password' in validated_data:
            validated_data['password'] = encrypt_password(validated_data['password'])
        return super().create(validated_data)
    
    # def create(self, validated_data):
    #     # Custom logic for OAuth token management (if needed)
    #     return ConnectedAccount.objects.create(**validated_data)
