# apps/huecos/views_fcm.py
from rest_framework import generics, permissions
from .models import DispositivoUsuario
from rest_framework.response import Response

class RegistrarTokenView(generics.CreateAPIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, *args, **kwargs):
        token = request.data.get("token_fcm")
        plataforma = request.data.get("plataforma", "android")
        if not token:
            return Response({"detail": "token_fcm requerido"}, status=400)
        dispositivo, creado = DispositivoUsuario.objects.update_or_create(
            usuario=request.user,
            plataforma=plataforma,
            defaults={"token_fcm": token}
        )
        return Response({"registrado": True, "nuevo": creado})
