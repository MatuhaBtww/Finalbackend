from django.core.management.base import BaseCommand

from apps.salon.services import backfill_ai_data_for_appointments


class Command(BaseCommand):
    help = "Создает или обновляет AI-данные для всех существующих записей."

    def handle(self, *args, **options):
        result = backfill_ai_data_for_appointments()
        self.stdout.write(
            self.style.SUCCESS(
                "Обработка завершена. "
                f"Всего записей: {result['processed']}, "
                f"создано/обновлено AI-данных: {result['created_or_updated']}, "
                f"пропущено: {result['skipped']}."
            )
        )
