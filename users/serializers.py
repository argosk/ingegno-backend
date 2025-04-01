from rest_framework import serializers
from django.core.exceptions import ValidationError
from django.contrib.auth.password_validation import validate_password
from .models import User


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('first_name', 'last_name', 'email', 'profile_image_url', 'is_google_user', 'credits')      


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ('first_name', 'last_name', 'email', 'password')

    def create(self, validated_data):
        user = User.objects.create_user(
            first_name=validated_data['first_name'],
            last_name=validated_data['last_name'],
            email=validated_data['email'],
            password=validated_data['password']
        )
        return user


class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField(write_only=True)
    new_password = serializers.CharField(write_only=True)
    confirm_password = serializers.CharField(write_only=True)

    def validate_old_password(self, value):
        if not self.context['request'].user.check_password(value):
            raise ValidationError("The old password is incorrect.")
        return value

    def validate(self, data):
        # Verifica corrispondenza password
        if data['new_password'] != data['confirm_password']:
            raise ValidationError("Passwords do not match.")

        # Validazione password con regole di Django
        try:
            validate_password(data['new_password'], self.context['request'].user)
        except ValidationError as e:
            raise ValidationError({'new_password': e.messages})
        
        return data

    def save(self):
        self.context['request'].user.set_password(self.validated_data['new_password'])
        self.context['request'].user.save()
        return self.context['request'].user
    
class ChangeEmailSerializer(serializers.Serializer):
    email = serializers.EmailField()

    def validate_email(self, value):
        user = self.context['request'].user
        if User.objects.filter(email=value).exclude(pk=user.pk).exists():
            raise ValidationError("This email is already used by another user.")
        return value

    def save(self):
        user = self.context['request'].user
        user.email = self.validated_data['email']
        user.save()
        return user
    
class UpdateUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['first_name', 'last_name']
        # fields = ['first_name', 'last_name', 'email']

    # def validate_email(self, value):
    #     user = self.context['request'].user
    #     if User.objects.filter(email=value).exclude(pk=user.pk).exists():
    #         raise ValidationError("This email is already used by another user.")
    #     return value

    def update(self, instance, validated_data):
        instance.first_name = validated_data.get('first_name', instance.first_name)
        instance.last_name = validated_data.get('last_name', instance.last_name)
        # instance.email = validated_data.get('email', instance.email)
        instance.save()
        return instance