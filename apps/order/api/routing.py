from django.urls import re_path

from .consumers import SosIncomingOrdersConsumer

websocket_urlpatterns = [
    re_path(r"ws/order/sos/$", SosIncomingOrdersConsumer.as_asgi()),
]

