from django.urls import path
from rest_framework.routers import DefaultRouter

from apps.salon.views import (
    AidataViewSet,
    AppointmentViewSet,
    AuditLogViewSet,
    MasterScheduleViewSet,
    NoShowModelInfoView,
    ServiceViewSet,
    StatusViewSet,
    TransactionViewSet,
)

router = DefaultRouter()
router.register("services", ServiceViewSet, basename="service")
router.register("statuses", StatusViewSet, basename="status")
router.register("master-schedules", MasterScheduleViewSet, basename="master-schedule")
router.register("appointments", AppointmentViewSet, basename="appointment")
router.register("transactions", TransactionViewSet, basename="transaction")
router.register("ai-data", AidataViewSet, basename="ai-data")
router.register("audit-logs", AuditLogViewSet, basename="audit-log")

urlpatterns = [
    path("ai/model-info/", NoShowModelInfoView.as_view(), name="ai-model-info"),
] + router.urls
