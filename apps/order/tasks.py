from __future__ import annotations

from celery import shared_task
from django.conf import settings
from django.utils import timezone

from .models import Order, OrderStatus


@shared_task(name='apps.order.tasks.expire_stale_master_offers')
def expire_stale_master_offers() -> int:
    """
    Beat task: every minute reject orders where master_response_deadline passed
    and still pending (master didn't accept).
    """
    now = timezone.now()
    qs = Order.objects.filter(
        status=OrderStatus.PENDING,
        master_response_deadline__isnull=False,
        master_response_deadline__lt=now,
    ).select_related('master')

    count = 0
    for order in qs:
        # Auto reject
        order.status = OrderStatus.REJECTED
        order.master = None
        order.master_response_deadline = None
        order.save(update_fields=['status', 'master', 'master_response_deadline', 'updated_at'])

        # push notifications
        try:
            from apps.accounts.push import send_push_to_user
            send_push_to_user(
                user=order.user,
                title='Заказ отклонён автоматически',
                body=f'Заказ №{order.id}: мастер не ответил вовремя. Заказ отклонён, исполнитель снят.',
                data={'type': 'order_offer_expired', 'order_id': str(order.id)},
            )
        except Exception:
            pass
        count += 1
    return count


@shared_task(name='apps.order.tasks.offer_deadline_reminder')
def offer_deadline_reminder(order_id: int) -> bool:
    """
    ETA task: reminder before deadline.
    """
    try:
        order = Order.objects.select_related('master').get(id=order_id)
    except Order.DoesNotExist:
        return False

    if order.status != OrderStatus.PENDING:
        return True
    if not order.master_response_deadline:
        return True
    if not order.master or not getattr(order.master, 'user', None):
        return True

    try:
        from apps.accounts.push import send_push_to_user
        minutes = int(getattr(settings, 'OFFER_REMINDER_MINUTES_BEFORE', 2))
        send_push_to_user(
            user=order.master.user,
            title='Напоминание по заказу',
            body=f'Заказ №{order.id}: осталось ~{minutes} мин. Примите заказ или отклоните заявку.',
            data={'type': 'order_offer_reminder', 'order_id': str(order.id)},
        )
    except Exception:
        pass
    return True


@shared_task(name='apps.order.tasks.expire_master_offer_for_order')
def expire_master_offer_for_order(order_id: int) -> bool:
    """
    ETA task: expire single order at exact deadline time.
    Beat task also covers this, this is extra safety.
    """
    try:
        order = Order.objects.select_related('master').get(id=order_id)
    except Order.DoesNotExist:
        return False

    if order.status != OrderStatus.PENDING:
        return True
    if not order.master_response_deadline:
        return True
    if timezone.now() < order.master_response_deadline:
        return True

    order.status = OrderStatus.REJECTED
    order.master = None
    order.master_response_deadline = None
    order.save(update_fields=['status', 'master', 'master_response_deadline', 'updated_at'])

    try:
        from apps.accounts.push import send_push_to_user
        send_push_to_user(
            user=order.user,
            title='Заказ отклонён автоматически',
            body=f'Заказ №{order.id}: мастер не ответил вовремя. Заказ отклонён.',
            data={'type': 'order_offer_expired', 'order_id': str(order.id)},
        )
    except Exception:
        pass
    return True


def schedule_offer_deadline_tasks(*, order_id: int, deadline) -> None:
    """
    Helper: schedule reminder + expire tasks.
    """
    try:
        minutes_before = int(getattr(settings, 'OFFER_REMINDER_MINUTES_BEFORE', 2))
        reminder_eta = deadline - timezone.timedelta(minutes=minutes_before)
        if reminder_eta > timezone.now():
            offer_deadline_reminder.apply_async(args=[order_id], eta=reminder_eta)
    except Exception:
        pass

    try:
        if deadline > timezone.now():
            expire_master_offer_for_order.apply_async(args=[order_id], eta=deadline)
    except Exception:
        pass

