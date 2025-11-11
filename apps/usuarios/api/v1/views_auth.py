from django.contrib.auth import authenticate, login
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions
from rest_framework_simplejwt.tokens import RefreshToken

from apps.usuarios.api.v1.serializers import (
    LoginRequestSerializer,
    LogoutResponseSerializer,
    TokenResponseSerializer,
    UserSerializer,
    GoogleLoginRequestSerializer
)
from apps.usuarios.auth import VersionedJWTAuthentication
from drf_spectacular.utils import extend_schema, OpenApiResponse
from django.contrib.auth import logout as dj_logout
from rest_framework_simplejwt.token_blacklist.models import OutstandingToken, BlacklistedToken

from django.conf import settings
from google.oauth2 import id_token as google_id_token
from google.auth.transport import requests as google_requests
from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils.text import slugify

User = get_user_model()

class LoginView(APIView):
    permission_classes = [permissions.AllowAny]
    authentication_classes = []
    serializer_class = TokenResponseSerializer

    @extend_schema(
        request=LoginRequestSerializer,
        responses={
            200: TokenResponseSerializer,
            400: OpenApiResponse(description="Email and password are required"),
            401: OpenApiResponse(description="Invalid credentials"),
        },
        tags=["auth"],
    )
    def post(self, request):
        email = request.data.get("email")
        password = request.data.get("password")
        if not email or not password:
            return Response(
                {"detail": "Email and password are required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # intenta con username=email y con email=email
        user = (
            authenticate(request, username=email, password=password)
            or authenticate(request, email=email, password=password)
        )
        if not user:
            return Response(
                {"detail": "Invalid credentials"},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        # --- Kill-switch de sesiones: sube la versión ---
        user.token_version = (getattr(user, "token_version", 1) or 1) + 1
        user.save(update_fields=["token_version"])

        # --- Inicia sesión de Django (por si usas SessionAuth en admin) ---
        login(request, user)

        # --- JWT firmados con la versión ---
        refresh = RefreshToken.for_user(user)
        refresh["ver"] = user.token_version
        access = refresh.access_token
        access["ver"] = user.token_version

        return Response(
            {
                # 👇 Sin token legacy
                "access": str(access),
                "refresh": str(refresh),
            },
            status=status.HTTP_200_OK,
        )


class LogoutView(APIView):
    # Permitir sin auth para poder cerrar con solo el refresh (aunque el access ya no sirva)
    permission_classes = [permissions.AllowAny]
    authentication_classes = []

    def post(self, request):
        all_sessions = bool(request.data.get("all", False))
        refresh_token = request.data.get("refresh")

        # (A) Cerrar TODAS las sesiones del usuario actual (requiere Authorization válido)
        if all_sessions:
            auth = VersionedJWTAuthentication().authenticate(request)
            if auth:
                user, _ = auth
                # Blacklistea todos los refresh del usuario
                try:
                    for ot in OutstandingToken.objects.filter(user=user):
                        BlacklistedToken.objects.get_or_create(token=ot)
                except Exception:
                    pass
                # Kill-switch: sube la versión para invalidar TODOS los access inmediatamente
                try:
                    user.token_version = (getattr(user, "token_version", 1) or 1) + 1
                    user.save(update_fields=["token_version"])
                except Exception:
                    pass

        # (B) Cerrar UNA sesión por refresh concreto (NO depende de Authorization)
        if refresh_token:
            try:
                rt = RefreshToken(refresh_token)   # valida que sea un refresh válido
                # Nota: usa payload.get(...) para evitar KeyError
                uid = rt.payload.get("user_id")
                # Si tienes blacklist habilitado en settings / app instalada:
                try:
                    rt.blacklist()
                except Exception:
                    # Si la blacklist no estuviera activa, no falles el logout
                    pass
                if uid:
                    # Kill-switch del dueño de ese refresh => mata TODOS los access
                    from apps.usuarios.models import User
                    u = User.objects.filter(pk=uid).first()
                    if u:
                        u.token_version = (getattr(u, "token_version", 1) or 1) + 1
                        u.save(update_fields=["token_version"])
            except Exception:
                # refresh inválido o ya blacklisteado -> idempotente
                pass

        # (C) Cierra sesión de SessionAuth si hubiera
        try:
            dj_logout(request)
        except Exception:
            pass

        # Idempotente: siempre 204 (sin cuerpo)
        return Response(status=status.HTTP_204_NO_CONTENT)


class MeView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = UserSerializer

    @extend_schema(responses=UserSerializer, tags=["auth"])
    def get(self, request):
        return Response(UserSerializer(request.user).data, status=status.HTTP_200_OK)


class GoogleLoginView(APIView):
    """
    POST /api/v1/google-login/
    body: { "id_token": "<ID_TOKEN_DE_GOOGLE>" }
    """
    permission_classes = [permissions.AllowAny]
    authentication_classes = []
    serializer_class = TokenResponseSerializer

    @extend_schema(
        request=GoogleLoginRequestSerializer,
        responses={200: TokenResponseSerializer, 400: OpenApiResponse(description="Invalid id_token")},
        tags=["auth"],
    )
    def post(self, request):
        serializer = GoogleLoginRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        id_token = serializer.validated_data["id_token"]

        google_client_id = getattr(settings, "GOOGLE_CLIENT_ID", None)

        try:
            # ✅ Verificación segura del token con Google
            payload = google_id_token.verify_oauth2_token(
                id_token,
                google_requests.Request(),
                audience=google_client_id if google_client_id else None
            )

            email = payload.get("email")
            email_verified = payload.get("email_verified", False)
            full_name = payload.get("name") or ""
            google_sub = payload.get("sub")  # ID único de Google

            if not email or not email_verified:
                return Response({"detail": "Email no verificado por Google"}, status=status.HTTP_400_BAD_REQUEST)

            with transaction.atomic():
                user, created = User.objects.get_or_create(
                    email=email,
                    defaults={
                        "username": _safe_username_from_email(email),
                        "first_name": full_name.split(" ", 1)[0] if full_name else "",
                        "last_name": (full_name.split(" ", 1)[1] if " " in full_name else ""),
                        "auth_provider": "google",
                    },
                )

                # 🔒 Caso 1: nuevo usuario por Google
                if created:
                    user.set_unusable_password()  # evita login por password
                    user.save()

                # Caso 2: ya existe pero fue creado por otro método
                elif user.auth_provider not in ["google", "mixed"]:
                    return Response(
                        {"detail": "Este correo fue registrado con otro método de autenticación."},
                        status=status.HTTP_400_BAD_REQUEST
                    )

                # Si era Google y luego agregó password → mixed
                if user.auth_provider == "mixed":
                    pass  # ✅ permitimos el login normal con Google también
                # ✅ Subir versión y emitir JWT
                user.token_version = (getattr(user, "token_version", 1) or 1) + 1
                user.save(update_fields=["token_version"])

                refresh = RefreshToken.for_user(user)
                refresh["ver"] = user.token_version
                access = refresh.access_token
                access["ver"] = user.token_version

                return Response(
                    {
                        "access": str(access),
                        "refresh": str(refresh),
                        "user": UserSerializer(user).data,
                    },
                    status=status.HTTP_200_OK,
                )

        except ValueError:
            return Response({"detail": "id_token inválido"}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            print(f"[GoogleLoginError] {e}")
            return Response({"detail": "Error en login con Google"}, status=status.HTTP_400_BAD_REQUEST)


def _safe_username_from_email(email: str) -> str:
    """
    Genera un username único a partir del email (respetando unicidad de User.username)
    """
    base = slugify(email.split("@")[0]) or "user"
    candidate = base
    i = 1
    while User.objects.filter(username=candidate).exists():
        i += 1
        candidate = f"{base}{i}"
    return candidate
