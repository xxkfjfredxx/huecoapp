# apps/utils/mixins.py
from django.conf import settings
from django.db    import models
from django.utils import timezone

AUTH_USER = settings.AUTH_USER_MODEL           # p. ej. "usuarios.User"


class AuditMixin(models.Model):
    """
    Campos comunes de auditoría + utilidades de soft-delete.
    No importa ningún modelo externo → evita ciclos de importación.
    """

    # -------- flags soft-delete -----------------------------------------
    is_deleted  = models.BooleanField(default=False)
    deleted_at  = models.DateTimeField(null=True, blank=True)
    deleted_by  = models.ForeignKey(
        AUTH_USER,
        null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name="deleted_%(class)s_set",
    )

    # -------- timestamps -------------------------------------------------
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(
        AUTH_USER,
        null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name="created_%(class)s_set",
    )
    updated_at = models.DateTimeField(auto_now=True)
    updated_by = models.ForeignKey(
        AUTH_USER,
        null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name="updated_%(class)s_set",
    )

    class Meta:
        abstract = True

    # --------------------------------------------------------------------
    # utilidades
    # --------------------------------------------------------------------
    def soft_delete(self, user=None):
        """Marca el registro como eliminado sin borrarlo físicamente."""
        self.is_deleted = True
        self.deleted_at = timezone.now()
        self.deleted_by = user
        self.save(update_fields=["is_deleted", "deleted_at", "deleted_by"])

    def restore(self):
        """Revierte un soft-delete."""
        self.is_deleted = False
        self.deleted_at = None
        self.deleted_by = None
        self.save(update_fields=["is_deleted", "deleted_at", "deleted_by"])
