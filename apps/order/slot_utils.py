"""
Общая логика слотов записи: рабочие часы мастера + пересечение с заказами.
Используется в AvailableTimeSlotsView и NearbyMastersView.
"""
from __future__ import annotations

from datetime import datetime, time

from .models import Order, OrderStatus, OrderType


def parse_working_time_bounds(working_time: str) -> tuple[int, int, int, int]:
    """
    Парсит строку вида "09:00-18:00" -> (start_h, start_m, end_h, end_m).
    При ошибке — дефолт 9:00–18:00 (как в AvailableTimeSlotsView).
    """
    raw = (working_time or '').strip() or '09:00-18:00'
    try:
        start_time_str, end_time_str = raw.split('-', 1)
        sh, sm = map(int, start_time_str.strip().split(':'))
        eh, em = map(int, end_time_str.strip().split(':'))
        return sh, sm, eh, em
    except (ValueError, AttributeError):
        return 9, 0, 18, 0


def build_slots_for_master_on_date(master, check_date) -> list[dict]:
    """
    Слоты по 2 часа в рамках рабочего дня + флаг available с учётом scheduled-заказов.
    Каждый элемент: start, end (строки HH:MM), available (bool), опционально order_id.
    """
    sh, sm, eh, em = parse_working_time_bounds(master.working_time or '')

    slots: list[dict] = []
    current_hour, current_minute = sh, sm

    while current_hour < eh or (current_hour == eh and current_minute < em):
        slot_start = time(current_hour, current_minute)
        next_hour = current_hour + 2
        next_minute = current_minute
        if next_hour > eh or (next_hour == eh and next_minute > em):
            break
        slot_end = time(next_hour, next_minute)
        slots.append({
            'start': slot_start.strftime('%H:%M'),
            'end': slot_end.strftime('%H:%M'),
        })
        current_hour, current_minute = next_hour, next_minute

    existing_orders = Order.objects.filter(
        master=master,
        order_type=OrderType.SCHEDULED,
        scheduled_date=check_date,
        status__in=[OrderStatus.PENDING, OrderStatus.IN_PROGRESS],
    )

    for slot in slots:
        slot['available'] = True
        slot_start_time = datetime.strptime(slot['start'], '%H:%M').time()
        slot_end_time = datetime.strptime(slot['end'], '%H:%M').time()
        for order in existing_orders:
            if not order.scheduled_time_start or not order.scheduled_time_end:
                continue
            if order.scheduled_time_start < slot_end_time and order.scheduled_time_end > slot_start_time:
                slot['available'] = False
                slot['order_id'] = order.id
                break

    return slots


def master_has_open_slot(master, check_date, at_time: time | None = None) -> bool:
    """
    Есть ли хотя бы один доступный слот в этот день.
    Если at_time задан — слот должен содержать это время (полуинтервал [start, end)).
    """
    slots = build_slots_for_master_on_date(master, check_date)
    if not slots:
        return False
    if at_time is None:
        return any(s.get('available') for s in slots)
    for s in slots:
        if not s.get('available'):
            continue
        st = datetime.strptime(s['start'], '%H:%M').time()
        en = datetime.strptime(s['end'], '%H:%M').time()
        if st <= at_time < en:
            return True
    return False
