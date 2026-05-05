from __future__ import annotations

import json

from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.core.serializers.json import DjangoJSONEncoder


class SosIncomingOrdersConsumer(AsyncWebsocketConsumer):
    """
    Master-side WebSocket for SOS incoming orders.

    Connect:
      ws://<host>/ws/order/sos/?token=<jwt>
    """

    @database_sync_to_async
    def _is_master_user(self, user) -> bool:
        return bool(getattr(user, "master_profiles", None) and user.master_profiles.exists())

    async def connect(self):
        user = self.scope.get("user")
        if not user or not getattr(user, "is_authenticated", False):
            await self.close(code=4001)
            return

        # Must be a master user
        if not await self._is_master_user(user):
            await self.close(code=4003)
            return

        self.user = user
        self.group_name = f"sos_orders_{self.user.id}"
        print(f"[SOS][WS_CONNECT] user_id={self.user.id} group={self.group_name}")

        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

        await self.send(
            text_data=json.dumps(
                {
                    "type": "connection_established",
                    "message": "Connected to SOS incoming orders",
                }
            )
        )

    async def disconnect(self, close_code):
        if getattr(self, "group_name", None):
            await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def sos_order(self, event):
        # event: {"type": "sos_order", "data": {"message": "...", "order": {...}}}
        await self.send(
            text_data=json.dumps(
                {"type": "sos_order", "data": event.get("data")},
                cls=DjangoJSONEncoder,
                ensure_ascii=False,
            )
        )

    async def sos_order_taken(self, event):
        # event: {"type": "sos_order_taken", "order_id": 1, "master_user_id": 2}
        await self.send(
            text_data=json.dumps(
                {
                    "type": "sos_order_taken",
                    "order_id": event.get("order_id"),
                    "master_user_id": event.get("master_user_id"),
                },
                ensure_ascii=False,
            )
        )

