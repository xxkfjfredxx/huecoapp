# apps/utils/permissions.py
from rest_framework.permissions import BasePermission, SAFE_METHODS

class CSRFDobleSubmitMutations(BasePermission):
    """
    Exige X-CSRF-Token que coincida con cookie 'csrf_token' SOLO en métodos no seguros
    y SOLO cuando la petición viene de un navegador (tiene cabecera Origin).
    No rompe server-to-server (BFF) porque ahí no hay Origin.
    """
    def has_permission(self, request, view):
        if request.method in SAFE_METHODS:
            return True

        origin = request.META.get("HTTP_ORIGIN")
        if not origin:
            # Llamadas servidor-servidor (BFF) u otras: no aplicamos CSRF aquí
            return True

        cookie_token = request.COOKIES.get("csrf_token")
        header_token = request.headers.get("X-CSRF-Token") or request.headers.get("X-CSRFToken")
        if not cookie_token or not header_token:
            return False
        return cookie_token == header_token
