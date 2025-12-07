from rest_framework import serializers
from .models import Car
from apps.categories.serializers import CategorySerializer
from apps.accounts.serializers import UserSerializer


class CarSerializer(serializers.ModelSerializer):
    """Сериализатор для машины"""
    category = serializers.SerializerMethodField()
    user = serializers.SerializerMethodField()
    
    class Meta:
        model = Car
        fields = [
            'id', 'category', 'brand', 'model', 'year', 
            'user', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'user', 'created_at', 'updated_at']
    
    def create(self, validated_data):
        """Создание машины с автоматическим назначением пользователя"""
        validated_data['user'] = self.context['request'].user
        return super().create(validated_data)

    def get_category(self, obj):
        return CategorySerializer(obj.category, context=self.context).data
    
    def get_user(self, obj):
        return UserSerializer(obj.user, context=self.context).data


class CarCreateSerializer(serializers.ModelSerializer):
    """Сериализатор для создания машины"""
    
    class Meta:
        model = Car
        fields = ['category', 'brand', 'model', 'year']
    
    def create(self, validated_data):
        """Создание машины с автоматическим назначением пользователя"""
        validated_data['user'] = self.context['request'].user
        return super().create(validated_data)
