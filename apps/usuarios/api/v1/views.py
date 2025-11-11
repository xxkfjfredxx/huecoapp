from rest_framework import viewsets, filters, status
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.exceptions import PermissionDenied, ValidationError, NotFound

from ...models import User
from .serializers import UserSerializer
from ...permissions import EsRolPermitido  # keep your existing permission name
from apps.utils.auditlogmimix import AuditLogMixin

class UserViewSet(AuditLogMixin, viewsets.ModelViewSet):
    queryset = User.objects.filter(is_deleted=False)
    serializer_class = UserSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ["auth_provider", "is_active"]
    search_fields = ["username", "first_name", "last_name", "email"]
    permission_classes = [EsRolPermitido]
    roles_permitidos = ["Admin", "RRHH"]
