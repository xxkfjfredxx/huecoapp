from rest_framework import permissions


class EsRolPermitido(permissions.BasePermission):
    """
    Permite acceso según privilegios o roles lógicos del usuario.
    Soporta superusuarios y staff sin depender de un campo 'role'.
    """

    def has_permission(self, request, view):
        user = request.user
        if not user.is_authenticated:
            return False

        # ✅ Superuser siempre puede
        if user.is_superuser:
            return True

        # ✅ Staff puede si la vista lo permite
        roles_permitidos = getattr(view, "roles_permitidos", None)
        if roles_permitidos is None:
            return True

        # ⚙️ Usa is_staff o auth_provider como referencia de rol
        if "Admin" in roles_permitidos and user.is_staff:
            return True

        if "RRHH" in roles_permitidos and user.auth_provider in ["email", "mixed"]:
            return True

        return False
