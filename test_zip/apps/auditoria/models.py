from django.db import models
from apps.usuarios.models import User
from apps.utils.mixins import AuditMixin

class SystemAudit(models.Model):
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    action = models.CharField(max_length=100)
    affected_table = models.CharField(max_length=100)
    record_id = models.IntegerField()
    previous_data = models.JSONField(null=True, blank=True)
    new_data = models.JSONField(null=True, blank=True)
    ip_address = models.CharField(max_length=50, blank=True, null=True)
    user_agent = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "system_audit"
        ordering = ["-created_at"]

    def __str__(self):
        base = f"{self.action} on {self.affected_table}"
        return f"{base} by {self.user}" if self.user else base