from __future__ import annotations

import json
import math
import time
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from django.conf import settings
from django.utils import timezone

from apps.salon.models import Appointment


MODEL_DIR = Path(settings.BASE_DIR) / 'apps' / 'salon' / 'ai_module'
MODEL_PATH = MODEL_DIR / 'no_show_model.cbm'
METADATA_PATH = MODEL_DIR / 'model_meta.json'
MODEL_VERSION = 'catboost-no-show-v1'
FEATURE_NAMES = [
    'weekday',
    'hour',
    'client_cancel_count_90d',
    'client_no_show_count_90d',
    'lead_time_days',
    'payment_status',
    'master_appointments_same_day',
    'master_id',
]
CAT_FEATURES = ['weekday', 'payment_status', 'master_id']
WEEKDAYS_RU = ['Пн', 'Вт', 'Ср', 'Чт', 'Пт', 'Сб', 'Вс']
PAYMENT_STATUS_MAPPING = {
    Appointment.PaymentStatus.UNPAID: 'не_оплачено',
    Appointment.PaymentStatus.PAID: 'оплачено',
    Appointment.PaymentStatus.REFUNDED: 'частично',
}
SUPPORTED_PAYMENT_STATUSES = {'не_оплачено', 'частично', 'оплачено'}


@dataclass(frozen=True)
class AppointmentFeaturesInput:
    appointment_start: datetime
    client_cancel_count_90d: int
    client_no_show_count_90d: int
    lead_time_days: int
    payment_status: str
    master_appointments_same_day: int
    master_id: str | int = 'unknown'

    def validate(self) -> None:
        if self.payment_status not in SUPPORTED_PAYMENT_STATUSES:
            raise ValueError(
                f"payment_status должен быть одним из {sorted(SUPPORTED_PAYMENT_STATUSES)}, получено: {self.payment_status!r}"
            )


def _import_runtime_dependencies():
    try:
        import pandas as pd
        from catboost import CatBoostClassifier, Pool
    except ImportError as exc:
        raise RuntimeError(
            'Для работы новой AI-модели нужны пакеты catboost, pandas и numpy. '
            'В текущем окружении они не установлены.'
        ) from exc
    return pd, CatBoostClassifier, Pool


def _status_code(appointment: Appointment) -> str:
    return (appointment.status.status_code or '').strip().lower()


def _weekday_ru(dt: datetime) -> str:
    return WEEKDAYS_RU[dt.weekday()]


def _map_payment_status(payment_status: str) -> str:
    return PAYMENT_STATUS_MAPPING.get(payment_status, 'не_оплачено')


def _safe_days(delta) -> int:
    return max(math.floor(delta.total_seconds() / 86400.0), 0)


def _appointments_within_last_90_days(appointment: Appointment):
    if not appointment.start_datetime:
        return Appointment.objects.none()
    window_start = appointment.start_datetime - timedelta(days=90)
    return Appointment.objects.select_related('status').filter(
        client=appointment.client,
        start_datetime__gte=window_start,
        start_datetime__lt=appointment.start_datetime,
    )


def build_feature_dict_for_appointment(appointment: Appointment) -> dict[str, Any]:
    if not appointment.start_datetime:
        raise ValueError('У записи не указано время начала.')

    history_90d = list(_appointments_within_last_90_days(appointment))
    client_cancel_count_90d = sum(1 for item in history_90d if _status_code(item) == 'cancelled')
    client_no_show_count_90d = sum(1 for item in history_90d if _status_code(item) == 'no_show')
    lead_time_days = _safe_days(appointment.start_datetime - (appointment.created_at or timezone.now()))
    master_appointments_same_day = (
        Appointment.objects.filter(master=appointment.master, start_datetime__date=appointment.start_datetime.date())
        .exclude(pk=appointment.pk)
        .count()
    )

    return {
        'weekday': _weekday_ru(appointment.start_datetime),
        'hour': int(appointment.start_datetime.hour),
        'client_cancel_count_90d': int(client_cancel_count_90d),
        'client_no_show_count_90d': int(client_no_show_count_90d),
        'lead_time_days': int(lead_time_days),
        'payment_status': _map_payment_status(appointment.payment_status),
        'master_appointments_same_day': int(master_appointments_same_day),
        'master_id': str(appointment.master_id or 'unknown'),
    }


def merge_feature_overrides(base_features: dict[str, Any], overrides: dict | None) -> dict[str, Any]:
    merged = dict(base_features)
    if not overrides:
        return merged
    for feature_name in FEATURE_NAMES:
        if feature_name in overrides and overrides[feature_name] is not None:
            merged[feature_name] = overrides[feature_name]
    return merged


