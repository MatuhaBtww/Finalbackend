from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from apps.users.models import AccessRight, Role, User


@admin.register(Role)
class RoleAdmin(admin.ModelAdmin):
    list_display = ("role_name", "role_description")
    search_fields = ("role_name", "role_description")


@admin.register(AccessRight)
class AccessRightAdmin(admin.ModelAdmin):
    list_display = ("role", "operation_name", "access_object", "permission")
    list_filter = ("role", "permission")
    search_fields = ("operation_name", "access_object", "permission")


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    fieldsets = UserAdmin.fieldsets + (
        ("Additional info", {"fields": ("full_name", "role", "account_status", "registration_date")}),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        ("Additional info", {"fields": ("email", "full_name", "role", "account_status")}),
    )
    list_display = ("username", "full_name", "email", "role", "account_status", "is_staff", "is_active")
    list_filter = ("role", "account_status", "is_staff", "is_active")
    readonly_fields = ("registration_date",)
    search_fields = ("username", "full_name", "email")
