from datetime import timedelta

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone


class Service(models.Model):
    service_name = models.CharField(max_length=150, unique=True, default="")
    duration_minutes = models.PositiveIntegerField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
    category = models.CharField(max_length=120, default="")

    class Meta:
        ordering = ("service_name",)
        verbose_name = "услуга"
        verbose_name_plural = "услуги"

    def __str__(self) -> str:
        return self.service_name


class Status(models.Model):
    status_code = models.CharField(max_length=50, unique=True)
    status_name = models.CharField(max_length=120)
    status_group = models.CharField(max_length=120, blank=True)
    color_indicator = models.CharField(max_length=30, blank=True)

    class Meta:
        ordering = ("status_group", "status_name")
        verbose_name = "статус"
        verbose_name_plural = "статусы"

    def __str__(self) -> str:
        return self.status_name


class MasterSchedule(models.Model):
    class Weekday(models.IntegerChoices):
        MONDAY = 1, "Понедельник"
        TUESDAY = 2, "Вторник"
        WEDNESDAY = 3, "Среда"
        THURSDAY = 4, "Четверг"
        FRIDAY = 5, "Пятница"
        SATURDAY = 6, "Суббота"
        SUNDAY = 7, "Воскресенье"

    master = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="master_schedules",
    )
    day_of_week = models.PositiveSmallIntegerField(choices=Weekday.choices)
    start_time = models.TimeField()
    end_time = models.TimeField()
    is_workday = models.BooleanField(default=True)
    breaks = models.TextField(blank=True)

    class Meta:
        ordering = ("master", "day_of_week", "start_time")
        unique_together = ("master", "day_of_week", "start_time", "end_time")
        verbose_name = "расписание мастера"
        verbose_name_plural = "расписания мастеров"

    def clean(self):
        super().clean()
        if self.start_time >= self.end_time:
            raise ValidationError("Working hours start time must be earlier than end time.")

    def __str__(self) -> str:
        return f"{self.master} - {self.get_day_of_week_display()}"


class Appointment(models.Model):
    class PaymentStatus(models.TextChoices):
        UNPAID = "unpaid", "Не оплачено"
        PAID = "paid", "Оплачено"
        REFUNDED = "refunded", "Возврат"

    client = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="client_appointments",
    )
    master = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="master_appointments",
    )
    service = models.ForeignKey(Service, on_delete=models.PROTECT, related_name="appointments")
    status = models.ForeignKey(Status, on_delete=models.PROTECT, related_name="appointments")
    start_datetime = models.DateTimeField(null=True, blank=True)
    end_datetime = models.DateTimeField(null=True, blank=True)
    comment = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    payment_status = models.CharField(
        max_length=20,
        choices=PaymentStatus.choices,
        default=PaymentStatus.UNPAID,
    )

    class Meta:
        ordering = ("start_datetime",)
        verbose_name = "запись"
        verbose_name_plural = "записи"

    def clean(self):
        super().clean()
        if self.master_id == self.client_id:
            raise ValidationError("Master and client must be different users.")
        if self.start_datetime and self.service_id:
            expected_end = self.start_datetime + timedelta(minutes=self.service.duration_minutes)
            if self.end_datetime and self.end_datetime != expected_end:
                raise ValidationError("Appointment end time must match service duration.")
        if self.start_datetime and self.end_datetime and self.start_datetime >= self.end_datetime:
            raise ValidationError("Appointment start time must be earlier than end time.")
        if self.start_datetime and self.end_datetime:
            overlaps = Appointment.objects.filter(
                master=self.master,
                start_datetime__lt=self.end_datetime,
                end_datetime__gt=self.start_datetime,
            ).exclude(status__status_code__iexact="cancelled")
            if self.pk:
                overlaps = overlaps.exclude(pk=self.pk)
            if overlaps.exists():
                raise ValidationError("The selected master already has an appointment in this time slot.")

    def save(self, *args, **kwargs):
        if self.start_datetime and self.service_id:
            self.end_datetime = self.start_datetime + timedelta(minutes=self.service.duration_minutes)
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return f"{self.client} -> {self.master} at {self.start_datetime:%Y-%m-%d %H:%M}"


class Transaction(models.Model):
    appointment = models.ForeignKey(Appointment, on_delete=models.CASCADE, related_name="transactions")
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    payment_method = models.CharField(max_length=50)
    status = models.CharField(max_length=50)
    payment_datetime = models.DateTimeField(default=timezone.now)
    external_id = models.CharField(max_length=120, blank=True)

    class Meta:
        ordering = ("-payment_datetime",)
        verbose_name = "транзакция"
        verbose_name_plural = "транзакции"

    def __str__(self) -> str:
        return f"{self.appointment_id} - {self.amount}"


class Aidata(models.Model):
    appointment = models.OneToOneField(Appointment, on_delete=models.CASCADE, related_name="ai_data")
    input_features = models.JSONField(default=dict, blank=True)
    target_value = models.IntegerField(null=True, blank=True)
    prediction_probability = models.DecimalField(max_digits=5, decimal_places=2)
    model_version = models.CharField(max_length=100)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ("-created_at",)
        verbose_name = "AI-данные"
        verbose_name_plural = "AI-данные"

    def __str__(self) -> str:
        return f"AI data for appointment {self.appointment_id}"


class AuditLog(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="audit_logs",
    )
    action_datetime = models.DateTimeField(default=timezone.now)
    action_type = models.CharField(max_length=100, default="")
    action_object = models.CharField(max_length=100, default="")
    result = models.CharField(max_length=100, default="")
    additional_data = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ("-action_datetime",)
        verbose_name = "журнал действий"
        verbose_name_plural = "журнал действий"

    def __str__(self) -> str:
        return f"{self.action_type} {self.action_object}"
