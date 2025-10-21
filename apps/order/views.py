from rest_framework import status, filters
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Q
from django.contrib.auth import get_user_model

from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

from .models import Order, OrderStatus
from .serializers import OrderSerializer, OrderCreateSerializer, OrderUpdateSerializer
from .permissions import IsOrderOwnerOrMaster, IsOrderOwner, IsMaster
from apps.master.models import Master
from apps.master.serializers import MasterSerializer
from apps.accounts.models import UserBalance

User = get_user_model()


class OrderListCreateView(APIView):
    """Список заказов и создание нового заказа"""
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

    @swagger_auto_schema(
        operation_summary="Получить список заказов",
        operation_description="Возвращает список заказов с возможностью фильтрации, поиска и сортировки",
        tags=['Order'],
        manual_parameters=[
            openapi.Parameter(
                'status',
                openapi.IN_QUERY,
                description="Фильтр по статусу заказа",
                type=openapi.TYPE_STRING,
                enum=[choice[0] for choice in OrderStatus.choices]
            ),
            openapi.Parameter(
                'priority',
                openapi.IN_QUERY,
                description="Фильтр по приоритету заказа",
                type=openapi.TYPE_STRING,
                enum=['low', 'high']
            ),
            openapi.Parameter(
                'master',
                openapi.IN_QUERY,
                description="Фильтр по мастеру (ID мастера)",
                type=openapi.TYPE_INTEGER
            ),
            openapi.Parameter(
                'search',
                openapi.IN_QUERY,
                description="Поиск по тексту заказа, местоположению или имени пользователя",
                type=openapi.TYPE_STRING
            ),
            openapi.Parameter(
                'ordering',
                openapi.IN_QUERY,
                description="Сортировка по полю (created_at, updated_at, status, priority)",
                type=openapi.TYPE_STRING,
                enum=['created_at', '-created_at', 'updated_at', '-updated_at', 'status', '-status', 'priority', '-priority']
            ),
        ],
        responses={
            200: openapi.Response(
                description="Список заказов",
                schema=OrderSerializer(many=True)
            ),
            401: openapi.Response(description="Не авторизован"),
        }
    )
    def get(self, request):
        """Получить список заказов"""
        queryset = self.get_queryset()
        
        # Применяем фильтры
        queryset = self.apply_filters(queryset, request)
        
        serializer = OrderSerializer(queryset, many=True)
        return Response(serializer.data)

    @swagger_auto_schema(
        operation_summary="Создать новый заказ",
        operation_description="Создает новый заказ для текущего пользователя",
        tags=['Order'],
        request_body=OrderCreateSerializer,
        responses={
            201: openapi.Response(
                description="Заказ успешно создан",
                schema=OrderSerializer
            ),
            400: openapi.Response(description="Ошибка валидации данных"),
            401: openapi.Response(description="Не авторизован"),
        }
    )
    def post(self, request):
        """Создать новый заказ"""
        serializer = OrderCreateSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(user=request.user)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

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

    @swagger_auto_schema(
        operation_summary="Получить детали заказа",
        operation_description="Возвращает детальную информацию о конкретном заказе",
        tags=['Order'],
        manual_parameters=[
            openapi.Parameter(
                'id',
                openapi.IN_PATH,
                description="ID заказа",
                type=openapi.TYPE_INTEGER,
                required=True
            ),
        ],
        responses={
            200: openapi.Response(
                description="Детали заказа",
                schema=OrderSerializer
            ),
            404: openapi.Response(description="Заказ не найден"),
            401: openapi.Response(description="Не авторизован"),
            403: openapi.Response(description="Нет прав доступа"),
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

    @swagger_auto_schema(
        operation_summary="Полное обновление заказа",
        operation_description="Полностью обновляет все поля заказа",
        tags=['Order'],
        manual_parameters=[
            openapi.Parameter(
                'id',
                openapi.IN_PATH,
                description="ID заказа",
                type=openapi.TYPE_INTEGER,
                required=True
            ),
        ],
        request_body=OrderUpdateSerializer,
        responses={
            200: openapi.Response(
                description="Заказ успешно обновлен",
                schema=OrderSerializer
            ),
            400: openapi.Response(description="Ошибка валидации данных"),
            404: openapi.Response(description="Заказ не найден"),
            401: openapi.Response(description="Не авторизован"),
            403: openapi.Response(description="Нет прав доступа"),
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

    @swagger_auto_schema(
        operation_summary="Частичное обновление заказа",
        operation_description="Частично обновляет поля заказа",
        tags=['Order'],
        manual_parameters=[
            openapi.Parameter(
                'id',
                openapi.IN_PATH,
                description="ID заказа",
                type=openapi.TYPE_INTEGER,
                required=True
            ),
        ],
        request_body=OrderUpdateSerializer,
        responses={
            200: openapi.Response(
                description="Заказ успешно обновлен",
                schema=OrderSerializer
            ),
            400: openapi.Response(description="Ошибка валидации данных"),
            404: openapi.Response(description="Заказ не найден"),
            401: openapi.Response(description="Не авторизован"),
            403: openapi.Response(description="Нет прав доступа"),
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

    @swagger_auto_schema(
        operation_summary="Удалить заказ",
        operation_description="Удаляет заказ из системы",
        tags=['Order'],
        manual_parameters=[
            openapi.Parameter(
                'id',
                openapi.IN_PATH,
                description="ID заказа",
                type=openapi.TYPE_INTEGER,
                required=True
            ),
        ],
        responses={
            204: openapi.Response(description="Заказ успешно удален"),
            404: openapi.Response(description="Заказ не найден"),
            401: openapi.Response(description="Не авторизован"),
            403: openapi.Response(description="Нет прав доступа"),
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


@swagger_auto_schema(
    method='get',
    operation_summary="Получить заказы текущего пользователя",
    operation_description="Возвращает все заказы текущего авторизованного пользователя",
    tags=['Order'],
    responses={
        200: openapi.Response(
            description="Список заказов пользователя",
            schema=OrderSerializer(many=True)
        ),
        401: openapi.Response(description="Не авторизован"),
    }
)
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def orders_by_user(request):
    """Получить заказы текущего пользователя с опциональным фильтром по имени мастера"""
    orders = Order.objects.filter(user=request.user)
    # name: фильтр по имени мастера (optional)
    name = request.query_params.get('name')
    if name:
        orders = orders.filter(
            Q(master__user__first_name__icontains=name) |
            Q(master__user__last_name__icontains=name) |
            Q(master__user__get_full_name__icontains=name)
        )
    serializer = OrderSerializer(orders, many=True)
    return Response(serializer.data)


@swagger_auto_schema(
    method='get',
    operation_summary="Получить заказы текущего мастера в области",
    operation_description="Возвращает список заказов, назначенных текущему мастеру, с фильтрацией по географической области (4 точки)",
    tags=['Order'],
    manual_parameters=[
        openapi.Parameter(
            'status',
            openapi.IN_QUERY,
            description="Фильтр по статусу заказа",
            type=openapi.TYPE_STRING,
            enum=[choice[0] for choice in OrderStatus.choices]
        ),
        openapi.Parameter(
            'priority',
            openapi.IN_QUERY,
            description="Фильтр по приоритету заказа",
            type=openapi.TYPE_STRING,
            enum=['low', 'high']
        ),
        # Координаты полигона (4 точки) для фильтрации по локации заказов
        openapi.Parameter('point1_lat', openapi.IN_QUERY, description='Широта точки 1', type=openapi.TYPE_NUMBER),
        openapi.Parameter('point1_lon', openapi.IN_QUERY, description='Долгота точки 1', type=openapi.TYPE_NUMBER),
        openapi.Parameter('point2_lat', openapi.IN_QUERY, description='Широта точки 2', type=openapi.TYPE_NUMBER),
        openapi.Parameter('point2_lon', openapi.IN_QUERY, description='Долгота точки 2', type=openapi.TYPE_NUMBER),
        openapi.Parameter('point3_lat', openapi.IN_QUERY, description='Широта точки 3', type=openapi.TYPE_NUMBER),
        openapi.Parameter('point3_lon', openapi.IN_QUERY, description='Долгота точки 3', type=openapi.TYPE_NUMBER),
        openapi.Parameter('point4_lat', openapi.IN_QUERY, description='Широта точки 4', type=openapi.TYPE_NUMBER),
        openapi.Parameter('point4_lon', openapi.IN_QUERY, description='Долгота точки 4', type=openapi.TYPE_NUMBER),
    ],
    responses={
        200: openapi.Response(
            description="Список заказов мастера в области",
            schema=OrderSerializer(many=True)
        ),
        401: openapi.Response(description="Не авторизован"),
        403: openapi.Response(description="Пользователь не является мастером"),
    }
)
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def orders_by_master(request):
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
    
    # Фильтр по статусу
    status_filter = request.query_params.get('status')
    if status_filter:
        orders = orders.filter(status=status_filter)
    
    # Фильтр по приоритету
    priority_filter = request.query_params.get('priority')
    if priority_filter:
        orders = orders.filter(priority=priority_filter)
    
    # Фильтр по локации: 4 точки полигона (bounding box)
    area_filter = _get_area_filter_for_orders(request)
    if area_filter:
        # Faqat koordinatalari bo'lgan orderlarni filter qilamiz
        orders = orders.filter(
            latitude__isnull=False,
            longitude__isnull=False,
            **area_filter
        )
    
    serializer = OrderSerializer(orders, many=True)
    return Response(serializer.data)




# by-name endpoint removed; name filtering added into by-user and by-master


@swagger_auto_schema(
    method='post',
    operation_summary="Обновить статус заказа",
    operation_description="Обновляет статус заказа на новый",
    tags=['Order'],
    manual_parameters=[
        openapi.Parameter(
            'order_id',
            openapi.IN_PATH,
            description="ID заказа",
            type=openapi.TYPE_INTEGER,
            required=True
        ),
    ],
    request_body=openapi.Schema(
        type=openapi.TYPE_OBJECT,
        properties={
            'status': openapi.Schema(
                type=openapi.TYPE_STRING,
                description="Новый статус заказа",
                enum=[choice[0] for choice in OrderStatus.choices]
            )
        },
        required=['status']
    ),
    responses={
        200: openapi.Response(
            description="Статус заказа успешно обновлен",
            schema=OrderSerializer
        ),
        400: openapi.Response(description="Статус обязателен или недопустимый статус"),
        404: openapi.Response(description="Заказ не найден"),
        401: openapi.Response(description="Не авторизован"),
        403: openapi.Response(description="Нет прав для изменения этого заказа"),
    }
)
@api_view(['POST'])
@permission_classes([IsAuthenticated, IsOrderOwnerOrMaster])
def update_order_status(request, order_id):
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


@swagger_auto_schema(
    method='post',
    operation_summary="Принять заказ в работу",
    operation_description="Принимает заказ в работу с проверкой минимального баланса пользователя (1000 ₽) и списанием 200 ₽ за каждый заказ",
    tags=['Order'],
    manual_parameters=[
        openapi.Parameter(
            'order_id',
            openapi.IN_PATH,
            description="ID заказа",
            type=openapi.TYPE_INTEGER,
            required=True
        ),
    ],
    responses={
        200: openapi.Response(
            description="Заказ успешно принят в работу",
            schema=openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'message': openapi.Schema(type=openapi.TYPE_STRING),
                    'order': openapi.Schema(type=openapi.TYPE_OBJECT),
                    'balance_after': openapi.Schema(type=openapi.TYPE_NUMBER)
                }
            )
        ),
        400: openapi.Response(description="Недостаточно средств на балансе или заказ уже принят"),
        404: openapi.Response(description="Заказ не найден"),
        401: openapi.Response(description="Не авторизован"),
        403: openapi.Response(description="Только мастера могут принимать заказы"),
    }
)
@api_view(['POST'])
@permission_classes([IsAuthenticated, IsMaster])
def accept_order(request, order_id):
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
            return Response(
                {'error': 'На балансе должно быть минимум 1000 ₽, чтобы брать заказы в работу'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Проверяем, может ли пользователь позволить себе заказ (200 ₽)
        if not user_balance.can_afford_order(200):
            return Response(
                {'error': 'Недостаточно средств для принятия заказа. Требуется 200 ₽'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
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
            return Response(
                {'error': 'Ошибка при списании средств с баланса'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
    
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
