# apps/utils/auditlogmimix.py
from django.utils import timezone
from django.db     import transaction


class AuditLogMixin:
    """
    Mixin para ViewSets que registra CREATE / UPDATE / DELETE
    en SystemAudit sin provocar importaciones circulares.
    """

    # ──────────────────────────────────────────────────────────────
    # CREATE
    # ──────────────────────────────────────────────────────────────
    def perform_create(self, serializer):
        extra = {}
        model_cls = getattr(getattr(serializer, "Meta", None), "model", None)
        if model_cls and hasattr(model_cls, "created_by") and self.request.user.is_authenticated:
            extra["created_by"] = self.request.user

        instance = serializer.save(**extra)
        self.log_audit("CREATED", instance)
        return instance

    # ──────────────────────────────────────────────────────────────
    # UPDATE
    # ──────────────────────────────────────────────────────────────
    def perform_update(self, serializer):
        old_instance = self.get_object()
        old_data     = self.serializer_class(old_instance).data
        instance     = serializer.save()
        self.log_audit("UPDATED", instance, previous_data=old_data)
        return instance

    # ──────────────────────────────────────────────────────────────
    # DELETE  (soft o hard)
    # ──────────────────────────────────────────────────────────────
    def perform_destroy(self, instance):
        old_data = self.serializer_class(instance).data

        if hasattr(instance, "soft_delete"):
            instance.soft_delete(user=self.request.user)
            action = "DELETED"
        else:
            instance.delete()
            action = "HARD_DELETED"

        self.log_audit(
            action,
            instance=None,
            previous_data=old_data,
            force_id=instance.pk,
            force_model=instance._meta.db_table,
        )

    # ──────────────────────────────────────────────────────────────
    # MÉTODO CENTRAL DE LOG
    # ──────────────────────────────────────────────────────────────
    def log_audit(
        self,
        action: str,
        instance=None,
        previous_data=None,
        force_id=None,
        force_model=None,
    ):
        """
        Registra la acción en SystemAudit.
        *Import diferido* → evita circulares.
        """
        # ⬇️ import aquí, no al inicio del módulo
        from apps.auditoria.models import SystemAudit

        request = self.request
        user    = request.user if request.user.is_authenticated else None

        table   = force_model or (instance._meta.db_table if instance else None)
        rec_id  = force_id    or (instance.pk            if instance else None)
        new_data = self.serializer_class(instance).data if instance else None


        # Nunca interrumpir la operación principal si el log falla
        try:
            with transaction.atomic():
                SystemAudit.objects.create(
                    user           = user,
                    action         = action,
                    affected_table = table,
                    record_id      = rec_id,
                    previous_data  = previous_data,
                    new_data       = new_data,
                    ip_address     = request.META.get("REMOTE_ADDR"),
                    user_agent     = request.META.get("HTTP_USER_AGENT"),
                    created_at     = timezone.now(),
                )
        except Exception:
            pass
