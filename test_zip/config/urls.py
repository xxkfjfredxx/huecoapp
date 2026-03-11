# config/urls.py
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from drf_spectacular.views import (
    SpectacularAPIView, SpectacularSwaggerView, SpectacularRedocView
)
from django.shortcuts import redirect
from .urls_v1 import urlpatterns as api_urls
# 👇 importa tus vistas de auth
from apps.usuarios.api.v1.views_password_reset import PasswordResetConfirmView,PasswordForgotView
from apps.usuarios.api.v1.views_auth import LoginView, LogoutView, MeView,GoogleLoginView,RegisterView,RegisterVerifyView
from rest_framework_simplejwt.views import TokenRefreshView


urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/v1/", include(api_urls)),
    path("api/auth/google-login/", GoogleLoginView.as_view(), name="google-login"), 
    
    # Registro + verificación de cuenta
    path("api/auth/register", RegisterView.as_view(), name="auth-register"),
    path("api/auth/register/verify", RegisterVerifyView.as_view(), name="auth-register-verify"),

    # Auth (public)
    path("password/forgot/", PasswordForgotView.as_view(), name="password_forgot"),
    path("password/reset/", PasswordResetConfirmView.as_view(), name="password_reset_confirm"),
    path("api/auth/login", LoginView.as_view(), name="auth-login"),
    path("api/auth/logout", LogoutView.as_view(), name="auth-logout"),
    path("api/auth/me", MeView.as_view(), name="auth-me"),
    path("api/auth/refresh", TokenRefreshView.as_view(), name="auth-refresh"),

    # --- Docs ---
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/schema/swagger-ui/", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui"),
    path("api/schema/redoc/", SpectacularRedocView.as_view(url_name="schema"), name="redoc"),
    path("api-auth/", include("rest_framework.urls")),
    path("jet/dashboard/", include("jet.dashboard.urls", "jet-dashboard")),
    path("jet/", include("jet.urls", namespace="jet")),

    path('', lambda request: redirect('admin:login')),
]

if settings.DEBUG:
    import debug_toolbar
    urlpatterns = [path("__debug__/", include(debug_toolbar.urls))] + urlpatterns

urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)