"""
Alfa acquiring orders API (non-template): getOrderStatusExtended.

This is needed to check payment status via API without opening bank admin panel.
"""

from __future__ import annotations

import logging
from typing import Any

import requests
from django.conf import settings

logger = logging.getLogger(__name__)


class AlfaOrdersConfigError(RuntimeError):
    pass


def _base() -> str:
    return getattr(settings, "ALFA_PAYMENT_REST_BASE", "").strip().rstrip("/")


def _credentials() -> tuple[str, str]:
    u = getattr(settings, "ALFA_API_USERNAME", "").strip()
    p = getattr(settings, "ALFA_API_PASSWORD", "").strip()
    return u, p


def alfa_orders_configured() -> bool:
    b = _base()
    u, p = _credentials()
    return bool(b and u and p)


def post_order_status_extended(*, order_id: str | None = None, order_number: str | None = None) -> dict[str, Any]:
    """
    Proxy to payment/rest/getOrderStatusExtended.do
    Must provide either order_id or order_number.
    """
    if not alfa_orders_configured():
        raise AlfaOrdersConfigError("ALFA_PAYMENT_REST_BASE / ALFA_API_USERNAME / ALFA_API_PASSWORD не заданы")
    if not (order_id or order_number):
        raise ValueError("Provide order_id or order_number")

    base = _base()
    user, password = _credentials()
    url = f"{base}/getOrderStatusExtended.do"

    payload: dict[str, Any] = {
        "userName": user,
        "password": password,
        "language": "ru",
    }
    if order_id:
        payload["orderId"] = str(order_id).strip()
    if order_number and not order_id:
        payload["orderNumber"] = str(order_number).strip()

    timeout = getattr(settings, "ALFA_HTTP_TIMEOUT", 60)
    try:
        resp = requests.post(
            url,
            data=payload,  # form-url-encoded
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            timeout=timeout,
        )
        resp.raise_for_status()
    except requests.RequestException as e:
        logger.exception("Alfa orders getOrderStatusExtended: %s", e)
        return {"error": True, "httpError": str(e)}

    try:
        return resp.json()
    except ValueError:
        logger.exception("Alfa orders getOrderStatusExtended: invalid JSON")
        return {"error": True, "errorMessage": "Invalid JSON from gateway"}


def register_order(
    *,
    order_number: str,
    amount_kopecks: int,
    description: str,
    return_url: str,
    fail_url: str | None = None,
    session_timeout_secs: int | None = None,
) -> dict[str, Any]:
    """
    payment/rest/register.do → returns {orderId, formUrl} or {errorCode, errorMessage}.
    """
    if not alfa_orders_configured():
        raise AlfaOrdersConfigError("ALFA_PAYMENT_REST_BASE / ALFA_API_USERNAME / ALFA_API_PASSWORD не заданы")
    base = _base()
    user, password = _credentials()
    url = f"{base}/register.do"

    payload: dict[str, Any] = {
        "userName": user,
        "password": password,
        "orderNumber": str(order_number)[:32],
        "amount": int(amount_kopecks),
        "returnUrl": str(return_url),
        "language": "ru",
        "description": str(description)[:512],
        "pageView": "MOBILE",
    }
    if fail_url:
        payload["failUrl"] = str(fail_url)
    if session_timeout_secs is not None:
        payload["sessionTimeoutSecs"] = int(session_timeout_secs)

    timeout = getattr(settings, "ALFA_HTTP_TIMEOUT", 60)
    try:
        resp = requests.post(
            url,
            data=payload,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            timeout=timeout,
        )
        resp.raise_for_status()
    except requests.RequestException as e:
        logger.exception("Alfa orders register.do: %s", e)
        return {"error": True, "httpError": str(e)}

    try:
        return resp.json()
    except ValueError:
        logger.exception("Alfa orders register.do: invalid JSON")
        return {"error": True, "errorMessage": "Invalid JSON from gateway"}


def is_paid_status(gw: dict[str, Any]) -> bool:
    """
    Best-effort paid detection for getOrderStatusExtended response.
    Common values:
    - orderStatus: 2 (paid), 1 (authorized), 0 (created)
    - actionCode: 0 on success
    """
    if not gw or gw.get("error"):
        return False
    action = str(gw.get("actionCode", ""))
    order_status = str(gw.get("orderStatus", ""))
    if action and action not in ("0", "00"):
        return False
    return order_status in ("1", "2")

