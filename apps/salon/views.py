from decimal import Decimal

from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.salon.models import Aidata, Appointment, AuditLog, MasterSchedule, Service, Status, Transaction
from apps.salon.permissions import (
    AidataPermission,
    AppointmentPermission,
    IsAdminOrReadOnlyAuthenticated,
    MasterSchedulePermission,
    TransactionPermission,
)
from apps.salon.serializers import (
    AidataSerializer,
    AppointmentSerializer,
    AuditLogSerializer,
    MasterScheduleSerializer,
    NoShowPredictionRequestSerializer,
    NoShowPredictionResponseSerializer,
    ServiceSerializer,
    StatusSerializer,
    TransactionSerializer,
)
from apps.users.permissions import get_role_name


def _clamp(value: float, lower: float = 0.0, upper: float = 100.0) -> float:
    return max(lower, min(upper, value))


def _calculate_no_show_probability(features: dict) -> Decimal:
    probability = 15.0
    probability += float(features.get("late_cancellations", 0)) * 12.0
    probability += float(features.get("no_shows", 0)) * 20.0
    probability -= min(float(features.get("previous_visits", 0)) * 1.5, 15.0)
    probability += min(float(features.get("days_until_appointment", 0)) * 0.8, 12.0)
    probability -= 10.0 if bool(features.get("prepaid", False)) else 0.0
    probability -= min(float(features.get("loyalty_score", 0)) * 2.0, 10.0)
    return Decimal(f"{_clamp(probability):.2f}")


class ServiceViewSet(viewsets.ModelViewSet):
    queryset = Service.objects.all()
    serializer_class = ServiceSerializer
    permission_classes = [IsAdminOrReadOnlyAuthenticated]

    def get_queryset(self):
        queryset = super().get_queryset()
        category = self.request.query_params.get("category")
        search = self.request.query_params.get("search")
        if category:
            queryset = queryset.filter(category__icontains=category)
        if search:
            queryset = queryset.filter(service_name__icontains=search)
        return queryset


class StatusViewSet(viewsets.ModelViewSet):
    queryset = Status.objects.all()
    serializer_class = StatusSerializer
    permission_classes = [IsAdminOrReadOnlyAuthenticated]


class MasterScheduleViewSet(viewsets.ModelViewSet):
    queryset = MasterSchedule.objects.select_related("master").all()
    serializer_class = MasterScheduleSerializer
    permission_classes = [MasterSchedulePermission]

    def get_queryset(self):
        queryset = super().get_queryset()
        role_name = get_role_name(self.request.user)
        if role_name == "master":
            queryset = queryset.filter(master=self.request.user)
        master_id = self.request.query_params.get("master_id")
        if master_id and role_name == "admin":
            queryset = queryset.filter(master_id=master_id)
        return queryset


