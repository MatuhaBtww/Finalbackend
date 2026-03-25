from rest_framework.permissions import BasePermission, SAFE_METHODS


def get_role_name(user) -> str:
    if not user or not user.is_authenticated:
        return ""
    if user.is_superuser:
        return "admin"
    role = getattr(user, "role", None)
    if not role:
        return ""
    return (role.role_name or "").strip().lower()


class IsAdminRole(BasePermission):
    def has_permission(self, request, view):
        return get_role_name(request.user) == "admin"


class IsAuthenticatedReadOnlyOrAdmin(BasePermission):
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        if request.method in SAFE_METHODS:
            return True
        return get_role_name(request.user) == "admin"


class IsAdminOrSelf(BasePermission):
    def has_object_permission(self, request, view, obj):
        return get_role_name(request.user) == "admin" or obj == request.user
