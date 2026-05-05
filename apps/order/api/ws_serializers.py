from __future__ import annotations

from typing import Any

from apps.order.models import Order
from apps.order.serializers import OrderSerializer


def order_to_ws_dict(order: Order) -> dict[str, Any]:
    """
    Minimal, request-independent payload for WebSocket.
    (DRF serializers in this project assume `context['request']` exists.)
    """
    return {
        "id": order.id,
        "order_type": order.order_type,
        "status": order.status,
        "priority": order.priority,
        "text": order.text,
        "location": order.location,
        "latitude": float(order.latitude) if order.latitude is not None else None,
        "longitude": float(order.longitude) if order.longitude is not None else None,
        "master_response_deadline": order.master_response_deadline.isoformat() if order.master_response_deadline else None,
        "created_at": order.created_at.isoformat() if order.created_at else None,
        "room_id": order.chat_room_id,
        "user_id": order.user_id,
    }


def order_to_ws_response(order: Order, *, message: str | None = None) -> dict[str, Any]:
    """
    WebSocket-friendly payload that matches HTTP response `order` shape
    as close as possible (uses OrderSerializer).
    """
    data = OrderSerializer(order, context={"request": None}).data
    return {
        "order": data,
    }

