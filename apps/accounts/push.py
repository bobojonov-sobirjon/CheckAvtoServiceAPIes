from __future__ import annotations

import os
from functools import lru_cache

from django.conf import settings
import logging

logger = logging.getLogger(__name__)

def _push_dbg(msg: str) -> None:
    """
    Celery/Django logging sometimes gets hijacked; prints are the most reliable
    way to see debug in Windows terminals. Toggle with PUSH_DEBUG_PRINT=1.
    """
    try:
        if (os.getenv("PUSH_DEBUG_PRINT") or "").strip().lower() in {"1", "true", "yes", "on"}:
            print(f"[PUSH_DEBUG] {msg}", flush=True)
    except Exception:
        return


@lru_cache(maxsize=1)
def _firebase_app():
    """
    Lazy init firebase-admin app from .env variables.
    If not configured, returns None.
    """
    try:
        import firebase_admin
        from firebase_admin import credentials
    except Exception:
        return None

    # If already initialized
    try:
        return firebase_admin.get_app()
    except Exception:
        pass

    project_id = (os.getenv('FIREBASE_PROJECT_ID') or '').strip()
    client_email = (os.getenv('FIREBASE_CLIENT_EMAIL') or '').strip()
    private_key = os.getenv('FIREBASE_PRIVATE_KEY') or ''

    if not (project_id and client_email and private_key):
        return None

    cred_info = {
        "type": os.getenv('FIREBASE_TYPE', 'service_account'),
        "project_id": project_id,
        "private_key_id": os.getenv('FIREBASE_PRIVATE_KEY_ID', ''),
        "private_key": private_key.replace('\\n', '\n'),
        "client_email": client_email,
        "client_id": os.getenv('FIREBASE_CLIENT_ID', ''),
        "auth_uri": os.getenv('FIREBASE_AUTH_URI', 'https://accounts.google.com/o/oauth2/auth'),
        "token_uri": os.getenv('FIREBASE_TOKEN_URI', 'https://oauth2.googleapis.com/token'),
        "auth_provider_x509_cert_url": os.getenv('FIREBASE_AUTH_PROVIDER_CERT_URL', 'https://www.googleapis.com/oauth2/v1/certs'),
        "client_x509_cert_url": os.getenv('FIREBASE_CLIENT_CERT_URL', ''),
    }

    try:
        cred = credentials.Certificate(cred_info)
        return firebase_admin.initialize_app(cred)
    except Exception as e:
        logger.exception("FCM init failed")
        _push_dbg(f"init_failed: {type(e).__name__}: {e}")
        return None


def send_push_to_tokens(*, tokens: list[str], title: str, body: str, data: dict[str, str] | None = None) -> dict:
    """
    Send push to raw FCM tokens. Returns delivery summary.
    """
    app = _firebase_app()
    if app is None:
        res = {"ok": False, "error": "firebase_not_configured", "sent": 0, "failed": len(tokens)}
        logger.warning("FCM push skipped: %s", res["error"])
        _push_dbg(f"skip: {res['error']} tokens={len(tokens)} title={title!r}")
        return res

    try:
        from firebase_admin import messaging
    except Exception:
        res = {"ok": False, "error": "firebase_admin_missing", "sent": 0, "failed": len(tokens)}
        logger.warning("FCM push skipped: %s", res["error"])
        _push_dbg(f"skip: {res['error']} tokens={len(tokens)} title={title!r}")
        return res

    tokens = [t for t in (tokens or []) if (t or '').strip()]
    if not tokens:
        _push_dbg(f"no_active_tokens title={title!r}")
        return {"ok": True, "sent": 0, "failed": 0}

    # Prefer multicast API when available (firebase-admin version dependent).
    msg = messaging.MulticastMessage(
        notification=messaging.Notification(title=title, body=body),
        data=data or {},
        tokens=tokens,
    )
    try:
        if hasattr(messaging, "send_multicast"):
            resp = messaging.send_multicast(msg, app=app)
            res = {"ok": True, "sent": resp.success_count, "failed": resp.failure_count}
            if res["failed"]:
                logger.warning("FCM multicast: sent=%s failed=%s", res["sent"], res["failed"])
            _push_dbg(f"multicast sent={res['sent']} failed={res['failed']} title={title!r}")
            return res

        # Older firebase-admin: use send_each_for_multicast if present.
        if hasattr(messaging, "send_each_for_multicast"):
            resp = messaging.send_each_for_multicast(msg, app=app)
            res = {"ok": True, "sent": resp.success_count, "failed": resp.failure_count}
            if res["failed"]:
                logger.warning("FCM multicast(each): sent=%s failed=%s", res["sent"], res["failed"])
            _push_dbg(f"multicast(each) sent={res['sent']} failed={res['failed']} title={title!r}")
            return res

        # Very old firebase-admin: fallback to per-token sends.
        sent = 0
        failed = 0
        for t in tokens:
            one = messaging.Message(
                notification=messaging.Notification(title=title, body=body),
                data=data or {},
                token=t,
            )
            try:
                messaging.send(one, app=app)
                sent += 1
            except Exception:
                failed += 1
        res = {"ok": True, "sent": sent, "failed": failed}
        if failed:
            logger.warning("FCM per-token: sent=%s failed=%s", sent, failed)
        _push_dbg(f"per_token sent={sent} failed={failed} title={title!r}")
        return res
    except Exception as e:
        logger.exception("FCM send_multicast failed")
        res = {"ok": False, "error": f"send_failed:{type(e).__name__}", "sent": 0, "failed": len(tokens)}
        _push_dbg(f"send_failed: {type(e).__name__}: {e}")
        return res


def send_push_to_user(*, user, title: str, body: str, data: dict[str, str] | None = None) -> dict:
    """
    Send push to all active devices of a user.
    """
    from .models import UserDevice

    qs = UserDevice.objects.filter(user=user, is_active=True).values_list('device_token', flat=True)
    _push_dbg(f"user_id={getattr(user, 'id', None)} active_devices={qs.count()} title={title!r}")
    return send_push_to_tokens(tokens=list(qs), title=title, body=body, data=data)

