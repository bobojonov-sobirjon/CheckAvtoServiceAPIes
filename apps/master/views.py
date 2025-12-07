from rest_framework.views import APIView
from rest_framework import status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from django.db.models import Q
from .models import Master, MasterService, MasterServiceItems, MasterInMaster
from .serializers import (
    MasterSerializer, MasterCreateSerializer, MasterUpdateSerializer, MasterNearbySerializer,
    MasterServiceSerializer, MasterServiceItemsSerializer, MasterInMasterSerializer
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
                            'category': openapi.Schema(type=openapi.TYPE_ARRAY, items=openapi.Schema(type=openapi.TYPE_STRING)),
                            'category_data': openapi.Schema(type=openapi.TYPE_ARRAY, items=openapi.Schema(type=openapi.TYPE_STRING)),
                            'master_in_master_data': openapi.Schema(type=openapi.TYPE_ARRAY, items=openapi.Schema(type=openapi.TYPE_STRING)),
                            'rating_data': openapi.Schema(type=openapi.TYPE_ARRAY, items=openapi.Schema(type=openapi.TYPE_STRING)),
                            'working_time': openapi.Schema(type=openapi.TYPE_STRING),
                            'phone': openapi.Schema(type=openapi.TYPE_STRING),
                            'description': openapi.Schema(type=openapi.TYPE_STRING),
                            'images': openapi.Schema(type=openapi.TYPE_ARRAY, items=openapi.Schema(type=openapi.TYPE_STRING)),
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
    permission_classes = [IsAuthenticated]
    
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
                                    'working_time': openapi.Schema(type=openapi.TYPE_STRING),
                                    'phone': openapi.Schema(type=openapi.TYPE_STRING),
                                    'description': openapi.Schema(type=openapi.TYPE_STRING),
                                    'images': openapi.Schema(type=openapi.TYPE_ARRAY, items=openapi.Schema(type=openapi.TYPE_STRING)),
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
    permission_classes = [IsAuthenticated]
    
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
        consumes=['multipart/form-data', 'application/json'],
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'city': openapi.Schema(type=openapi.TYPE_STRING, description='Город'),
                'address': openapi.Schema(type=openapi.TYPE_STRING, description='Адрес'),
                'latitude': openapi.Schema(type=openapi.TYPE_NUMBER, description='Широта'),
                'longitude': openapi.Schema(type=openapi.TYPE_NUMBER, description='Долгота'),
                'phone': openapi.Schema(type=openapi.TYPE_STRING, description='Телефон'),
                'working_time': openapi.Schema(type=openapi.TYPE_STRING, description='Рабочее время'),
                'service_type': openapi.Schema(type=openapi.TYPE_STRING, description='Тип услуги'),
                'card_number': openapi.Schema(type=openapi.TYPE_STRING, description='Номер карты'),
                'card_expiry_month': openapi.Schema(type=openapi.TYPE_INTEGER, description='Месяц истечения'),
                'card_expiry_year': openapi.Schema(type=openapi.TYPE_INTEGER, description='Год истечения'),
                'card_cvv': openapi.Schema(type=openapi.TYPE_STRING, description='CVV/CVC'),
                'description': openapi.Schema(type=openapi.TYPE_STRING, description='Описание'),
                'images': openapi.Schema(
                    type=openapi.TYPE_ARRAY,
                    items=openapi.Schema(type=openapi.TYPE_STRING, format=openapi.FORMAT_BINARY),
                    description='Изображения мастера (можно загрузить несколько)'
                )
            }
        ),
        responses={
            200: openapi.Response(
                description="Мастер обновлен",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'id': openapi.Schema(type=openapi.TYPE_INTEGER),
                        'user_info': openapi.Schema(type=openapi.TYPE_OBJECT),
                        'city': openapi.Schema(type=openapi.TYPE_STRING),
                        'address': openapi.Schema(type=openapi.TYPE_STRING),
                        'latitude': openapi.Schema(type=openapi.TYPE_NUMBER),
                        'longitude': openapi.Schema(type=openapi.TYPE_NUMBER),
                        'phone': openapi.Schema(type=openapi.TYPE_STRING),
                        'working_time': openapi.Schema(type=openapi.TYPE_STRING),
                        'service_type_display': openapi.Schema(type=openapi.TYPE_STRING),
                        'services': openapi.Schema(type=openapi.TYPE_ARRAY, items=openapi.Schema(type=openapi.TYPE_OBJECT)),
                        'card_number': openapi.Schema(type=openapi.TYPE_STRING),
                        'card_expiry_month': openapi.Schema(type=openapi.TYPE_INTEGER),
                        'card_expiry_year': openapi.Schema(type=openapi.TYPE_INTEGER),
                        'card_cvv': openapi.Schema(type=openapi.TYPE_STRING),
                        'balance': openapi.Schema(type=openapi.TYPE_NUMBER),
                        'reserved_amount': openapi.Schema(type=openapi.TYPE_NUMBER),
                        'description': openapi.Schema(type=openapi.TYPE_STRING),
                        'images': openapi.Schema(type=openapi.TYPE_ARRAY, items=openapi.Schema(type=openapi.TYPE_OBJECT)),
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
        
        # Multipart/form-data uchun request.data va request.FILES ni birlashtirish
        # QueryDict ni dict ga o'tkazish
        if hasattr(request.data, 'dict'):
            data = request.data.dict()
        else:
            data = dict(request.data) if hasattr(request.data, '__iter__') else request.data
        
        # Agar images ko'p bo'lsa, ularni listga o'tkazish
        if request.FILES:
            images = request.FILES.getlist('images')
            if images:
                data['images'] = images
        
        serializer = MasterUpdateSerializer(master, data=data, context={'request': request})
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
    API для добавления услуги мастеру.
    
    POST: добавление услуги мастеру
    """
    permission_classes = [IsMasterGroup]
    
    def get_master(self):
        """Получить мастера текущего пользователя"""
        try:
            return Master.objects.get(user=self.request.user)
        except Master.DoesNotExist:
            return None
    
    @swagger_auto_schema(
        operation_description="Добавить услугу мастеру",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'master_id': openapi.Schema(type=openapi.TYPE_INTEGER, description='ID мастера'),
                'master_items': openapi.Schema(
                    type=openapi.TYPE_ARRAY,
                    items=openapi.Schema(
                        type=openapi.TYPE_OBJECT,
                        properties={
                            'name': openapi.Schema(type=openapi.TYPE_STRING, description='Название услуги'),
                            'price_from': openapi.Schema(type=openapi.TYPE_NUMBER, description='Цена от'),
                            'price_to': openapi.Schema(type=openapi.TYPE_NUMBER, description='Цена до'),
                            'category': openapi.Schema(type=openapi.TYPE_INTEGER, description='ID категории')
                        },
                        required=['name', 'price_from', 'price_to', 'category']
                    ),
                    description='Список элементов услуги'
                )
            },
            required=['master_id', 'master_items']
        ),
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
        
        master_id = request.data.get('master_id')
        if not master_id:
            return Response(
                {'error': 'master_id обязателен'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Проверяем, что master_id совпадает с текущим мастером
        if master.id != master_id:
            return Response(
                {'error': 'Вы можете добавлять услуги только для своего профиля мастера'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        serializer = MasterServiceSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            serializer.save(master=master)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class MasterServicesByMasterView(APIView):
    """
    API для получения услуг мастера по master_id.
    
    GET: получение услуг мастера с элементами, сгруппированными по категориям
    """
    permission_classes = [IsAuthenticated]
    
    @swagger_auto_schema(
        operation_description="Получить услуги мастера по ID мастера (с элементами, сгруппированными по категориям)",
        responses={
            200: openapi.Response(
                description="Услуги мастера", 
                schema=MasterServiceSerializer
            ),
            404: openapi.Response(description="Мастер не найден"),
            403: openapi.Response(description="Нет прав доступа")
        },
        tags=['Master Services']
    )
    def get(self, request, master_id):
        """Получение услуг мастера"""
        try:
            master = Master.objects.get(id=master_id)
        except Master.DoesNotExist:
            return Response(
                {'error': 'Мастер не найден'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        master_services = MasterService.objects.filter(master=master)
        serializer = MasterServiceSerializer(master_services, many=True, context={'request': request})
        return Response(serializer.data, status=status.HTTP_200_OK)


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


class MasterServiceItemsView(APIView):
    """
    API для добавления элементов услуги мастера.
    
    POST: добавление элементов услуги (multiple)
    """
    permission_classes = [IsMasterGroup]
    
    @swagger_auto_schema(
        operation_description="Добавить элементы услуги мастера",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'master_items': openapi.Schema(
                    type=openapi.TYPE_ARRAY,
                    items=openapi.Schema(
                        type=openapi.TYPE_OBJECT,
                        properties={
                            'name': openapi.Schema(type=openapi.TYPE_STRING),
                            'price_from': openapi.Schema(type=openapi.TYPE_NUMBER),
                            'price_to': openapi.Schema(type=openapi.TYPE_NUMBER),
                            'category': openapi.Schema(type=openapi.TYPE_INTEGER)
                        }
                    )
                )
            }
        ),
        responses={
            201: openapi.Response(description="Элементы добавлены"),
            400: openapi.Response(description="Неверные данные"),
            404: openapi.Response(description="Услуга не найдена"),
            403: openapi.Response(description="Нет прав доступа")
        },
        tags=['Master Service Items']
    )
    def post(self, request, master_service_id):
        """Добавление элементов услуги мастера"""
        try:
            master_service = MasterService.objects.get(id=master_service_id)
            # Проверяем, что услуга принадлежит текущему пользователю
            if master_service.master.user != request.user:
                return Response(
                    {'error': 'У вас нет доступа к этой услуге'},
                    status=status.HTTP_403_FORBIDDEN
                )
        except MasterService.DoesNotExist:
            return Response(
                {'error': 'Услуга не найдена'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        master_items = request.data.get('master_items', [])
        if not isinstance(master_items, list):
            return Response(
                {'error': 'master_items должен быть списком'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        created_items = []
        for item_data in master_items:
            serializer = MasterServiceItemsSerializer(data=item_data, context={'request': request})
            if serializer.is_valid():
                item = serializer.save(master_service=master_service)
                created_items.append(serializer.data)
            else:
                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        return Response(created_items, status=status.HTTP_201_CREATED)


class MasterServiceItemsDetailView(APIView):
    """
    API для управления конкретным элементом услуги мастера.
    
    Поддерживаемые операции:
    - GET: получение элемента услуги
    - PUT: обновление элемента услуги
    - PATCH: частичное обновление элемента услуги
    - DELETE: удаление элемента услуги
    """
    permission_classes = [IsMasterGroup]
    
    def get_object(self, item_id):
        """Получить элемент услуги мастера"""
        try:
            item = MasterServiceItems.objects.get(id=item_id)
            # Проверяем, что элемент принадлежит текущему пользователю
            if item.master_service.master.user != self.request.user:
                return None
            return item
        except MasterServiceItems.DoesNotExist:
            return None
    
    @swagger_auto_schema(
        operation_description="Получить элемент услуги мастера по ID",
        responses={
            200: openapi.Response(description="Элемент услуги", schema=MasterServiceItemsSerializer),
            404: openapi.Response(description="Элемент не найден"),
            403: openapi.Response(description="Нет прав доступа")
        },
        tags=['Master Service Items']
    )
    def get(self, request, item_id):
        """Получение элемента услуги мастера"""
        item = self.get_object(item_id)
        if not item:
            return Response(
                {'error': 'Элемент не найден'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        serializer = MasterServiceItemsSerializer(item, context={'request': request})
        return Response(serializer.data, status=status.HTTP_200_OK)
    
    @swagger_auto_schema(
        operation_description="Обновить элемент услуги мастера",
        request_body=MasterServiceItemsSerializer,
        responses={
            200: openapi.Response(description="Элемент обновлен", schema=MasterServiceItemsSerializer),
            400: openapi.Response(description="Неверные данные"),
            404: openapi.Response(description="Элемент не найден"),
            403: openapi.Response(description="Нет прав доступа")
        },
        tags=['Master Service Items']
    )
    def put(self, request, item_id):
        """Обновление элемента услуги мастера"""
        item = self.get_object(item_id)
        if not item:
            return Response(
                {'error': 'Элемент не найден'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        serializer = MasterServiceItemsSerializer(item, data=request.data, context={'request': request})
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @swagger_auto_schema(
        operation_description="Частичное обновление элемента услуги мастера",
        request_body=MasterServiceItemsSerializer,
        responses={
            200: openapi.Response(description="Элемент обновлен", schema=MasterServiceItemsSerializer),
            400: openapi.Response(description="Неверные данные"),
            404: openapi.Response(description="Элемент не найден"),
            403: openapi.Response(description="Нет прав доступа")
        },
        tags=['Master Service Items']
    )
    def patch(self, request, item_id):
        """Частичное обновление элемента услуги мастера"""
        item = self.get_object(item_id)
        if not item:
            return Response(
                {'error': 'Элемент не найден'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        serializer = MasterServiceItemsSerializer(item, data=request.data, partial=True, context={'request': request})
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @swagger_auto_schema(
        operation_description="Удалить элемент услуги мастера",
        responses={
            204: openapi.Response(description="Элемент удален"),
            404: openapi.Response(description="Элемент не найден"),
            403: openapi.Response(description="Нет прав доступа")
        },
        tags=['Master Service Items']
    )
    def delete(self, request, item_id):
        """Удаление элемента услуги мастера"""
        item = self.get_object(item_id)
        if not item:
            return Response(
                {'error': 'Элемент не найден'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        item.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class MasterInMasterView(APIView):
    """
    API для добавления мастера в мастера.
    
    POST: создание нового пользователя и добавление его в мастера
    """
    permission_classes = [IsMasterGroup]
    
    @swagger_auto_schema(
        operation_description="Добавить мастера в мастера (создает нового пользователя)",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'master': openapi.Schema(type=openapi.TYPE_INTEGER, description='ID мастера'),
                'category': openapi.Schema(type=openapi.TYPE_INTEGER, description='ID категории'),
                'first_name': openapi.Schema(type=openapi.TYPE_STRING, description='Имя'),
                'last_name': openapi.Schema(type=openapi.TYPE_STRING, description='Фамилия'),
                'phone': openapi.Schema(type=openapi.TYPE_STRING, description='Телефон'),
                'email': openapi.Schema(type=openapi.TYPE_STRING, description='Email'),
                'description': openapi.Schema(type=openapi.TYPE_STRING, description='Описание')
                
            },
            required=['master', 'category', 'first_name', 'last_name', 'phone', 'email']
        ),
        responses={
            201: openapi.Response(description="Мастер добавлен", schema=MasterInMasterSerializer),
            400: openapi.Response(description="Неверные данные"),
            404: openapi.Response(description="Мастер или категория не найдены"),
            403: openapi.Response(description="Нет прав доступа")
        },
        tags=['Master In Master']
    )
    def post(self, request):
        """Добавление мастера в мастера с созданием нового пользователя"""
        from django.contrib.auth import get_user_model
        from django.contrib.auth.models import Group
        from apps.categories.models import Category
        import secrets
        import string
        
        User = get_user_model()
        
        # Получаем данные
        master_id = request.data.get('master')
        category_id = request.data.get('category')
        first_name = request.data.get('first_name')
        last_name = request.data.get('last_name')
        description = request.data.get('description')
        phone = request.data.get('phone')
        email = request.data.get('email')
        
        # Валидация обязательных полей
        if not all([master_id, category_id, first_name, last_name, phone, email]):
            return Response(
                {'error': 'Все поля обязательны: master, category, first_name, last_name, phone, email'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Проверяем, что мастер существует
        try:
            master = Master.objects.get(id=master_id)
        except Master.DoesNotExist:
            return Response(
                {'error': 'Мастер не найден'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Проверяем, что категория существует
        try:
            category = Category.objects.get(id=category_id)
        except Category.DoesNotExist:
            return Response(
                {'error': 'Категория не найдена'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Проверяем, что email уникален
        if User.objects.filter(email=email).exists():
            return Response(
                {'error': 'Пользователь с таким email уже существует'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Проверяем, что phone уникален
        if User.objects.filter(phone_number=phone).exists():
            return Response(
                {'error': 'Пользователь с таким телефоном уже существует'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Генерируем уникальный username
        username = email.split('@')[0]
        base_username = username
        counter = 1
        while User.objects.filter(username=username).exists():
            username = f"{base_username}{counter}"
            counter += 1
        
        # Генерируем случайный пароль
        password = ''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(12))
        
        # Создаем пользователя
        masterinmaster_user = User.objects.create_user(
            username=username,
            email=email,
            password=password,
            first_name=first_name,
            last_name=last_name,
            phone_number=phone,
            description=description
        )
        
        # Добавляем в группу MasterInMaster
        try:
            master_in_master_group = Group.objects.get(name='MasterInMaster')
            masterinmaster_user.groups.add(master_in_master_group)
        except Group.DoesNotExist:
            # Если группа не существует, создаем её
            master_in_master_group = Group.objects.create(name='MasterInMaster')
            masterinmaster_user.groups.add(master_in_master_group)
        
        # Проверяем, что связь не существует
        if MasterInMaster.objects.filter(master=master, masterinmaster=masterinmaster_user).exists():
            return Response(
                {'error': 'Мастер уже добавлен'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Создаем MasterInMaster
        master_in_master = MasterInMaster.objects.create(
            master=master,
            masterinmaster=masterinmaster_user,
            category=category
        )
        
        serializer = MasterInMasterSerializer(master_in_master, context={'request': request})
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class MasterInMasterByMasterView(APIView):
    """
    API для получения списка мастеров в мастере по master_id.
    
    GET: получение списка мастеров в мастере для конкретного мастера
    """
    permission_classes = [IsAuthenticated]
    
    @swagger_auto_schema(
        operation_description="Получить список мастеров в мастере по ID мастера",
        responses={
            200: openapi.Response(
                description="Список мастеров в мастере", 
                schema=MasterInMasterSerializer
            ),
            404: openapi.Response(description="Мастер не найден"),
            403: openapi.Response(description="Нет прав доступа")
        },
        tags=['Master In Master']
    )
    def get(self, request, master_id):
        """Получение списка мастеров в мастере"""
        try:
            master = Master.objects.get(id=master_id)
        except Master.DoesNotExist:
            return Response(
                {'error': 'Мастер не найден'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        master_in_masters = MasterInMaster.objects.filter(master=master).select_related('masterinmaster', 'category')
        serializer = MasterInMasterSerializer(master_in_masters, many=True, context={'request': request})
        return Response(serializer.data, status=status.HTTP_200_OK)


class MasterInMasterDetailView(APIView):
    """
    API для управления конкретным мастером в мастере.
    
    Поддерживаемые операции:
    - PUT/PATCH: обновление мастера в мастере (обновляет CustomUser)
    - DELETE: удаление мастера из мастера
    """
    permission_classes = [IsMasterGroup]
    
    def get_object(self, master_in_master_id):
        """Получить мастера в мастере"""
        try:
            return MasterInMaster.objects.get(id=master_in_master_id)
        except MasterInMaster.DoesNotExist:
            return None
    
    @swagger_auto_schema(
        operation_description="Обновить мастера в мастере (обновляет данные пользователя)",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'first_name': openapi.Schema(type=openapi.TYPE_STRING, description='Имя'),
                'last_name': openapi.Schema(type=openapi.TYPE_STRING, description='Фамилия'),
                'phone': openapi.Schema(type=openapi.TYPE_STRING, description='Телефон'),
                'email': openapi.Schema(type=openapi.TYPE_STRING, description='Email'),
                'category': openapi.Schema(type=openapi.TYPE_INTEGER, description='ID категории')
            }
        ),
        responses={
            200: openapi.Response(description="Мастер обновлен", schema=MasterInMasterSerializer),
            400: openapi.Response(description="Неверные данные"),
            404: openapi.Response(description="Мастер не найден"),
            403: openapi.Response(description="Нет прав доступа")
        },
        tags=['Master In Master']
    )
    def put(self, request, master_in_master_id):
        """Обновление мастера в мастере"""
        master_in_master = self.get_object(master_in_master_id)
        if not master_in_master:
            return Response(
                {'error': 'Мастер не найден'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        from django.contrib.auth import get_user_model
        from apps.categories.models import Category
        User = get_user_model()
        
        # Обновляем данные пользователя
        user = master_in_master.masterinmaster
        first_name = request.data.get('first_name')
        last_name = request.data.get('last_name')
        phone = request.data.get('phone')
        email = request.data.get('email')
        category_id = request.data.get('category')
        
        if first_name:
            user.first_name = first_name
        if last_name:
            user.last_name = last_name
        if phone:
            # Проверяем уникальность телефона
            if User.objects.filter(phone_number=phone).exclude(id=user.id).exists():
                return Response(
                    {'error': 'Пользователь с таким телефоном уже существует'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            user.phone_number = phone
        if email:
            # Проверяем уникальность email
            if User.objects.filter(email=email).exclude(id=user.id).exists():
                return Response(
                    {'error': 'Пользователь с таким email уже существует'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            user.email = email
            user.username = email.split('@')[0]  # Обновляем username
        
        user.save()
        
        # Обновляем категорию если передана
        if category_id:
            try:
                category = Category.objects.get(id=category_id)
                master_in_master.category = category
                master_in_master.save()
            except Category.DoesNotExist:
                return Response(
                    {'error': 'Категория не найдена'},
                    status=status.HTTP_404_NOT_FOUND
                )
        
        serializer = MasterInMasterSerializer(master_in_master, context={'request': request})
        return Response(serializer.data, status=status.HTTP_200_OK)
    
    @swagger_auto_schema(
        operation_description="Частичное обновление мастера в мастере",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'first_name': openapi.Schema(type=openapi.TYPE_STRING, description='Имя'),
                'last_name': openapi.Schema(type=openapi.TYPE_STRING, description='Фамилия'),
                'phone': openapi.Schema(type=openapi.TYPE_STRING, description='Телефон'),
                'email': openapi.Schema(type=openapi.TYPE_STRING, description='Email'),
                'category': openapi.Schema(type=openapi.TYPE_INTEGER, description='ID категории')
            }
        ),
        responses={
            200: openapi.Response(description="Мастер обновлен", schema=MasterInMasterSerializer),
            400: openapi.Response(description="Неверные данные"),
            404: openapi.Response(description="Мастер не найден"),
            403: openapi.Response(description="Нет прав доступа")
        },
        tags=['Master In Master']
    )
    def patch(self, request, master_in_master_id):
        """Частичное обновление мастера в мастере"""
        return self.put(request, master_in_master_id)
    
    @swagger_auto_schema(
        operation_description="Удалить мастера из мастера",
        responses={
            204: openapi.Response(description="Мастер удален"),
            404: openapi.Response(description="Мастер не найден"),
            403: openapi.Response(description="Нет прав доступа")
        },
        tags=['Master In Master']
    )
    def delete(self, request, master_in_master_id):
        """Удаление мастера из мастера"""
        master_in_master = self.get_object(master_in_master_id)
        if not master_in_master:
            return Response(
                {'error': 'Мастер не найден'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        master_in_master.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