def appointment_to_features_input(appointment: Appointment, feature_overrides: dict | None = None) -> AppointmentFeaturesInput:
    feature_row = merge_feature_overrides(build_feature_dict_for_appointment(appointment), feature_overrides)
    inp = AppointmentFeaturesInput(
        appointment_start=appointment.start_datetime,
        client_cancel_count_90d=int(feature_row['client_cancel_count_90d']),
        client_no_show_count_90d=int(feature_row['client_no_show_count_90d']),
        lead_time_days=int(feature_row['lead_time_days']),
        payment_status=str(feature_row['payment_status']),
        master_appointments_same_day=int(feature_row['master_appointments_same_day']),
        master_id=feature_row['master_id'],
    )
    inp.validate()
    return inp


def features_to_dataframe(rows):
    pd, _, _ = _import_runtime_dependencies()
    return pd.DataFrame(list(rows))


def recommend_for_admin(probability: float) -> str:
    p = float(probability)
    if p < 0.25:
        return 'Риск низкий: достаточно стандартного напоминания о записи.'
    if p < 0.45:
        return 'Умеренный риск: желательно дополнительно подтвердить визит по телефону или в мессенджере.'
    if p < 0.65:
        return 'Повышенный риск: рекомендуется запросить предоплату или подтверждение визита.'
    if p < 0.85:
        return 'Высокий риск: лучше работать только по предоплате или перенести запись на другой слот.'
    return 'Критический риск неявки: не подтверждать запись без гарантий со стороны клиента.'


def risk_color_for_master(probability: float) -> str:
    p = float(probability)
    if p < 0.35:
        return 'green'
    if p < 0.65:
        return 'yellow'
    return 'red'


def _load_model():
    _, CatBoostClassifier, _ = _import_runtime_dependencies()
    if not MODEL_PATH.is_file():
        raise FileNotFoundError(f'Файл AI-модели не найден: {MODEL_PATH}')
    model = CatBoostClassifier()
    model.load_model(str(MODEL_PATH))
    return model


def load_training_meta() -> dict[str, Any] | None:
    if not METADATA_PATH.is_file():
        return None
    return json.loads(METADATA_PATH.read_text(encoding='utf-8-sig'))


def get_model_info() -> dict[str, Any]:
    metadata = load_training_meta() or {}
    return {
        'is_trained': MODEL_PATH.is_file(),
        'model_type': 'CatBoostClassifier',
        'model_version': metadata.get('model_version', MODEL_VERSION),
        'trained_at': metadata.get('trained_at', ''),
        'feature_names': metadata.get('feature_columns', FEATURE_NAMES),
        'cat_features': metadata.get('cat_features', CAT_FEATURES),
        'validation_accuracy': metadata.get('validation_accuracy'),
        'n_samples': metadata.get('n_samples'),
        'positive_class_is_no_show': metadata.get('positive_class_is_no_show', True),
    }


def predict_no_show(appointment: Appointment, feature_overrides: dict | None = None) -> dict[str, Any]:
    _, _, Pool = _import_runtime_dependencies()
    t0 = time.perf_counter()
    features_input = appointment_to_features_input(appointment, feature_overrides)
    feature_row = {
        'weekday': _weekday_ru(features_input.appointment_start),
        'hour': int(features_input.appointment_start.hour),
        'client_cancel_count_90d': int(features_input.client_cancel_count_90d),
        'client_no_show_count_90d': int(features_input.client_no_show_count_90d),
        'lead_time_days': int(features_input.lead_time_days),
        'payment_status': features_input.payment_status,
        'master_appointments_same_day': int(features_input.master_appointments_same_day),
        'master_id': str(features_input.master_id),
    }
    model = _load_model()
    data_frame = features_to_dataframe([feature_row])
    pool = Pool(data=data_frame, cat_features=CAT_FEATURES)
    raw_proba = model.predict_proba(pool)[0]
    no_show_probability = float(raw_proba[1]) if len(raw_proba) > 1 else float(raw_proba[0])
    elapsed_ms = (time.perf_counter() - t0) * 1000.0
    return {
        'no_show_probability': round(no_show_probability, 4),
        'admin_recommendation': recommend_for_admin(no_show_probability),
        'master_risk_color': risk_color_for_master(no_show_probability),
        'feature_snapshot': feature_row,
        'inference_time_ms': round(elapsed_ms, 2),
    }
