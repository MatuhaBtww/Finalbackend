from datetime import timedelta

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone


class Service(models.Model):
    service_name = models.CharField("Название услуги", max_length=150, unique=True, default="")
    duration_minutes = models.PositiveIntegerField("Длительность, мин")
    price = models.DecimalField("Цена", max_digits=10, decimal_places=2)
    category = models.CharField("Категория", max_length=120, default="")

    class Meta:
        ordering = ("service_name",)
        verbose_name = "услуга"
        verbose_name_plural = "услуги"

    def __str__(self) -> str:
        return self.service_name


class Status(models.Model):
    status_code = models.CharField("Код статуса", max_length=50, unique=True)
    status_name = models.CharField("Название статуса", max_length=120)
    status_group = models.CharField("Группа статусов", max_length=120, blank=True)
    color_indicator = models.CharField("Цветовой индикатор", max_length=30, blank=True)

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
        verbose_name="Мастер",
    )
    day_of_week = models.PositiveSmallIntegerField("День недели", choices=Weekday.choices)
    start_time = models.TimeField("Время начала")
    end_time = models.TimeField("Время окончания")
    is_workday = models.BooleanField("Рабочий день", default=True)
    breaks = models.TextField("Перерывы", blank=True)

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
        verbose_name="Клиент",
    )
    master = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="master_appointments",
        verbose_name="Мастер",
    )
    service = models.ForeignKey(
        Service,
        on_delete=models.PROTECT,
        related_name="appointments",
        verbose_name="Услуга",
    )
    status = models.ForeignKey(
        Status,
        on_delete=models.PROTECT,
        related_name="appointments",
        verbose_name="Статус",
    )
    start_datetime = models.DateTimeField("Дата и время начала", null=True, blank=True)
    end_datetime = models.DateTimeField("Дата и время окончания", null=True, blank=True)
    comment = models.TextField("Комментарий", blank=True)
    created_at = models.DateTimeField("Дата создания", auto_now_add=True)
    payment_status = models.CharField(
        "Статус оплаты",
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
        client_label = str(self.client) if self.client_id else "Клиент не указан"
        master_label = str(self.master) if self.master_id else "Мастер не указан"
        if self.start_datetime:
            start_label = self.start_datetime.strftime("%Y-%m-%d %H:%M")
        else:
            start_label = "время не указано"
        return f"{client_label} -> {master_label}, {start_label}"


class Transaction(models.Model):
    appointment = models.ForeignKey(
        Appointment,
        on_delete=models.CASCADE,
        related_name="transactions",
        verbose_name="Запись",
    )
    amount = models.DecimalField("Сумма", max_digits=10, decimal_places=2)
    payment_method = models.CharField("Способ оплаты", max_length=50)
    status = models.CharField("Статус транзакции", max_length=50)
    payment_datetime = models.DateTimeField("Дата и время оплаты", default=timezone.now)
    external_id = models.CharField("Внешний идентификатор", max_length=120, blank=True)

    class Meta:
        ordering = ("-payment_datetime",)
        verbose_name = "транзакция"
        verbose_name_plural = "транзакции"

    def __str__(self) -> str:
        return f"{self.appointment_id} - {self.amount}"


class Aidata(models.Model):
    appointment = models.OneToOneField(
        Appointment,
        on_delete=models.CASCADE,
        related_name="ai_data",
        verbose_name="Запись",
    )
    input_features = models.JSONField("Входные признаки", default=dict, blank=True)
    target_value = models.IntegerField("Целевое значение", null=True, blank=True)
    prediction_probability = models.DecimalField("Вероятность неявки", max_digits=5, decimal_places=2)
    admin_recommendation = models.TextField("Рекомендация администратору", blank=True)
    master_risk_color = models.CharField("Цвет риска для мастера", max_length=20, blank=True)
    inference_time_ms = models.DecimalField("Время инференса, мс", max_digits=8, decimal_places=2, null=True, blank=True)
    model_version = models.CharField("Версия модели", max_length=100)
    created_at = models.DateTimeField("Дата создания", default=timezone.now)

    class Meta:
        ordering = ("-created_at",)
        verbose_name = "AI-данные"
        verbose_name_plural = "AI-данные"

    def __str__(self) -> str:
        return f"AI-данные для записи {self.appointment_id}"


class AuditLog(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="audit_logs",
        verbose_name="Пользователь",
    )
    action_datetime = models.DateTimeField("Дата и время действия", default=timezone.now)
    action_type = models.CharField("Тип действия", max_length=100, default="")
    action_object = models.CharField("Объект действия", max_length=100, default="")
    result = models.CharField("Результат", max_length=100, default="")
    additional_data = models.JSONField("Дополнительные данные", default=dict, blank=True)

    class Meta:
        ordering = ("-action_datetime",)
        verbose_name = "журнал действий"
        verbose_name_plural = "журнал действий"

    def __str__(self) -> str:
        return f"{self.action_type} {self.action_object}"
