from rest_framework import serializers
from ...models import User
from typing import Optional
from drf_spectacular.utils import extend_schema_field
from drf_spectacular.types import OpenApiTypes


class UserSerializer(serializers.ModelSerializer):
    employee_id = serializers.SerializerMethodField()
    is_deleted = serializers.BooleanField(read_only=True)

    class Meta:
        model  = User
        fields = [
            "id", "username", "first_name", "last_name", "email",
            "is_superuser", "is_staff",
            "role", "role_id",
            "employee_id",
            "password",
            "is_deleted",
            "is_active",
        ]
        extra_kwargs = {
            "username": {"validators": []},
            "password": {"write_only": True, "required": True},
        }


# Serializador para la autenticación de login (Request)
class LoginRequestSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField()


# Respuesta del login (con token y datos del usuario)
class TokenResponseSerializer(serializers.Serializer):
    access = serializers.CharField(required=False, allow_blank=True)
    refresh = serializers.CharField(required=False, allow_blank=True)
    user = UserSerializer()  # Usuario detallado usando su serializer


# Serializador para solicitud OTP (email)
class OTPRequestSerializer(serializers.Serializer):
    email = serializers.EmailField()


# Respuesta de la solicitud OTP
class OTPRequestResponseSerializer(serializers.Serializer):
    status = serializers.CharField()
    dev_code = serializers.CharField(required=False)  # Solo en Debug


# Serializador para verificar el OTP (con código)
class OTPVerifySerializer(serializers.Serializer):
    email = serializers.EmailField()
    code = serializers.CharField()

class LogoutResponseSerializer(serializers.Serializer):
    message = serializers.CharField(default="Logged out successfully")