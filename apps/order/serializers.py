from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import Order, OrderStatus, OrderPriority, Rating
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
    car_data = serializers.SerializerMethodField()
    category_data = serializers.SerializerMethodField()

    class Meta:
        model = Order
        fields = [
            'id', 'user',
            'car_data', 'category_data',
            'text', 'status', 'status_display', 'priority', 'priority_display',
            'location', 'latitude', 'longitude', 'master', 'masters',
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
    
    Поддерживает два сценария:
    1. SOS заказ: без мастера (master_id не указан) - для экстренных ситуаций
    2. Обычный заказ: с выбором мастера (master_id указан)
    
    Обязательные поля для обоих сценариев:
    - text: описание проблемы
    - priority: приоритет (low или high)
    - location: адрес местоположения
    - latitude: широта
    - longitude: долгота
    - car_list: список ID машин
    - category_list: список ID категорий проблем
    
    Необязательные поля:
    - master_id: ID мастера (для обычного заказа)
    - masters_list: список ID пользователей-мастеров (для рейтинга)
    """
    master_id = serializers.IntegerField(
        required=False,
        allow_null=True,
        write_only=True,
        help_text="ID мастера (необязательно). Не указывайте для SOS заказа, укажите для обычного заказа"
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
            'text', 'priority', 'location', 'latitude', 'longitude', 
            'master_id', 'car_list', 'category_list', 'masters_list'
        ]
        extra_kwargs = {
            'text': {'required': True},
            'priority': {'required': True},
            'location': {'required': True},
            'latitude': {'required': True},
            'longitude': {'required': True},
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
        Проверяет расстояние между заказом и мастером (если указан master_id)
        """
        master_id = attrs.get('master_id')
        order_lat = attrs.get('latitude')
        order_lon = attrs.get('longitude')
        
        # Если указан master_id, проверяем расстояние
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
            'text', 'status', 'priority', 'location', 'latitude', 'longitude', 'master'
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


class RatingSerializer(serializers.ModelSerializer):
    """Сериализатор для рейтинга"""
    user_name = serializers.CharField(source='user.get_full_name', read_only=True)
    master_name = serializers.CharField(source='master.full_name', read_only=True)
    
    class Meta:
        model = Rating
        fields = [
            'id', 'order', 'user', 'user_name', 'master', 'master_name',
            'rating', 'comment', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'user', 'created_at', 'updated_at']
    
    def validate_rating(self, value):
        """Валидация рейтинга"""
        if value < 1 or value > 5:
            raise serializers.ValidationError('Рейтинг должен быть от 1 до 5')
        return value
    
    def validate(self, data):
        """Общая валидация"""
        master = data.get('master')
        
        if not master:
            raise serializers.ValidationError('Должен быть указан мастер')
        
        return data
    
    def create(self, validated_data):
        """Создание рейтинга с автоматическим назначением пользователя"""
        validated_data['user'] = self.context['request'].user
        return super().create(validated_data)