class AppointmentViewSet(viewsets.ModelViewSet):
    queryset = Appointment.objects.select_related("client", "master", "service", "status").all()
    serializer_class = AppointmentSerializer
    permission_classes = [AppointmentPermission]

    def get_queryset(self):
        queryset = super().get_queryset()
        role_name = get_role_name(self.request.user)
        if role_name == "client":
            queryset = queryset.filter(client=self.request.user)
        elif role_name == "master":
            queryset = queryset.filter(master=self.request.user)
        master_id = self.request.query_params.get("master_id")
        client_id = self.request.query_params.get("client_id")
        status_value = self.request.query_params.get("status")
        date_from = self.request.query_params.get("date_from")
        date_to = self.request.query_params.get("date_to")
        if master_id:
            queryset = queryset.filter(master_id=master_id)
        if client_id:
            queryset = queryset.filter(client_id=client_id)
        if status_value:
            queryset = queryset.filter(status__status_code__iexact=status_value)
        if date_from:
            queryset = queryset.filter(start_datetime__date__gte=date_from)
        if date_to:
            queryset = queryset.filter(start_datetime__date__lte=date_to)
        return queryset

    def perform_create(self, serializer):
        actor = self.request.user if self.request.user.is_authenticated else None
        payload = {}
        if get_role_name(actor) == "client":
            payload["client"] = actor
        if get_role_name(actor) == "master":
            payload["master"] = actor
        appointment = serializer.save(**payload)
        AuditLog.objects.create(
            user=actor,
            action_type="created",
            action_object=f"appointment:{appointment.id}",
            result="success",
            additional_data={"status": appointment.status.status_code},
        )

    def perform_update(self, serializer):
        previous_status = self.get_object().status.status_code
        actor = self.request.user if self.request.user.is_authenticated else None
        appointment = serializer.save()
        action = "status_changed" if previous_status != appointment.status.status_code else "updated"
        AuditLog.objects.create(
            user=actor,
            action_type=action,
            action_object=f"appointment:{appointment.id}",
            result="success",
            additional_data={"status": appointment.status.status_code},
        )

    def destroy(self, request, *args, **kwargs):
        appointment = self.get_object()
        cancelled_status = Status.objects.filter(status_code__iexact="cancelled").first()
        if cancelled_status is None:
            return Response(
                {"detail": "Create a Status with code 'cancelled' before cancelling appointments."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        appointment.status = cancelled_status
        appointment.comment = request.data.get("comment", appointment.comment)
        appointment.save(update_fields=["status", "comment", "end_datetime"])

        actor = request.user if request.user.is_authenticated else None
        AuditLog.objects.create(
            user=actor,
            action_type="cancelled",
            action_object=f"appointment:{appointment.id}",
            result="success",
            additional_data={"status": appointment.status.status_code, "comment": appointment.comment},
        )
        serializer = self.get_serializer(appointment)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(detail=True, methods=["post"], url_path="predict-no-show")
    def predict_no_show(self, request, pk=None):
        appointment = self.get_object()
        serializer = NoShowPredictionRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        input_features = serializer.validated_data["input_features"]
        target_value = serializer.validated_data.get("target_value")
        model_version = serializer.validated_data["model_version"]
        probability = _calculate_no_show_probability(input_features)

        ai_data, _ = Aidata.objects.update_or_create(
            appointment=appointment,
            defaults={
                "input_features": input_features,
                "target_value": target_value,
                "prediction_probability": probability,
                "model_version": model_version,
            },
        )

        actor = request.user if request.user.is_authenticated else None
        AuditLog.objects.create(
            user=actor,
            action_type="ai_prediction",
            action_object=f"appointment:{appointment.id}",
            result="success",
            additional_data={
                "prediction_probability": str(ai_data.prediction_probability),
                "model_version": ai_data.model_version,
            },
        )

        response = NoShowPredictionResponseSerializer(
            {
                "appointment_id": appointment.id,
                "prediction_probability": f"{ai_data.prediction_probability}%",
                "model_version": ai_data.model_version,
                "input_features": ai_data.input_features,
                "target_value": ai_data.target_value,
            }
        )
        return Response(response.data, status=status.HTTP_200_OK)

    @action(detail=True, methods=["post"], url_path="confirm")
    def confirm(self, request, pk=None):
        appointment = self.get_object()
        confirmed_status = Status.objects.filter(status_code__iexact="confirmed").first()
        if confirmed_status is None:
            return Response({"detail": "Create a Status with code 'confirmed' first."}, status=status.HTTP_400_BAD_REQUEST)
        appointment.status = confirmed_status
        appointment.save(update_fields=["status"])
        AuditLog.objects.create(
            user=request.user,
            action_type="confirmed",
            action_object=f"appointment:{appointment.id}",
            result="success",
            additional_data={"status": appointment.status.status_code},
        )
        return Response(self.get_serializer(appointment).data)

    @action(detail=True, methods=["post"], url_path="complete")
    def complete(self, request, pk=None):
        appointment = self.get_object()
        completed_status = Status.objects.filter(status_code__iexact="completed").first()
        if completed_status is None:
            return Response({"detail": "Create a Status with code 'completed' first."}, status=status.HTTP_400_BAD_REQUEST)
        appointment.status = completed_status
        appointment.save(update_fields=["status"])
        AuditLog.objects.create(
            user=request.user,
            action_type="completed",
            action_object=f"appointment:{appointment.id}",
            result="success",
            additional_data={"status": appointment.status.status_code},
        )
        return Response(self.get_serializer(appointment).data)

    @action(detail=True, methods=["post"], url_path="cancel")
    def cancel(self, request, pk=None):
        return self.destroy(request, pk=pk)

    @action(detail=True, methods=["post"], url_path="pay")
    def pay(self, request, pk=None):
        appointment = self.get_object()
        amount = request.data.get("amount") or appointment.service.price
        payment_method = request.data.get("payment_method", "cash")
        external_id = request.data.get("external_id", "")
        transaction = Transaction.objects.create(
            appointment=appointment,
            amount=amount,
            payment_method=payment_method,
            status="paid",
            external_id=external_id,
        )
        appointment.payment_status = Appointment.PaymentStatus.PAID
        appointment.save(update_fields=["payment_status"])
        AuditLog.objects.create(
            user=request.user,
            action_type="payment_created",
            action_object=f"appointment:{appointment.id}",
            result="success",
            additional_data={"transaction_id": transaction.id, "amount": str(transaction.amount)},
        )
        return Response(TransactionSerializer(transaction, context={"request": request}).data, status=status.HTTP_201_CREATED)


class TransactionViewSet(viewsets.ModelViewSet):
    queryset = Transaction.objects.select_related("appointment").all()
    serializer_class = TransactionSerializer
    permission_classes = [TransactionPermission]

    def get_queryset(self):
        queryset = super().get_queryset()
        role_name = get_role_name(self.request.user)
        if role_name == "client":
            queryset = queryset.filter(appointment__client=self.request.user)
        elif role_name == "master":
            queryset = queryset.filter(appointment__master=self.request.user)
        appointment_id = self.request.query_params.get("appointment_id")
        if appointment_id:
            queryset = queryset.filter(appointment_id=appointment_id)
        return queryset


class AidataViewSet(viewsets.ModelViewSet):
    queryset = Aidata.objects.select_related("appointment").all()
    serializer_class = AidataSerializer
    permission_classes = [AidataPermission]

    def get_queryset(self):
        queryset = super().get_queryset()
        role_name = get_role_name(self.request.user)
        if role_name == "master":
            queryset = queryset.filter(appointment__master=self.request.user)
        appointment_id = self.request.query_params.get("appointment_id")
        if appointment_id:
            queryset = queryset.filter(appointment_id=appointment_id)
        return queryset


class AuditLogViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = AuditLog.objects.select_related("user").all()
    serializer_class = AuditLogSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        queryset = super().get_queryset()
        if get_role_name(self.request.user) != "admin":
            queryset = queryset.filter(user=self.request.user)
        return queryset
