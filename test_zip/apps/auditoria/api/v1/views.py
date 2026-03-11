from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from django.utils.dateparse import parse_date
from apps.utils.auditlogmimix import AuditLogMixin
from django_ratelimit.decorators import ratelimit


from ...models import (
    SystemAudit
)
from .serializers import (
    SystemAuditSerializer
)


# --------- READ-ONLY LOGS ------------------------------------------------
class SystemAuditViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = SystemAudit.objects.all()
    serializer_class = SystemAuditSerializer
    permission_classes = [AllowAny]  # cambia a IsAdminUser cuando termines de depurar

    # APLICA EL DECORADOR AL METODO `list`
    @ratelimit(key='ip', rate='15/m', method='GET', block=True)
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    # Si quieres, también puedes aplicarlo al método `retrieve`
    @ratelimit(key='ip', rate='15/m', method='GET', block=True)
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)