from rest_framework import permissions


class EsRolPermitido(permissions.BasePermission):
    def has_permission(self, request, view):
        user = request.user
        if not user.is_authenticated:
            return False

        # ✅ superusers siempre pueden
        if user.is_superuser:
            return True

        roles_permitidos = getattr(view, "roles_permitidos", None)
        if roles_permitidos is None:
            return True

        return user.role and user.role.name in roles_permitidos
