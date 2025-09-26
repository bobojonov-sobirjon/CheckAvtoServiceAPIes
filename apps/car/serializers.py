from rest_framework import serializers
from .models import Car


class CarSerializer(serializers.ModelSerializer):
    """Сериализатор для машины"""
    user_name = serializers.ReadOnlyField(source='user.get_full_name')
    user_phone = serializers.ReadOnlyField(source='user.phone_number')
    
    class Meta:
        model = Car
        fields = [
            'id', 'type_car', 'brand', 'model', 'year', 
            'user', 'user_name', 'user_phone', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'user', 'created_at', 'updated_at']
    
    def create(self, validated_data):
        """Создание машины с автоматическим назначением пользователя"""
        validated_data['user'] = self.context['request'].user
        return super().create(validated_data)


class CarCreateSerializer(serializers.ModelSerializer):
    """Сериализатор для создания машины"""
    
    class Meta:
        model = Car
        fields = ['type_car', 'brand', 'model', 'year']
    
    def create(self, validated_data):
        """Создание машины с автоматическим назначением пользователя"""
        validated_data['user'] = self.context['request'].user
        return super().create(validated_data)
