"""
Зачисление на доступный баланс мастера после оплаты заказа клиентом (идемпотентно по заказу).
"""
from __future__ import annotations

from decimal import Decimal

from django.apps import apps


def credit_master_when_order_paid(intent) -> None:
    if not intent:
        return
    from apps.accounts.models import MasterAvailableBalance, MasterOrderEarningCredit

    Order = apps.get_model('order', 'Order')
    orders = Order.objects.filter(sbp_payment_intent_id=intent.pk).select_related('master', 'master__user')
    for order in orders:
        master_user = getattr(getattr(order, 'master', None), 'user', None)
        if not master_user:
            continue
        credit, created = MasterOrderEarningCredit.objects.get_or_create(
            order=order,
            defaults={'master_user': master_user, 'amount': intent.amount},
        )
        if created:
            MasterAvailableBalance.add_amount(master_user, Decimal(str(intent.amount)))
