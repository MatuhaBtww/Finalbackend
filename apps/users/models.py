from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone


class Role(models.Model):
    role_name = models.CharField(max_length=100, unique=True)
    role_description = models.TextField(blank=True)

    class Meta:
        ordering = ("role_name",)
        verbose_name = "роль"
        verbose_name_plural = "роли"

    def __str__(self) -> str:
        return self.role_name


class AccessRight(models.Model):
    role = models.ForeignKey(Role, on_delete=models.CASCADE, related_name="access_rights")
    operation_name = models.CharField(max_length=150)
    access_object = models.CharField(max_length=150)
    permission = models.CharField(max_length=100)

    class Meta:
        ordering = ("role__role_name", "operation_name")
        verbose_name = "право доступа"
        verbose_name_plural = "права доступа"

    def __str__(self) -> str:
        return f"{self.role} - {self.operation_name}"


class User(AbstractUser):
    class AccountStatus(models.TextChoices):
        ACTIVE = "active", "Активен"
        INACTIVE = "inactive", "Неактивен"
        BLOCKED = "blocked", "Заблокирован"

    role = models.ForeignKey(
        Role,
        on_delete=models.PROTECT,
        related_name="users",
        null=True,
        blank=True,
    )
    full_name = models.CharField(max_length=255, default="")
    email = models.EmailField(unique=True)
    account_status = models.CharField(
        max_length=20,
        choices=AccountStatus.choices,
        default=AccountStatus.ACTIVE,
    )
    registration_date = models.DateTimeField(default=timezone.now)

    REQUIRED_FIELDS = ["email", "full_name"]

    class Meta:
        verbose_name = "пользователь"
        verbose_name_plural = "пользователи"

    def save(self, *args, **kwargs):
        if not self.full_name:
            self.full_name = self.get_full_name() or self.username
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return self.full_name or self.username
