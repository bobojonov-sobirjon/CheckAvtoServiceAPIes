"""СБП QR для оплаты заказа: та же логика, что POST /api/auth/balance/sbp-qr/."""
from __future__ import annotations

from decimal import Decimal

from django.conf import settings

from apps.accounts.models import SbpPaymentIntent
from apps.accounts.sbp_qr import pay_url_to_qr_png_base64
from apps.accounts.serializers import MIN_SBP_TOPUP_RUB


def _line_amount(master_service_item) -> Decimal:
    pf = master_service_item.price_from or Decimal('0')
    pt = master_service_item.price_to or pf
    if pf == pt:
        return pf
    return (pf + pt) / Decimal('2')


def compute_order_services_total(order) -> Decimal:
    """Сумма по услугам заказа минус скидка заказа (₽)."""
    total = Decimal('0')
    for os in order.order_services.select_related('master_service_item'):
        if os.master_service_item_id:
            total += _line_amount(os.master_service_item)
    discount = order.discount or Decimal('0')
    total -= discount
    if total < 0:
        total = Decimal('0')
    return total.quantize(Decimal('0.01'))


def effective_sbp_amount(raw_total: Decimal) -> Decimal:
    """Минимальная сумма как у balance/sbp-qr (MIN_SBP_TOPUP_RUB)."""
    return max(raw_total, MIN_SBP_TOPUP_RUB)


def create_order_payment_intent(order, *, amount: Decimal) -> tuple[SbpPaymentIntent, str, str]:
    """
    Создаёт SbpPaymentIntent для клиента (order.user), привязывает к заказу, возвращает QR.
    Raises ValueError если нет SBP_QR_PAY_URL.
    """
    pay_url = getattr(settings, 'SBP_QR_PAY_URL', '').strip()
    if not pay_url:
        raise ValueError('SBP_QR_PAY_URL не задан')

    intent = SbpPaymentIntent.objects.create(
        user=order.user,
        amount=amount,
        status=SbpPaymentIntent.STATUS_PENDING,
    )
    qr_b64 = pay_url_to_qr_png_base64(pay_url)
    return intent, pay_url, qr_b64
