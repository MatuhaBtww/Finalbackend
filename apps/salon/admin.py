from django.contrib import admin

from apps.salon.models import Aidata, Appointment, AuditLog, MasterSchedule, Service, Status, Transaction


@admin.register(Service)
class ServiceAdmin(admin.ModelAdmin):
    list_display = ("service_name", "category", "duration_minutes", "price")
    list_filter = ("category",)
    search_fields = ("service_name", "category")


@admin.register(Status)
class StatusAdmin(admin.ModelAdmin):
    list_display = ("status_code", "status_name", "status_group", "color_indicator")
    list_filter = ("status_group",)
    search_fields = ("status_code", "status_name")


@admin.register(MasterSchedule)
class MasterScheduleAdmin(admin.ModelAdmin):
    list_display = ("master", "day_of_week", "start_time", "end_time", "is_workday")
    list_filter = ("day_of_week", "is_workday")
    search_fields = ("master__full_name", "master__username")


@admin.register(Appointment)
class AppointmentAdmin(admin.ModelAdmin):
    list_display = ("client", "master", "service", "status", "start_datetime", "end_datetime", "payment_status")
    list_filter = ("status", "service", "master", "payment_status")
    search_fields = ("client__full_name", "master__full_name", "service__service_name")


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ("appointment", "amount", "payment_method", "status", "payment_datetime", "external_id")
    list_filter = ("payment_method", "status")
    search_fields = ("external_id",)


@admin.register(Aidata)
class AidataAdmin(admin.ModelAdmin):
    list_display = ("appointment", "prediction_probability", "master_risk_color", "model_version", "created_at")
    list_filter = ("master_risk_color", "model_version")
    search_fields = ("model_version",)


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ("user", "action_type", "action_object", "result", "action_datetime")
    list_filter = ("action_type", "result")
    search_fields = ("action_object", "user__full_name", "user__username")
