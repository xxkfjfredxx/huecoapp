from django.contrib import admin


class BaseAuditAdmin(admin.ModelAdmin):
    readonly_fields = [
        "created_by",
        "created_at",
        "updated_by",
        "updated_at",
        "deleted_by",
        "deleted_at",
    ]

    def get_readonly_fields(self, request, obj=None):
        # Permitir extender con otros campos en subclasses
        return super().get_readonly_fields(request, obj) + list(
            self.readonly_fields or []
        )

    def save_model(self, request, obj, form, change):
        # Automáticamente guardar updated_by
        if not obj.pk and hasattr(obj, "created_by"):
            obj.created_by = request.user

        if hasattr(obj, "updated_by"):
            obj.updated_by = request.user

        super().save_model(request, obj, form, change)
