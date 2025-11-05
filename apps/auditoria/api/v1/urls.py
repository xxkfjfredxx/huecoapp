from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    SystemAuditViewSet
)

router = DefaultRouter()
router.register(r"system-audit", SystemAuditViewSet, basename="system-audit")

urlpatterns = [
    path("", include(router.urls)),
]
