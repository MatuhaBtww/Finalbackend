from rest_framework import serializers

from apps.salon.models import Aidata, Appointment, AuditLog, MasterSchedule, Service, Status, Transaction
from apps.users.models import User
from apps.users.serializers import UserSerializer


class ServiceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Service
        fields = ("id", "service_name", "duration_minutes", "price", "category")


class StatusSerializer(serializers.ModelSerializer):
    class Meta:
        model = Status
        fields = ("id", "status_code", "status_name", "status_group", "color_indicator")


class MasterScheduleSerializer(serializers.ModelSerializer):
    master = UserSerializer(read_only=True)
    master_id = serializers.PrimaryKeyRelatedField(source="master", queryset=User.objects.all(), write_only=True)

    class Meta:
        model = MasterSchedule
        fields = ("id", "master", "master_id", "day_of_week", "start_time", "end_time", "is_workday", "breaks")


class AppointmentSerializer(serializers.ModelSerializer):
    client = UserSerializer(read_only=True)
    master = UserSerializer(read_only=True)
    service = ServiceSerializer(read_only=True)
    status = StatusSerializer(read_only=True)
    client_id = serializers.PrimaryKeyRelatedField(source="client", queryset=User.objects.all(), write_only=True)
    master_id = serializers.PrimaryKeyRelatedField(source="master", queryset=User.objects.all(), write_only=True)
    service_id = serializers.PrimaryKeyRelatedField(source="service", queryset=Service.objects.all(), write_only=True)
    status_id = serializers.PrimaryKeyRelatedField(source="status", queryset=Status.objects.all(), write_only=True)

    class Meta:
        model = Appointment
        fields = (
            "id",
            "client",
            "master",
            "service",
            "status",
            "client_id",
            "master_id",
            "service_id",
            "status_id",
            "start_datetime",
            "end_datetime",
            "comment",
            "created_at",
            "payment_status",
        )
        read_only_fields = ("end_datetime", "created_at")


class TransactionSerializer(serializers.ModelSerializer):
    appointment = AppointmentSerializer(read_only=True)
    appointment_id = serializers.PrimaryKeyRelatedField(source="appointment", queryset=Appointment.objects.all(), write_only=True)

    class Meta:
        model = Transaction
        fields = ("id", "appointment", "appointment_id", "amount", "payment_method", "status", "payment_datetime", "external_id")


class AidataSerializer(serializers.ModelSerializer):
    appointment = AppointmentSerializer(read_only=True)
    appointment_id = serializers.PrimaryKeyRelatedField(source="appointment", queryset=Appointment.objects.all(), write_only=True)
    prediction_probability = serializers.SerializerMethodField()

    class Meta:
        model = Aidata
        fields = (
            "id",
            "appointment",
            "appointment_id",
            "input_features",
            "target_value",
            "prediction_probability",
            "model_version",
            "created_at",
        )

    def get_prediction_probability(self, obj: Aidata) -> str:
        return f"{obj.prediction_probability}%"


class AuditLogSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    user_id = serializers.PrimaryKeyRelatedField(
        source="user",
        queryset=User.objects.all(),
        write_only=True,
        allow_null=True,
        required=False,
    )

    class Meta:
        model = AuditLog
        fields = ("id", "user", "user_id", "action_datetime", "action_type", "action_object", "result", "additional_data")


class NoShowPredictionRequestSerializer(serializers.Serializer):
    input_features = serializers.JSONField()
    target_value = serializers.IntegerField(required=False, allow_null=True)
    model_version = serializers.CharField(required=False, default="heuristic-v1")


class NoShowPredictionResponseSerializer(serializers.Serializer):
    appointment_id = serializers.IntegerField()
    prediction_probability = serializers.CharField()
    model_version = serializers.CharField()
    input_features = serializers.JSONField()
    target_value = serializers.IntegerField(required=False, allow_null=True)
