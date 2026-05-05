from __future__ import annotations

from celery import shared_task
from django.conf import settings
from django.utils import timezone
import logging

from apps.accounts.alfa_orders import post_order_status_extended, is_paid_status
from apps.accounts.models import PaymentTransaction, PaymentStatus, SbpPaymentIntent

logger = logging.getLogger(__name__)

@shared_task(name='apps.accounts.tasks.check_pending_payments')
def check_pending_payments(limit: int = 50) -> dict:
    """
    Poll Alfa gateway for pending payments. Runs frequently (e.g. every 5s).
    When paid -> mark transaction paid and complete intent (tops up balance).
    """
    now = timezone.now()
    expire_minutes = int(getattr(settings, 'PAYMENT_PENDING_EXPIRE_MINUTES', 15))
    cutoff = now - timezone.timedelta(minutes=expire_minutes)

    # 1) Expire stale pending tx
    stale_qs = PaymentTransaction.objects.filter(status=PaymentStatus.PENDING, created_at__lt=cutoff).order_by('created_at')[: max(1, int(limit))]
    expired = 0
    for tx in stale_qs:
        tx.status = PaymentStatus.FAILED
        tx.gateway_last_response = {
            "error": False,
            "expired": True,
            "reason": f"pending_timeout_{expire_minutes}m",
        }
        tx.last_checked_at = now
        tx.save(update_fields=['status', 'gateway_last_response', 'last_checked_at', 'updated_at'])

        # Mark intent expired if still pending
        try:
            if tx.intent and tx.intent.status == SbpPaymentIntent.STATUS_PENDING:
                tx.intent.status = SbpPaymentIntent.STATUS_EXPIRED
                tx.intent.save(update_fields=['status'])
        except Exception:
            pass

        # Push notifications about expiration
        try:
            from apps.accounts.push import send_push_to_user
            from apps.accounts.push import _push_dbg
            if tx.kind == 'master_topup':
                if tx.initiated_by_id:
                    res = send_push_to_user(
                        user=tx.initiated_by,
                        title='Оплата не завершена',
                        body='Срок оплаты истёк. Платёж отменён. При необходимости создайте оплату заново.',
                        data={'type': 'payment_expired', 'tx_id': str(tx.id)},
                    )
                    _push_dbg(f"tx_expired push owner tx_id={tx.id} res={res}")
                    if res.get("ok") is False:
                        logger.warning("Push failed (owner expired): %s", res)
                if tx.beneficiary_id:
                    res = send_push_to_user(
                        user=tx.beneficiary,
                        title='Платёж отменён',
                        body='Срок оплаты истёк. Пополнение баланса не выполнено.',
                        data={'type': 'payment_expired', 'tx_id': str(tx.id)},
                    )
                    _push_dbg(f"tx_expired push beneficiary tx_id={tx.id} res={res}")
                    if res.get("ok") is False:
                        logger.warning("Push failed (beneficiary expired): %s", res)
            else:
                # Order payment: notify order owner (initiated_by/beneficiary are order.user)
                if tx.beneficiary_id:
                    res = send_push_to_user(
                        user=tx.beneficiary,
                        title='Оплата не завершена',
                        body='Срок оплаты истёк. Платёж отменён. Вы можете запросить оплату повторно.',
                        data={'type': 'payment_expired', 'tx_id': str(tx.id)},
                    )
                    _push_dbg(f"tx_expired push order tx_id={tx.id} res={res}")
                    if res.get("ok") is False:
                        logger.warning("Push failed (order expired): %s", res)
        except Exception:
            pass

        expired += 1

    # 2) Poll active pending tx
    qs = PaymentTransaction.objects.filter(status=PaymentStatus.PENDING).order_by('created_at')[: max(1, int(limit))]

    checked = 0
    marked_paid = 0
    failed = 0

    for tx in qs:
        checked += 1
        try:
            gw = post_order_status_extended(order_id=tx.alfa_order_id or None, order_number=tx.alfa_order_number or None)
        except Exception as e:
            tx.gateway_last_response = {"error": True, "errorMessage": str(e)}
            tx.last_checked_at = now
            tx.save(update_fields=['gateway_last_response', 'last_checked_at', 'updated_at'])
            failed += 1
            continue

        tx.gateway_last_response = gw
        tx.last_checked_at = now
        tx.save(update_fields=['gateway_last_response', 'last_checked_at', 'updated_at'])

        if gw.get('error'):
            failed += 1
            continue

        paid = is_paid_status(gw)
        if not paid:
            continue

        # Mark paid + complete intent (idempotent)
        code, intent = SbpPaymentIntent.complete_pending(
            tx.intent_id,
            bank_reference=tx.alfa_order_id or tx.alfa_order_number or '',
            expected_amount=tx.amount,
        )

        if code in ('ok', 'already_completed'):
            tx.status = PaymentStatus.PAID
            tx.save(update_fields=['status', 'updated_at'])
            marked_paid += 1

            # If this intent is bound to an order, update order.payment_status as before.
            try:
                from apps.accounts.views import _sync_order_payment_paid
                _sync_order_payment_paid(intent)
            except Exception:
                pass

            # Push notifications
            try:
                from apps.accounts.push import send_push_to_user
                from apps.accounts.push import _push_dbg
                # Owner/master-topup: notify initiator + master user
                if tx.kind == 'master_topup':
                    if tx.initiated_by_id:
                        res = send_push_to_user(
                            user=tx.initiated_by,
                            title='Оплата прошла успешно',
                            body='Пополнение баланса выполнено. Средства зачислены мастеру.',
                            data={'type': 'master_balance_topup_paid', 'tx_id': str(tx.id)},
                        )
                        _push_dbg(f"tx_paid push owner tx_id={tx.id} res={res}")
                        if res.get("ok") is False:
                            logger.warning("Push failed (owner paid): %s", res)
                    if tx.beneficiary_id:
                        res = send_push_to_user(
                            user=tx.beneficiary,
                            title='Баланс пополнен',
                            body=f'Баланс пополнен на {tx.amount} ₽.',
                            data={'type': 'master_balance_topup_received', 'tx_id': str(tx.id)},
                        )
                        _push_dbg(f"tx_paid push beneficiary tx_id={tx.id} res={res}")
                        if res.get("ok") is False:
                            logger.warning("Push failed (beneficiary paid): %s", res)
                else:
                    # Order payment: _sync_order_payment_paid already pushes to user+master
                    pass
            except Exception:
                pass

    return {"expired": expired, "checked": checked, "marked_paid": marked_paid, "failed": failed}

