from rest_framework import serializers
from .models import Master, MasterService, ServiceType


class MasterSerializer(serializers.ModelSerializer):
    """Сериализатор для мастера"""
    user_info = serializers.SerializerMethodField()
    service_type_display = serializers.SerializerMethodField()
    services = serializers.SerializerMethodField()
    
    class Meta:
        model = Master
        fields = [
            'id', 'user_info', 'city', 'address', 
            'latitude', 'longitude', 'phone', 'working_time', 'service_type_display', 'services',
            'card_number', 'card_expiry_month', 'card_expiry_year', 
            'card_cvv', 'balance', 'created_at', 'updated_at', 
            'last_activity'
        ]
        read_only_fields = ['id', 'user', 'created_at', 'updated_at', 'last_activity']
    
    def get_service_type_display(self, obj):
        """Получить отображаемое название типа услуги"""
        if obj.service_type:
            for choice in ServiceType.choices:
                if choice[0] == obj.service_type:
                    return choice[1]
        return obj.service_type
    
    def get_user_info(self, obj):
        """Получить полную информацию о пользователе"""
        return {
            'id': obj.user.id,
            'full_name': obj.user.get_full_name(),
            'phone_number': obj.user.phone_number,
            'email': obj.user.email,
            'is_active': obj.user.is_active,
            'date_joined': obj.user.date_joined
        }
    
    def get_services(self, obj):
        """Получить услуги мастера"""
        master_services = MasterService.objects.filter(master=obj)
        return MasterServiceSerializer(master_services, many=True, context=self.context).data
    
    def validate_service_type(self, value):
        """Валидация типа услуги"""
        if value and value not in [choice[0] for choice in ServiceType.choices]:
            raise serializers.ValidationError(f"Неверный тип услуги: {value}")
        return value
    
    def validate_latitude(self, value):
        """Валидация широты"""
        if value is not None:
            if not (-90 <= value <= 90):
                raise serializers.ValidationError("Широта должна быть между -90 и 90")
        return value
    
    def validate_longitude(self, value):
        """Валидация долготы"""
        if value is not None:
            if not (-180 <= value <= 180):
                raise serializers.ValidationError("Долгота должна быть между -180 и 180")
        return value
    
    def create(self, validated_data):
        """Создание мастера с автоматическим назначением пользователя"""
        validated_data['user'] = self.context['request'].user
        return super().create(validated_data)


class MasterCreateSerializer(serializers.ModelSerializer):
    """Сериализатор для создания мастера"""
    services = serializers.ListField(
        child=serializers.DictField(),
        required=False,
        allow_empty=True,
        write_only=True
    )
    
    class Meta:
        model = Master
        fields = [
            'city', 'address', 'latitude', 'longitude', 'service_type', 'services',
            'card_number', 'card_expiry_month', 'card_expiry_year', 
            'card_cvv'
        ]
    
    def validate_service_type(self, value):
        """Валидация типа услуги"""
        if value and value not in [choice[0] for choice in ServiceType.choices]:
            raise serializers.ValidationError(f"Неверный тип услуги: {value}")
        return value
    
    def validate_latitude(self, value):
        """Валидация широты"""
        if value is not None:
            if not (-90 <= value <= 90):
                raise serializers.ValidationError("Широта должна быть между -90 и 90")
        return value
    
    def validate_longitude(self, value):
        """Валидация долготы"""
        if value is not None:
            if not (-180 <= value <= 180):
                raise serializers.ValidationError("Долгота должна быть между -180 и 180")
        return value
    
    def validate_services(self, value):
        """Валидация услуг"""
        if not isinstance(value, list):
            raise serializers.ValidationError("Услуги должны быть списком")
        
        # Проверяем, что каждый элемент - это объект с name, price_from и price_to
        for service in value:
            if not isinstance(service, dict):
                raise serializers.ValidationError("Каждая услуга должна быть объектом")
            if 'name' not in service:
                raise serializers.ValidationError("Каждая услуга должна содержать 'name'")
            if 'price_from' not in service:
                raise serializers.ValidationError("Каждая услуга должна содержать 'price_from'")
            if 'price_to' not in service:
                raise serializers.ValidationError("Каждая услуга должна содержать 'price_to'")
        
        return value
    
    def create(self, validated_data):
        """Создание мастера с автоматическим назначением пользователя"""
        services_data = validated_data.pop('services', [])
        validated_data['user'] = self.context['request'].user
        
        master = super().create(validated_data)
        
        # Создаем услуги мастера
        for service_data in services_data:
            MasterService.objects.create(
                master=master,
                name=service_data['name'],
                price_from=service_data['price_from'],
                price_to=service_data['price_to']
            )
        
        return master


