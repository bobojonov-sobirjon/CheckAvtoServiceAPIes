from rest_framework.views import APIView
from rest_framework import status
from rest_framework.response import Response
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from django.db.models import Q
from .models import Master, ServiceType, MasterService
from .serializers import (
    MasterSerializer, MasterCreateSerializer, MasterUpdateSerializer, MasterNearbySerializer,
    MasterServiceSerializer
)
from .permissions import IsMasterGroup


class MasterProfileView(APIView):
    """
    API для управления профилем мастера.
    
    Поддерживаемые операции:
    - GET: получение профиля текущего пользователя
    - POST: создание профиля или управление услугами
    """
    permission_classes = [IsMasterGroup]
    
    def get_object(self):
        """Получение всех профилей мастера текущего пользователя"""
        return Master.objects.filter(user=self.request.user)
    
    @swagger_auto_schema(
        operation_description="Получить профиль мастера",
        security=[{'Bearer': []}],
        responses={
            200: openapi.Response(
                description="Профиль мастера или пустой массив если профиль не найден",
                schema=openapi.Schema(
                    type=openapi.TYPE_ARRAY,
                    items=openapi.Schema(
                        type=openapi.TYPE_OBJECT,
                        properties={
                            'id': openapi.Schema(type=openapi.TYPE_INTEGER),
                            'user_info': openapi.Schema(
                                type=openapi.TYPE_OBJECT,
                                properties={
                                    'id': openapi.Schema(type=openapi.TYPE_INTEGER),
                                    'full_name': openapi.Schema(type=openapi.TYPE_STRING),
                                    'phone_number': openapi.Schema(type=openapi.TYPE_STRING),
                                    'email': openapi.Schema(type=openapi.TYPE_STRING),
                                    'is_active': openapi.Schema(type=openapi.TYPE_BOOLEAN),
                                    'date_joined': openapi.Schema(type=openapi.TYPE_STRING, format=openapi.FORMAT_DATETIME)
                                }
                            ),
                            'city': openapi.Schema(type=openapi.TYPE_STRING),
                            'address': openapi.Schema(type=openapi.TYPE_STRING),
                            'latitude': openapi.Schema(type=openapi.TYPE_NUMBER),
                            'longitude': openapi.Schema(type=openapi.TYPE_NUMBER),
                            'service_type': openapi.Schema(type=openapi.TYPE_STRING),
                            'service_type_display': openapi.Schema(type=openapi.TYPE_STRING),
                            'services': openapi.Schema(type=openapi.TYPE_ARRAY, items=openapi.Schema(type=openapi.TYPE_STRING)),
                            'card_number': openapi.Schema(type=openapi.TYPE_STRING),
                            'card_expiry_month': openapi.Schema(type=openapi.TYPE_INTEGER),
                            'card_expiry_year': openapi.Schema(type=openapi.TYPE_INTEGER),
                            'card_cvv': openapi.Schema(type=openapi.TYPE_STRING),
                            'balance': openapi.Schema(type=openapi.TYPE_NUMBER),
                            'created_at': openapi.Schema(type=openapi.TYPE_STRING, format=openapi.FORMAT_DATETIME),
                            'updated_at': openapi.Schema(type=openapi.TYPE_STRING, format=openapi.FORMAT_DATETIME),
                            'last_activity': openapi.Schema(type=openapi.TYPE_STRING, format=openapi.FORMAT_DATETIME)
                        }
                    )
                )
            ),
            403: openapi.Response(description="Нет прав доступа")
        },
        tags=['Masters']
    )
    def get(self, request):
        """Получение всех профилей мастера"""
        masters = self.get_object()
        if not masters.exists():
            return Response([], status=status.HTTP_200_OK)
        
        serializer = MasterSerializer(masters, many=True, context={'request': request})
        return Response(serializer.data, status=status.HTTP_200_OK)
    
    @swagger_auto_schema(
        operation_description="Создать профиль мастера",
        security=[{'Bearer': []}],
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'city': openapi.Schema(type=openapi.TYPE_STRING, description='Город'),
                'address': openapi.Schema(type=openapi.TYPE_STRING, description='Адрес'),
                'latitude': openapi.Schema(type=openapi.TYPE_NUMBER, description='Широта'),
                'longitude': openapi.Schema(type=openapi.TYPE_NUMBER, description='Долгота'),
                'service_type': openapi.Schema(type=openapi.TYPE_STRING, description='Тип услуги (diagnostics, service, tire_repair, towing, car_wash, road_help)'),
                'services': openapi.Schema(
                    type=openapi.TYPE_ARRAY, 
                    items=openapi.Schema(
                        type=openapi.TYPE_OBJECT,
                        properties={
                            'name': openapi.Schema(type=openapi.TYPE_STRING, description='Название услуги'),
                            'price_from': openapi.Schema(type=openapi.TYPE_NUMBER, description='Цена от'),
                            'price_to': openapi.Schema(type=openapi.TYPE_NUMBER, description='Цена до')
                        }
                    ), 
                    description='Список услуг мастера'
                ),
                'card_number': openapi.Schema(type=openapi.TYPE_STRING, description='Номер карты'),
                'card_expiry_month': openapi.Schema(type=openapi.TYPE_INTEGER, description='Месяц истечения'),
                'card_expiry_year': openapi.Schema(type=openapi.TYPE_INTEGER, description='Год истечения'),
                'card_cvv': openapi.Schema(type=openapi.TYPE_STRING, description='CVV/CVC')
            }
        ),
        responses={
            201: openapi.Response(
                description="Профиль мастера создан",
                schema=openapi.Schema(
                    type=openapi.TYPE_ARRAY,
                    items=openapi.Schema(
                        type=openapi.TYPE_OBJECT,
                    properties={
                        'id': openapi.Schema(type=openapi.TYPE_INTEGER),
                        'user': openapi.Schema(type=openapi.TYPE_INTEGER),
                        'user_name': openapi.Schema(type=openapi.TYPE_STRING),
                        'user_phone': openapi.Schema(type=openapi.TYPE_STRING),
                        'city': openapi.Schema(type=openapi.TYPE_STRING),
                        'address': openapi.Schema(type=openapi.TYPE_STRING),
                        'latitude': openapi.Schema(type=openapi.TYPE_NUMBER),
                        'longitude': openapi.Schema(type=openapi.TYPE_NUMBER),
                        'service_type': openapi.Schema(type=openapi.TYPE_STRING),
                        'services': openapi.Schema(type=openapi.TYPE_ARRAY, items=openapi.Schema(type=openapi.TYPE_STRING)),
                        'services_display': openapi.Schema(type=openapi.TYPE_ARRAY, items=openapi.Schema(type=openapi.TYPE_STRING)),
                        'card_number': openapi.Schema(type=openapi.TYPE_STRING),
                        'card_expiry_month': openapi.Schema(type=openapi.TYPE_INTEGER),
                        'card_expiry_year': openapi.Schema(type=openapi.TYPE_INTEGER),
                        'card_cvv': openapi.Schema(type=openapi.TYPE_STRING),
                        'reserved_amount': openapi.Schema(type=openapi.TYPE_NUMBER),
                        'created_at': openapi.Schema(type=openapi.TYPE_STRING, format=openapi.FORMAT_DATETIME),
                        'updated_at': openapi.Schema(type=openapi.TYPE_STRING, format=openapi.FORMAT_DATETIME),
                        'last_activity': openapi.Schema(type=openapi.TYPE_STRING, format=openapi.FORMAT_DATETIME)
                        }
                    )
                )
            ),
            400: openapi.Response(description="Неверные данные"),
            403: openapi.Response(description="Нет прав доступа")
        },
        tags=['Masters']
    )
    def post(self, request):
        """Создание профиля мастера"""
        serializer = MasterCreateSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            master = serializer.save()
            response_serializer = MasterSerializer(master, context={'request': request})
            return Response([response_serializer.data], status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class MasterListView(APIView):
    """
    API для получения списка мастеров с возможностью фильтрации.
    
    Поддерживаемые фильтры:
    - city: фильтр по городу
    - service: фильтр по типу услуги
    - point1_lat, point1_lon, point2_lat, point2_lon, point3_lat, point3_lon, point4_lat, point4_lon: 
      фильтр по прямоугольной области (4 точки)
    - page, page_size: пагинация
    """
    permission_classes = [IsMasterGroup]
    
    # Константы для валидации
    MIN_LATITUDE = -90
    MAX_LATITUDE = 90
    MIN_LONGITUDE = -180
    MAX_LONGITUDE = 180
    DEFAULT_PAGE_SIZE = 20
    MAX_PAGE_SIZE = 100
    
    @swagger_auto_schema(
        operation_description="Получить список всех мастеров с возможностью фильтрации",
        security=[{'Bearer': []}],
        manual_parameters=[
            openapi.Parameter(
                'city', 
                openapi.IN_QUERY, 
                description="Фильтр по городу (частичное совпадение)", 
                type=openapi.TYPE_STRING,
                required=False
            ),
            openapi.Parameter(
                'service_type', 
                openapi.IN_QUERY, 
                description="Фильтр по типу услуги (diagnostics, service, tire_repair, towing, car_wash, road_help)", 
                type=openapi.TYPE_STRING,
                enum=['diagnostics', 'service', 'tire_repair', 'towing', 'car_wash', 'road_help'],
                required=False
            ),
            openapi.Parameter(
                'point1_lat', 
                openapi.IN_QUERY, 
                description="Широта первой точки", 
                type=openapi.TYPE_NUMBER,
                required=False
            ),
            openapi.Parameter(
                'point1_lon', 
                openapi.IN_QUERY, 
                description="Долгота первой точки", 
                type=openapi.TYPE_NUMBER,
                required=False
            ),
            openapi.Parameter(
                'point2_lat', 
                openapi.IN_QUERY, 
                description="Широта второй точки", 
                type=openapi.TYPE_NUMBER,
                required=False
            ),
            openapi.Parameter(
                'point2_lon', 
                openapi.IN_QUERY, 
                description="Долгота второй точки", 
                type=openapi.TYPE_NUMBER,
                required=False
            ),
            openapi.Parameter(
                'point3_lat', 
                openapi.IN_QUERY, 
                description="Широта третьей точки", 
                type=openapi.TYPE_NUMBER,
                required=False
            ),
            openapi.Parameter(
                'point3_lon', 
                openapi.IN_QUERY, 
                description="Долгота третьей точки", 
                type=openapi.TYPE_NUMBER,
                required=False
            ),
            openapi.Parameter(
                'point4_lat', 
                openapi.IN_QUERY, 
                description="Широта четвертой точки", 
                type=openapi.TYPE_NUMBER,
                required=False
            ),
            openapi.Parameter(
                'point4_lon', 
                openapi.IN_QUERY, 
                description="Долгота четвертой точки", 
                type=openapi.TYPE_NUMBER,
                required=False
            ),
            openapi.Parameter(
                'page', 
                openapi.IN_QUERY, 
                description="Номер страницы (начиная с 1)", 
                type=openapi.TYPE_INTEGER,
                required=False
            ),
            openapi.Parameter(
                'page_size', 
                openapi.IN_QUERY, 
                description=f"Размер страницы (максимум {MAX_PAGE_SIZE})", 
                type=openapi.TYPE_INTEGER,
                required=False
            )
        ],
        responses={
            200: openapi.Response(
                description="Список мастеров с метаданными пагинации",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'results': openapi.Schema(
                            type=openapi.TYPE_ARRAY,
                            items=openapi.Schema(
                                type=openapi.TYPE_OBJECT,
                                properties={
                                    'id': openapi.Schema(type=openapi.TYPE_INTEGER),
                                    'user': openapi.Schema(type=openapi.TYPE_INTEGER),
                                    'user_name': openapi.Schema(type=openapi.TYPE_STRING),
                                    'user_phone': openapi.Schema(type=openapi.TYPE_STRING),
                                    'city': openapi.Schema(type=openapi.TYPE_STRING),
                                    'address': openapi.Schema(type=openapi.TYPE_STRING),
                                    'latitude': openapi.Schema(type=openapi.TYPE_NUMBER),
                                    'longitude': openapi.Schema(type=openapi.TYPE_NUMBER),
                                    'services': openapi.Schema(type=openapi.TYPE_ARRAY, items=openapi.Schema(type=openapi.TYPE_STRING)),
                                    'services_display': openapi.Schema(type=openapi.TYPE_ARRAY, items=openapi.Schema(type=openapi.TYPE_STRING)),
                                    'card_number': openapi.Schema(type=openapi.TYPE_STRING),
                                    'card_expiry_month': openapi.Schema(type=openapi.TYPE_INTEGER),
                                    'card_expiry_year': openapi.Schema(type=openapi.TYPE_INTEGER),
                                    'card_cvv': openapi.Schema(type=openapi.TYPE_STRING),
                                    'reserved_amount': openapi.Schema(type=openapi.TYPE_NUMBER),
                                    'created_at': openapi.Schema(type=openapi.TYPE_STRING, format=openapi.FORMAT_DATETIME),
                                    'updated_at': openapi.Schema(type=openapi.TYPE_STRING, format=openapi.FORMAT_DATETIME),
                                    'last_activity': openapi.Schema(type=openapi.TYPE_STRING, format=openapi.FORMAT_DATETIME)
                                }
                            )
                        ),
                        'count': openapi.Schema(type=openapi.TYPE_INTEGER),
                        'page': openapi.Schema(type=openapi.TYPE_INTEGER),
                        'page_size': openapi.Schema(type=openapi.TYPE_INTEGER),
                        'total_pages': openapi.Schema(type=openapi.TYPE_INTEGER)
                    }
                )
            ),
            400: openapi.Response(description="Неверные параметры запроса"),
            403: openapi.Response(description="Нет прав доступа")
        },
        tags=['Masters']
    )
    def get(self, request):
        """Получение списка мастеров с фильтрацией и пагинацией"""
        try:
            # Получаем базовый queryset мастеров с координатами
            masters = self._get_base_queryset()
            
            # Применяем фильтры
            masters = self._apply_filters(masters, request)
            
            # Применяем пагинацию
            paginated_data = self._apply_pagination(masters, request)
            
            # Сериализуем данные
            serializer = MasterSerializer(
                paginated_data['results'], 
                many=True, 
                context={'request': request}
            )
            
            return Response({
                'results': serializer.data,
                'count': paginated_data['count'],
                'page': paginated_data['page'],
                'page_size': paginated_data['page_size'],
                'total_pages': paginated_data['total_pages']
            }, status=status.HTTP_200_OK)
            
        except ValueError as e:
            return Response(
                {'error': str(e)}, 
                status=status.HTTP_400_BAD_REQUEST
            )
    
    def _get_base_queryset(self):
        """Получение базового queryset мастеров с координатами"""
        return Master.objects.filter(
            latitude__isnull=False,
            longitude__isnull=False
        )
    
    def _apply_filters(self, queryset, request):
        """Применение фильтров к queryset"""
        # Фильтр по городу
        city = request.query_params.get('city')
        if city:
            queryset = queryset.filter(city__icontains=city)
        
        # Фильтр по услуге
        service = request.query_params.get('service')
        if service:
            # Фильтруем по услугам через MasterService
            queryset = queryset.filter(master_services__name__icontains=service).distinct()
        
        # Фильтр по типу услуги
        service_type = request.query_params.get('service_type')
        print(f"Service type: {service_type}")
        if service_type:
            queryset = queryset.filter(service_type=service_type)
        
        # Фильтр по прямоугольной области
        area_filter = self._get_area_filter(request)
        if area_filter:
            queryset = queryset.filter(**area_filter)
        
        return queryset
    
    def _get_area_filter(self, request):
        """Получение фильтра по прямоугольной области"""
        # Получаем параметры точек
        point_params = {
            'point1': (request.query_params.get('point1_lat'), request.query_params.get('point1_lon')),
            'point2': (request.query_params.get('point2_lat'), request.query_params.get('point2_lon')),
            'point3': (request.query_params.get('point3_lat'), request.query_params.get('point3_lon')),
            'point4': (request.query_params.get('point4_lat'), request.query_params.get('point4_lon'))
        }
        
        # Проверяем, что все параметры переданы
        all_params = [param for point in point_params.values() for param in point]
        if any(all_params) and not all(all_params):
            raise ValueError(
                'Для фильтрации по области необходимо передать все восемь параметров: '
                'point1_lat, point1_lon, point2_lat, point2_lon, '
                'point3_lat, point3_lon, point4_lat, point4_lon'
            )
        
        if not all(all_params):
            return None
        
        # Валидируем и преобразуем координаты
        points = []
        for point_name, (lat_str, lon_str) in point_params.items():
            try:
                lat = float(lat_str)
                lon = float(lon_str)
                self._validate_coordinates(lat, lon, point_name)
                points.append((lat, lon))
            except (ValueError, TypeError) as e:
                raise ValueError(f'Неверные координаты для {point_name}: {str(e)}')
        
        # Вычисляем границы прямоугольника
        lats = [point[0] for point in points]
        lons = [point[1] for point in points]
        
        min_lat = min(lats)
        max_lat = max(lats)
        min_lon = min(lons)
        max_lon = max(lons)
        
        # Проверяем, что точки образуют прямоугольник
        # Для правильного прямоугольника должны быть только 2 уникальных значения по каждой оси
        unique_lats = len(set(lats))
        unique_lons = len(set(lons))
        
        
        return {
            'latitude__gte': min_lat,
            'latitude__lte': max_lat,
            'longitude__gte': min_lon,
            'longitude__lte': max_lon
        }
    
    def _validate_coordinates(self, lat, lon, point_name):
        """Валидация координат"""
        if not (self.MIN_LATITUDE <= lat <= self.MAX_LATITUDE):
            raise ValueError(
                f'Широта для {point_name} должна быть между {self.MIN_LATITUDE} и {self.MAX_LATITUDE}, '
                f'получено: {lat}'
            )
        
        if not (self.MIN_LONGITUDE <= lon <= self.MAX_LONGITUDE):
            raise ValueError(
                f'Долгота для {point_name} должна быть между {self.MIN_LONGITUDE} и {self.MAX_LONGITUDE}, '
                f'получено: {lon}'
            )
    
    def _apply_pagination(self, queryset, request):
        """Применение пагинации к queryset"""
        try:
            page = int(request.query_params.get('page', 1))
            page_size = int(request.query_params.get('page_size', self.DEFAULT_PAGE_SIZE))
        except (ValueError, TypeError):
            page = 1
            page_size = self.DEFAULT_PAGE_SIZE
        
        # Валидация параметров пагинации
        if page < 1:
            page = 1
        
        if page_size < 1:
            page_size = self.DEFAULT_PAGE_SIZE
        elif page_size > self.MAX_PAGE_SIZE:
            page_size = self.MAX_PAGE_SIZE
        
        # Вычисляем пагинацию
        total_count = queryset.count()
        start = (page - 1) * page_size
        end = start + page_size
        
        results = queryset[start:end]
        total_pages = (total_count + page_size - 1) // page_size
        
        return {
            'results': results,
            'count': total_count,
            'page': page,
            'page_size': page_size,
            'total_pages': total_pages
        }


