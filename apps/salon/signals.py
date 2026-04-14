from django.db.models.signals import post_save
from django.dispatch import receiver

from apps.salon.models import Appointment
from apps.salon.services import upsert_ai_data_for_appointment


@receiver(post_save, sender=Appointment)
def ensure_ai_data_for_appointment(sender, instance: Appointment, **kwargs):
    try:
        upsert_ai_data_for_appointment(instance)
    except Exception:
        # AI-анализ не должен ломать сохранение записи, если окружение модели пока не готово.
        return
