from rest_framework.permissions import BasePermission, SAFE_METHODS

from apps.users.permissions import get_role_name


class IsAdminOrReadOnlyAuthenticated(BasePermission):
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        if request.method in SAFE_METHODS:
            return True
        return get_role_name(request.user) == "admin"


class AppointmentPermission(BasePermission):
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        role_name = get_role_name(request.user)
        if request.method in SAFE_METHODS:
            return role_name in {"admin", "master", "client"}
        if getattr(view, "action", "") in {"predict_no_show", "confirm", "complete"}:
            return role_name in {"admin", "master"}
        if getattr(view, "action", "") in {"cancel"}:
            return role_name in {"admin", "master", "client"}
        return role_name in {"admin", "client", "master"}

    def has_object_permission(self, request, view, obj):
        role_name = get_role_name(request.user)
        if role_name == "admin":
            return True
        if role_name == "master":
            return obj.master_id == request.user.id
        if role_name == "client":
            return obj.client_id == request.user.id
        return False


class MasterSchedulePermission(BasePermission):
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        role_name = get_role_name(request.user)
        if request.method in SAFE_METHODS:
            return role_name in {"admin", "master", "client"}
        return role_name in {"admin", "master"}

    def has_object_permission(self, request, view, obj):
        role_name = get_role_name(request.user)
        if role_name == "admin":
            return True
        return role_name == "master" and obj.master_id == request.user.id


class TransactionPermission(BasePermission):
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        role_name = get_role_name(request.user)
        if request.method in SAFE_METHODS:
            return role_name in {"admin", "master", "client"}
        return role_name == "admin"

    def has_object_permission(self, request, view, obj):
        role_name = get_role_name(request.user)
        if role_name == "admin":
            return True
        if role_name == "master":
            return obj.appointment.master_id == request.user.id
        if role_name == "client":
            return obj.appointment.client_id == request.user.id
        return False


class AidataPermission(BasePermission):
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        role_name = get_role_name(request.user)
        if request.method in SAFE_METHODS:
            return role_name in {"admin", "master"}
        return role_name == "admin"

    def has_object_permission(self, request, view, obj):
        role_name = get_role_name(request.user)
        if role_name == "admin":
            return True
        return role_name == "master" and obj.appointment.master_id == request.user.id