class MasterDetailsView(APIView):
    """
    API для операций с конкретным мастером по ID.
    
    Поддерживаемые операции:
    - GET: получение деталей мастера
    - PUT: полное обновление мастера
    - PATCH: частичное обновление мастера
    - DELETE: удаление мастера
    """
    permission_classes = [IsMasterGroup]
    
    def get_object(self, master_id):
        """Получение мастера по ID"""
        try:
            return Master.objects.get(id=master_id)
        except Master.DoesNotExist:
            return None
    
    @swagger_auto_schema(
        operation_description="Получить детали мастера по ID",
        security=[{'Bearer': []}],
        responses={
            200: openapi.Response(
                description="Детали мастера",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'id': openapi.Schema(type=openapi.TYPE_INTEGER),
                        'user': openapi.Schema(type=openapi.TYPE_INTEGER),
                        'user_name': openapi.Schema(type=openapi.TYPE_STRING),
                        'user_phone': openapi.Schema(type=openapi.TYPE_STRING),
                        'city': openapi.Schema(type=openapi.TYPE_STRING),
                        'address': openapi.Schema(type=openapi.TYPE_STRING),
                        'latitude': openapi.Schema(type=openapi.TYPE_NUMBER),
                        'longitude': openapi.Schema(type=openapi.TYPE_NUMBER),
                        'service_type': openapi.Schema(type=openapi.TYPE_STRING),
                        'services': openapi.Schema(type=openapi.TYPE_ARRAY, items=openapi.Schema(type=openapi.TYPE_STRING)),
                        'services_display': openapi.Schema(type=openapi.TYPE_ARRAY, items=openapi.Schema(type=openapi.TYPE_STRING)),
                        'card_number': openapi.Schema(type=openapi.TYPE_STRING),
                        'card_expiry_month': openapi.Schema(type=openapi.TYPE_INTEGER),
                        'card_expiry_year': openapi.Schema(type=openapi.TYPE_INTEGER),
                        'card_cvv': openapi.Schema(type=openapi.TYPE_STRING),
                        'reserved_amount': openapi.Schema(type=openapi.TYPE_NUMBER),
                        'created_at': openapi.Schema(type=openapi.TYPE_STRING, format=openapi.FORMAT_DATETIME),
                        'updated_at': openapi.Schema(type=openapi.TYPE_STRING, format=openapi.FORMAT_DATETIME),
                        'last_activity': openapi.Schema(type=openapi.TYPE_STRING, format=openapi.FORMAT_DATETIME)
                    }
                )
            ),
            404: openapi.Response(description="Мастер не найден"),
            403: openapi.Response(description="Нет прав доступа")
        },
        tags=['Masters']
    )
    def get(self, request, master_id):
        """Получение деталей мастера по ID"""
        master = self.get_object(master_id)
        if not master:
            return Response(
                {'error': 'Мастер не найден'}, 
                status=status.HTTP_404_NOT_FOUND
            )
        
        serializer = MasterSerializer(master, context={'request': request})
        return Response(serializer.data, status=status.HTTP_200_OK)
    
    @swagger_auto_schema(
        operation_description="Обновить мастера по ID",
        security=[{'Bearer': []}],
        request_body=MasterSerializer,
        responses={
            200: openapi.Response(
                description="Мастер обновлен",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'id': openapi.Schema(type=openapi.TYPE_INTEGER),
                        'user': openapi.Schema(type=openapi.TYPE_INTEGER),
                        'user_name': openapi.Schema(type=openapi.TYPE_STRING),
                        'user_phone': openapi.Schema(type=openapi.TYPE_STRING),
                        'city': openapi.Schema(type=openapi.TYPE_STRING),
                        'address': openapi.Schema(type=openapi.TYPE_STRING),
                        'latitude': openapi.Schema(type=openapi.TYPE_NUMBER),
                        'longitude': openapi.Schema(type=openapi.TYPE_NUMBER),
                        'service_type': openapi.Schema(type=openapi.TYPE_STRING),
                        'services': openapi.Schema(type=openapi.TYPE_ARRAY, items=openapi.Schema(type=openapi.TYPE_STRING)),
                        'services_display': openapi.Schema(type=openapi.TYPE_ARRAY, items=openapi.Schema(type=openapi.TYPE_STRING)),
                        'card_number': openapi.Schema(type=openapi.TYPE_STRING),
                        'card_expiry_month': openapi.Schema(type=openapi.TYPE_INTEGER),
                        'card_expiry_year': openapi.Schema(type=openapi.TYPE_INTEGER),
                        'card_cvv': openapi.Schema(type=openapi.TYPE_STRING),
                        'reserved_amount': openapi.Schema(type=openapi.TYPE_NUMBER),
                        'created_at': openapi.Schema(type=openapi.TYPE_STRING, format=openapi.FORMAT_DATETIME),
                        'updated_at': openapi.Schema(type=openapi.TYPE_STRING, format=openapi.FORMAT_DATETIME),
                        'last_activity': openapi.Schema(type=openapi.TYPE_STRING, format=openapi.FORMAT_DATETIME)
                    }
                )
            ),
            400: openapi.Response(description="Неверные данные"),
            404: openapi.Response(description="Мастер не найден"),
            403: openapi.Response(description="Нет прав доступа")
        },
        tags=['Masters']
    )
    def put(self, request, master_id):
        """Полное обновление мастера по ID"""
        master = self.get_object(master_id)
        if not master:
            return Response(
                {'error': 'Мастер не найден'}, 
                status=status.HTTP_404_NOT_FOUND
            )
        
        serializer = MasterUpdateSerializer(master, data=request.data, context={'request': request})
        if serializer.is_valid():
            serializer.save()
            # To'liq master ma'lumotlarini qaytarish
            response_serializer = MasterSerializer(master, context={'request': request})
            return Response(response_serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @swagger_auto_schema(
        operation_description="Частичное обновление мастера по ID",
        security=[{'Bearer': []}],
        request_body=MasterSerializer,
        responses={
            200: openapi.Response(
                description="Мастер обновлен",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'id': openapi.Schema(type=openapi.TYPE_INTEGER),
                        'user': openapi.Schema(type=openapi.TYPE_INTEGER),
                        'user_name': openapi.Schema(type=openapi.TYPE_STRING),
                        'user_phone': openapi.Schema(type=openapi.TYPE_STRING),
                        'city': openapi.Schema(type=openapi.TYPE_STRING),
                        'address': openapi.Schema(type=openapi.TYPE_STRING),
                        'latitude': openapi.Schema(type=openapi.TYPE_NUMBER),
                        'longitude': openapi.Schema(type=openapi.TYPE_NUMBER),
                        'service_type': openapi.Schema(type=openapi.TYPE_STRING),
                        'services': openapi.Schema(type=openapi.TYPE_ARRAY, items=openapi.Schema(type=openapi.TYPE_STRING)),
                        'services_display': openapi.Schema(type=openapi.TYPE_ARRAY, items=openapi.Schema(type=openapi.TYPE_STRING)),
                        'card_number': openapi.Schema(type=openapi.TYPE_STRING),
                        'card_expiry_month': openapi.Schema(type=openapi.TYPE_INTEGER),
                        'card_expiry_year': openapi.Schema(type=openapi.TYPE_INTEGER),
                        'card_cvv': openapi.Schema(type=openapi.TYPE_STRING),
                        'reserved_amount': openapi.Schema(type=openapi.TYPE_NUMBER),
                        'created_at': openapi.Schema(type=openapi.TYPE_STRING, format=openapi.FORMAT_DATETIME),
                        'updated_at': openapi.Schema(type=openapi.TYPE_STRING, format=openapi.FORMAT_DATETIME),
                        'last_activity': openapi.Schema(type=openapi.TYPE_STRING, format=openapi.FORMAT_DATETIME)
                    }
                )
            ),
            400: openapi.Response(description="Неверные данные"),
            404: openapi.Response(description="Мастер не найден"),
            403: openapi.Response(description="Нет прав доступа")
        },
        tags=['Masters']
    )
    def patch(self, request, master_id):
        """Частичное обновление мастера по ID"""
        master = self.get_object(master_id)
        if not master:
            return Response(
                {'error': 'Мастер не найден'}, 
                status=status.HTTP_404_NOT_FOUND
            )
        
        serializer = MasterSerializer(master, data=request.data, partial=True, context={'request': request})
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @swagger_auto_schema(
        operation_description="Удалить мастера по ID",
        security=[{'Bearer': []}],
        responses={
            204: openapi.Response(description="Мастер удален"),
            404: openapi.Response(description="Мастер не найден"),
            403: openapi.Response(description="Нет прав доступа")
        },
        tags=['Masters']
    )
    def delete(self, request, master_id):
        """Удаление мастера по ID"""
        master = self.get_object(master_id)
        if not master:
            return Response(
                {'error': 'Мастер не найден'}, 
                status=status.HTTP_404_NOT_FOUND
            )
        
        master.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class MasterServiceView(APIView):
    """
    API для управления услугами мастера.
    
    Поддерживаемые операции:
    - GET: получение услуг мастера
    - POST: добавление услуги мастеру
    - PUT: обновление услуги мастера
    - DELETE: удаление услуги у мастера
    """
    permission_classes = [IsMasterGroup]
    
    def get_master(self):
        """Получить мастера текущего пользователя"""
        try:
            return Master.objects.get(user=self.request.user)
        except Master.DoesNotExist:
            return None
    
    @swagger_auto_schema(
        operation_description="Получить услуги мастера",
        responses={
            200: openapi.Response(
                description="Услуги мастера",
                schema=openapi.Schema(
                    type=openapi.TYPE_ARRAY,
                    items=openapi.Schema(
                        type=openapi.TYPE_OBJECT,
                        properties={
                            'id': openapi.Schema(type=openapi.TYPE_INTEGER),
                            'master': openapi.Schema(type=openapi.TYPE_INTEGER),
                            'name': openapi.Schema(type=openapi.TYPE_STRING),
                            'price_from': openapi.Schema(type=openapi.TYPE_NUMBER),
                            'price_to': openapi.Schema(type=openapi.TYPE_NUMBER),
                            'created_at': openapi.Schema(type=openapi.TYPE_STRING, format=openapi.FORMAT_DATETIME)
                        }
                    )
                )
            ),
            404: openapi.Response(description="Профиль мастера не найден"),
            403: openapi.Response(description="Нет прав доступа")
        },
        tags=['Master Services']
    )
    def get(self, request):
        """Получение услуг мастера"""
        master = self.get_master()
        if not master:
            return Response(
                {'error': 'Профиль мастера не найден'}, 
                status=status.HTTP_404_NOT_FOUND
            )
        
        master_services = MasterService.objects.filter(master=master)
        serializer = MasterServiceSerializer(master_services, many=True, context={'request': request})
        return Response(serializer.data, status=status.HTTP_200_OK)
    
    @swagger_auto_schema(
        operation_description="Добавить услугу мастеру",
        request_body=MasterServiceSerializer,
        responses={
            201: openapi.Response(description="Услуга добавлена", schema=MasterServiceSerializer),
            400: openapi.Response(description="Неверные данные"),
            404: openapi.Response(description="Профиль мастера не найден"),
            403: openapi.Response(description="Нет прав доступа")
        },
        tags=['Master Services']
    )
    def post(self, request):
        """Добавление услуги мастеру"""
        master = self.get_master()
        if not master:
            return Response(
                {'error': 'Профиль мастера не найден'}, 
                status=status.HTTP_404_NOT_FOUND
            )
        
        serializer = MasterServiceSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            serializer.save(master=master)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class MasterServiceDetailView(APIView):
    """
    API для управления конкретной услугой мастера.
    
    Поддерживаемые операции:
    - GET: получение услуги мастера
    - PUT: обновление услуги мастера
    - PATCH: частичное обновление услуги мастера
    - DELETE: удаление услуги у мастера
    """
    permission_classes = [IsMasterGroup]
    
    def get_master(self):
        """Получить мастера текущего пользователя"""
        try:
            return Master.objects.get(user=self.request.user)
        except Master.DoesNotExist:
            return None
    
    def get_object(self, service_id):
        """Получить услугу мастера"""
        master = self.get_master()
        if not master:
            return None
        try:
            return MasterService.objects.get(master=master, id=service_id)
        except MasterService.DoesNotExist:
            return None
    
    @swagger_auto_schema(
        operation_description="Получить услугу мастера по ID",
        responses={
            200: openapi.Response(description="Услуга мастера", schema=MasterServiceSerializer),
            404: openapi.Response(description="Услуга не найдена"),
            403: openapi.Response(description="Нет прав доступа")
        },
        tags=['Master Services']
    )
    def get(self, request, service_id):
        """Получение услуги мастера"""
        master_service = self.get_object(service_id)
        if not master_service:
            return Response(
                {'error': 'Услуга не найдена'}, 
                status=status.HTTP_404_NOT_FOUND
            )
        
        serializer = MasterServiceSerializer(master_service, context={'request': request})
        return Response(serializer.data, status=status.HTTP_200_OK)
    
    @swagger_auto_schema(
        operation_description="Обновить услугу мастера",
        request_body=MasterServiceSerializer,
        responses={
            200: openapi.Response(description="Услуга обновлена", schema=MasterServiceSerializer),
            400: openapi.Response(description="Неверные данные"),
            404: openapi.Response(description="Услуга не найдена"),
            403: openapi.Response(description="Нет прав доступа")
        },
        tags=['Master Services']
    )
    def put(self, request, service_id):
        """Обновление услуги мастера"""
        master_service = self.get_object(service_id)
        if not master_service:
            return Response(
                {'error': 'Услуга не найдена'}, 
                status=status.HTTP_404_NOT_FOUND
            )
        
        serializer = MasterServiceSerializer(master_service, data=request.data, context={'request': request})
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @swagger_auto_schema(
        operation_description="Частичное обновление услуги мастера",
        request_body=MasterServiceSerializer,
        responses={
            200: openapi.Response(description="Услуга обновлена", schema=MasterServiceSerializer),
            400: openapi.Response(description="Неверные данные"),
            404: openapi.Response(description="Услуга не найдена"),
            403: openapi.Response(description="Нет прав доступа")
        },
        tags=['Master Services']
    )
    def patch(self, request, service_id):
        """Частичное обновление услуги мастера"""
        master_service = self.get_object(service_id)
        if not master_service:
            return Response(
                {'error': 'Услуга не найдена'}, 
                status=status.HTTP_404_NOT_FOUND
            )
        
        serializer = MasterServiceSerializer(master_service, data=request.data, partial=True, context={'request': request})
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @swagger_auto_schema(
        operation_description="Удалить услугу у мастера",
        responses={
            204: openapi.Response(description="Услуга удалена"),
            404: openapi.Response(description="Услуга не найдена"),
            403: openapi.Response(description="Нет прав доступа")
        },
        tags=['Master Services']
    )
    def delete(self, request, service_id):
        """Удаление услуги у мастера"""
        master_service = self.get_object(service_id)
        if not master_service:
            return Response(
                {'error': 'Услуга не найдена'}, 
                status=status.HTTP_404_NOT_FOUND
            )
        
        master_service.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

