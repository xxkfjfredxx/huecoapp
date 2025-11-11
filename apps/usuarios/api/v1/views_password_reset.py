# apps/usuarios/api/v1/views_password_reset.py

from django.contrib.auth.tokens import PasswordResetTokenGenerator
from django.contrib.auth import get_user_model
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.core.mail import send_mail
from django.conf import settings
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions
from django.db import transaction

User = get_user_model()
token_generator = PasswordResetTokenGenerator()


class PasswordForgotView(APIView):
    """
    Envía al correo un deep link con el token para cambiar contraseña.
    """
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        email = request.data.get("email")
        if not email:
            return Response({"detail": "Email requerido"}, status=400)

        user = User.objects.filter(email=email).first()
        if not user:
            # Seguridad: no revelar si existe
            return Response({"detail": "Si el correo existe, se ha enviado un enlace"}, status=200)

        uid = urlsafe_base64_encode(force_bytes(user.pk))
        token = token_generator.make_token(user)
        deep_link = f"huecoapp://reset-password?uid={uid}&token={token}"

        send_mail(
            subject="Recupera tu contraseña - HuecoApp",
            message=f"Hola {user.first_name or 'usuario'},\n\nUsa este enlace para restablecer tu contraseña:\n{deep_link}\n\nSi no solicitaste esto, ignora este correo.",
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            fail_silently=False,
        )

        return Response({"detail": "Correo enviado si el usuario existe"}, status=200)


class PasswordResetConfirmView(APIView):
    """
    Valida token y actualiza contraseña desde el deep link.
    """
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        uidb64 = request.data.get("uid")
        token = request.data.get("token")
        new_password = request.data.get("password")

        if not uidb64 or not token or not new_password:
            return Response({"detail": "Faltan datos"}, status=400)

        try:
            uid = force_str(urlsafe_base64_decode(uidb64))
            user = User.objects.get(pk=uid)
        except Exception:
            return Response({"detail": "Token inválido"}, status=400)

        if not token_generator.check_token(user, token):
            return Response({"detail": "Token inválido o expirado"}, status=400)

        with transaction.atomic():
            user.set_password(new_password)
            if user.auth_provider != "mixed":
                user.auth_provider = "mixed"
            user.save(update_fields=["password", "auth_provider"])

        return Response({"detail": "Contraseña actualizada correctamente"}, status=200)
