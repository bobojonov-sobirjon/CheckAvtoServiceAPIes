from rest_framework import status, filters
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.pagination import PageNumberPagination
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Q
from django.contrib.auth import get_user_model
import uuid

from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiExample
from drf_spectacular.types import OpenApiTypes

from decimal import Decimal, ROUND_HALF_UP

from .models import (
    Order,
    OrderStatus,
    OrderType,
    OrderPaymentStatus,
    Rating,
    OrderService,
    Review,
    ReviewTag,
    MasterCancelReason,
    MasterOrderCancellation,
    OrderWorkCompletionImage,
)
from .workflow import (
    assert_booking_date_allowed_for_master,
    client_cancel_penalty_percent,
    generate_completion_pin,
    order_amount_for_penalty,
    workflow_transition_allowed,
)
from .serializers import (
    OrderSerializer, OrderCreateSerializer, OrderUpdateSerializer,
    AddServicesToOrderSerializer, OrderServiceSerializer, AddMastersToOrderSerializer,
    ReviewSerializer, ReviewCreateSerializer
)
from .permissions import IsOrderOwnerOrMaster, IsOrderOwner, IsMaster
from .sbp_payment import compute_order_services_total, effective_sbp_amount, create_order_payment_intent
from apps.accounts.alfa_orders import register_order
from apps.master.models import Master
from apps.master.serializers import MasterSerializer
from apps.accounts.models import UserBalance, SbpPaymentIntent
from apps.accounts.models import PaymentTransaction, PaymentKind, PaymentStatus
from apps.accounts.push import send_push_to_user
from apps.chat.models import ChatRoom
from django.utils import timezone
from django.conf import settings as dj_settings
from .tasks import schedule_offer_deadline_tasks
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from math import radians, sin, cos, sqrt, atan2

from apps.order.api.ws_serializers import order_to_ws_dict, order_to_ws_response

User = get_user_model()


def _safe_push(user, *, title: str, body: str, data: dict[str, str] | None = None) -> None:
    """
    Best-effort push. Never breaks API flow.
    """
    try:
        send_push_to_user(user=user, title=title, body=body, data=data)
    except Exception:
        return


class OrderPagination(PageNumberPagination):
    """Пагинация для заказов"""
    page_size = 10
    page_size_query_param = 'page_size'
    max_page_size = 100


