from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.conf import settings
from .models import (
    Order,
    OrderStatus,
    OrderPriority,
    OrderType,
    OrderPaymentStatus,
    Rating,
    OrderService,
    Review,
    ReviewTag,
    UserRating,
)
from apps.accounts.models import SbpPaymentIntent
from apps.accounts.sbp_qr import pay_url_to_qr_png_base64
from apps.car.models import Car
from apps.categories.models import Category
from apps.master.models import Master
from apps.accounts.serializers import UserSerializer
from apps.car.serializers import CarSerializer
from apps.categories.serializers import CategorySerializer
from apps.master.serializers import MasterSerializer

User = get_user_model()


class OrderSerializer(serializers.ModelSerializer):
    """Сериализатор для заказа"""
    user = serializers.SerializerMethodField()
    master = serializers.SerializerMethodField()
    masters = serializers.SerializerMethodField()
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    priority_display = serializers.CharField(source='get_priority_display', read_only=True)
    order_type_display = serializers.CharField(source='get_order_type_display', read_only=True)
    car_data = serializers.SerializerMethodField()
    category_data = serializers.SerializerMethodField()
    services = serializers.SerializerMethodField()
    reviews = serializers.SerializerMethodField()
    average_rating = serializers.SerializerMethodField()
    payment = serializers.SerializerMethodField()

    class Meta:
        model = Order
        fields = [
            'id', 'user', 'order_type', 'order_type_display',
            'car_data', 'category_data',
            'text', 'status', 'status_display', 'priority', 'priority_display',
            'location', 'latitude', 'longitude', 'master', 'masters',
            'scheduled_date', 'scheduled_time_start', 'scheduled_time_end',
            'discount', 'services', 'reviews', 'average_rating', 'payment',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def get_user(self, obj):
        return UserSerializer(obj.user, context=self.context).data
    
    def get_master(self, obj):
        return MasterSerializer(obj.master, context=self.context).data
    
    def get_masters(self, obj):
        """Получить список назначенных мастеров (пользователей)"""
        masters = obj.masters.all()
        return [
            {
                'id': user.id,
                'private_id': user.private_id,
                'full_name': user.get_full_name(),
                'phone_number': user.phone_number,
                'email': user.email,
                'avatar': self.context['request'].build_absolute_uri(user.avatar.url) if user.avatar and self.context.get('request') else None
            }
            for user in masters
        ]
    
    def get_car_data(self, obj):
        return CarSerializer(obj.car, many=True, context=self.context).data
    
    def get_category_data(self, obj):
        return CategorySerializer(obj.category, many=True, context=self.context).data
    
    def get_car_data(self, obj):
        """Получить данные машин"""
        cars = obj.car.all()
        return [
            {
                'id': car.id,
                'brand': car.brand,
                'model': car.model,
                'year': car.year,
                'category': car.category.name if car.category else None
            }
            for car in cars
        ]
    
    def get_category_data(self, obj):
        """Получить данные категорий"""
        categories = obj.category.all()
        return [
            {
                'id': category.id,
                'name': category.name,
                'type_category': category.type_category
            }
            for category in categories
        ]
    
    def get_services(self, obj):
        """Получить услуги заказа"""
        from apps.master.serializers import MasterServiceItemsSerializer
        
        order_services = obj.order_services.all().select_related('master_service_item')
        return [
            MasterServiceItemsSerializer(os.master_service_item).data
            for os in order_services if os.master_service_item
        ]

    def get_payment(self, obj):
        """Оплата заказа: dynamic Alfa form_url + статус intent (если используется)."""
        pay_url = (getattr(settings, 'SBP_QR_PAY_URL', '') or '').strip()
        intent = obj.sbp_payment_intent
        data: dict = {
            'status': obj.payment_status,
            'calculated_total': None,
            'amount': None,
            'intent_id': None,
            'sbp_intent_status': None,
            'alfa_order_id': obj.alfa_order_id or None,
            'alfa_order_number': obj.alfa_order_number or None,
            'form_url': obj.alfa_form_url or None,
        }
        try:
            from .sbp_payment import compute_order_services_total

            data['calculated_total'] = str(compute_order_services_total(obj))
        except Exception:
            pass
        if intent:
            data['amount'] = str(intent.amount)
            data['intent_id'] = str(intent.id)
            data['sbp_intent_status'] = intent.status
        # NB: Для заказов используем только form_url (dynamic). Статический pay_url/QR здесь не отдаём,
        # чтобы клиент не оплатил «мимо» нужного mdOrder.
        return data
    
    def get_reviews(self, obj):
        """Получить отзывы о заказе"""
        from .models import Review
        
        reviews = Review.objects.filter(order=obj).select_related('reviewer')
        if not reviews.exists():
            return []
        
        return [
            {
                'id': review.id,
                'rating': review.rating,
                'comment': review.comment,
                'tag': review.tag,
                'tag_display': review.get_tag_display(),
                'reviewer': {
                    'id': review.reviewer.id,
                    'full_name': review.reviewer.get_full_name(),
                    'avatar': self.context['request'].build_absolute_uri(review.reviewer.avatar.url) if review.reviewer.avatar and self.context.get('request') else None
                } if review.reviewer else None,
                'created_at': review.created_at
            }
            for review in reviews
        ]
    
    def get_average_rating(self, obj):
        """Получить средний рейтинг заказа"""
        from django.db.models import Avg
        from .models import Review
        
        avg = Review.objects.filter(order=obj).aggregate(avg_rating=Avg('rating'))
        return round(avg['avg_rating'], 2) if avg['avg_rating'] else None

    def validate_latitude(self, value):
        """Валидация широты"""
        if value is not None and (value < -90 or value > 90):
            raise serializers.ValidationError('Широта должна быть между -90 и 90')
        return value

    def validate_longitude(self, value):
        """Валидация долготы"""
        if value is not None and (value < -180 or value > 180):
            raise serializers.ValidationError('Долгота должна быть между -180 и 180')
        return value


class OrderCreateSerializer(serializers.ModelSerializer):
    """
    Сериализатор для создания заказа
    
    Поддерживает два типа заказов:
    1. SCHEDULED (запланированный): клиент выбирает мастера, дату и время визита
    2. SOS (экстренный): клиент делает срочный заказ с текущей геолокацией
    
    Обязательные поля для обоих типов:
    - order_type: тип заказа ('scheduled' или 'sos')
    - text: описание проблемы
    - location: адрес местоположения
    - latitude: широта
    - longitude: долгота
    - car_list: список ID машин
    - category_list: список ID категорий проблем
    
    Для SCHEDULED заказа дополнительно обязательно:
    - master_id: ID мастера
    - scheduled_date: дата визита
    - scheduled_time_start: время начала
    - scheduled_time_end: время окончания
    
    Для SOS заказа дополнительно обязательно:
    - master_id: ID мастера
    - priority: приоритет заказа ('low' или 'high')
    """
    order_type = serializers.ChoiceField(
        choices=OrderType.choices,
        required=True,
        help_text="Тип заказа: 'scheduled' (запланированный) или 'sos' (экстренный)"
    )
    master_id = serializers.IntegerField(
        required=False,
        allow_null=True,
        write_only=True,
        help_text="ID мастера (обязательно для scheduled и sos)"
    )
    car_list = serializers.ListField(
        child=serializers.IntegerField(),
        required=True,
        allow_empty=False,
        write_only=True,
        help_text="Список ID машин [1, 2, 3, ...] (обязательно)"
    )
    category_list = serializers.ListField(
        child=serializers.IntegerField(),
        required=True,
        allow_empty=False,
        write_only=True,
        help_text="Список ID категорий [1, 2, 3, ...] (обязательно)"
    )
    masters_list = serializers.ListField(
        child=serializers.IntegerField(),
        required=False,
        allow_empty=True,
        write_only=True,
        help_text="Список ID пользователей-мастеров [1, 2, 3, ...] для назначения на заказ (необязательно)"
    )
    
    class Meta:
        model = Order
        fields = [
            'order_type', 'text', 'priority', 'location', 'latitude', 'longitude', 
            'master_id', 'scheduled_date', 'scheduled_time_start', 'scheduled_time_end',
            'car_list', 'category_list', 'masters_list'
        ]
        extra_kwargs = {
            'text': {'required': True},
            'location': {'required': True},
            'latitude': {'required': True},
            'longitude': {'required': True},
            'priority': {'required': False},  # Для SOS avtomatik
            'scheduled_date': {'required': False},
            'scheduled_time_start': {'required': False},
            'scheduled_time_end': {'required': False},
        }

    def validate_master_id(self, value):
        """Валидация мастера"""
        if value is not None:
            try:
                Master.objects.get(id=value)
            except Master.DoesNotExist:
                raise serializers.ValidationError(f"Мастер с ID {value} не найден")
        return value
    
    def validate_car_list(self, value):
        """Валидация списка машин"""
        if not isinstance(value, list):
            raise serializers.ValidationError("car_list должен быть списком ID")
        
        for car_id in value:
            try:
                Car.objects.get(id=car_id)
            except Car.DoesNotExist:
                raise serializers.ValidationError(f"Машина с ID {car_id} не найдена")
        
        return value
    
    def validate_category_list(self, value):
        """Валидация списка категорий"""
        if not isinstance(value, list):
            raise serializers.ValidationError("category_list должен быть списком ID")
        
        for category_id in value:
            try:
                Category.objects.get(id=category_id)
            except Category.DoesNotExist:
                raise serializers.ValidationError(f"Категория с ID {category_id} не найдена")
        
        return value
    
    def validate_masters_list(self, value):
        """Валидация списка мастеров (пользователей)"""
        if not isinstance(value, list):
            raise serializers.ValidationError("masters_list должен быть списком ID")
        
        for user_id in value:
            try:
                User.objects.get(id=user_id)
            except User.DoesNotExist:
                raise serializers.ValidationError(f"Пользователь с ID {user_id} не найден")
        
        return value

    def validate_latitude(self, value):
        """Валидация широты"""
        if value is not None and (value < -90 or value > 90):
            raise serializers.ValidationError('Широта должна быть между -90 и 90')
        return value

    def validate_longitude(self, value):
        """Валидация долготы"""
        if value is not None and (value < -180 or value > 180):
            raise serializers.ValidationError('Долгота должна быть между -180 и 180')
        return value
    
    def validate(self, attrs):
        """
        Общая валидация данных заказа
        Проверяет обязательные поля в зависимости от типа заказа
        """
        order_type = attrs.get('order_type')
        master_id = attrs.get('master_id')
        order_lat = attrs.get('latitude')
        order_lon = attrs.get('longitude')
        
        # Валидация для SCHEDULED заказов
        if order_type == OrderType.SCHEDULED:
            # Для scheduled обязательны: master_id, scheduled_date, scheduled_time_start, scheduled_time_end
            if not master_id:
                raise serializers.ValidationError({
                    'master_id': 'Для запланированного заказа необходимо указать мастера'
                })
            if not attrs.get('scheduled_date'):
                raise serializers.ValidationError({
                    'scheduled_date': 'Для запланированного заказа необходимо указать дату визита'
                })
            if not attrs.get('scheduled_time_start'):
                raise serializers.ValidationError({
                    'scheduled_time_start': 'Для запланированного заказа необходимо указать время начала'
                })
            if not attrs.get('scheduled_time_end'):
                raise serializers.ValidationError({
                    'scheduled_time_end': 'Для запланированного заказа необходимо указать время окончания'
                })
            
            # Проверяем, что дата в будущем
            from datetime import date
            if attrs.get('scheduled_date') < date.today():
                raise serializers.ValidationError({
                    'scheduled_date': 'Дата визита не может быть в прошлом'
                })
            
            # Проверяем, что время начала < времени окончания
            if attrs.get('scheduled_time_start') >= attrs.get('scheduled_time_end'):
                raise serializers.ValidationError({
                    'scheduled_time_start': 'Время начала должно быть меньше времени окончания'
                })
        
        # Валидация для SOS заказов
        elif order_type == OrderType.SOS:
            # Для SOS обязательны: master_id и priority
            if not master_id:
                raise serializers.ValidationError({
                    'master_id': 'Для SOS заказа необходимо указать мастера'
                })
            
            # Проверяем, что priority указан
            if not attrs.get('priority'):
                raise serializers.ValidationError({
                    'priority': 'Для SOS заказа необходимо указать приоритет (low или high)'
                })
            
            # SOS не должен иметь scheduled полей
            attrs['scheduled_date'] = None
            attrs['scheduled_time_start'] = None
            attrs['scheduled_time_end'] = None
        
        # Проверка расстояния между заказом и мастером (если указан master_id)
        if master_id and order_lat and order_lon:
            try:
                master = Master.objects.get(id=master_id)
                
                # Проверяем, есть ли у мастера координаты
                if not master.latitude or not master.longitude:
                    raise serializers.ValidationError({
                        'master_id': 'У выбранного мастера не указаны координаты. Пожалуйста, выберите другого мастера.'
                    })
                
                # Вычисляем расстояние по формуле Haversine
                from math import radians, sin, cos, sqrt, atan2
                
                R = 6371.0  # Радиус Земли в километрах
                
                # Координаты мастера
                master_lat = float(master.latitude)
                master_lon = float(master.longitude)
                
                # Координаты заказа
                lat1 = float(order_lat)
                lon1 = float(order_lon)
                
                # Конвертируем в радианы
                lat1_rad = radians(lat1)
                lon1_rad = radians(lon1)
                lat2_rad = radians(master_lat)
                lon2_rad = radians(master_lon)
                
                # Формула Haversine
                dlat = lat2_rad - lat1_rad
                dlon = lon2_rad - lon1_rad
                
                a = sin(dlat / 2)**2 + cos(lat1_rad) * cos(lat2_rad) * sin(dlon / 2)**2
                c = 2 * atan2(sqrt(a), sqrt(1 - a))
                distance = R * c
                
                # Проверяем, что расстояние не больше 50 км
                MAX_DISTANCE = 50  # км
                if distance > MAX_DISTANCE:
                    raise serializers.ValidationError({
                        'master_id': f'Выбранный мастер находится слишком далеко ({distance:.1f} км). '
                                   f'Максимальное расстояние: {MAX_DISTANCE} км. '
                                   f'Пожалуйста, выберите мастера ближе к вашему местоположению.'
                    })
                
            except Master.DoesNotExist:
                # Эта ошибка уже обрабатывается в validate_master_id
                pass
        
        return attrs
    
    def create(self, validated_data):
        """Создание заказа с машинами, категориями и мастерами"""
        # Извлекаем списки ID
        master_id = validated_data.pop('master_id', None)
        car_list = validated_data.pop('car_list', [])
        category_list = validated_data.pop('category_list', [])
        masters_list = validated_data.pop('masters_list', [])
        
        # Устанавливаем мастера, если указан
        if master_id:
            validated_data['master'] = Master.objects.get(id=master_id)
        
        # Создаем заказ
        order = super().create(validated_data)
        
        # Добавляем машины
        if car_list:
            order.car.set(car_list)
        
        # Добавляем категории
        if category_list:
            order.category.set(category_list)
        
        # Добавляем мастеров (пользователей)
        if masters_list:
            order.masters.set(masters_list)
        
        return order


class OrderUpdateSerializer(serializers.ModelSerializer):
    """Сериализатор для обновления заказа"""
    
    class Meta:
        model = Order
        fields = [
            'text', 'status', 'priority', 'location', 'latitude', 'longitude', 'master',
            'scheduled_date', 'scheduled_time_start', 'scheduled_time_end'
        ]

    def validate_latitude(self, value):
        """Валидация широты"""
        if value is not None and (value < -90 or value > 90):
            raise serializers.ValidationError('Широта должна быть между -90 и 90')
        return value

    def validate_longitude(self, value):
        """Валидация долготы"""
        if value is not None and (value < -180 or value > 180):
            raise serializers.ValidationError('Долгота должна быть между -180 и 180')
        return value


class OrderStatusUpdateSerializer(serializers.Serializer):
    """Сериализатор для обновления статуса заказа"""
    status = serializers.ChoiceField(choices=OrderStatus.choices)
    
    def validate_status(self, value):
        """Валидация статуса"""
        if value not in [choice[0] for choice in OrderStatus.choices]:
            raise serializers.ValidationError('Недопустимый статус заказа')
        return value


class OrderServiceSerializer(serializers.ModelSerializer):
    """Сериализатор для услуг в заказе"""
    service_details = serializers.SerializerMethodField()
    
    class Meta:
        model = OrderService
        fields = ['id', 'order', 'master_service_item', 'service_details', 'created_at']
        read_only_fields = ['id', 'created_at']
    
    def get_service_details(self, obj):
        """Получить детали услуги"""
        if obj.master_service_item:
            from apps.master.serializers import MasterServiceItemsSerializer
            return MasterServiceItemsSerializer(obj.master_service_item).data
        return None


class AddServicesToOrderSerializer(serializers.Serializer):
    """Сериализатор для добавления услуг к заказу"""
    order_id = serializers.IntegerField()
    services_list = serializers.ListField(
        child=serializers.IntegerField(),
        allow_empty=False,
        help_text='Список ID услуг мастера (MasterServiceItems)'
    )
    discount = serializers.DecimalField(
        max_digits=10,
        decimal_places=2,
        required=False,
        default=0.00,
        help_text='Скидка на заказ'
    )
    
    def validate_order_id(self, value):
        """Проверка существования заказа"""
        try:
            Order.objects.get(id=value)
        except Order.DoesNotExist:
            raise serializers.ValidationError(f'Заказ с ID {value} не найден')
        return value
    
    def validate_services_list(self, value):
        """Проверка существования услуг"""
        from apps.master.models import MasterServiceItems
        
        if not value:
            raise serializers.ValidationError('Список услуг не может быть пустым')
        
        # Проверяем существование всех услуг
        existing_services = MasterServiceItems.objects.filter(id__in=value)
        existing_ids = set(existing_services.values_list('id', flat=True))
        
        invalid_ids = set(value) - existing_ids
        if invalid_ids:
            raise serializers.ValidationError(
                f'Услуги с ID {list(invalid_ids)} не найдены'
            )
        
        return value


class AddMastersToOrderSerializer(serializers.Serializer):
    """Сериализатор для добавления мастеров к заказу"""
    order_id = serializers.IntegerField(
        help_text='ID заказа'
    )
    master_ids = serializers.ListField(
        child=serializers.IntegerField(),
        allow_empty=False,
        help_text='Список ID пользователей-мастеров [1, 2, 3, ...]'
    )
    
    def validate_order_id(self, value):
        """Проверка существования заказа"""
        try:
            Order.objects.get(id=value)
        except Order.DoesNotExist:
            raise serializers.ValidationError(f'Заказ с ID {value} не найден')
        return value
    
    def validate_master_ids(self, value):
        """Проверка существования пользователей"""
        if not value:
            raise serializers.ValidationError('Список master_ids не может быть пустым')
        
        # Проверяем существование всех пользователей
        existing_users = User.objects.filter(id__in=value)
        existing_ids = set(existing_users.values_list('id', flat=True))
        
        invalid_ids = set(value) - existing_ids
        if invalid_ids:
            raise serializers.ValidationError(
                f'Пользователи с ID {list(invalid_ids)} не найдены'
            )
        
        return value


class ReviewSerializer(serializers.ModelSerializer):
    """Сериализатор для отзывов"""
    reviewer_info = serializers.SerializerMethodField()
    tag_display = serializers.CharField(source='get_tag_display', read_only=True)
    order_info = serializers.SerializerMethodField()
    
    class Meta:
        model = Review
        fields = [
            'id', 'order', 'order_info', 'reviewer', 'reviewer_info', 
            'rating', 'comment', 'tag', 'tag_display', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'reviewer', 'created_at', 'updated_at']
    
    def get_reviewer_info(self, obj):
        """Информация об авторе отзыва"""
        if obj.reviewer:
            return {
                'id': obj.reviewer.id,
                'full_name': obj.reviewer.get_full_name(),
                'email': obj.reviewer.email,
                'avatar': obj.reviewer.avatar.url if obj.reviewer.avatar else None
            }
        return None
    
    def get_order_info(self, obj):
        """Краткая информация о заказе"""
        if obj.order:
            return {
                'id': obj.order.id,
                'text': obj.order.text,
                'status': obj.order.status,
                'created_at': obj.order.created_at
            }
        return None


class ReviewCreateSerializer(serializers.Serializer):
    """Сериализатор для создания отзыва"""
    order_id = serializers.IntegerField(
        help_text='ID заказа'
    )
    rating = serializers.IntegerField(
        min_value=1,
        max_value=5,
        help_text='Рейтинг от 1 до 5'
    )
    comment = serializers.CharField(
        required=False,
        allow_blank=True,
        help_text='Комментарий к отзыву'
    )
    tag = serializers.ChoiceField(
        choices=ReviewTag.choices,
        help_text='Что понравилось в работе мастера (выберите одно)'
    )
    
    def validate_order_id(self, value):
        """Проверка существования заказа"""
        try:
            order = Order.objects.get(id=value)
            
            # Проверяем, что заказ завершен
            if order.status != OrderStatus.COMPLETED:
                raise serializers.ValidationError(
                    'Отзыв можно оставить только для завершенного заказа'
                )
            
            # Проверяем, что отзыв еще не оставлен
            if Review.objects.filter(order=order).exists():
                raise serializers.ValidationError(
                    'Отзыв для этого заказа уже оставлен'
                )
            
        except Order.DoesNotExist:
            raise serializers.ValidationError(f'Заказ с ID {value} не найден')
        return value
