from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import Order, OrderStatus, OrderPriority

User = get_user_model()


class OrderSerializer(serializers.ModelSerializer):
    """Сериализатор для заказа"""
    user_name = serializers.CharField(source='user.get_full_name', read_only=True)
    user_email = serializers.CharField(source='user.email', read_only=True)
    user_phone = serializers.CharField(source='user.phone_number', read_only=True)
    master_name = serializers.CharField(source='master.full_name', read_only=True)
    master_phone = serializers.CharField(source='master.phone', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    priority_display = serializers.CharField(source='get_priority_display', read_only=True)

    class Meta:
        model = Order
        fields = [
            'id', 'user', 'user_name', 'user_email', 'user_phone',
            'text', 'status', 'status_display', 'priority', 'priority_display',
            'data', 'location', 'latitude', 'longitude', 'master', 
            'master_name', 'master_phone', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

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
    
    class Meta:
        model = Order
        fields = [
            'text', 'priority', 'data', 'location', 'latitude', 'longitude', 'master'
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


class OrderUpdateSerializer(serializers.ModelSerializer):
    """Сериализатор для обновления заказа"""
    
    class Meta:
        model = Order
        fields = [
            'text', 'status', 'priority', 'data', 'location', 'latitude', 'longitude', 'master'
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