class ScheduledOrderCreateView(APIView):
    """Создание запланированного заказа (Order by Date)"""
    permission_classes = [IsAuthenticated]
    
    @extend_schema(
        summary="Driver: создать запланированный заказ (Scheduled)",
        description="""
# 📅 Запланированный заказ (Order by Date)

Этот endpoint используется для создания **запланированного заказа**, когда клиент:
- Заранее выбирает мастера/мастерскую
- Выбирает конкретную дату визита
- Выбирает временной слот (например: 10:00-11:00)
- Указывает услуги, которые нужны

## 🎯 Когда использовать этот endpoint?

✅ Клиент планирует **плановое ТО** (замена масла, шиномонтаж, диагностика)
✅ Клиент хочет **записаться на конкретное время**
✅ Клиент **выбрал мастерскую** из списка

❌ НЕ используйте для **экстренных случаев** (используйте `/api/order/sos/`)

## 📋 Обязательные поля:

### Основные:
- **order_type**: всегда "scheduled"
- **text**: описание услуги (например: "Замена масла и фильтров")
- **car_list**: список ID машин клиента [1, 2]
- **category_list**: список ID категорий услуг [1, 2]

### Выбор мастера:
- **master_id**: ID выбранной мастерской/мастера

### Дата и время:
- **scheduled_date**: дата визита (формат: YYYY-MM-DD, например: 2026-01-30)
- **scheduled_time_start**: время начала (формат: HH:MM, например: 14:00)
- **scheduled_time_end**: время окончания (формат: HH:MM, например: 15:00)

### Местоположение:
- **location**: адрес мастерской (строка)
- **latitude**: широта мастерской (от -90 до 90)
- **longitude**: долгота мастерской (от -180 до 180)

## ⚠️ Важные проверки:

1. **Дата не может быть в прошлом** - система проверит, что дата визита >= сегодня
2. **Время начала < времени окончания** - система проверит логику времени
3. **Расстояние до мастера <= 50 км** - система проверит, что клиент не слишком далеко от мастера
4. **Временной слот должен быть свободен** - мастер не должен быть занят в это время

## 📝 Примеры использования:

### Пример 1: Замена масла
```json
{
  "order_type": "scheduled",
  "master_id": 5,
  "scheduled_date": "2026-01-30",
  "scheduled_time_start": "14:00",
  "scheduled_time_end": "15:00",
  "text": "Замена масла и масляного фильтра",
  "location": "СТО 'Автосервис', ул. Навои, д. 15",
  "latitude": 41.3111,
  "longitude": 69.2797,
  "car_list": [2],
  "category_list": [1]
}
```

### Пример 2: Шиномонтаж
```json
{
  "order_type": "scheduled",
  "master_id": 8,
  "scheduled_date": "2026-02-01",
  "scheduled_time_start": "10:00",
  "scheduled_time_end": "11:00",
  "text": "Замена резины на летнюю",
  "location": "Шиномонтаж 'Колесо', пр. Амира Темура, 45",
  "latitude": 41.3150,
  "longitude": 69.2800,
  "car_list": [3],
  "category_list": [2, 5]
}
```

## 🎯 Workflow:

1. Клиент выбирает мастера в приложении
2. Клиент выбирает дату (календарь)
3. Клиент выбирает свободный временной слот
4. Клиент заполняет описание и отправляет заказ
5. ✅ Мастер получает уведомление о новом заказе
6. Мастер подтверждает или отклоняет заказ
        """,
        tags=['Orders (Driver) · SOS & scheduled'],
        request={
            'application/json': {
                'type': 'object',
                'required': ['order_type', 'master_id', 'scheduled_date', 'scheduled_time_start', 'scheduled_time_end', 'text', 'location', 'latitude', 'longitude', 'car_list', 'category_list'],
                'properties': {
                    'order_type': {'type': 'string', 'enum': ['scheduled'], 'description': 'Тип заказа (всегда "scheduled")', 'example': 'scheduled'},
                    'master_id': {'type': 'integer', 'description': 'ID мастера/мастерской (обязательно)', 'example': 5},
                    'scheduled_date': {'type': 'string', 'format': 'date', 'description': 'Дата визита (YYYY-MM-DD)', 'example': '2026-01-30'},
                    'scheduled_time_start': {'type': 'string', 'format': 'time', 'description': 'Время начала (HH:MM)', 'example': '14:00'},
                    'scheduled_time_end': {'type': 'string', 'format': 'time', 'description': 'Время окончания (HH:MM)', 'example': '15:00'},
                    'text': {'type': 'string', 'description': 'Описание услуги', 'example': 'Замена масла и масляного фильтра'},
                    'location': {'type': 'string', 'description': 'Адрес мастерской', 'example': 'СТО Автосервис, ул. Навои, д. 15'},
                    'latitude': {'type': 'number', 'description': 'Широта мастерской', 'example': 41.3111},
                    'longitude': {'type': 'number', 'description': 'Долгота мастерской', 'example': 69.2797},
                    'car_list': {'type': 'array', 'items': {'type': 'integer'}, 'description': 'Список ID машин', 'example': [2]},
                    'category_list': {'type': 'array', 'items': {'type': 'integer'}, 'description': 'Список ID категорий услуг', 'example': [1]}
                }
            }
        },
        responses={
            201: {
                'description': 'Заказ успешно создан',
                'content': {
                    'application/json': {
                        'example': {
                            'message': 'Ваш заказ успешно создан и отправлен мастеру',
                            'order': {
                                'id': 123,
                                'order_type': 'scheduled',
                                'status': 'pending',
                                'scheduled_date': '2026-01-30',
                                'scheduled_time_start': '14:00',
                                'scheduled_time_end': '15:00',
                                'master': {'id': 5, 'name': 'СТО Автосервис'},
                                'text': 'Замена масла и масляного фильтра'
                            }
                        }
                    }
                }
            },
            400: {
                'description': 'Ошибка валидации',
                'content': {
                    'application/json': {
                        'examples': {
                            'missing_master': {
                                'summary': 'Не указан мастер',
                                'value': {'master_id': ['Для запланированного заказа необходимо указать мастера']}
                            },
                            'missing_date': {
                                'summary': 'Не указана дата',
                                'value': {'scheduled_date': ['Для запланированного заказа необходимо указать дату визита']}
                            },
                            'past_date': {
                                'summary': 'Дата в прошлом',
                                'value': {'scheduled_date': ['Дата визита не может быть в прошлом']}
                            },
                            'distance_error': {
                                'summary': 'Мастер слишком далеко',
                                'value': {'master_id': ['Выбранный мастер находится слишком далеко (150.5 км). Максимальное расстояние: 50 км.']}
                            }
                        }
                    }
                }
            },
            401: {'description': 'Не авторизован'}
        }
    )
    def post(self, request):
        """Создать запланированный заказ"""
        # Принудительно устанавливаем order_type
        data = request.data.copy()
        data['order_type'] = OrderType.SCHEDULED
        
        serializer = OrderCreateSerializer(data=data)
        if serializer.is_valid():
            order = serializer.save(user=request.user)
            # offer deadline
            try:
                minutes = int(getattr(dj_settings, 'MASTER_OFFER_RESPONSE_MINUTES', 15))
                deadline = timezone.now() + timezone.timedelta(minutes=minutes)
                order.master_response_deadline = deadline
                order.save(update_fields=['master_response_deadline', 'updated_at'])
                schedule_offer_deadline_tasks(order_id=order.id, deadline=deadline)
            except Exception:
                pass
            # push -> выбранный мастер
            if order.master and getattr(order.master, 'user', None):
                _safe_push(
                    order.master.user,
                    title='Новый заказ',
                    body=f'Заказ №{order.id}: требуется ваш ответ. Примите или отклоните в течение ограниченного времени.',
                    data={'type': 'order_created', 'order_id': str(order.id), 'order_type': str(order.order_type)},
                )
            order_serializer = OrderSerializer(order)
            return Response({
                'message': 'Ваш заказ успешно создан и отправлен мастеру',
                'order': order_serializer.data
            }, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class SOSOrderCreateView(APIView):
    """Создание SOS заказа (экстренная помощь)"""
    permission_classes = [IsAuthenticated]
    
    @extend_schema(
        summary="Driver: создать SOS заказ (экстренная помощь)",
        description="""
# 🚨 SOS заказ (Экстренная помощь)

Этот endpoint используется для создания **экстренного заказа**, когда клиент:
- Находится в **аварийной ситуации** (машина сломалась, колесо пробито и т.д.)
- Нужна **немедленная помощь**
- Отправляет свою **текущую GPS-локацию**
- Система автоматически находит **ближайших свободных мастеров** в радиусе

## 🎯 Когда использовать этот endpoint?

✅ Машина **сломалась на дороге**
✅ **Пробито колесо** посреди трассы
✅ **Не заводится двигатель** на парковке
✅ Любая **экстренная ситуация**, требующая немедленной помощи

❌ НЕ используйте для **плановых работ** (используйте `/api/order/scheduled/`)

## 📋 Обязательные поля:

### Основные:
- **order_type**: всегда "sos"
- **text**: описание проблемы (например: "Пробито колесо, не могу ехать дальше")
- **priority**: приоритет заказа - "low" (низкий) или "high" (высокий)
- **car_list**: список ID машин клиента [1, 2]
- **category_list**: список ID категорий проблем [1, 2]

### Текущее местоположение (GPS):
- **location**: описание текущего места (например: "Трасса М39, около заправки Shell")
- **latitude**: текущая широта клиента (от -90 до 90)
- **longitude**: текущая долгота клиента (от -180 до 180)

## ⚠️ Важные проверки:

1. **Приоритет устанавливается клиентом** - клиент выбирает "Низкий" или "Высокий" приоритет
2. **Мастер выбирается системой** — сервер рассылает заказ ближайшим подходящим мастерам (по радиусу и категориям/услугам)
3. **Расстояние до мастера <= 50 км** - система проверит, что мастер находится в пределах радиуса от клиента
4. **Уведомление мастерам** - всем подходящим мастерам отправляется push/WS offer

## 📝 Примеры использования:

### Пример 1: Пробито колесо на трассе (высокий приоритет)
```json
{
  "order_type": "sos",
  "priority": "high",
  "text": "Пробито переднее правое колесо на трассе. Нужна срочная замена.",
  "location": "Трасса M39, км 45, около заправки Shell",
  "latitude": 41.2548,
  "longitude": 69.2107,
  "car_list": [2],
  "category_list": [1]
}
```

### Пример 2: Не заводится машина (низкий приоритет)
```json
{
  "order_type": "sos",
  "priority": "low",
  "text": "Машина не заводится, аккумулятор сел. Нужна помощь с прикуриванием.",
  "location": "Торговый центр Mega Planet, подземная парковка -1 этаж",
  "latitude": 41.3250,
  "longitude": 69.2890,
  "car_list": [3],
  "category_list": [4]
}
```


## 🎯 Workflow:

1. Клиент нажимает кнопку "SOS" в приложении
2. Приложение автоматически получает GPS-координаты
3. Клиент описывает проблему и выбирает приоритет
4. ✅ Система рассылает SOS ближайшим подходящим мастерам
5. Первый мастер, который примет заказ, становится исполнителем
6. Клиент видит информацию о мастере и может с ним связаться
        """,
        tags=['Orders (Driver) · SOS & scheduled'],
        request={
            'application/json': {
                'type': 'object',
                'required': ['order_type', 'priority', 'text', 'location', 'latitude', 'longitude', 'car_list', 'category_list'],
                'properties': {
                    'order_type': {'type': 'string', 'enum': ['sos'], 'description': 'Тип заказа (всегда "sos")', 'example': 'sos'},
                    'priority': {'type': 'string', 'enum': ['low', 'high'], 'description': 'Приоритет заказа: low (низкий) или high (высокий)', 'example': 'high'},
                    'text': {'type': 'string', 'description': 'Описание проблемы', 'example': 'Пробито переднее правое колесо на трассе'},
                    'location': {'type': 'string', 'description': 'Описание текущего места', 'example': 'Трасса M39, км 45, около заправки Shell'},
                    'latitude': {'type': 'number', 'description': 'Текущая широта (GPS)', 'example': 41.2548},
                    'longitude': {'type': 'number', 'description': 'Текущая долгота (GPS)', 'example': 69.2107},
                    'car_list': {'type': 'array', 'items': {'type': 'integer'}, 'description': 'Список ID машин', 'example': [2]},
                    'category_list': {'type': 'array', 'items': {'type': 'integer'}, 'description': 'Список ID категорий проблем', 'example': [1]}
                }
            }
        },
        responses={
            201: {
                'description': 'SOS заказ успешно создан',
                'content': {
                    'application/json': {
                        'example': {
                            'message': 'Ваш экстренный заказ отправлен мастеру!',
                            'order': {
                                'id': 456,
                                'order_type': 'sos',
                                'status': 'pending',
                                'priority': 'high',
                                'master': {'id': 5, 'name': 'СТО Автосервис'},
                                'location': 'Трасса M39, км 45',
                                'latitude': 41.2548,
                                'longitude': 69.2107,
                                'text': 'Пробито переднее правое колесо'
                            }
                        }
                    }
                }
            },
            400: {
                'description': 'Ошибка валидации',
                'content': {
                    'application/json': {
                        'examples': {
                            'missing_master': {
                                'summary': 'Не указан мастер',
                                'value': {'master_id': ['Для SOS заказа необходимо указать мастера']}
                            },
                            'missing_location': {
                                'summary': 'Не указано местоположение',
                                'value': {'latitude': ['Это поле обязательно'], 'longitude': ['Это поле обязательно']}
                            },
                            'distance_error': {
                                'summary': 'Мастер слишком далеко',
                                'value': {'master_id': ['Выбранный мастер находится слишком далеко (150.5 км). Максимальное расстояние: 50 км.']}
                            }
                        }
                    }
                }
            },
            401: {'description': 'Не авторизован'}
        }
    )
    def post(self, request):
        """Создать SOS заказ"""
        # Принудительно устанавливаем order_type
        data = request.data.copy()
        data['order_type'] = OrderType.SOS
        # SOS broadcast: client must NOT pick master_id.
        # Even if provided, ignore to ensure nearest-eligible broadcast logic.
        data.pop('master_id', None)
        
        serializer = OrderCreateSerializer(data=data)
        if serializer.is_valid():
            order = serializer.save(user=request.user)
            print(f"[SOS][CREATE] order_id={order.id} driver_user_id={request.user.id} lat={order.latitude} lon={order.longitude}")
            # Deadline for SOS broadcast offers (default 120 seconds)
            try:
                seconds = int(getattr(dj_settings, 'SOS_BROADCAST_RESPONSE_SECONDS', 120))
                deadline = timezone.now() + timezone.timedelta(seconds=seconds)
                order.master_response_deadline = deadline
                order.save(update_fields=['master_response_deadline', 'updated_at'])
                schedule_offer_deadline_tasks(order_id=order.id, deadline=deadline)
            except Exception:
                deadline = None
            print(f"[SOS][DEADLINE] order_id={order.id} deadline={order.master_response_deadline}")

            # Broadcast to masters within radius (default 50km) and matching categories/services.
            channel_layer = get_channel_layer()
            radius_km = float(getattr(dj_settings, 'SOS_BROADCAST_RADIUS_KM', 50))
            print(f"[SOS][BROADCAST] order_id={order.id} radius_km={radius_km} direct_master=no")

            def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
                R = 6371.0
                lat1_rad = radians(lat1)
                lon1_rad = radians(lon1)
                lat2_rad = radians(lat2)
                lon2_rad = radians(lon2)
                dlat = lat2_rad - lat1_rad
                dlon = lon2_rad - lon1_rad
                a = sin(dlat / 2) ** 2 + cos(lat1_rad) * cos(lat2_rad) * sin(dlon / 2) ** 2
                c = 2 * atan2(sqrt(a), sqrt(1 - a))
                return R * c

            # WS payload: match HTTP-ish response shape
            ws_payload = order_to_ws_response(order)
            ws_event = {"type": "sos_order", "data": ws_payload}

            # Broadcast by radius + category/service match
            try:
                order_lat = float(order.latitude) if order.latitude is not None else None
                order_lon = float(order.longitude) if order.longitude is not None else None
            except Exception:
                order_lat, order_lon = None, None

            order_category_ids = list(order.category.values_list("id", flat=True))
            print(f"[SOS][CATEGORIES] order_id={order.id} category_ids={order_category_ids}")

            if order_lat is not None and order_lon is not None:
                # Filter by category (Master.category) OR by actual service items (MasterServiceItems.category)
                masters = (
                    Master.objects.exclude(latitude__isnull=True)
                    .exclude(longitude__isnull=True)
                    .filter(
                        Q(category__id__in=order_category_ids)
                        | Q(master_services__master_service_items__category_id__in=order_category_ids)
                    )
                    .distinct()
                    .select_related("user")
                )

                selected_users = []
                for m in masters:
                    try:
                        d = haversine_km(order_lat, order_lon, float(m.latitude), float(m.longitude))
                    except Exception:
                        continue
                    if d <= radius_km and getattr(m, "user", None):
                        selected_users.append(m.user)

                if selected_users:
                    order.masters.add(*selected_users)
                    print(f"[SOS][ELIGIBLE] order_id={order.id} master_user_ids={[u.id for u in selected_users]}")
                    # WS fan-out
                    for u in selected_users:
                        try:
                            async_to_sync(channel_layer.group_send)(f"sos_orders_{u.id}", ws_event)
                        except Exception:
                            continue
                    # Push fan-out (best-effort)
                    for u in selected_users:
                        _safe_push(
                            u,
                            title="Срочный заказ (SOS)",
                            body=f"Новый SOS заказ №{order.id}. Откройте приложение, чтобы принять или отклонить.",
                            data={"type": "sos_offer", "order_id": str(order.id), "order_type": str(order.order_type)},
                        )
                else:
                    print(f"[SOS][ELIGIBLE] order_id={order.id} master_user_ids=[] (none within radius/category)")
            else:
                print(f"[SOS][CREATE_ERR] order_id={order.id} missing lat/lon -> cannot broadcast")

            order_serializer = OrderSerializer(order)
            return Response({
                'message': 'Ваш экстренный заказ успешно создан и отправлен мастерам поблизости',
                'order': order_serializer.data
            }, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class AvailableTimeSlotsView(APIView):
    """Получение доступных временных слотов для мастера на конкретную дату"""
    permission_classes = [IsAuthenticated]
    
    @extend_schema(
        summary="Получить доступные временные слоты для записи",
        description="""
# 🕐 Доступные временные слоты

Этот endpoint возвращает список временных слотов (каждые 2 часа) для записи к мастеру на конкретную дату.

## 🎯 Когда использовать?

✅ Клиент выбирает **дату визита** в календаре
✅ Нужно показать **доступные** и **занятые** временные слоты
✅ Клиент записывается на **конкретное время** (например: 11:00-13:00)

## 📋 Обязательные параметры:

- **master_id** (query) - ID мастера/мастерской
- **date** (query) - Дата в формате YYYY-MM-DD (например: 2026-01-30)

## 📊 Формат ответа:

Каждый временной слот - это отдельный объект со следующими полями:
- **start** - время начала слота (HH:MM)
- **end** - время окончания слота (HH:MM)
- **available** - доступен ли слот (true/false)
- **order_id** - ID заказа (если слот занят)

## ⏰ Логика работы:

1. Берется **рабочее время мастера** (например: 09:00-18:00)
2. Делится на слоты **по 2 часа**: 09:00-11:00, 11:00-13:00, 13:00-15:00, 15:00-17:00, 17:00-19:00
3. Проверяются **существующие заказы** на эту дату
4. Возвращается список слотов с пометкой **available/unavailable**

## 📝 Пример ответа:

```json
{
  "date": "2026-01-30",
  "master_id": 5,
  "master_name": "СТО Автосервис",
  "working_hours": "09:00-18:00",
  "slots": [
    {
      "start": "09:00",
      "end": "11:00",
      "available": true
    },
    {
      "start": "11:00",
      "end": "13:00",
      "available": false,
      "order_id": 123
    },
    {
      "start": "13:00",
      "end": "15:00",
      "available": true
    },
    {
      "start": "15:00",
      "end": "17:00",
      "available": true
    },
    {
      "start": "17:00",
      "end": "19:00",
      "available": false,
      "order_id": 456
    }
  ]
}
```
        """,
        tags=['Orders (Driver) · Time slots'],
        parameters=[
            OpenApiParameter(
                name='master_id',
                type=OpenApiTypes.INT,
                location=OpenApiParameter.QUERY,
                description='ID мастера (обязательно). Пример: 5',
                required=True
            ),
            OpenApiParameter(
                name='date',
                type=OpenApiTypes.DATE,
                location=OpenApiParameter.QUERY,
                description='Дата для проверки слотов (формат: YYYY-MM-DD). Пример: 2026-01-30',
                required=True
            ),
        ],
        responses={
            200: {
                'description': 'Список доступных временных слотов',
                'content': {
                    'application/json': {
                        'example': {
                            'date': '2026-01-30',
                            'master_id': 5,
                            'master_name': 'СТО Автосервис',
                            'working_hours': '09:00-18:00',
                            'slots': [
                                {
                                    'start': '09:00',
                                    'end': '11:00',
                                    'available': True
                                },
                                {
                                    'start': '11:00',
                                    'end': '13:00',
                                    'available': False,
                                    'order_id': 123
                                },
                                {
                                    'start': '13:00',
                                    'end': '15:00',
                                    'available': True
                                }
                            ]
                        }
                    }
                }
            },
            400: {
                'description': 'Ошибка валидации',
                'content': {
                    'application/json': {
                        'examples': {
                            'missing_params': {
                                'summary': 'Отсутствуют параметры',
                                'value': {'error': 'master_id и date обязательны'}
                            },
                            'invalid_date': {
                                'summary': 'Неверный формат даты',
                                'value': {'error': 'Неверный формат даты. Используйте YYYY-MM-DD'}
                            }
                        }
                    }
                }
            },
            404: {
                'description': 'Мастер не найден',
                'content': {
                    'application/json': {
                        'example': {'error': 'Мастер не найден'}
                    }
                }
            }
        }
    )
    def get(self, request):
        """Получить доступные временные слоты"""
        from datetime import datetime, timedelta, time
        
        # Получаем параметры
        master_id = request.query_params.get('master_id')
        date_str = request.query_params.get('date')
        
        # Валидация параметров
        if not master_id or not date_str:
            return Response(
                {'error': 'master_id и date обязательны'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Валидация даты
        try:
            check_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        except ValueError:
            return Response(
                {'error': 'Неверный формат даты. Используйте YYYY-MM-DD (например: 2026-01-30)'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Получаем мастера
        try:
            master = Master.objects.get(id=master_id)
        except Master.DoesNotExist:
            return Response(
                {'error': 'Мастер не найден'},
                status=status.HTTP_404_NOT_FOUND
            )

        ok, err_msg = assert_booking_date_allowed_for_master(
            master_user_id=master.user_id,
            booking_date=check_date,
        )
        if not ok:
            return Response({'error': err_msg}, status=status.HTTP_400_BAD_REQUEST)

        from .slot_utils import build_slots_for_master_on_date

        working_time = master.working_time or '09:00-18:00'
        slots = build_slots_for_master_on_date(master, check_date)
        return Response({
            'date': date_str,
            'master_id': master.id,
            'master_name': master.name or master.user.get_full_name(),
            'working_hours': working_time,
            'slots': slots,
        })


class IncomingOrdersSyncView(APIView):
    """
    Master app sync endpoint for "incoming / not finished" orders.
    This is a fallback for WS/push delivery issues.
    """

    permission_classes = [IsAuthenticated, IsMaster]

    def get(self, request):
        user = request.user
        active_statuses = [
            OrderStatus.PENDING,
            OrderStatus.ACCEPTED,
            OrderStatus.ON_THE_WAY,
            OrderStatus.ARRIVED,
            OrderStatus.IN_PROGRESS,
        ]
        qs = (
            Order.objects.filter(status__in=active_statuses)
            .filter(Q(masters=user) | Q(master__user=user))
            .distinct()
            .order_by("-created_at")
        )
        serializer = OrderSerializer(qs, many=True, context={"request": request})
        return Response({"results": serializer.data})


class OrderListCreateView(APIView):
    """Список заказов"""
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['status', 'priority', 'master']
    search_fields = ['text', 'location', 'user__first_name', 'user__last_name', 'user__email']
    ordering_fields = ['created_at', 'updated_at', 'status', 'priority']
    ordering = ['-created_at']

    def get_queryset(self):
        user = self.request.user
        
        # Если пользователь - мастер, показываем заказы, назначенные ему
        master = user.master_profiles.first()
        if master:
            return Order.objects.filter(master=master)
        
        # Если обычный пользователь, показываем только его заказы
        return Order.objects.filter(user=user)

    @extend_schema(
        summary="Получить список заказов",
        description="Возвращает список заказов с возможностью фильтрации, поиска и сортировки",
        tags=['Orders (Driver) · CRUD & list'],
        parameters=[
            {'name': 'status', 'in': 'query', 'description': 'Фильтр по статусу заказа', 'type': 'string', 'enum': [choice[0] for choice in OrderStatus.choices]},
            {'name': 'priority', 'in': 'query', 'description': 'Фильтр по приоритету заказа', 'type': 'string', 'enum': ['low', 'high']},
            {'name': 'master', 'in': 'query', 'description': 'Фильтр по мастеру (ID мастера)', 'type': 'integer'},
            {'name': 'search', 'in': 'query', 'description': 'Поиск по тексту заказа, местоположению или имени пользователя', 'type': 'string'},
            {'name': 'ordering', 'in': 'query', 'description': 'Сортировка по полю (created_at, updated_at, status, priority)', 'type': 'string', 'enum': ['created_at', '-created_at', 'updated_at', '-updated_at', 'status', '-status', 'priority', '-priority']},
        ],
        responses={
            200: OrderSerializer(many=True),
            401: {'type': 'object', 'properties': {'detail': {'type': 'string'}}},
        }
    )
    def get(self, request):
        """Получить список заказов"""
        queryset = self.get_queryset()
        
        # Применяем фильтры
        queryset = self.apply_filters(queryset, request)
        
        serializer = OrderSerializer(queryset, many=True)
        return Response(serializer.data)

    def apply_filters(self, queryset, request):
        """Применить фильтры к queryset"""
        # Фильтрация по статусу
        if 'status' in request.query_params:
            queryset = queryset.filter(status=request.query_params['status'])
        
        # Фильтрация по приоритету
        if 'priority' in request.query_params:
            queryset = queryset.filter(priority=request.query_params['priority'])
        
        # Фильтрация по мастеру
        if 'master' in request.query_params:
            queryset = queryset.filter(master=request.query_params['master'])
        
        # Поиск
        if 'search' in request.query_params:
            search_term = request.query_params['search']
            queryset = queryset.filter(
                Q(text__icontains=search_term) |
                Q(location__icontains=search_term) |
                Q(user__first_name__icontains=search_term) |
                Q(user__last_name__icontains=search_term) |
                Q(user__email__icontains=search_term)
            )
        
        # Сортировка
        ordering = request.query_params.get('ordering', '-created_at')
        if ordering in self.ordering_fields:
            queryset = queryset.order_by(ordering)
        else:
            queryset = queryset.order_by(*self.ordering)
        
        return queryset


class OrderDetailView(APIView):
    """Детали заказа, обновление и удаление"""
    permission_classes = [IsAuthenticated, IsOrderOwnerOrMaster]

    def get_object(self, order_id):
        """Получить объект заказа"""
        try:
            order = Order.objects.get(id=order_id)
            # Проверяем права доступа
            self.check_object_permissions(self.request, order)
            return order
        except Order.DoesNotExist:
            return None

    @extend_schema(
        summary="Получить детали заказа",
        description="Возвращает детальную информацию о конкретном заказе",
        tags=['Orders (Driver) · CRUD & list'],
        parameters=[
            {'name': 'id', 'in': 'path', 'description': 'ID заказа', 'type': 'integer', 'required': True},
        ],
        responses={
            200: OrderSerializer,
            404: {'type': 'object', 'properties': {'error': {'type': 'string'}}},
            401: {'type': 'object', 'properties': {'detail': {'type': 'string'}}},
            403: {'type': 'object', 'properties': {'detail': {'type': 'string'}}},
        }
    )
    def get(self, request, id):
        """Получить детали заказа"""
        order = self.get_object(id)
        if not order:
            return Response(
                {'error': 'Заказ не найден'}, 
                status=status.HTTP_404_NOT_FOUND
            )
        
        serializer = OrderSerializer(order)
        return Response(serializer.data)

    @extend_schema(
        summary="Полное обновление заказа",
        description="Полностью обновляет все поля заказа. "
                  "Поля: text - описание заказа, location - адрес или описание места, "
                  "priority - приоритет заказа (low - низкий, high - высокий), "
                  "status - статус заказа (pending - ожидает, in_progress - в работе, completed - завершен, cancelled - отменен, rejected - отклонен), "
                  "latitude - широта местоположения (от -90 до 90), "
                  "longitude - долгота местоположения (от -180 до 180), "
                  "master - ID мастера.",
        tags=['Orders (Driver) · CRUD & list'],
        parameters=[
            {'name': 'id', 'in': 'path', 'description': 'ID заказа', 'type': 'integer', 'required': True},
        ],
        request={
            'application/json': {
                'type': 'object',
                'properties': {
                    'text': {'type': 'string', 'description': 'Описание заказа', 'example': 'Нужна помощь с заменой колеса'},
                    'status': {'type': 'string', 'enum': ['pending', 'in_progress', 'completed', 'cancelled', 'rejected'], 'description': 'Статус заказа', 'example': 'in_progress'},
                    'priority': {'type': 'string', 'enum': ['low', 'high'], 'description': 'Приоритет заказа', 'example': 'high'},
                    'location': {'type': 'string', 'description': 'Адрес или описание места', 'example': 'ул. Навои, д. 15, Ташкент'},
                    'latitude': {'type': 'number', 'description': 'Широта местоположения (от -90 до 90)', 'example': 41.3111},
                    'longitude': {'type': 'number', 'description': 'Долгота местоположения (от -180 до 180)', 'example': 69.2797},
                    'master': {'type': 'integer', 'description': 'ID мастера', 'example': 1}
                }
            }
        },
        responses={
            200: OrderSerializer,
            400: {'type': 'object', 'properties': {'detail': {'type': 'string'}}},
            404: {'type': 'object', 'properties': {'error': {'type': 'string'}}},
            401: {'type': 'object', 'properties': {'detail': {'type': 'string'}}},
            403: {'type': 'object', 'properties': {'detail': {'type': 'string'}}},
        }
    )
    def put(self, request, id):
        """Полное обновление заказа"""
        order = self.get_object(id)
        if not order:
            return Response(
                {'error': 'Заказ не найден'}, 
                status=status.HTTP_404_NOT_FOUND
            )
        
        serializer = OrderUpdateSerializer(order, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @extend_schema(
        summary="Частичное обновление заказа",
        description="Частично обновляет поля заказа. Можно указать только те поля, которые нужно обновить. "
                  "Поля: text - описание заказа, location - адрес или описание места, "
                  "priority - приоритет заказа (low - низкий, high - высокий), "
                  "status - статус заказа (pending - ожидает, in_progress - в работе, completed - завершен, cancelled - отменен, rejected - отклонен), "
                  "latitude - широта местоположения (от -90 до 90), "
                  "longitude - долгота местоположения (от -180 до 180), "
                  "master - ID мастера.",
        tags=['Orders (Driver) · CRUD & list'],
        parameters=[
            {'name': 'id', 'in': 'path', 'description': 'ID заказа', 'type': 'integer', 'required': True},
        ],
        request={
            'application/json': {
                'type': 'object',
                'properties': {
                    'text': {'type': 'string', 'description': 'Описание заказа', 'example': 'Нужна помощь с заменой колеса'},
                    'status': {'type': 'string', 'enum': ['pending', 'in_progress', 'completed', 'cancelled', 'rejected'], 'description': 'Статус заказа', 'example': 'in_progress'},
                    'priority': {'type': 'string', 'enum': ['low', 'high'], 'description': 'Приоритет заказа', 'example': 'high'},
                    'location': {'type': 'string', 'description': 'Адрес или описание места', 'example': 'ул. Навои, д. 15, Ташкент'},
                    'latitude': {'type': 'number', 'description': 'Широта местоположения (от -90 до 90)', 'example': 41.3111},
                    'longitude': {'type': 'number', 'description': 'Долгота местоположения (от -180 до 180)', 'example': 69.2797},
                    'master': {'type': 'integer', 'description': 'ID мастера', 'example': 1}
                }
            }
        },
        responses={
            200: OrderSerializer,
            400: {'type': 'object', 'properties': {'detail': {'type': 'string'}}},
            404: {'type': 'object', 'properties': {'error': {'type': 'string'}}},
            401: {'type': 'object', 'properties': {'detail': {'type': 'string'}}},
            403: {'type': 'object', 'properties': {'detail': {'type': 'string'}}},
        }
    )
    def patch(self, request, id):
        """Частичное обновление заказа"""
        order = self.get_object(id)
        if not order:
            return Response(
                {'error': 'Заказ не найден'}, 
                status=status.HTTP_404_NOT_FOUND
            )
        
        serializer = OrderUpdateSerializer(order, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @extend_schema(
        summary="Удалить заказ",
        description="Удаляет заказ из системы",
        tags=['Orders (Driver) · CRUD & list'],
        parameters=[
            {'name': 'id', 'in': 'path', 'description': 'ID заказа', 'type': 'integer', 'required': True},
        ],
        responses={
            204: {'description': 'Заказ успешно удален'},
            404: {'type': 'object', 'properties': {'error': {'type': 'string'}}},
            401: {'type': 'object', 'properties': {'detail': {'type': 'string'}}},
            403: {'type': 'object', 'properties': {'detail': {'type': 'string'}}},
        }
    )
    def delete(self, request, id):
        """Удалить заказ"""
        order = self.get_object(id)
        if not order:
            return Response(
                {'error': 'Заказ не найден'}, 
                status=status.HTTP_404_NOT_FOUND
            )
        
        order.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class OrdersByUserView(APIView):
    """
    API для получения заказов текущего пользователя
    """
    permission_classes = [IsAuthenticated]
    pagination_class = OrderPagination
    
    @extend_schema(
        summary="Получить заказы текущего пользователя",
        description="""
## Описание
Возвращает все заказы текущего авторизованного пользователя (user берется из header/token).

## Фильтры (все необязательные)

### 1. Статус заказа (status)
- Значения: pending, in_progress, completed, cancelled, rejected
- Пример: `status=in_progress`

### 2. Приоритет (priority)
- Значения: low (низкий), high (высокий)
- Пример: `priority=high`

### 3. Тип проблемы (category)
- ID категории типа **by_order**
- Использует **smart filter** через service_type
- Пример: `category=1` (где 1 - это "Пробито колесо", service_type="Шиномонтаж")
- Найдёт все заказы с похожим service_type или именем категории

### 4. Район (location)
- Поиск по адресу заказа
- Пример: `location=Ташкент` или `location=Навои`
- Поиск нечувствителен к регистру

### 5. Тип ТС (car_category)
- ID категории машины типа **by_car**
- Прямой фильтр по ID
- Пример: `car_category=3` (где 3 - это "Легковой")

### 6. Тип заказа (order_type)
- Фильтр по типу заказа
- Значения: `scheduled` (запланированный) или `sos` (экстренный)
- Пример: `order_type=scheduled` - показывает только запланированные заказы
- Пример: `order_type=sos` - показывает только SOS заказы

### 7. Имя мастера (name)
- Поиск по имени мастера
- Пример: `name=Алексей`

## Pagination
- По умолчанию 10 заказов на страницу
- Можно изменить через `page_size` (макс. 100)

## Примеры запросов

**Базовый:**
```
GET /api/order/by-user/
```

**С фильтром по статусу:**
```
GET /api/order/by-user/?status=in_progress
```

**С фильтром по проблеме (smart filter):**
```
GET /api/order/by-user/?category=1
```

**С несколькими фильтрами:**
```
GET /api/order/by-user/?status=pending&priority=high&category=1&location=Ташкент
```

**Только запланированные заказы (Order by Date):**
```
GET /api/order/by-user/?order_type=scheduled
```

**Только SOS заказы (экстренные):**
```
GET /api/order/by-user/?order_type=sos
```

**Запланированные заказы со статусом pending:**
```
GET /api/order/by-user/?order_type=scheduled&status=pending
```
        """,
        tags=['Orders (Driver) · My orders'],
        parameters=[
            OpenApiParameter(name='status', type=OpenApiTypes.STR, location=OpenApiParameter.QUERY, description='Фильтр по статусу заказа', required=False, enum=[choice[0] for choice in OrderStatus.choices]),
            OpenApiParameter(name='priority', type=OpenApiTypes.STR, location=OpenApiParameter.QUERY, description='Фильтр по приоритету (low, high)', required=False, enum=['low', 'high']),
            OpenApiParameter(name='category', type=OpenApiTypes.INT, location=OpenApiParameter.QUERY, description='Фильтр по типу проблемы. ID категории типа by_order. Использует smart filter через service_type.', required=False),
            OpenApiParameter(name='location', type=OpenApiTypes.STR, location=OpenApiParameter.QUERY, description='Фильтр по району (поиск по адресу заказа)', required=False),
            OpenApiParameter(name='car_category', type=OpenApiTypes.INT, location=OpenApiParameter.QUERY, description='Фильтр по типу ТС (ID категории машины типа by_car)', required=False),
            OpenApiParameter(name='order_type', type=OpenApiTypes.STR, location=OpenApiParameter.QUERY, description='Фильтр по типу заказа (scheduled - запланированные, sos - экстренные)', required=False, enum=['scheduled', 'sos']),
            OpenApiParameter(name='name', type=OpenApiTypes.STR, location=OpenApiParameter.QUERY, description='Поиск по имени мастера', required=False),
            OpenApiParameter(name='page', type=OpenApiTypes.INT, location=OpenApiParameter.QUERY, description='Номер страницы для пагинации', required=False),
            OpenApiParameter(name='page_size', type=OpenApiTypes.INT, location=OpenApiParameter.QUERY, description='Количество заказов на странице (макс. 100)', required=False),
        ],
        responses={
            200: OrderSerializer(many=True),
            401: {'type': 'object', 'properties': {'detail': {'type': 'string'}}},
        }
    )
    def get(self, request):
        """Получить заказы текущего пользователя"""
        orders = Order.objects.filter(user=request.user)
        
        # Фильтр по статусу
        status_filter = request.query_params.get('status')
        if status_filter:
            orders = orders.filter(status=status_filter)
        
        # Фильтр по приоритету
        priority_filter = request.query_params.get('priority')
        if priority_filter:
            orders = orders.filter(priority=priority_filter)
        
        # Фильтр по типу заказа (scheduled или sos)
        order_type_filter = request.query_params.get('order_type')
        if order_type_filter:
            if order_type_filter in ['scheduled', 'sos']:
                orders = orders.filter(order_type=order_type_filter)
        
        # Smart фильтр по категории проблемы (Тип проблемы)
        category_filter = request.query_params.get('category')
        if category_filter:
            try:
                from apps.categories.models import Category
                category_id = int(category_filter)
                category = Category.objects.get(id=category_id)
                
                # Если это by_order категория - используем smart filter через service_type
                if category.type_category == 'by_order':
                    category_conditions = Q()
                    
                    if category.service_type:
                        # Ищем заказы с похожим service_type
                        category_conditions |= Q(category__service_type__icontains=category.service_type)
                    
                    if category.name:
                        # Также ищем по имени категории
                        category_conditions |= Q(category__name__icontains=category.name)
                    
                    if category_conditions:
                        orders = orders.filter(category_conditions)
                else:
                    # Для других типов - прямой фильтр по ID
                    orders = orders.filter(category__id=category_id)
                    
            except Category.DoesNotExist:
                pass
            except (ValueError, TypeError):
                pass
        
        # Фильтр по району/местоположению (Районы)
        location_filter = request.query_params.get('location')
        if location_filter:
            orders = orders.filter(location__icontains=location_filter)
        
        # Фильтр по типу ТС (категория машины)
        car_category_filter = request.query_params.get('car_category')
        if car_category_filter:
            try:
                car_category_id = int(car_category_filter)
                orders = orders.filter(car__category__id=car_category_id)
            except (ValueError, TypeError):
                pass
        
        # Фильтр по имени мастера
        name = request.query_params.get('name')
        if name:
            orders = orders.filter(
                Q(master__user__first_name__icontains=name) |
                Q(master__user__last_name__icontains=name) |
                Q(master__user__get_full_name__icontains=name)
            )
        
        # Убираем дубликаты и сортируем
        orders = orders.distinct().order_by('-created_at')
        
        # Применяем пагинацию
        paginator = self.pagination_class()
        page = paginator.paginate_queryset(orders, request)
        if page is not None:
            serializer = OrderSerializer(page, many=True, context={'request': request})
            return paginator.get_paginated_response(serializer.data)
        
        serializer = OrderSerializer(orders, many=True, context={'request': request})
        return Response(serializer.data)


class OrdersByMasterView(APIView):
    """
    API для получения заказов текущего мастера
    """
    permission_classes = [IsAuthenticated]
    pagination_class = OrderPagination
    
    @extend_schema(
        summary="Получить заказы текущего мастера",
        description="""
## Описание
Возвращает список заказов, назначенных текущему мастеру (master берется из header/token).

## Фильтры (все необязательные)

### 1. Статус заказа (status)
- Значения: pending, in_progress, completed, cancelled, rejected
- Пример: `status=in_progress`

### 2. Приоритет (priority)
- Значения: low (низкий), high (высокий)
- Пример: `priority=high`

### 3. Тип проблемы (category)
- ID категории типа **by_order**
- Использует **smart filter** через service_type
- Пример: `category=1` (где 1 - это "Пробито колесо", service_type="Шиномонтаж")
- Найдёт все заказы с похожим service_type или именем категории

### 4. Район (location)
- Поиск по адресу заказа
- Пример: `location=Ташкент` или `location=Навои`
- Поиск нечувствителен к регистру

### 5. Тип ТС (car_category)
- ID категории машины типа **by_car**
- Прямой фильтр по ID
- Пример: `car_category=3` (где 3 - это "Легковой")

### 6. Географическая область (4 точки)
- Фильтр по координатам (полигон)
- Требуется указать все 4 точки
- Пример: `point1_lat=41.3&point1_lon=69.2&point2_lat=...`

### 7. Новые заказы (is_new)
- Фильтр для отображения новых заказов
- Значение: `true` или `false`
- Показывает заказы где master=null И masters пустой
- Пример: `is_new=true`

### 8. В работе (is_work)
- Фильтр для заказов в работе
- Значение: `true` или `false`
- Показывает заказы текущего мастера со статусом IN_PROGRESS
- Пример: `is_work=true`

### 9. Архив (is_archive)
- Фильтр для завершенных заказов
- Значение: `true` или `false`
- Показывает заказы текущего мастера со статусом COMPLETED
- Пример: `is_archive=true`

### 10. Тип заказа (order_type)
- Фильтр по типу заказа
- Значения: `scheduled` (запланированный) или `sos` (экстренный)
- Пример: `order_type=scheduled` - показывает только запланированные заказы
- Пример: `order_type=sos` - показывает только SOS заказы

## Pagination
- По умолчанию 10 заказов на страницу
- Можно изменить через `page_size` (макс. 100)

## Примеры запросов

**Базовый:**
```
GET /api/order/by-master/
```

**Новые заказы:**
```
GET /api/order/by-master/?is_new=true
```

**Заказы в работе:**
```
GET /api/order/by-master/?is_work=true
```

**Завершенные заказы (архив):**
```
GET /api/order/by-master/?is_archive=true
```

**С фильтром по статусу:**
```
GET /api/order/by-master/?status=in_progress
```

**С фильтром по проблеме (smart filter):**
```
GET /api/order/by-master/?category=1
```

**С несколькими фильтрами:**
```
GET /api/order/by-master/?status=pending&priority=high&category=1&location=Ташкент
```

**Только запланированные заказы (Order by Date):**
```
GET /api/order/by-master/?order_type=scheduled
```

**Только SOS заказы (экстренные):**
```
GET /api/order/by-master/?order_type=sos
```

**Запланированные заказы со статусом pending:**
```
GET /api/order/by-master/?order_type=scheduled&status=pending
```
        """,
        tags=['Orders (Master) · My orders'],
        parameters=[
            OpenApiParameter(name='status', type=OpenApiTypes.STR, location=OpenApiParameter.QUERY, description='Фильтр по статусу заказа', required=False, enum=[choice[0] for choice in OrderStatus.choices]),
            OpenApiParameter(name='priority', type=OpenApiTypes.STR, location=OpenApiParameter.QUERY, description='Фильтр по приоритету (low, high)', required=False, enum=['low', 'high']),
            OpenApiParameter(name='category', type=OpenApiTypes.INT, location=OpenApiParameter.QUERY, description='Фильтр по типу проблемы. ID категории типа by_order. Использует smart filter через service_type.', required=False),
            OpenApiParameter(name='location', type=OpenApiTypes.STR, location=OpenApiParameter.QUERY, description='Фильтр по району (поиск по адресу заказа)', required=False),
            OpenApiParameter(name='car_category', type=OpenApiTypes.INT, location=OpenApiParameter.QUERY, description='Фильтр по типу ТС (ID категории машины типа by_car)', required=False),
            # Координаты полигона (4 точки)
            OpenApiParameter(name='point1_lat', type=OpenApiTypes.FLOAT, location=OpenApiParameter.QUERY, description='Широта точки 1 (для географического фильтра)', required=False),
            OpenApiParameter(name='point1_lon', type=OpenApiTypes.FLOAT, location=OpenApiParameter.QUERY, description='Долгота точки 1', required=False),
            OpenApiParameter(name='point2_lat', type=OpenApiTypes.FLOAT, location=OpenApiParameter.QUERY, description='Широта точки 2', required=False),
            OpenApiParameter(name='point2_lon', type=OpenApiTypes.FLOAT, location=OpenApiParameter.QUERY, description='Долгота точки 2', required=False),
            OpenApiParameter(name='point3_lat', type=OpenApiTypes.FLOAT, location=OpenApiParameter.QUERY, description='Широта точки 3', required=False),
            OpenApiParameter(name='point3_lon', type=OpenApiTypes.FLOAT, location=OpenApiParameter.QUERY, description='Долгота точки 3', required=False),
            OpenApiParameter(name='point4_lat', type=OpenApiTypes.FLOAT, location=OpenApiParameter.QUERY, description='Широта точки 4', required=False),
            OpenApiParameter(name='point4_lon', type=OpenApiTypes.FLOAT, location=OpenApiParameter.QUERY, description='Долгота точки 4', required=False),
            OpenApiParameter(name='is_new', type=OpenApiTypes.BOOL, location=OpenApiParameter.QUERY, description='Новые заказы (master=null и masters пустой)', required=False),
            OpenApiParameter(name='is_work', type=OpenApiTypes.BOOL, location=OpenApiParameter.QUERY, description='Заказы в работе (status=IN_PROGRESS)', required=False),
            OpenApiParameter(name='is_archive', type=OpenApiTypes.BOOL, location=OpenApiParameter.QUERY, description='Завершенные заказы (status=COMPLETED)', required=False),
            OpenApiParameter(name='order_type', type=OpenApiTypes.STR, location=OpenApiParameter.QUERY, description='Фильтр по типу заказа (scheduled - запланированные, sos - экстренные)', required=False, enum=['scheduled', 'sos']),
            OpenApiParameter(name='page', type=OpenApiTypes.INT, location=OpenApiParameter.QUERY, description='Номер страницы для пагинации', required=False),
            OpenApiParameter(name='page_size', type=OpenApiTypes.INT, location=OpenApiParameter.QUERY, description='Количество заказов на странице (макс. 100)', required=False),
        ],
        responses={
            200: OrderSerializer(many=True),
            401: {'type': 'object', 'properties': {'detail': {'type': 'string'}}},
            403: {'type': 'object', 'properties': {'error': {'type': 'string'}}},
        }
    )
    def get(self, request):
        """Получить заказы текущего мастера в области"""
        # Проверяем, что пользователь является мастером
        try:
            master = request.user.master_profiles.first()
            if not master:
                return Response(
                    {'error': 'Пользователь не является мастером'}, 
                    status=status.HTTP_403_FORBIDDEN
                )
        except AttributeError:
            return Response(
                {'error': 'Пользователь не является мастером'}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Получаем заказы для текущего мастера через foreign key
        orders = Order.objects.filter(master=master)
        
        # Фильтр is_new - новые заказы (master=null и masters пустой)
        is_new = request.query_params.get('is_new', '').lower() == 'true'
        if is_new:
            from django.db.models import Count
            # Показываем заказы без мастера
            orders = Order.objects.annotate(
                masters_count=Count('masters')
            ).filter(
                master__isnull=True,
                masters_count=0
            )
        
        # Фильтр is_work — активные после принятия (в пути / прибыл / в работе)
        is_work = request.query_params.get('is_work', '').lower() == 'true'
        if is_work:
            orders = Order.objects.filter(
                master=master,
                status__in=[
                    OrderStatus.ACCEPTED,
                    OrderStatus.ON_THE_WAY,
                    OrderStatus.ARRIVED,
                    OrderStatus.IN_PROGRESS,
                ],
            )
        
        # Фильтр is_archive - завершенные заказы (COMPLETED)
        is_archive = request.query_params.get('is_archive', '').lower() == 'true'
        if is_archive:
            orders = Order.objects.filter(master=master, status=OrderStatus.COMPLETED)
        
        # Фильтр по статусу
        status_filter = request.query_params.get('status')
        if status_filter:
            orders = orders.filter(status=status_filter)
        
        # Фильтр по приоритету
        priority_filter = request.query_params.get('priority')
        if priority_filter:
            orders = orders.filter(priority=priority_filter)
        
        # Фильтр по типу заказа (scheduled или sos)
        order_type_filter = request.query_params.get('order_type')
        if order_type_filter:
            if order_type_filter in ['scheduled', 'sos']:
                orders = orders.filter(order_type=order_type_filter)
        
        # Smart фильтр по категории проблемы (Тип проблемы)
        category_filter = request.query_params.get('category')
        if category_filter:
            try:
                from apps.categories.models import Category
                category_id = int(category_filter)
                category = Category.objects.get(id=category_id)
                
                # Если это by_order категория - используем smart filter через service_type
                if category.type_category == 'by_order':
                    category_conditions = Q()
                    
                    if category.service_type:
                        # Ищем заказы с похожим service_type
                        category_conditions |= Q(category__service_type__icontains=category.service_type)
                    
                    if category.name:
                        # Также ищем по имени категории
                        category_conditions |= Q(category__name__icontains=category.name)
                    
                    if category_conditions:
                        orders = orders.filter(category_conditions)
                else:
                    # Для других типов - прямой фильтр по ID
                    orders = orders.filter(category__id=category_id)
                    
            except Category.DoesNotExist:
                pass
            except (ValueError, TypeError):
                pass
        
        # Фильтр по району/местоположению (Районы)
        location_filter = request.query_params.get('location')
        if location_filter:
            orders = orders.filter(location__icontains=location_filter)
        
        # Фильтр по типу ТС (категория машины)
        car_category_filter = request.query_params.get('car_category')
        if car_category_filter:
            try:
                car_category_id = int(car_category_filter)
                orders = orders.filter(car__category__id=car_category_id)
            except (ValueError, TypeError):
                pass
        
        # Фильтр по локации: 4 точки полигона (bounding box)
        area_filter = _get_area_filter_for_orders(request)
        if area_filter:
            # Faqat koordinatalari bo'lgan orderlarni filter qilamiz
            orders = orders.filter(
                latitude__isnull=False,
                longitude__isnull=False,
                **area_filter
            )
        
        # Убираем дубликаты и сортируем
        orders = orders.distinct().order_by('-created_at')
        
        # Применяем пагинацию
        paginator = self.pagination_class()
        page = paginator.paginate_queryset(orders, request)
        if page is not None:
            serializer = OrderSerializer(page, many=True, context={'request': request})
            return paginator.get_paginated_response(serializer.data)
        
        serializer = OrderSerializer(orders, many=True, context={'request': request})
        return Response(serializer.data)


class UpdateOrderStatusView(APIView):
    """
    API для обновления статуса заказа
    """
    permission_classes = [IsAuthenticated, IsOrderOwnerOrMaster]
    
    @extend_schema(
        summary="Master: изменить статус заказа",
        description="Обновляет статус заказа на новый. "
                  "Статусы: pending - ожидает, in_progress - в работе, completed - завершен, cancelled - отменен, rejected - отклонен. "
                  "Доступно только владельцу заказа или мастеру.",
        tags=['Orders (Master) · Workflow'],
        parameters=[
            {'name': 'order_id', 'in': 'path', 'description': 'ID заказа', 'type': 'integer', 'required': True},
        ],
        request={
            'application/json': {
                'type': 'object',
                'required': ['status'],
                'properties': {
                    'status': {
                        'type': 'string',
                        'enum': ['pending', 'in_progress', 'completed', 'cancelled', 'rejected'],
                        'description': 'Статус заказа: pending (Ожидает), in_progress (В работе), completed (Завершен), cancelled (Отменен), rejected (Отклонен)',
                        'example': 'in_progress'
                    }
                }
            }
        },
        responses={
            200: OrderSerializer,
            400: {'type': 'object', 'properties': {'detail': {'type': 'string'}}},
            404: {'type': 'object', 'properties': {'error': {'type': 'string'}}},
            401: {'type': 'object', 'properties': {'detail': {'type': 'string'}}},
            403: {'type': 'object', 'properties': {'detail': {'type': 'string'}}},
        }
    )
    def post(self, request, order_id):
        """Обновить статус заказа"""
        try:
            order = Order.objects.get(id=order_id)
            new_status = request.data.get('status')
            
            if not new_status:
                return Response(
                    {'error': 'Статус обязателен'}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            if new_status not in [choice[0] for choice in OrderStatus.choices]:
                return Response(
                    {'error': 'Недопустимый статус'}, 
                    status=status.HTTP_400_BAD_REQUEST
                )

            if new_status == OrderStatus.COMPLETED:
                return Response(
                    {
                        'error': 'Завершение только через POST .../complete/ с PIN клиента и фото работы.',
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            if new_status in (
                OrderStatus.ACCEPTED,
                OrderStatus.ON_THE_WAY,
                OrderStatus.ARRIVED,
                OrderStatus.IN_PROGRESS,
            ):
                return Response(
                    {
                        'error': 'Эти статусы задаются через POST .../accept/ и POST .../workflow/.',
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )
            
            order.status = new_status
            order.save()

            # push -> order owner
            _safe_push(
                order.user,
                title='Статус заказа изменён',
                body=f'Заказ №{order.id}: новый статус — {order.get_status_display()}.',
                data={'type': 'order_status', 'order_id': str(order.id), 'status': str(order.status)},
            )
            
            serializer = OrderSerializer(order)
            return Response(serializer.data)
        
        except Order.DoesNotExist:
            return Response(
                {'error': 'Заказ не найден'}, 
                status=status.HTTP_404_NOT_FOUND
            )


class DeclineOrderView(APIView):
    """
    Master: decline (отклонить) заказ.
    """
    permission_classes = [IsAuthenticated, IsMaster]

    def post(self, request, order_id):
        try:
            order = Order.objects.get(id=order_id)
        except Order.DoesNotExist:
            return Response({'error': 'Заказ не найден'}, status=status.HTTP_404_NOT_FOUND)

        master = request.user.master_profiles.first()
        if order.master and master and order.master.id != master.id:
            return Response({'error': 'Заказ уже назначен другому мастеру'}, status=status.HTTP_400_BAD_REQUEST)

        # SOS broadcast: decline only removes this master from offer queue.
        # Do NOT reject the whole order unless nobody is left.
        if order.order_type == OrderType.SOS and order.status == OrderStatus.PENDING and not order.master:
            # only eligible masters can decline
            if order.masters.filter(id=request.user.id).exists():
                order.masters.remove(request.user)
                # If nobody left -> reject order
                if order.masters.count() == 0:
                    order.status = OrderStatus.REJECTED
                    order.master_response_deadline = None
                    order.save(update_fields=['status', 'master_response_deadline', 'updated_at'])

                    _safe_push(
                        order.user,
                        title='Заказ отклонён',
                        body=f'Заказ №{order.id}: все мастера отклонили SOS запрос. Создайте новый заказ или попробуйте позже.',
                        data={'type': 'order_declined', 'order_id': str(order.id)},
                    )
                return Response({'message': 'SOS отклонён', 'order_id': order.id}, status=status.HTTP_200_OK)

        # Scheduled / direct-master flow: reject whole order
        order.master = None
        order.status = OrderStatus.REJECTED
        order.master_response_deadline = None
        order.save(update_fields=['master', 'status', 'master_response_deadline', 'updated_at'])

        _safe_push(
            order.user,
            title='Заказ отклонён',
            body=f'Заказ №{order.id}: мастер отклонил заявку. Вы можете выбрать другого мастера или создать новый заказ.',
            data={'type': 'order_declined', 'order_id': str(order.id)},
        )

        serializer = OrderSerializer(order, context={'request': request})
        return Response({'message': 'Заказ отклонен', 'order': serializer.data}, status=status.HTTP_200_OK)


class AcceptOrderView(APIView):
    """
    API для принятия заказа в работу
    """
    permission_classes = [IsAuthenticated, IsMaster]
    
    @extend_schema(
        summary="Master: принять заказ в работу",
        description="""
Принимает заказ в работу с проверкой минимального баланса **мастера** (1000 ₽) и списанием 200 ₽ за каждый заказ.

## Проверки баланса мастера:
1. **Минимальный баланс**: У мастера на балансе должно быть минимум 1000 ₽
2. **Списание за заказ**: С баланса мастера спишется 200 ₽ при принятии заказа

## Response при ошибке баланса:
```json
{
  "error": "Описание ошибки",
  "current_balance": 500.00,
  "required_balance": 1000
}
```

**Важно:** Проверяется баланс **мастера**, который принимает заказ, а не клиента!
        """,
        tags=['Orders (Master) · Workflow'],
        parameters=[
            {'name': 'order_id', 'in': 'path', 'description': 'ID заказа', 'type': 'integer', 'required': True},
        ],
        responses={
            200: {
                'type': 'object',
                'properties': {
                    'message': {'type': 'string'},
                    'order': {'type': 'object'},
                    'balance_after': {'type': 'number'}
                }
            },
            400: {
                'type': 'object',
                'properties': {
                    'error': {'type': 'string'},
                    'current_balance': {'type': 'number'},
                    'required_balance': {'type': 'number'},
                    'required_amount': {'type': 'number'}
                }
            },
            404: {'type': 'object', 'properties': {'error': {'type': 'string'}}},
            401: {'type': 'object', 'properties': {'detail': {'type': 'string'}}},
            403: {'type': 'object', 'properties': {'detail': {'type': 'string'}}},
        }
    )
    def post(self, request, order_id):
        """Принять заказ в работу"""
        try:
            order = Order.objects.get(id=order_id)

            # Order must still be pending to accept
            if order.status != OrderStatus.PENDING:
                return Response(
                    {
                        "error": "Заказ уже недоступен для принятия",
                        "status": str(order.status),
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # If offer deadline passed — do not allow accept (safety; celery should reject too)
            if order.master_response_deadline and timezone.now() > order.master_response_deadline:
                return Response(
                    {"error": "Время предложения истекло"},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            
            # Проверяем, что заказ не назначен другому мастеру
            master = request.user.master_profiles.first()
            if order.master and order.master.id != master.id:
                return Response(
                    {'error': 'Заказ уже назначен другому мастеру'}, 
                    status=status.HTTP_400_BAD_REQUEST
                )

            # SOS broadcast: only eligible masters can accept, and only while deadline not passed
            if order.order_type == OrderType.SOS and order.status == OrderStatus.PENDING and not order.master:
                if not order.masters.filter(id=request.user.id).exists():
                    return Response({'error': 'Вы не в очереди предложений по этому SOS заказу'}, status=status.HTTP_400_BAD_REQUEST)
            
            # Проверяем, что заказ не истек
            if order.is_expired():
                order.mark_as_cancelled_if_expired()
                return Response(
                    {'error': 'Заказ истек и был отменен'}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Проверяем баланс мастера (кто принимает заказ)
            user_balance = UserBalance.get_or_create_balance(request.user)
            if not user_balance.has_minimum_balance(1000):
                return Response({
                    'error': 'На балансе должно быть минимум 1000 ₽, чтобы брать заказы в работу',
                    'current_balance': float(user_balance.amount),
                    'required_balance': 1000
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Проверяем, может ли пользователь позволить себе заказ (200 ₽)
            if not user_balance.can_afford_order(200):
                return Response({
                    'error': 'Недостаточно средств для принятия заказа. Требуется 200 ₽',
                    'current_balance': float(user_balance.amount),
                    'required_amount': 200
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Списываем 200 ₽ с баланса
            if user_balance.deduct_amount(200):
                # Назначаем заказ текущему мастеру; дальше — workflow (в пути → прибыл → в работе)
                order.master = master
                order.status = OrderStatus.ACCEPTED
                order.accepted_at = timezone.now()
                order.master_response_deadline = None
                order.save(update_fields=['master', 'status', 'accepted_at', 'master_response_deadline', 'updated_at'])

                # SOS broadcast: close offers for other masters + notify via WS (best-effort)
                try:
                    if order.order_type == OrderType.SOS:
                        other_ids = list(order.masters.exclude(id=request.user.id).values_list("id", flat=True))
                        # Keep only accepted master in queue/history
                        order.masters.clear()
                        order.masters.add(request.user)

                        channel_layer = get_channel_layer()
                        evt = {"type": "sos_order_taken", "order_id": order.id, "master_user_id": request.user.id}
                        for uid in other_ids:
                            try:
                                async_to_sync(channel_layer.group_send)(f"sos_orders_{uid}", {"type": "sos_order_taken", **evt})
                            except Exception:
                                continue
                except Exception:
                    pass

                # Создаем чат комнату (master initiator, driver receiver)
                try:
                    existing_room = ChatRoom.objects.filter(participants=master.user).filter(participants=order.user).first()
                    if existing_room:
                        room = existing_room
                    else:
                        room = ChatRoom.objects.create(initiator=master.user)
                        room.participants.add(master.user, order.user)
                    # Если в Order будет поле chat_room — свяжем позже (migrate)
                    if hasattr(order, 'chat_room_id'):
                        order.chat_room = room
                        order.save(update_fields=['chat_room', 'updated_at'])
                except Exception:
                    room = None

                # push -> order owner
                _safe_push(
                    order.user,
                    title='Заказ принят мастером',
                    body=f'Заказ №{order.id}: мастер принял заказ. Ожидайте выезд / статус в приложении.',
                    data={'type': 'order_accepted', 'order_id': str(order.id), 'room_id': str(room.id) if room else ''},
                )
                
                # Обновляем баланс после списания
                user_balance.refresh_from_db()
                
                serializer = OrderSerializer(order, context={'request': request})
                return Response({
                    'message': 'Заказ принят. 200 ₽ списаны с баланса мастера. Дальше переводите статусы через /workflow/.',
                    'order': serializer.data,
                    'balance_after': float(user_balance.amount)
                })
            else:
                return Response({
                    'error': 'Ошибка при списании средств с баланса',
                    'current_balance': float(user_balance.amount)
                }, status=status.HTTP_400_BAD_REQUEST)
        
        except Order.DoesNotExist:
            return Response(
                {'error': 'Заказ не найден'}, 
                status=status.HTTP_404_NOT_FOUND
            )


class CompleteOrderView(APIView):
    """
    API для завершения заказа (отметка как выполненного)
    """
    permission_classes = [IsAuthenticated, IsMaster]

    def _master(self, request):
        return request.user.master_profiles.first()
    
    @extend_schema(
        summary="Master: завершить заказ (Completed)",
        description="""
## Описание
Завершает заказ (**COMPLETED**). Сумма берётся из услуг заказа (`OrderService` / цены услуг мастера), без тела запроса.
Создаётся оплата СБП как у **POST /api/auth/balance/sbp-qr/** (тот же `intent_id`, QR, `pay_url`) для **клиента** (водителя).

## Условия
- Заказ в статусе **in_progress** (цепочка `POST .../workflow/`).
- Тело JSON: **`completion_pin`** — PIN, который клиент видит в заказе после перехода в «в работе».
- Загружено минимум одно фото: **`POST .../work-completion-images/`** (multipart `images`).
- В заказе должны быть добавлены услуги (`add-services/`), сумма после скидки > 0.
- В `.env` должен быть `SBP_QR_PAY_URL`.
- Только назначенный мастер заказа.

## Статусы оплаты заказа (`order.payment`)
- `none` → после `complete`: `pending`, пока клиент не оплатит
- `paid` — после webhook **POST /api/auth/balance/sbp-webhook/** по этому `intent_id`

## Пример запроса:
```json
POST /api/order/5/complete/
{"completion_pin": "4821"}
```
        """,
        tags=['Orders (Master) · Workflow'],
        parameters=[
            {'name': 'order_id', 'in': 'path', 'description': 'ID заказа', 'type': 'integer', 'required': True},
        ],
        request={
            'application/json': {
                'type': 'object',
                'required': ['completion_pin'],
                'properties': {
                    'completion_pin': {'type': 'string', 'description': 'PIN из приложения клиента', 'example': '4821'},
                },
            }
        },
        responses={
            200: {
                'type': 'object',
                'properties': {
                    'message': {'type': 'string', 'example': 'Заказ успешно завершен'},
                    'order': {'$ref': '#/components/schemas/Order'},
                    'payment': {
                        'type': 'object',
                        'properties': {
                            'intent_id': {'type': 'string'},
                            'price': {'type': 'string'},
                            'pay_url': {'type': 'string'},
                            'qr_image_base64': {'type': 'string'},
                        },
                    },
                }
            },
            400: {'type': 'object', 'properties': {'error': {'type': 'string'}}},
            404: {
                'type': 'object',
                'properties': {'error': {'type': 'string', 'example': 'Заказ не найден'}}
            },
            401: {
                'type': 'object',
                'properties': {'detail': {'type': 'string', 'example': 'Authentication credentials were not provided.'}}
            },
            503: {'type': 'object', 'properties': {'error': {'type': 'string'}}},
        }
    )
    def post(self, request, order_id):
        """Завершить заказ: COMPLETED + СБП intent для клиента (как balance/sbp-qr)."""
        master = self._master(request)
        if not master:
            return Response({'error': 'Пользователь не является мастером'}, status=status.HTTP_403_FORBIDDEN)

        try:
            order = Order.objects.prefetch_related(
                'order_services__master_service_item'
            ).get(id=order_id)
        except Order.DoesNotExist:
            return Response({'error': 'Заказ не найден'}, status=status.HTTP_404_NOT_FOUND)

        if order.master_id != master.id:
            return Response(
                {'error': 'Этот заказ назначен другому мастеру'},
                status=status.HTTP_403_FORBIDDEN,
            )

        if order.status == OrderStatus.COMPLETED and order.payment_status == OrderPaymentStatus.PAID:
            serializer = OrderSerializer(order, context={'request': request})
            return Response(
                {
                    'message': 'Заказ уже завершён и оплачен',
                    'order': serializer.data,
                },
                status=status.HTTP_200_OK,
            )

        if order.status == OrderStatus.COMPLETED and order.payment_status == OrderPaymentStatus.PENDING:
            if order.sbp_payment_intent_id:
                from django.conf import settings as dj_settings
                from apps.accounts.sbp_qr import pay_url_to_qr_png_base64

                pay_url = (getattr(dj_settings, 'SBP_QR_PAY_URL', '') or '').strip()
                intent = order.sbp_payment_intent
                serializer = OrderSerializer(order, context={'request': request})
                return Response(
                    {
                        'message': 'Заказ уже завершён, ожидается оплата',
                        'order': serializer.data,
                        'payment': {
                            'intent_id': str(intent.id),
                            'price': str(intent.amount),
                            'pay_url': pay_url,
                            'qr_image_base64': pay_url_to_qr_png_base64(pay_url) if pay_url else None,
                        },
                    },
                    status=status.HTTP_200_OK,
                )

        if order.status == OrderStatus.COMPLETED:
            serializer = OrderSerializer(order, context={'request': request})
            return Response(
                {
                    'message': 'Заказ уже завершён',
                    'order': serializer.data,
                },
                status=status.HTTP_200_OK,
            )

        if order.status != OrderStatus.IN_PROGRESS:
            return Response(
                {
                    'error': 'Завершить можно только заказ в статусе «в работе». Используйте цепочку /workflow/.',
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        pin = (request.data.get('completion_pin') or '').strip()
        if not order.completion_pin or pin != str(order.completion_pin).strip():
            return Response({'error': 'Неверный или пустой PIN завершения'}, status=status.HTTP_400_BAD_REQUEST)

        if not order.work_completion_images.exists():
            return Response(
                {'error': 'Нужно минимум одно фото выполненной работы (POST .../work-completion-images/).'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not order.order_services.exists():
            return Response(
                {'error': 'Добавьте услуги к заказу (POST /api/order/add-services/) перед завершением'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        raw_total = compute_order_services_total(order)
        if raw_total <= 0:
            breakdown = []
            try:
                for os in order.order_services.select_related('master_service_item'):
                    msi = os.master_service_item
                    if not msi:
                        continue
                    breakdown.append(
                        {
                            'order_service_id': os.id,
                            'service_item_id': msi.id,
                            'name': msi.name,
                            'price_from': str(msi.price_from),
                            'price_to': str(msi.price_to),
                        }
                    )
            except Exception:
                breakdown = []
            return Response(
                {
                    'error': 'Сумма заказа по услугам должна быть больше 0 (проверьте услуги и скидку)',
                    'debug': {
                        'order_id': order.id,
                        'discount': str(order.discount),
                        'services': breakdown,
                        'calculated_total': str(raw_total),
                    },
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        amount = effective_sbp_amount(raw_total)

        # Dynamic Alfa order (register.do) → orderId/formUrl
        # If already registered earlier, reuse to avoid "orderNumber already processed".
        if order.alfa_order_id and order.alfa_form_url:
            alfa_order_id = order.alfa_order_id
            order_number = order.alfa_order_number or f'order-{order.id}'
            form_url = order.alfa_form_url
        else:
            order_number = order.alfa_order_number or f'order-{order.id}'
            from django.conf import settings as dj_settings
            gw = register_order(
                order_number=order_number,
                amount_kopecks=int(amount * 100),
                description=f'CheckAvto order #{order.id}',
                return_url=getattr(dj_settings, 'ALFA_RETURN_URL', ''),
                fail_url=getattr(dj_settings, 'ALFA_FAIL_URL', ''),
                session_timeout_secs=getattr(dj_settings, 'ALFA_SESSION_TIMEOUT_SECS', 900),
            )
            if gw.get('error') or str(gw.get('errorCode', '0')) not in ('0', '00', 0):
                return Response({'error': 'Alfa register.do failed', 'gateway': gw}, status=status.HTTP_502_BAD_GATEWAY)
            alfa_order_id = str(gw.get('orderId') or '').strip()
            form_url = str(gw.get('formUrl') or '').strip()

        # Local intent (optional): used for internal tracking; do NOT show static pay_url to client.
        try:
            intent, _pay_url, _qr_b64 = create_order_payment_intent(order, amount=amount)
        except ValueError as e:
            return Response({'error': str(e)}, status=status.HTTP_503_SERVICE_UNAVAILABLE)

        order.status = OrderStatus.COMPLETED
        order.payment_status = OrderPaymentStatus.PENDING
        order.sbp_payment_intent = intent
        order.alfa_order_id = alfa_order_id
        order.alfa_order_number = order_number
        order.alfa_form_url = form_url
        order.save(update_fields=['status', 'payment_status', 'sbp_payment_intent', 'alfa_order_id', 'alfa_order_number', 'alfa_form_url', 'updated_at'])

        # track payment transaction
        try:
            PaymentTransaction.objects.update_or_create(
                intent=intent,
                defaults={
                    'kind': PaymentKind.ORDER,
                    'status': PaymentStatus.PENDING,
                    'initiated_by': order.user,
                    'beneficiary': order.user,
                    'amount': amount,
                    'order': order,
                    'master': order.master,
                    'alfa_order_id': alfa_order_id,
                    'alfa_order_number': order_number,
                    'form_url': form_url,
                },
            )
        except Exception:
            pass

        _safe_push(
            order.user,
            title='Заказ завершён',
            body=f'Заказ №{order.id}: работа завершена. Пожалуйста, перейдите к оплате.',
            data={'type': 'order_completed_payment', 'order_id': str(order.id), 'payment_status': str(order.payment_status)},
        )

        serializer = OrderSerializer(order, context={'request': request})
        return Response(
            {
                'message': 'Заказ успешно завершен. Оплата: QR для клиента (как /api/auth/balance/sbp-qr/).',
                'order': serializer.data,
                'payment': {
                    'intent_id': str(intent.id),
                    'price': str(amount),
                    'calculated_total': str(raw_total),
                    'alfa_order_id': alfa_order_id,
                    'alfa_order_number': order_number,
                    'form_url': form_url,
                    'note': (
                        'Клиент оплачивает по form_url (mdOrder). Статус: POST /api/auth/balance/alfa-order-status/.'
                    ),
                },
            },
            status=status.HTTP_200_OK,
        )


class AdvanceOrderWorkflowView(APIView):
    """Мастер: accepted → on_the_way → arrived → in_progress (PIN клиенту при in_progress)."""

    permission_classes = [IsAuthenticated, IsMaster]

    def post(self, request, order_id):
        master = request.user.master_profiles.first()
        if not master:
            return Response({'error': 'Пользователь не является мастером'}, status=status.HTTP_403_FORBIDDEN)

        try:
            order = Order.objects.get(id=order_id)
        except Order.DoesNotExist:
            return Response({'error': 'Заказ не найден'}, status=status.HTTP_404_NOT_FOUND)

        if order.master_id != master.id:
            return Response({'error': 'Этот заказ назначен другому мастеру'}, status=status.HTTP_403_FORBIDDEN)

        new_status = (request.data.get('status') or '').strip()
        if new_status not in (OrderStatus.ON_THE_WAY, OrderStatus.ARRIVED, OrderStatus.IN_PROGRESS):
            return Response(
                {'error': 'Укажите JSON поле status: on_the_way | arrived | in_progress'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        ok, err = workflow_transition_allowed(order, new_status)
        if not ok:
            return Response({'error': err}, status=status.HTTP_400_BAD_REQUEST)

        now = timezone.now()
        if new_status == OrderStatus.ON_THE_WAY:
            order.status = new_status
            order.on_the_way_started_at = now
            order.save(update_fields=['status', 'on_the_way_started_at', 'updated_at'])
        elif new_status == OrderStatus.ARRIVED:
            order.status = new_status
            order.arrived_at = now
            order.save(update_fields=['status', 'arrived_at', 'updated_at'])
        else:
            order.status = OrderStatus.IN_PROGRESS
            if not order.completion_pin:
                order.completion_pin = generate_completion_pin()
            order.save(update_fields=['status', 'completion_pin', 'updated_at'])

        _safe_push(
            order.user,
            title='Статус заказа',
            body=f'Заказ №{order.id}: {order.get_status_display()}.',
            data={'type': 'order_status', 'order_id': str(order.id), 'status': str(order.status)},
        )

        serializer = OrderSerializer(order, context={'request': request})
        return Response(serializer.data, status=status.HTTP_200_OK)


class OrderWorkCompletionImagesView(APIView):
    """Мастер: загрузить фото выполненной работы (multipart, поле images)."""

    permission_classes = [IsAuthenticated, IsMaster]

    def post(self, request, order_id):
        master = request.user.master_profiles.first()
        if not master:
            return Response({'error': 'Пользователь не является мастером'}, status=status.HTTP_403_FORBIDDEN)

        try:
            order = Order.objects.get(id=order_id)
        except Order.DoesNotExist:
            return Response({'error': 'Заказ не найден'}, status=status.HTTP_404_NOT_FOUND)

        if order.master_id != master.id:
            return Response({'error': 'Этот заказ назначен другому мастеру'}, status=status.HTTP_403_FORBIDDEN)

        files = request.FILES.getlist('images')
        if not files:
            return Response({'error': 'Передайте файлы в поле images (multipart)'}, status=status.HTTP_400_BAD_REQUEST)
        if len(files) > 15:
            return Response({'error': 'Не более 15 файлов за один запрос'}, status=status.HTTP_400_BAD_REQUEST)

        created = []
        for f in files:
            img = OrderWorkCompletionImage.objects.create(order=order, image=f)
            created.append(img.id)

        return Response({'message': 'Фото сохранены', 'image_ids': created}, status=status.HTTP_201_CREATED)


class ClientCancelOrderView(APIView):
    """Клиент: отмена заказа с удержанием штрафа по правилам workflow."""

    permission_classes = [IsAuthenticated]

    def post(self, request, order_id):
        try:
            order = Order.objects.get(id=order_id)
        except Order.DoesNotExist:
            return Response({'error': 'Заказ не найден'}, status=status.HTTP_404_NOT_FOUND)

        if order.user_id != request.user.id:
            return Response({'error': 'Доступно только владельцу заказа'}, status=status.HTTP_403_FORBIDDEN)

        allowed, pct, err_msg = client_cancel_penalty_percent(order)
        if not allowed:
            return Response({'error': err_msg or 'Отмена невозможна'}, status=status.HTTP_400_BAD_REQUEST)

        base = order_amount_for_penalty(order)
        penalty_amt = (base * pct / Decimal('100')).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

        if penalty_amt > 0:
            ub = UserBalance.get_or_create_balance(request.user)
            if ub.amount < penalty_amt:
                return Response(
                    {
                        'error': 'Недостаточно средств на балансе для удержания штрафа',
                        'penalty_amount': str(penalty_amt),
                        'balance': str(ub.amount),
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )
            if not ub.deduct_amount(penalty_amt):
                return Response(
                    {'error': 'Не удалось удержать штраф с баланса'},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        order.status = OrderStatus.CANCELLED
        order.save(update_fields=['status', 'updated_at'])

        if order.master and getattr(order.master, 'user', None):
            _safe_push(
                order.master.user,
                title='Заказ отменён клиентом',
                body=f'Заказ №{order.id} отменён клиентом.',
                data={'type': 'order_cancelled', 'order_id': str(order.id)},
            )

        serializer = OrderSerializer(order, context={'request': request})
        return Response(
            {
                'message': 'Заказ отменён',
                'penalty_percent': str(pct),
                'penalty_amount': str(penalty_amt),
                'order': serializer.data,
            },
            status=status.HTTP_200_OK,
        )


class MasterCancelAfterAcceptView(APIView):
    """Мастер: отмена после принятия (логируется; причина too_far запрещена)."""

    permission_classes = [IsAuthenticated, IsMaster]

    def post(self, request, order_id):
        master = request.user.master_profiles.first()
        if not master:
            return Response({'error': 'Пользователь не является мастером'}, status=status.HTTP_403_FORBIDDEN)

        try:
            order = Order.objects.get(id=order_id)
        except Order.DoesNotExist:
            return Response({'error': 'Заказ не найден'}, status=status.HTTP_404_NOT_FOUND)

        if order.master_id != master.id:
            return Response({'error': 'Этот заказ назначен другому мастеру'}, status=status.HTTP_403_FORBIDDEN)

        reason = (request.data.get('cancel_reason') or '').strip()
        if reason == 'too_far':
            return Response({'error': 'Причина too_far не используется'}, status=status.HTTP_400_BAD_REQUEST)

        allowed_reasons = {m.value for m in MasterCancelReason}
        if reason not in allowed_reasons:
            return Response(
                {'error': f'Некорректная cancel_reason. Допустимо: {", ".join(sorted(allowed_reasons))}'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if order.status not in (
            OrderStatus.ACCEPTED,
            OrderStatus.ON_THE_WAY,
            OrderStatus.ARRIVED,
            OrderStatus.IN_PROGRESS,
        ):
            return Response(
                {'error': 'Отмена мастером в этом статусе недоступна (используйте decline для pending).'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        MasterOrderCancellation.objects.create(
            master_user=request.user,
            order=order,
            reason=reason,
        )
        order.status = OrderStatus.CANCELLED
        order.save(update_fields=['status', 'updated_at'])

        _safe_push(
            order.user,
            title='Заказ отменён мастером',
            body=f'Заказ №{order.id} отменён мастером.',
            data={'type': 'order_cancelled', 'order_id': str(order.id)},
        )

        serializer = OrderSerializer(order, context={'request': request})
        return Response({'message': 'Заказ отменён', 'order': serializer.data}, status=status.HTTP_200_OK)


class ResendOrderPaymentView(APIView):
    """
    Повторно открыть оплату (новый formUrl/orderId) если клиент не успел оплатить.
    """

    permission_classes = [IsAuthenticated, IsMaster]

    @extend_schema(
        summary="Master: resend payment (новый formUrl)",
        description=(
            "Если клиент не успел оплатить (сессия истекла), создаём новый dynamic order в Альфа (register.do) "
            "с новым уникальным orderNumber, чтобы не было ошибки «заказ с таким номером уже обработан»."
        ),
        tags=['Orders (Master) · Payment'],
        responses={200: {"type": "object"}, 400: {"type": "object"}, 403: {"type": "object"}, 404: {"type": "object"}, 502: {"type": "object"}},
    )
    def post(self, request, order_id):
        master = request.user.master_profiles.first()
        if not master:
            return Response({'error': 'Пользователь не является мастером'}, status=status.HTTP_403_FORBIDDEN)

        try:
            order = Order.objects.prefetch_related('order_services__master_service_item').get(id=order_id)
        except Order.DoesNotExist:
            return Response({'error': 'Заказ не найден'}, status=status.HTTP_404_NOT_FOUND)

        if order.master_id != master.id:
            return Response({'error': 'Этот заказ назначен другому мастеру'}, status=status.HTTP_403_FORBIDDEN)

        if order.status != OrderStatus.COMPLETED:
            return Response({'error': 'Resend доступен только после завершения заказа (completed).'}, status=status.HTTP_400_BAD_REQUEST)

        if order.payment_status == OrderPaymentStatus.PAID:
            serializer = OrderSerializer(order, context={'request': request})
            return Response({'message': 'Заказ уже оплачен', 'order': serializer.data}, status=status.HTTP_200_OK)

        if not order.order_services.exists():
            return Response({'error': 'Добавьте услуги к заказу перед оплатой'}, status=status.HTTP_400_BAD_REQUEST)

        raw_total = compute_order_services_total(order)
        if raw_total <= 0:
            return Response({'error': 'Сумма заказа по услугам должна быть больше 0'}, status=status.HTTP_400_BAD_REQUEST)

        amount = effective_sbp_amount(raw_total)

        # новый уникальный orderNumber (Alfa ограничивает 32 символа)
        suffix = uuid.uuid4().hex[:8]
        order_number = f'order-{order.id}-{suffix}'[:32]

        from django.conf import settings as dj_settings
        gw = register_order(
            order_number=order_number,
            amount_kopecks=int(amount * 100),
            description=f'CheckAvto order #{order.id} (resend)',
            return_url=getattr(dj_settings, 'ALFA_RETURN_URL', ''),
            fail_url=getattr(dj_settings, 'ALFA_FAIL_URL', ''),
            session_timeout_secs=getattr(dj_settings, 'ALFA_SESSION_TIMEOUT_SECS', 900),
        )
        if gw.get('error') or str(gw.get('errorCode', '0')) not in ('0', '00', 0):
            return Response({'error': 'Alfa register.do failed', 'gateway': gw}, status=status.HTTP_502_BAD_GATEWAY)

        alfa_order_id = str(gw.get('orderId') or '').strip()
        form_url = str(gw.get('formUrl') or '').strip()

        # новый internal intent (актуальная попытка оплаты)
        intent = SbpPaymentIntent.objects.create(
            user=order.user,
            amount=amount,
            status=SbpPaymentIntent.STATUS_PENDING,
        )

        order.payment_status = OrderPaymentStatus.PENDING
        order.sbp_payment_intent = intent
        order.alfa_order_id = alfa_order_id
        order.alfa_order_number = order_number
        order.alfa_form_url = form_url
        order.save(update_fields=['payment_status', 'sbp_payment_intent', 'alfa_order_id', 'alfa_order_number', 'alfa_form_url', 'updated_at'])

        try:
            PaymentTransaction.objects.update_or_create(
                intent=intent,
                defaults={
                    'kind': PaymentKind.ORDER,
                    'status': PaymentStatus.PENDING,
                    'initiated_by': order.user,
                    'beneficiary': order.user,
                    'amount': amount,
                    'order': order,
                    'master': order.master,
                    'alfa_order_id': alfa_order_id,
                    'alfa_order_number': order_number,
                    'form_url': form_url,
                },
            )
        except Exception:
            pass

        serializer = OrderSerializer(order, context={'request': request})
        return Response(
            {
                'success': True,
                'message': 'Новая оплата создана (resend).',
                'order': serializer.data,
                'payment': {
                    'intent_id': str(intent.id),
                    'price': str(amount),
                    'calculated_total': str(raw_total),
                    'alfa_order_id': alfa_order_id,
                    'alfa_order_number': order_number,
                    'form_url': form_url,
                },
            },
            status=status.HTTP_200_OK,
        )


class CreateReviewView(APIView):
    """
    API для создания отзыва о заказе и мастерах
    """
    permission_classes = [IsAuthenticated]
    
    @extend_schema(
        summary="Создать отзыв о заказе",
        description="""
## Описание
Создает отзыв о выполненном заказе. Рейтинг автоматически применяется ко всем мастерам, 
назначенным на заказ (главный мастер и все мастера из списка).

## 🎯 Когда использовать?
- ✅ После завершения заказа (status = COMPLETED)
- ✅ Клиент хочет оценить работу мастера
- ✅ Один раз на заказ (повторные отзывы запрещены)

## Request Body
- `order_id`: ID завершенного заказа (обязательно)
- `rating`: Рейтинг от 1 до 5 (обязательно)
- `comment`: Текст отзыва (необязательно)
- `tag`: Что понравилось в работе мастера - выберите ОДНО (обязательно):
  - `fast_work` - Оперативная работа
  - `no_overpay` - Без переплат
  - `deadline` - Соблюдение сроков
  - `always_available` - Всегда на связи
  - `individual_approach` - Индивидуальный подход
  - `polite` - Вежливость

## Пример запроса:
```json
{
  "order_id": 5,
  "rating": 5,
  "comment": "Отличная работа! Быстро и качественно.",
  "tag": "fast_work"
}
```

## Response:
```json
{
  "message": "Отзыв успешно создан. Рейтинг применен к мастерам.",
  "review": {
    "id": 1,
    "order": 5,
    "rating": 5,
    "comment": "Отличная работа!",
    "tag": "fast_work",
    "tag_display": "Оперативная работа",
    "created_at": "2026-01-31T10:00:00Z"
  }
}
```

## Что происходит автоматически:
1. ✅ Отзыв сохраняется в БД
2. ✅ Рейтинг применяется ко ВСЕМ мастерам из заказа:
   - Главный мастер (order.master)
   - Все мастера из списка (order.masters)
3. ✅ Обновляется средний рейтинг каждого мастера
4. ✅ Рейтинг появляется в профиле мастера
        """,
        tags=['Orders (Driver) · Reviews'],
        request=ReviewCreateSerializer,
        responses={
            201: ReviewSerializer,
            400: {
                'type': 'object',
                'properties': {'error': {'type': 'string'}},
                'examples': {
                    'not_completed': {'value': {'error': 'Отзыв можно оставить только для завершенного заказа'}},
                    'already_exists': {'value': {'error': 'Отзыв для этого заказа уже оставлен'}}
                }
            },
            404: {
                'type': 'object',
                'properties': {'error': {'type': 'string'}},
                'example': {'error': 'Заказ не найден'}
            },
            401: {
                'type': 'object',
                'properties': {'detail': {'type': 'string'}}
            },
        }
    )
    def post(self, request):
        """Создать отзыв о заказе"""
        serializer = ReviewCreateSerializer(data=request.data)
        
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        order_id = serializer.validated_data['order_id']
        rating = serializer.validated_data['rating']
        comment = serializer.validated_data.get('comment', '')
        tag = serializer.validated_data['tag']
        
        try:
            order = Order.objects.get(id=order_id)
            
            # Создаем отзыв
            review = Review.objects.create(
                order=order,
                reviewer=request.user,
                rating=rating,
                comment=comment,
                tag=tag
            )
            
            # Рейтинг автоматически применится ко всем мастерам через save() метод

            # push -> masters attached to order
            recipients = []
            try:
                if order.master and getattr(order.master, 'user', None):
                    recipients.append(order.master.user)
            except Exception:
                pass
            try:
                recipients.extend(list(order.masters.all()))
            except Exception:
                pass
            for u in {r.id: r for r in recipients}.values():
                _safe_push(
                    u,
                    title='Новый отзыв',
                    body=f'По заказу №{order.id} оставлен отзыв. Откройте карточку заказа для деталей.',
                    data={'type': 'order_review', 'order_id': str(order.id)},
                )
            
            result_serializer = ReviewSerializer(review)
            return Response({
                'message': 'Отзыв успешно создан. Рейтинг применен к мастерам.',
                'review': result_serializer.data
            }, status=status.HTTP_201_CREATED)
        
        except Order.DoesNotExist:
            return Response(
                {'error': 'Заказ не найден'},
                status=status.HTTP_404_NOT_FOUND
            )


def _get_area_filter_for_orders(request):
    """Получение фильтра по прямоугольной области для orders_by_master - Order model ichidagi lat/long bilan"""
    # Получаем параметры точек
    point_params = {
        'point1': (request.query_params.get('point1_lat'), request.query_params.get('point1_lon')),
        'point2': (request.query_params.get('point2_lat'), request.query_params.get('point2_lon')),
        'point3': (request.query_params.get('point3_lat'), request.query_params.get('point3_lon')),
        'point4': (request.query_params.get('point4_lat'), request.query_params.get('point4_lon'))
    }
    
    # Проверяем, что все параметры переданы
    all_params = [param for point in point_params.values() for param in point]
    
    # Agar heч qanday parametr berilmagan bo'lsa, None qaytar
    if not any(all_params):
        return None
    
    # Agar ba'zi parametrlar berilgan bo'lsa, lekin barchasi emas bo'lsa, None qaytar
    if not all(all_params):
        return None
    
    # Валидируем и преобразуем координаты
    points = []
    for point_name, (lat_str, lon_str) in point_params.items():
        try:
            lat = float(lat_str)
            lon = float(lon_str)
            # Order model uchun coordinate validation
            if not (-90 <= lat <= 90):
                return None
            if not (-180 <= lon <= 180):
                return None
            points.append((lat, lon))
        except (ValueError, TypeError):
            return None
    
    # Вычисляем границы прямоугольника
    lats = [point[0] for point in points]
    lons = [point[1] for point in points]
    
    min_lat = min(lats)
    max_lat = max(lats)
    min_lon = min(lons)
    max_lon = max(lons)
    
    # Order model ichidagi latitude va longitude bilan filter qilamiz
    return {
        'latitude__gte': min_lat,
        'latitude__lte': max_lat,
        'longitude__gte': min_lon,
        'longitude__lte': max_lon
    }


class AvailableOrdersForMasterView(APIView):
    """
    API для получения доступных заказов для мастера
    Показывает заказы без назначенного мастера в радиусе от мастера
    """
    permission_classes = [IsAuthenticated]
    pagination_class = OrderPagination
    
    def calculate_distance(self, lat1, lon1, lat2, lon2):
        """
        Вычисление расстояния между двумя точками по формуле Haversine
        Возвращает расстояние в километрах
        """
        from math import radians, sin, cos, sqrt, atan2
        
        # Радиус Земли в километрах
        R = 6371.0
        
        # Конвертируем градусы в радианы
        lat1_rad = radians(lat1)
        lon1_rad = radians(lon1)
        lat2_rad = radians(lat2)
        lon2_rad = radians(lon2)
        
        # Разница координат
        dlat = lat2_rad - lat1_rad
        dlon = lon2_rad - lon1_rad
        
        # Формула Haversine
        a = sin(dlat / 2)**2 + cos(lat1_rad) * cos(lat2_rad) * sin(dlon / 2)**2
        c = 2 * atan2(sqrt(a), sqrt(1 - a))
        
        distance = R * c
        return distance
    
    @extend_schema(
        summary="Получить доступные заказы для мастера",
        description="""
## Описание
Возвращает список доступных заказов (без назначенного мастера) в радиусе от местоположения мастера.

## Обязательные параметры
- **master_id** - ID мастера (координаты берутся из профиля мастера)

## Необязательные параметры
- **radius** - Радиус поиска в километрах (по умолчанию 10 км, можно увеличить до 50+ км)

## Фильтры (все необязательные)

### 1. Тип проблемы (category)
- ID категории типа **by_order**
- Использует **smart filter** через service_type
- Пример: `category=1` (где 1 - это "Пробито колесо", service_type="Шиномонтаж")
- Найдёт все заказы с похожим service_type или именем категории

### 2. Район (location)
- Поиск по адресу заказа
- Пример: `location=Ташкент` или `location=Навои`
- Поиск нечувствителен к регистру (case-insensitive)

### 3. Тип ТС (car_category)
- ID категории машины типа **by_car**
- Прямой фильтр по ID
- Пример: `car_category=3` (где 3 - это "Легковой")

### 4. Приоритет (priority)
- Уровень приоритета заказа
- Значения: `low` (низкий) или `high` (высокий)
- Пример: `priority=high`

## Логика работы
1. Берутся координаты мастера из его профиля (Master.latitude, Master.longitude)
2. Фильтруются заказы где master=null И masters пустой список
3. Применяются дополнительные фильтры (category, location, car_category, priority)
4. Вычисляется расстояние от мастера до каждого заказа (Haversine formula)
5. Фильтруются заказы в пределах указанного радиуса
6. Сортировка по расстоянию (ближайшие сначала)

## Pagination
- По умолчанию 10 заказов на страницу
- Можно изменить через `page_size` (макс. 100)
- Навигация через `page` (номер страницы)

## Примеры запросов

**Базовый (только обязательные параметры):**
```
GET /api/order/available/?master_id=5
```

**С радиусом:**
```
GET /api/order/available/?master_id=5&radius=20
```

**С фильтром по проблеме:**
```
GET /api/order/available/?master_id=5&radius=15&category=1
```

**С несколькими фильтрами:**
```
GET /api/order/available/?master_id=5&radius=15&category=1&location=Ташкент&car_category=3&priority=high
```

**С пагинацией:**
```
GET /api/order/available/?master_id=5&radius=10&page=2&page_size=20
```
        """,
        tags=['Orders (Master) · Available'],
        parameters=[
            OpenApiParameter(
                name='master_id',
                type=OpenApiTypes.INT,
                location=OpenApiParameter.QUERY,
                description='ID мастера (обязательно). Координаты берутся из профиля мастера.',
                required=True
            ),
            OpenApiParameter(
                name='radius',
                type=OpenApiTypes.FLOAT,
                location=OpenApiParameter.QUERY,
                description='Радиус поиска в километрах. По умолчанию 10 км. Можно указать от 1 до 100 км.',
                required=False
            ),
            OpenApiParameter(
                name='category',
                type=OpenApiTypes.INT,
                location=OpenApiParameter.QUERY,
                description='Фильтр по типу проблемы. ID категории типа by_order. Использует smart filter через service_type (например: 1 для "Пробито колесо").',
                required=False
            ),
            OpenApiParameter(
                name='location',
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                description='Фильтр по району. Поиск по адресу заказа (например: "Ташкент", "Навои", "ул. Амира Темура").',
                required=False
            ),
            OpenApiParameter(
                name='car_category',
                type=OpenApiTypes.INT,
                location=OpenApiParameter.QUERY,
                description='Фильтр по типу ТС. ID категории машины типа by_car (например: 3 для "Легковой").',
                required=False
            ),
            OpenApiParameter(
                name='priority',
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                description='Фильтр по приоритету. Допустимые значения: "low" (низкий) или "high" (высокий).',
                required=False
            ),
            OpenApiParameter(
                name='page',
                type=OpenApiTypes.INT,
                location=OpenApiParameter.QUERY,
                description='Номер страницы для пагинации. Начинается с 1.',
                required=False
            ),
            OpenApiParameter(
                name='page_size',
                type=OpenApiTypes.INT,
                location=OpenApiParameter.QUERY,
                description='Количество заказов на странице. По умолчанию 10, максимум 100.',
                required=False
            ),
        ],
        responses={
            200: {
                'description': 'Успешный ответ с пагинацией',
                'content': {
                    'application/json': {
                        'example': {
                            'count': 5,
                            'next': 'http://localhost:8000/api/order/available/?master_id=5&page=2',
                            'previous': None,
                            'results': [
                                {
                                    'id': 10,
                                    'user': {
                                        'id': 4,
                                        'private_id': '829137',
                                        'full_name': 'Иван Иванов',
                                        'phone_number': '998914495644',
                                        'email': 'ivan@example.com',
                                        'avatar': 'http://localhost:8000/media/avatars/avatar.jpg'
                                    },
                                    'car_data': [
                                        {
                                            'id': 2,
                                            'brand': 'Toyota',
                                            'model': 'Camry',
                                            'year': 2020,
                                            'category': {'id': 3, 'name': 'Легковой', 'type_category': 'by_car'}
                                        }
                                    ],
                                    'category_data': [
                                        {
                                            'id': 1,
                                            'name': 'Пробито колесо',
                                            'type_category': 'by_order',
                                            'service_type': 'Шиномонтаж'
                                        }
                                    ],
                                    'text': 'Нужна помощь с заменой колеса',
                                    'status': 'pending',
                                    'priority': 'high',
                                    'location': 'ул. Навои, д. 15, Ташкент',
                                    'latitude': '41.3111000',
                                    'longitude': '69.2797000',
                                    'master': None,
                                    'masters': [],
                                    'distance': 2.35,
                                    'created_at': '2026-01-21T12:00:00Z',
                                    'updated_at': '2026-01-21T12:00:00Z'
                                }
                            ]
                        }
                    }
                }
            },
            400: {
                'description': 'Ошибка валидации параметров',
                'content': {
                    'application/json': {
                        'examples': {
                            'missing_master_id': {
                                'summary': 'Не указан master_id',
                                'value': {'error': 'Параметр master_id обязателен'}
                            },
                            'invalid_format': {
                                'summary': 'Неверный формат параметров',
                                'value': {'error': 'Неверный формат параметров'}
                            },
                            'no_coordinates': {
                                'summary': 'У мастера нет координат',
                                'value': {'error': 'У мастера не указаны координаты'}
                            }
                        }
                    }
                }
            },
            401: {
                'description': 'Не авторизован',
                'content': {
                    'application/json': {
                        'example': {'detail': 'Authentication credentials were not provided.'}
                    }
                }
            },
            404: {
                'description': 'Мастер не найден',
                'content': {
                    'application/json': {
                        'example': {'error': 'Мастер не найден'}
                    }
                }
            },
        }
    )
    def get(self, request):
        """Получить доступные заказы для мастера"""
        # Получаем параметры
        master_id = request.query_params.get('master_id')
        radius = request.query_params.get('radius', 10)  # По умолчанию 10 км
        
        # Валидация обязательных параметров
        if not master_id:
            return Response(
                {'error': 'Параметр master_id обязателен'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            master_id = int(master_id)
            radius = float(radius)
        except (ValueError, TypeError):
            return Response(
                {'error': 'Неверный формат параметров'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Проверяем существование мастера
        try:
            master = Master.objects.get(id=master_id)
        except Master.DoesNotExist:
            return Response(
                {'error': 'Мастер не найден'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Получаем координаты мастера
        if not master.latitude or not master.longitude:
            return Response(
                {'error': 'У мастера не указаны координаты'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        master_lat = float(master.latitude)
        master_long = float(master.longitude)
        
        # Получаем заказы без назначенного мастера
        # master=null И masters пустой (ManyToMany)
        from django.db.models import Count
        
        orders = Order.objects.annotate(
            masters_count=Count('masters')
        ).filter(
            master__isnull=True,
            masters_count=0,
            latitude__isnull=False,
            longitude__isnull=False
        )
        
        # Применяем дополнительные фильтры
        category_filter = request.query_params.get('category')
        location_filter = request.query_params.get('location')
        car_category_filter = request.query_params.get('car_category')
        priority_filter = request.query_params.get('priority')
        
        # Smart фильтр по категории проблемы (Тип проблемы)
        if category_filter:
            try:
                from apps.categories.models import Category
                category_id = int(category_filter)
                category = Category.objects.get(id=category_id)
                
                # Если это by_order категория - используем smart filter через service_type
                if category.type_category == 'by_order':
                    category_conditions = Q()
                    
                    if category.service_type:
                        # Ищем заказы с похожим service_type
                        category_conditions |= Q(category__service_type__icontains=category.service_type)
                    
                    if category.name:
                        # Также ищем по имени категории
                        category_conditions |= Q(category__name__icontains=category.name)
                    
                    if category_conditions:
                        orders = orders.filter(category_conditions)
                else:
                    # Для других типов - прямой фильтр по ID
                    orders = orders.filter(category__id=category_id)
                    
            except Category.DoesNotExist:
                pass
            except (ValueError, TypeError):
                pass
        
        # Фильтр по району (location)
        if location_filter:
            orders = orders.filter(location__icontains=location_filter)
        
        # Smart фильтр по типу ТС (car_category)
        if car_category_filter:
            try:
                from apps.categories.models import Category
                car_cat_id = int(car_category_filter)
                car_category = Category.objects.get(id=car_cat_id)
                
                # Прямой фильтр по ID категории машины
                orders = orders.filter(car__category__id=car_cat_id)
                
            except Category.DoesNotExist:
                pass
            except (ValueError, TypeError):
                pass
        
        # Фильтр по приоритету
        if priority_filter:
            orders = orders.filter(priority=priority_filter)
        
        # Убираем дубликаты после фильтров
        orders = orders.distinct()
        
        # Вычисляем расстояние и фильтруем по радиусу
        filtered_orders = []
        for order in orders:
            distance = self.calculate_distance(
                master_lat, master_long,
                float(order.latitude), float(order.longitude)
            )
            
            if distance <= radius:
                # Добавляем расстояние как атрибут
                order.distance = round(distance, 2)
                filtered_orders.append(order)
        
        # Сортируем по расстоянию (ближайшие сначала)
        filtered_orders.sort(key=lambda x: x.distance)
        
        # Применяем пагинацию
        paginator = self.pagination_class()
        page = paginator.paginate_queryset(filtered_orders, request)
        if page is not None:
            serializer = OrderSerializer(page, many=True, context={'request': request})
            return paginator.get_paginated_response(serializer.data)
        
        serializer = OrderSerializer(filtered_orders, many=True, context={'request': request})
        return Response(serializer.data)


class AddServicesToOrderView(APIView):
    """
    API для добавления услуг к заказу
    """
    permission_classes = [IsAuthenticated]
    
    @extend_schema(
        summary="Добавить услуги к заказу",
        description="""
## Описание
Добавляет выбранные услуги мастера к заказу.

## Request Body
- `order_id`: ID заказа
- `services_list`: Список ID услуг мастера (MasterServiceItems)
- `discount`: Скидка на заказ (необязательно, по умолчанию 0.00)

## Пример запроса:
```json
{
  "order_id": 5,
  "services_list": [1, 2, 3, 4, 5],
  "discount": 150.00
}
```

## Response
Возвращает список добавленных услуг с полной информацией о каждой услуге.
        """,
        tags=['Orders (Driver) · Services'],
        request=AddServicesToOrderSerializer,
        responses={
            201: OrderServiceSerializer(many=True),
            400: {
                'type': 'object',
                'properties': {
                    'error': {'type': 'string'}
                },
                'examples': {
                    'application/json': {
                        'example': {'error': 'Заказ с ID 999 не найден'}
                    }
                }
            },
            401: {'type': 'object', 'properties': {'detail': {'type': 'string'}}},
        }
    )
    def post(self, request):
        """Добавить услуги к заказу"""
        serializer = AddServicesToOrderSerializer(data=request.data)
        
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        order_id = serializer.validated_data['order_id']
        services_list = serializer.validated_data['services_list']
        discount = serializer.validated_data.get('discount', 0.00)
        
        # Получаем заказ
        try:
            order = Order.objects.get(id=order_id)
        except Order.DoesNotExist:
            return Response(
                {'error': f'Заказ с ID {order_id} не найден'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Обновляем скидку в заказе
        order.discount = discount
        order.save()
        
        # Создаем связи OrderService
        from apps.master.models import MasterServiceItems
        created_services = []
        
        for service_id in services_list:
            try:
                service_item = MasterServiceItems.objects.get(id=service_id)
                # Используем get_or_create чтобы избежать дубликатов
                order_service, created = OrderService.objects.get_or_create(
                    order=order,
                    master_service_item=service_item
                )
                created_services.append(order_service)
            except MasterServiceItems.DoesNotExist:
                continue
        
        # Сериализуем результат
        result_serializer = OrderServiceSerializer(created_services, many=True)

        # push -> order owner
        _safe_push(
            order.user,
            title='Услуги добавлены',
            body=f'Заказ №{order.id}: к заказу добавлены услуги. Проверьте состав и итоговую стоимость.',
            data={'type': 'order_services_added', 'order_id': str(order.id)},
        )
        return Response(result_serializer.data, status=status.HTTP_201_CREATED)


class MasterServicesListView(APIView):
    """
    API для получения услуг мастера
    """
    permission_classes = [IsAuthenticated]
    
    @extend_schema(
        summary="Получить услуги мастера",
        description="""
## Описание
Возвращает список всех услуг (MasterServiceItems) для указанного мастера.
Формат ответа аналогичен формату в detail мастера.

## Параметры
- `master_id`: ID мастера (обязательный)

## Пример запроса:
```
GET /api/order/services-list/?master_id=5
```

## Response
Возвращает список услуг мастера с полной информацией:
- ID услуги
- Название
- Цена (от - до)
- Категория
- Мастер
        """,
        tags=['Orders (Driver) · Services'],
        parameters=[
            OpenApiParameter(
                name='master_id',
                type=OpenApiTypes.INT,
                location=OpenApiParameter.QUERY,
                description='ID мастера',
                required=True
            ),
        ],
        responses={
            200: {
                'type': 'array',
                'items': {
                    'type': 'object',
                    'properties': {
                        'id': {'type': 'integer'},
                        'name': {'type': 'string'},
                        'price_from': {'type': 'number'},
                        'price_to': {'type': 'number'},
                        'category': {'type': 'object'},
                        'master_service': {'type': 'integer'},
                    }
                },
                'example': [
                    {
                        'id': 1,
                        'name': 'Замена масла',
                        'price_from': 1000.0,
                        'price_to': 2000.0,
                        'category': {
                            'id': 1,
                            'name': 'Ремонт двигателя'
                        },
                        'master_service': 5
                    }
                ]
            },
            400: {
                'type': 'object',
                'properties': {'error': {'type': 'string'}},
                'example': {'error': 'Параметр master_id обязателен'}
            },
            404: {
                'type': 'object',
                'properties': {'error': {'type': 'string'}},
                'example': {'error': 'Мастер не найден'}
            },
            401: {'type': 'object', 'properties': {'detail': {'type': 'string'}}},
        }
    )
    def get(self, request):
        """Получить услуги мастера"""
        master_id = request.query_params.get('master_id')
        
        if not master_id:
            return Response(
                {'error': 'Параметр master_id обязателен'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            master_id = int(master_id)
        except ValueError:
            return Response(
                {'error': 'Неверный формат master_id'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Проверяем существование мастера
        try:
            master = Master.objects.get(id=master_id)
        except Master.DoesNotExist:
            return Response(
                {'error': 'Мастер не найден'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Получаем все MasterServiceItems для этого мастера
        from apps.master.models import MasterServiceItems, MasterService
        from apps.master.serializers import MasterServiceItemsSerializer
        
        # Находим все MasterService для этого мастера
        master_services = MasterService.objects.filter(master=master)
        
        # Получаем все items этих services
        service_items = MasterServiceItems.objects.filter(
            master_service__in=master_services
        ).select_related('category', 'master_service')
        
        # Сериализуем
        serializer = MasterServiceItemsSerializer(service_items, many=True)
        return Response(serializer.data)


class AddMastersToOrderView(APIView):
    """
    API для добавления мастеров к заказу
    """
    permission_classes = [IsAuthenticated]
    
    @extend_schema(
        summary="Добавить мастеров к заказу",
        description="""
## Описание
Добавляет выбранных пользователей-мастеров к заказу.
Эти мастера будут назначены на заказ и получат уведомление.

## Request Body
- `order_id`: ID заказа (обязательно)
- `master_ids`: Список ID пользователей-мастеров [1, 2, 3, ...] (обязательно)

## Пример запроса:
```json
{
  "order_id": 5,
  "master_ids": [1, 2, 3]
}
```

## Response
Возвращает обновленный заказ со списком назначенных мастеров.

## 🎯 Когда использовать?
- Когда нужно назначить несколько мастеров на один заказ
- Когда мастер хочет делегировать заказ своим сотрудникам
- Для командной работы над сложным заказом
        """,
        tags=['Orders (Master) · Team'],
        request=AddMastersToOrderSerializer,
        responses={
            200: OrderSerializer,
            400: {
                'type': 'object',
                'properties': {'error': {'type': 'string'}},
                'example': {'error': 'Заказ с ID 999 не найден'}
            },
            404: {
                'type': 'object',
                'properties': {'error': {'type': 'string'}},
                'example': {'error': 'Заказ не найден'}
            },
            401: {'type': 'object', 'properties': {'detail': {'type': 'string'}}},
        }
    )
    def post(self, request):
        """Добавить мастеров к заказу"""
        serializer = AddMastersToOrderSerializer(data=request.data)
        
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        order_id = serializer.validated_data['order_id']
        master_ids = serializer.validated_data['master_ids']
        
        # Получаем заказ
        try:
            order = Order.objects.get(id=order_id)
        except Order.DoesNotExist:
            return Response(
                {'error': f'Заказ с ID {order_id} не найден'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Добавляем мастеров к заказу (ManyToMany)
        for master_id in master_ids:
            try:
                user = User.objects.get(id=master_id)
                order.masters.add(user)
                _safe_push(
                    user,
                    title='Назначение на заказ',
                    body=f'Вы назначены исполнителем по заказу №{order.id}. Откройте заказ для деталей.',
                    data={'type': 'order_master_added', 'order_id': str(order.id)},
                )
            except User.DoesNotExist:
                continue
        
        # Возвращаем обновленный заказ
        order.refresh_from_db()
        result_serializer = OrderSerializer(order, context={'request': request})
        return Response(result_serializer.data, status=status.HTTP_200_OK)
