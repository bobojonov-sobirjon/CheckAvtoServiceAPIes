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
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    priority_display = serializers.CharField(source='get_priority_display', read_only=True)
    master_in_master_data = serializers.SerializerMethodField()
    car_data = serializers.SerializerMethodField()
    category_data = serializers.SerializerMethodField()

    class Meta:
        model = Order
        fields = [
            'id', 'user',
            'car_data', 'category_data',
            'text', 'status', 'status_display', 'priority', 'priority_display',
            'location', 'latitude', 'longitude', 'master', 
            'master_in_master_data', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def get_user(self, obj):
        return UserSerializer(obj.user, context=self.context).data
    
    def get_master(self, obj):
        return MasterSerializer(obj.master, context=self.context).data
    
    def get_car_data(self, obj):
        return CarSerializer(obj.car, many=True, context=self.context).data
    
    def get_category_data(self, obj):
        return CategorySerializer(obj.category, many=True, context=self.context).data
    
    def get_master_in_master_data(self, obj):
        """Получить данные мастеров в мастере"""
        master_in_masters = obj.master_in_master.all()
        return [
            {
                'id': user.id,
                'full_name': user.get_full_name(),
                'phone_number': user.phone_number,
                'email': user.email,
                'description': user.description
            }
            for user in master_in_masters
        ]
    
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
    """Сериализатор для создания заказа"""
    master_id = serializers.IntegerField(
        required=False,
        allow_null=True,
        write_only=True,
        help_text="ID мастера"
    )
    car_list = serializers.ListField(
        child=serializers.IntegerField(),
        required=False,
        allow_empty=True,
        write_only=True,
        help_text="Список ID машин [1, 2, 3, ...]"
    )
    category_list = serializers.ListField(
        child=serializers.IntegerField(),
        required=False,
        allow_empty=True,
        write_only=True,
        help_text="Список ID категорий [1, 2, 3, ...]"
    )
    master_in_master_list = serializers.ListField(
        child=serializers.IntegerField(),
        required=False,
        allow_empty=True,
        write_only=True,
        help_text="Список ID пользователей (MasterInMaster group) [1, 2, 3, ...]"
    )
    
    class Meta:
        model = Order
        fields = [
            'text', 'priority', 'location', 'latitude', 'longitude', 
            'master_id', 'car_list', 'category_list', 'master_in_master_list'
        ]

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
    
    def validate_master_in_master_list(self, value):
        """Валидация мастеров в мастере"""
        if not isinstance(value, list):
            raise serializers.ValidationError("master_in_master_list должен быть списком ID")
        
        # Проверяем, что все пользователи существуют и в группе MasterInMaster
        for user_id in value:
            try:
                user = User.objects.get(id=user_id)
                if not user.groups.filter(name='MasterInMaster').exists():
                    raise serializers.ValidationError(f"Пользователь с ID {user_id} должен быть в группе MasterInMaster")
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
    
    def create(self, validated_data):
        """Создание заказа с машинами, категориями и мастерами в мастере"""
        # Извлекаем списки ID
        master_id = validated_data.pop('master_id', None)
        car_list = validated_data.pop('car_list', [])
        category_list = validated_data.pop('category_list', [])
        master_in_master_list = validated_data.pop('master_in_master_list', [])
        
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
        
        # Добавляем мастеров в мастере
        if master_in_master_list:
            order.master_in_master.set(master_in_master_list)
        
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
    master_in_master_name = serializers.CharField(source='master_in_master.get_full_name', read_only=True)
    
    class Meta:
        model = Rating
        fields = [
            'id', 'order', 'user', 'user_name', 'master', 'master_name',
            'master_in_master', 'master_in_master_name', 'rating', 'comment',
            'created_at', 'updated_at'
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
        master_in_master = data.get('master_in_master')
        
        if not master and not master_in_master:
            raise serializers.ValidationError('Должен быть указан либо мастер, либо мастер в мастере')
        
        if master and master_in_master:
            raise serializers.ValidationError('Нельзя указать одновременно и мастер, и мастер в мастере')
        
        return data
    
    def create(self, validated_data):
        """Создание рейтинга с автоматическим назначением пользователя"""
        validated_data['user'] = self.context['request'].user
        return super().create(validated_data)
