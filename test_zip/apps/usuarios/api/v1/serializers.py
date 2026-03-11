from rest_framework import serializers
from ...models import User
from typing import Optional
from drf_spectacular.utils import extend_schema_field
from drf_spectacular.types import OpenApiTypes


class UserSerializer(serializers.ModelSerializer):
    employee_id = serializers.SerializerMethodField()
    is_deleted = serializers.BooleanField(read_only=True)

    class Meta:
        model = User
        fields = [
            "id", "username", "first_name", "last_name", "email",
            "is_superuser", "is_staff",
            "auth_provider",
            "employee_id",
            "password",
            "is_deleted",
            "is_active",
        ]
        extra_kwargs = {
            "username": {"validators": []},
            "password": {"write_only": True, "required": False},
        }

    def get_employee_id(self, obj):
        return f"EMP-{obj.id:05d}"


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

class GoogleLoginRequestSerializer(serializers.Serializer):
    id_token = serializers.CharField()

# --- Registro de usuario con verificación por correo ---
class RegisterSerializer(serializers.ModelSerializer):
    """
    Serializer para crear un usuario nuevo con email + password + username + nombres.
    El usuario se crea inactivo, y luego se activa con un código OTP enviado por correo.
    """

    password = serializers.CharField(write_only=True, min_length=6)

    class Meta:
        model = User
        fields = [
            "username",
            "first_name",
            "last_name",
            "email",
            "password",
        ]

    def validate_email(self, value):
        value = value.lower().strip()
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("Ya existe un usuario con este correo.")
        return value

    def validate_username(self, value: Optional[str]):
        # Como tú dijiste, el username es solo “nombre visible”
        # y NO hace falta que sea único, así que solo lo limpiamos un poco.
        if value:
            value = value.strip()
        return value

    def create(self, validated_data):
        # Extraemos y limpiamos email
        email = validated_data.pop("email").lower().strip()

        password = validated_data.pop("password")

        # Crear usuario inactivo
        user = User(
            email=email,
            **validated_data  # username, first_name, last_name
        )
        user.set_password(password)
        user.is_active = False
        user.auth_provider = "email"
        user.save()

        return user