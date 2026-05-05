"""
Order lifecycle: client penalties on cancel, master post-accept cancel logging,
schedule horizon limits, completion PIN, workflow transitions.
"""
from __future__ import annotations

import secrets
from datetime import date, datetime, time as dt_time, timedelta
from decimal import Decimal

from django.conf import settings
from django.utils import timezone

from .models import Order, OrderStatus, MasterOrderCancellation


def _d(v) -> Decimal:
    return Decimal(str(v))


def master_cancellations_this_month_count(master_user_id: int) -> int:
    now = timezone.now()
    start = date(now.year, now.month, 1)
    start_dt = timezone.make_aware(datetime.combine(start, dt_time.min))
    return MasterOrderCancellation.objects.filter(
        master_user_id=master_user_id,
        created_at__gte=start_dt,
    ).count()


def master_schedule_max_extra_days(master_user_id: int) -> int | None:
    """
    None = no extra restriction (beyond common sense).
    int = max days from today that booking date may be (inclusive offset from today).
    """
    n = master_cancellations_this_month_count(master_user_id)
    if n <= 3:
        return None
    if n == 4:
        return 10
    if n == 5:
        return 5
    return 0  # only today


def assert_booking_date_allowed_for_master(*, master_user_id: int, booking_date: date) -> tuple[bool, str | None]:
    extra = master_schedule_max_extra_days(master_user_id)
    if extra is None:
        return True, None
    today = timezone.localdate()
    if booking_date < today:
        return False, "Дата не может быть в прошлом"
    latest = today + timedelta(days=extra)
    if booking_date > latest:
        return (
            False,
            f"Из-за частых отмен мастером в этом месяце доступна запись только до {latest.isoformat()}",
        )
    return True, None


def order_amount_for_penalty(order: Order) -> Decimal:
    from .sbp_payment import compute_order_services_total

    try:
        total = compute_order_services_total(order)
    except Exception:
        total = Decimal("0")
    return _d(total) if total and total > 0 else Decimal("0")


def client_cancel_penalty_percent(order: Order) -> tuple[bool, Decimal, str | None]:
    """
    Returns (allowed, percent, error_message).
    percent is 0–100 of order services total (0 if no services).
    """
    now = timezone.now()
    st = order.status

    if st in (OrderStatus.COMPLETED, OrderStatus.CANCELLED, OrderStatus.REJECTED):
        return False, Decimal("0"), "Заказ уже закрыт"

    if st == OrderStatus.IN_PROGRESS:
        return False, Decimal("0"), "Нельзя отменить заказ в работе"

    grace_min = int(getattr(settings, "CLIENT_CANCEL_ACCEPTED_GRACE_MINUTES", 10))
    pct_after_grace = _d(getattr(settings, "CLIENT_CANCEL_ACCEPTED_PENALTY_PERCENT", 10))
    pct_on_the_way = _d(getattr(settings, "CLIENT_CANCEL_ON_THE_WAY_PENALTY_PERCENT", 15))
    pct_arrived = _d(getattr(settings, "CLIENT_CANCEL_ARRIVED_PENALTY_PERCENT", 25))
    on_the_way_free_hours = int(getattr(settings, "CLIENT_CANCEL_ON_THE_WAY_FREE_HOURS", 2))

    if st == OrderStatus.PENDING:
        return True, Decimal("0"), None

    if st == OrderStatus.ACCEPTED:
        if not order.accepted_at:
            return True, pct_after_grace, None
        if now <= order.accepted_at + timedelta(minutes=grace_min):
            return True, Decimal("0"), None
        return True, pct_after_grace, None

    if st == OrderStatus.ON_THE_WAY:
        if order.on_the_way_started_at:
            if now >= order.on_the_way_started_at + timedelta(hours=on_the_way_free_hours):
                return True, Decimal("0"), None
        return True, pct_on_the_way, None

    if st == OrderStatus.ARRIVED:
        return True, pct_arrived, None

    return False, Decimal("0"), "Отмена в этом статусе недоступна"


def generate_completion_pin() -> str:
    return f"{secrets.randbelow(9000) + 1000:04d}"


def workflow_transition_allowed(order: Order, new_status: str) -> tuple[bool, str | None]:
    cur = order.status
    allowed = {
        OrderStatus.ACCEPTED: {OrderStatus.ON_THE_WAY},
        OrderStatus.ON_THE_WAY: {OrderStatus.ARRIVED},
        OrderStatus.ARRIVED: {OrderStatus.IN_PROGRESS},
    }
    if new_status not in (OrderStatus.ON_THE_WAY, OrderStatus.ARRIVED, OrderStatus.IN_PROGRESS):
        return False, "Недопустимый статус"
    nxt = allowed.get(cur, set())
    if new_status not in nxt:
        return False, f"Переход {cur} → {new_status} запрещён"
    return True, None