class MasterUpdateSerializer(serializers.ModelSerializer):
    """Сериализатор для обновления мастера (частичное обновление)"""
    
    class Meta:
        model = Master
        fields = [
            'city', 'address', 'latitude', 'longitude', 'phone', 'working_time', 
            'service_type', 'card_number', 'card_expiry_month', 'card_expiry_year', 
            'card_cvv'
        ]
        extra_kwargs = {
            'city': {'required': False},
            'address': {'required': False},
            'latitude': {'required': False},
            'longitude': {'required': False},
            'phone': {'required': False},
            'working_time': {'required': False},
            'service_type': {'required': False},
            'card_number': {'required': False},
            'card_expiry_month': {'required': False},
            'card_expiry_year': {'required': False},
            'card_cvv': {'required': False},
        }
    
    def validate_service_type(self, value):
        """Валидация типа услуги"""
        if value and value not in [choice[0] for choice in ServiceType.choices]:
            raise serializers.ValidationError(f"Неверный тип услуги: {value}")
        return value
    
    def validate_latitude(self, value):
        """Валидация широты"""
        if value is not None:
            if not (-90 <= value <= 90):
                raise serializers.ValidationError("Широта должна быть между -90 и 90")
        return value
    
    def validate_longitude(self, value):
        """Валидация долготы"""
        if value is not None:
            if not (-180 <= value <= 180):
                raise serializers.ValidationError("Долгота должна быть между -180 и 180")
        return value


class MasterNearbySerializer(serializers.ModelSerializer):
    """Сериализатор для мастеров поблизости"""
    user_name = serializers.ReadOnlyField(source='user.get_full_name')
    user_phone = serializers.ReadOnlyField(source='user.phone_number')
    services_display = serializers.SerializerMethodField()
    distance = serializers.SerializerMethodField()
    
    class Meta:
        model = Master
        fields = [
            'id', 'user_name', 'user_phone', 'city', 'address', 
            'latitude', 'longitude', 'services', 'services_display', 
            'distance'
        ]
    
    def get_services_display(self, obj):
        """Получить отображаемые названия услуг"""
        master_services = MasterService.objects.filter(master=obj)
        return [service.name for service in master_services]
    
    def get_distance(self, obj):
        """Получить расстояние (будет установлено в view)"""
        return getattr(obj, 'calculated_distance', None)


class MasterServiceSerializer(serializers.ModelSerializer):
    """Сериализатор для услуг мастера"""
    
    class Meta:
        model = MasterService
        fields = [
            'id', 'name', 'price_from', 'price_to', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']
    
    def validate_price_from(self, value):
        """Валидация цены от"""
        if value < 0:
            raise serializers.ValidationError("Цена не может быть отрицательной")
        return value
    
    def validate_price_to(self, value):
        """Валидация цены до"""
        if value < 0:
            raise serializers.ValidationError("Цена не может быть отрицательной")
        return value
    
    def validate(self, data):
        """Общая валидация"""
        price_from = data.get('price_from')
        price_to = data.get('price_to')
        
        if price_from and price_to and price_from > price_to:
            raise serializers.ValidationError(
                "Цена 'от' не может быть больше цены 'до'"
            )
        
        return data


