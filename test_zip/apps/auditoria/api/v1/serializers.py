from rest_framework import serializers
from ...models import (
    SystemAudit
)


class SystemAuditSerializer(serializers.ModelSerializer):
    class Meta:
        model = SystemAudit
        fields = "__all__"
        read_only_fields = ("id", "created_at")