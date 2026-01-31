from rest_framework import status, filters
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.pagination import PageNumberPagination
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Q
from django.contrib.auth import get_user_model

from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiExample
from drf_spectacular.types import OpenApiTypes

from .models import Order, OrderStatus, OrderType, Rating, OrderService, Review, ReviewTag
from .serializers import (
    OrderSerializer, OrderCreateSerializer, OrderUpdateSerializer, RatingSerializer,
    AddServicesToOrderSerializer, OrderServiceSerializer, AddMastersToOrderSerializer,
    ReviewSerializer, ReviewCreateSerializer
)
from .permissions import IsOrderOwnerOrMaster, IsOrderOwner, IsMaster
from apps.master.models import Master
from apps.master.serializers import MasterSerializer
from apps.accounts.models import UserBalance

User = get_user_model()


class OrderPagination(PageNumberPagination):
    """Пагинация для заказов"""
    page_size = 10
    page_size_query_param = 'page_size'
    max_page_size = 100


class ScheduledOrderCreateView(APIView):
    """Создание запланированного заказа (Order by Date)"""
    permission_classes = [IsAuthenticated]
    
    @extend_schema(
        summary="📅 Создать запланированный заказ (Order by Date)",
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
        tags=['Orders'],
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
        summary="🚨 Создать SOS заказ (экстренная помощь)",
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
- **master_id**: ID мастера/мастерской (обязательно)
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
2. **Мастер выбирается клиентом** - клиент указывает конкретного мастера
3. **Расстояние до мастера <= 50 км** - система проверит, что мастер находится в пределах 50 км от клиента
4. **Уведомление мастеру** - выбранный мастер получит push-уведомление о новом SOS заказе

## 📝 Примеры использования:

### Пример 1: Пробито колесо на трассе (высокий приоритет)
```json
{
  "order_type": "sos",
  "master_id": 5,
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
  "master_id": 8,
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
3. Клиент выбирает мастера из списка ближайших
4. Клиент описывает проблему и выбирает приоритет
5. ✅ Выбранный мастер получает уведомление о SOS заказе
6. Мастер подтверждает или отклоняет заказ
7. Клиент видит информацию о мастере и может с ним связаться
        """,
        tags=['Orders'],
        request={
            'application/json': {
                'type': 'object',
                'required': ['order_type', 'master_id', 'priority', 'text', 'location', 'latitude', 'longitude', 'car_list', 'category_list'],
                'properties': {
                    'order_type': {'type': 'string', 'enum': ['sos'], 'description': 'Тип заказа (всегда "sos")', 'example': 'sos'},
                    'master_id': {'type': 'integer', 'description': 'ID мастера/мастерской (обязательно)', 'example': 5},
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
        
        serializer = OrderCreateSerializer(data=data)
        if serializer.is_valid():
            order = serializer.save(user=request.user)
            order_serializer = OrderSerializer(order)
            return Response({
                'message': 'Ваш экстренный заказ успешно создан и отправлен мастеру',
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
        tags=['Orders'],
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
        
        # Парсим рабочее время мастера (например: "09:00-18:00")
        working_time = master.working_time or "09:00-18:00"
        
        try:
            start_time_str, end_time_str = working_time.split('-')
            start_hour, start_minute = map(int, start_time_str.strip().split(':'))
            end_hour, end_minute = map(int, end_time_str.strip().split(':'))
        except:
            # Если не удалось распарсить, используем дефолтные значения
            start_hour, start_minute = 9, 0
            end_hour, end_minute = 18, 0
        
        # Генерируем временные слоты (каждые 2 часа)
        slots = []
        current_hour = start_hour
        current_minute = start_minute
        
        while current_hour < end_hour:
            slot_start = time(current_hour, current_minute)
            
            # Добавляем 2 часа
            next_hour = current_hour + 2
            next_minute = current_minute
            
            # Проверяем, не выходим ли за рабочее время
            if next_hour > end_hour or (next_hour == end_hour and next_minute > end_minute):
                break
            
            slot_end = time(next_hour, next_minute)
            
            slots.append({
                'start': slot_start.strftime('%H:%M'),
                'end': slot_end.strftime('%H:%M'),
            })
            
            current_hour = next_hour
            current_minute = next_minute
        
        # Получаем существующие заказы на эту дату для этого мастера
        existing_orders = Order.objects.filter(
            master=master,
            order_type=OrderType.SCHEDULED,
            scheduled_date=check_date,
            status__in=[OrderStatus.PENDING, OrderStatus.IN_PROGRESS]
        ).select_related('user')
        
        # Проверяем доступность каждого слота
        for slot in slots:
            slot['available'] = True
            
            for order in existing_orders:
                if not order.scheduled_time_start or not order.scheduled_time_end:
                    continue
                
                order_start = order.scheduled_time_start.strftime('%H:%M')
                order_end = order.scheduled_time_end.strftime('%H:%M')
                
                # Проверяем пересечение временных интервалов
                slot_start_time = datetime.strptime(slot['start'], '%H:%M').time()
                slot_end_time = datetime.strptime(slot['end'], '%H:%M').time()
                
                # Если заказ пересекается со слотом
                if (order.scheduled_time_start < slot_end_time and 
                    order.scheduled_time_end > slot_start_time):
                    slot['available'] = False
                    slot['order_id'] = order.id
                    break
        
        return Response({
            'date': date_str,
            'master_id': master.id,
            'master_name': master.name or master.user.get_full_name(),
            'working_hours': working_time,
            'slots': slots
        })


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
        tags=['Orders'],
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
        tags=['Orders'],
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
        tags=['Orders'],
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
        tags=['Orders'],
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
        tags=['Orders'],
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
        tags=['Orders'],
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
        tags=['Orders'],
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
        
        # Фильтр is_work - заказы в работе (IN_PROGRESS)
        is_work = request.query_params.get('is_work', '').lower() == 'true'
        if is_work:
            orders = Order.objects.filter(master=master, status=OrderStatus.IN_PROGRESS)
        
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
        summary="Обновить статус заказа",
        description="Обновляет статус заказа на новый. "
                  "Статусы: pending - ожидает, in_progress - в работе, completed - завершен, cancelled - отменен, rejected - отклонен. "
                  "Доступно только владельцу заказа или мастеру.",
        tags=['Orders'],
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
            
            order.status = new_status
            order.save()
            
            serializer = OrderSerializer(order)
            return Response(serializer.data)
        
        except Order.DoesNotExist:
            return Response(
                {'error': 'Заказ не найден'}, 
                status=status.HTTP_404_NOT_FOUND
            )


class AcceptOrderView(APIView):
    """
    API для принятия заказа в работу
    """
    permission_classes = [IsAuthenticated, IsMaster]
    
    @extend_schema(
        summary="Принять заказ в работу",
        description="""
Принимает заказ в работу с проверкой минимального баланса пользователя (1000 ₽) и списанием 200 ₽ за каждый заказ.

## Проверки баланса:
1. **Минимальный баланс**: На балансе должно быть минимум 1000 ₽
2. **Списание за заказ**: С баланса спишется 200 ₽ при принятии заказа

## Response при ошибке баланса:
```json
{
  "error": "Описание ошибки",
  "current_balance": 500.00,
  "required_balance": 1000
}
```
        """,
        tags=['Orders'],
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
            
            # Проверяем, что заказ не назначен другому мастеру
            master = request.user.master_profiles.first()
            if order.master and order.master.id != master.id:
                return Response(
                    {'error': 'Заказ уже назначен другому мастеру'}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Проверяем, что заказ не истек
            if order.is_expired():
                order.mark_as_cancelled_if_expired()
                return Response(
                    {'error': 'Заказ истек и был отменен'}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Проверяем баланс пользователя (владельца заказа)
            user_balance = UserBalance.get_or_create_balance(order.user)
            print(f"DEBUG: user_balance = {user_balance}")
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
                # Назначаем заказ текущему мастеру и меняем статус
                order.master = master
                order.status = OrderStatus.IN_PROGRESS
                order.save()
                
                # Обновляем баланс после списания
                user_balance.refresh_from_db()
                
                serializer = OrderSerializer(order)
                return Response({
                    'message': 'Заказ взят в работу. 200 ₽ были списаны с баланса.',
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
    permission_classes = [IsAuthenticated]
    
    @extend_schema(
        summary="Завершить заказ",
        description="""
## Описание
Завершает заказ, устанавливая статус **COMPLETED** (Завершен).

## 🎯 Когда использовать?
- ✅ Работа по заказу выполнена
- ✅ Клиент доволен результатом
- ✅ Заказ готов к закрытию
- ✅ Можно оставить рейтинг и отзыв

## Требования:
- Заказ должен существовать
- Пользователь должен быть авторизован

## Пример запроса:
```
POST /api/order/5/complete/
```

## Response:
```json
{
  "message": "Заказ успешно завершен",
  "order": {
    "id": 5,
    "status": "completed",
    "status_display": "Завершен",
    "user": {...},
    "master": {...},
    "text": "Замена масла",
    "created_at": "2026-01-30T10:00:00Z"
  }
}
```

## Workflow:
1. Мастер завершает работу по заказу
2. Отправляет POST запрос на `/api/order/{order_id}/complete/`
3. Заказ переходит в статус **COMPLETED**
4. Клиент может оставить рейтинг и отзыв
        """,
        tags=['Orders'],
        parameters=[
            {'name': 'order_id', 'in': 'path', 'description': 'ID заказа', 'type': 'integer', 'required': True},
        ],
        responses={
            200: {
                'type': 'object',
                'properties': {
                    'message': {'type': 'string', 'example': 'Заказ успешно завершен'},
                    'order': {'$ref': '#/components/schemas/Order'}
                }
            },
            404: {
                'type': 'object',
                'properties': {'error': {'type': 'string', 'example': 'Заказ не найден'}}
            },
            401: {
                'type': 'object',
                'properties': {'detail': {'type': 'string', 'example': 'Authentication credentials were not provided.'}}
            },
        }
    )
    def post(self, request, order_id):
        """Завершить заказ (установить статус COMPLETED)"""
        try:
            order = Order.objects.get(id=order_id)
            
            # Устанавливаем статус COMPLETED
            order.status = OrderStatus.COMPLETED
            order.save()
            
            serializer = OrderSerializer(order, context={'request': request})
            return Response({
                'message': 'Заказ успешно завершен',
                'order': serializer.data
            }, status=status.HTTP_200_OK)
        
        except Order.DoesNotExist:
            return Response(
                {'error': 'Заказ не найден'}, 
                status=status.HTTP_404_NOT_FOUND
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
        tags=['Orders'],
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


class RatingCreateView(APIView):
    """
    API для создания рейтинга для заказа.
    
    POST: создание рейтинга для мастера или мастера в мастере
    """
    permission_classes = [IsAuthenticated]
    
    @extend_schema(
        summary="Создать рейтинг",
        description="Создает рейтинг для мастера или мастера в мастере после завершения заказа",
        tags=['Rating'],
        request={
            'application/json': {
                'type': 'object',
                'properties': {
                    'order': {'type': 'integer', 'description': 'ID заказа'},
                    'master': {'type': 'integer', 'description': 'ID мастера'},
                    'rating': {'type': 'integer', 'description': 'Рейтинг от 1 до 5'},
                    'comment': {'type': 'string', 'description': 'Комментарий'}
                },
                'required': ['order', 'rating']
            }
        },
        responses={
            201: RatingSerializer,
            400: {'type': 'object', 'properties': {'detail': {'type': 'string'}}},
            404: {'type': 'object', 'properties': {'error': {'type': 'string'}}},
            401: {'type': 'object', 'properties': {'detail': {'type': 'string'}}}
        }
    )
    def post(self, request):
        """Создание рейтинга"""
        serializer = RatingSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            order_id = serializer.validated_data.get('order').id
            
            # Проверяем, что заказ существует и принадлежит пользователю
            try:
                order = Order.objects.get(id=order_id, user=request.user)
            except Order.DoesNotExist:
                return Response(
                    {'error': 'Заказ не найден или не принадлежит вам'},
                    status=status.HTTP_404_NOT_FOUND
                )
            
            # Проверяем, что заказ завершен
            if order.status != OrderStatus.COMPLETED:
                return Response(
                    {'error': 'Рейтинг можно оставить только для завершенных заказов'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Проверяем, что рейтинг еще не был оставлен
            master = serializer.validated_data.get('master')
            
            if master:
                if Rating.objects.filter(order=order, user=request.user, master=master).exists():
                    return Response(
                        {'error': 'Вы уже оставили рейтинг для этого мастера по этому заказу'},
                        status=status.HTTP_400_BAD_REQUEST
                    )
            
            rating = serializer.save()
            return Response(RatingSerializer(rating, context={'request': request}).data, status=status.HTTP_201_CREATED)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class RatingListView(APIView):
    """
    API для получения списка рейтингов.
    
    GET: получение рейтингов для мастера или мастера в мастере
    """
    permission_classes = [IsAuthenticated]
    
    @extend_schema(
        summary="Получить список рейтингов",
        description="Возвращает список рейтингов для мастера",
        tags=['Rating'],
        parameters=[
            {'name': 'master', 'in': 'query', 'description': 'ID мастера', 'type': 'integer', 'required': True}
        ],
        responses={
            200: RatingSerializer(many=True),
            401: {'type': 'object', 'properties': {'detail': {'type': 'string'}}}
        }
    )
    def get(self, request):
        """Получение списка рейтингов"""
        master_id = request.query_params.get('master')
        
        if not master_id:
            return Response(
                {'error': 'Необходимо указать master'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        ratings = Rating.objects.filter(master_id=master_id)
        
        serializer = RatingSerializer(ratings, many=True, context={'request': request})
        return Response(serializer.data, status=status.HTTP_200_OK)


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
        tags=['Orders'],
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
        
        print(f"\n{'='*60}")
        print(f"ПОИСК ДОСТУПНЫХ ЗАКАЗОВ ДЛЯ МАСТЕРА ID: {master_id}")
        print(f"Координаты мастера: lat={master_lat}, long={master_long}")
        print(f"Радиус поиска: {radius} км")
        print(f"{'='*60}")
        
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
                
                print(f"Фильтр по категории: ID={category_filter}, Name={category.name}, Type={category.type_category}")
                
                # Если это by_order категория - используем smart filter через service_type
                if category.type_category == 'by_order':
                    category_conditions = Q()
                    
                    if category.service_type:
                        # Ищем заказы с похожим service_type
                        category_conditions |= Q(category__service_type__icontains=category.service_type)
                        print(f"  Smart filter по service_type: {category.service_type}")
                    
                    if category.name:
                        # Также ищем по имени категории
                        category_conditions |= Q(category__name__icontains=category.name)
                        print(f"  Smart filter по name: {category.name}")
                    
                    if category_conditions:
                        orders = orders.filter(category_conditions)
                else:
                    # Для других типов - прямой фильтр по ID
                    orders = orders.filter(category__id=category_id)
                    print(f"  Прямой filter по ID")
                    
            except Category.DoesNotExist:
                print(f"  ОШИБКА: Категория {category_filter} не найдена")
            except (ValueError, TypeError):
                print(f"  ОШИБКА: Неверный формат category ID")
        
        # Фильтр по району (location)
        if location_filter:
            orders = orders.filter(location__icontains=location_filter)
            print(f"Фильтр по району: {location_filter}")
        
        # Smart фильтр по типу ТС (car_category)
        if car_category_filter:
            try:
                from apps.categories.models import Category
                car_cat_id = int(car_category_filter)
                car_category = Category.objects.get(id=car_cat_id)
                
                print(f"Фильтр по типу ТС: ID={car_cat_id}, Name={car_category.name}, Type={car_category.type_category}")
                
                # Прямой фильтр по ID категории машины
                orders = orders.filter(car__category__id=car_cat_id)
                print(f"  Filter по car__category__id")
                
            except Category.DoesNotExist:
                print(f"  ОШИБКА: Категория машины {car_category_filter} не найдена")
            except (ValueError, TypeError):
                print(f"  ОШИБКА: Неверный формат car_category ID")
        
        # Фильтр по приоритету
        if priority_filter:
            orders = orders.filter(priority=priority_filter)
            print(f"Фильтр по приоритету: {priority_filter}")
        
        # Убираем дубликаты после фильтров
        orders = orders.distinct()
        
        print(f"\nВсего найдено заказов без мастера (после фильтров): {orders.count()}")
        
        # Вычисляем расстояние и фильтруем по радиусу
        filtered_orders = []
        for order in orders:
            distance = self.calculate_distance(
                master_lat, master_long,
                float(order.latitude), float(order.longitude)
            )
            
            print(f"\nOrder ID: {order.id}")
            print(f"  Координаты: lat={order.latitude}, long={order.longitude}")
            print(f"  Расстояние от мастера: {distance:.2f} км")
            print(f"  Радиус: {radius} км")
            print(f"  Попадает в радиус: {'✅ ДА' if distance <= radius else '❌ НЕТ'}")
            
            if distance <= radius:
                # Добавляем расстояние как атрибут
                order.distance = round(distance, 2)
                filtered_orders.append(order)
        
        print(f"\n{'='*60}")
        print(f"ИТОГО заказов в радиусе {radius} км: {len(filtered_orders)}")
        print(f"{'='*60}\n")
        
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
        tags=['Orders'],
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
        tags=['Orders'],
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
        tags=['Orders'],
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
            except User.DoesNotExist:
                continue
        
        # Возвращаем обновленный заказ
        order.refresh_from_db()
        result_serializer = OrderSerializer(order, context={'request': request})
        return Response(result_serializer.data, status=status.HTTP_200_OK)
