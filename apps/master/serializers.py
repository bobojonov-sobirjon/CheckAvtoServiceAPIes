from rest_framework import serializers
from .models import Master, ServiceType


class MasterSerializer(serializers.ModelSerializer):
    """Сериализатор для мастера"""
    user_name = serializers.ReadOnlyField(source='user.get_full_name')
    user_phone = serializers.ReadOnlyField(source='user.phone_number')
    services_display = serializers.SerializerMethodField()
    
    class Meta:
        model = Master
        fields = [
            'id', 'user', 'user_name', 'user_phone', 'city', 'services', 
            'services_display', 'card_number', 'card_expiry_month', 
            'card_expiry_year', 'card_cvv', 'reserved_amount', 
            'created_at', 'updated_at', 'last_activity'
        ]
        read_only_fields = ['id', 'user', 'created_at', 'updated_at', 'last_activity']
    
    def get_services_display(self, obj):
        """Получить отображаемые названия услуг"""
        return obj.get_services_display()
    
    def validate_services(self, value):
        """Валидация услуг"""
        if not isinstance(value, list):
            raise serializers.ValidationError("Услуги должны быть списком")
        
        valid_services = [choice[0] for choice in ServiceType.choices]
        for service in value:
            if service not in valid_services:
                raise serializers.ValidationError(f"Неверная услуга: {service}")
        
        return value
    
    def create(self, validated_data):
        """Создание мастера с автоматическим назначением пользователя"""
        validated_data['user'] = self.context['request'].user
        return super().create(validated_data)


class MasterCreateSerializer(serializers.ModelSerializer):
    """Сериализатор для создания мастера"""
    services = serializers.MultipleChoiceField(
        choices=ServiceType.choices,
        required=False,
        allow_empty=True
    )
    
    class Meta:
        model = Master
        fields = [
            'city', 'services', 'card_number', 'card_expiry_month', 
            'card_expiry_year', 'card_cvv'
        ]
    
    def validate_services(self, value):
        """Валидация услуг"""
        if not isinstance(value, list):
            raise serializers.ValidationError("Услуги должны быть списком")
        
        valid_services = [choice[0] for choice in ServiceType.choices]
        for service in value:
            if service not in valid_services:
                raise serializers.ValidationError(f"Неверная услуга: {service}")
        
        return value
    
    def create(self, validated_data):
        """Создание мастера с автоматическим назначением пользователя"""
        validated_data['user'] = self.context['request'].user
        return super().create(validated_data)


class ServiceTypeSerializer(serializers.Serializer):
    """Сериализатор для типов услуг"""
    value = serializers.CharField()
    label = serializers.CharField()
    
    @classmethod
    def get_all_services(cls):
        """Получить все доступные услуги"""
        return [
            {'value': choice[0], 'label': choice[1]} 
            for choice in ServiceType.choices
        ]
