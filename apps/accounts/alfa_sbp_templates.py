"""
Прокси к REST Альфа-Банк: статические шаблоны СБП QR.
createTemplate / updateTemplate — JSON (application/json).
getTemplateDetails — по требованию поддержки: application/x-www-form-urlencoded.
"""
from __future__ import annotations

import logging
from typing import Any

import requests
from django.conf import settings

logger = logging.getLogger(__name__)


class AlfaSbpTemplatesConfigError(RuntimeError):
    pass


def _base() -> str:
    return getattr(settings, 'ALFA_PAYMENT_REST_BASE', '').strip().rstrip('/')


def _credentials_default() -> tuple[str, str]:
    u = getattr(settings, 'ALFA_API_USERNAME', '').strip()
    p = getattr(settings, 'ALFA_API_PASSWORD', '').strip()
    return u, p


def _credentials_for_endpoint(endpoint: str) -> tuple[str, str]:
    if endpoint == 'getTemplateDetails.do':
        u = getattr(settings, 'ALFA_TEMPLATES_DETAILS_USERNAME', '').strip()
        p = getattr(settings, 'ALFA_TEMPLATES_DETAILS_PASSWORD', '').strip()
        if u and p:
            return u, p
    return _credentials_default()


def alfa_sbp_gateway_ready(endpoint: str) -> bool:
    """База + логин/пароль для данного метода (для details можно отдельная пара)."""
    if not _base():
        return False
    u, p = _credentials_for_endpoint(endpoint)
    return bool(u and p)


def alfa_sbp_templates_configured() -> bool:
    """Только основной API-логин (create/update)."""
    b, (u, p) = _base(), _credentials_default()
    return bool(b and u and p)


def alfa_template_gateway_failed(data: dict[str, Any]) -> bool:
    """Ошибка шлюза: сеть, или errorCode не 0 (в т.ч. «username не задан»)."""
    if not data or data.get('error'):
        return True
    if 'errorCode' not in data:
        return False
    code = data.get('errorCode')
    return str(code) not in ('0', '00', 0)


def post_template_json(endpoint: str, body: dict[str, Any]) -> dict[str, Any]:
    """
    endpoint: 'createTemplate.do' | 'getTemplateDetails.do' | 'updateTemplate.do'
    body: поля без логина.
    """
    if not alfa_sbp_gateway_ready(endpoint):
        raise AlfaSbpTemplatesConfigError('ALFA_PAYMENT_REST_BASE и креды для этого метода не заданы')

    base = _base()
    user, password = _credentials_for_endpoint(endpoint)
    url = f'{base}/templates/{endpoint}'

    if endpoint == 'getTemplateDetails.do':
        # Form-urlencoded (как просила поддержка): классическая пара userName/password,
        # без дублирующего username — часть шлюзов на это отвечает errorCode 5.
        payload = {
            **body,
            'userName': user,
            'password': password,
            'language': 'ru',
        }
    else:
        payload = {**body, 'username': user, 'password': password}

    merchant = getattr(settings, 'ALFA_MERCHANT', '').strip()
    # merchant на чтение деталей шаблона часто не нужен и может ужесточать проверку прав
    if merchant and endpoint != 'getTemplateDetails.do':
        payload['merchant'] = merchant

    timeout = getattr(settings, 'ALFA_HTTP_TIMEOUT', 60)

    # getTemplateDetails: поддержка просит form-urlencoded, не JSON
    if endpoint == 'getTemplateDetails.do':
        form_data = {k: ('' if v is None else str(v)) for k, v in payload.items()}
        try:
            resp = requests.post(
                url,
                data=form_data,
                headers={'Content-Type': 'application/x-www-form-urlencoded'},
                timeout=timeout,
            )
            resp.raise_for_status()
        except requests.RequestException as e:
            logger.exception('Alfa templates %s: %s', endpoint, e)
            return {'error': True, 'httpError': str(e), 'errorCode': '-1'}
        try:
            return resp.json()
        except ValueError:
            logger.exception('Alfa templates %s: invalid JSON', endpoint)
            return {'error': True, 'errorCode': '-2', 'errorMessage': 'Invalid JSON from gateway'}

    try:
        resp = requests.post(
            url,
            json=payload,
            headers={'Content-Type': 'application/json'},
            timeout=timeout,
        )
        resp.raise_for_status()
    except requests.RequestException as e:
        logger.exception('Alfa templates %s: %s', endpoint, e)
        return {'error': True, 'httpError': str(e), 'errorCode': '-1'}

    try:
        return resp.json()
    except ValueError:
        logger.exception('Alfa templates %s: invalid JSON', endpoint)
        return {'error': True, 'errorCode': '-2', 'errorMessage': 'Invalid JSON from gateway'}
