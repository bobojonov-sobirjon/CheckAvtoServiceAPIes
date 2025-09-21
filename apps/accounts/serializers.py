from rest_framework import serializers
from django.core.exceptions import ValidationError
import re
from .models import CustomUser


def validate_phone_number_format(value):
    """Проверка и форматирование номера телефона - Узбекистан и Россия"""
    if not value:
        raise ValidationError("Номер телефона не введен")
    
    # Удаление всех нецифровых символов
    cleaned = re.sub(r'\D', '', value)
    
    # Узбекистан номер (+998)
    if cleaned.startswith('998'):
        if len(cleaned) == 12:  # 998XXXXXXXXX
            return cleaned
        else:
            raise ValidationError("Узбекский номер должен быть 12 цифр (998XXXXXXXXX)")
    
    # Российский номер (+7)
    elif cleaned.startswith('8'):
        if len(cleaned) == 11:  # 8XXXXXXXXXX
            cleaned = '7' + cleaned[1:]
            return cleaned
        else:
            raise ValidationError("Российский номер должен быть 11 цифр (8XXXXXXXXXX)")
    elif cleaned.startswith('7'):
        if len(cleaned) == 11:  # 7XXXXXXXXXX
            return cleaned
        else:
            raise ValidationError("Российский номер должен быть 11 цифр (7XXXXXXXXXX)")
    
    # Начинается с +998
    elif value.startswith('+998'):
        if len(cleaned) == 12:
            return cleaned
        else:
            raise ValidationError("Узбекский номер должен быть 12 цифр (+998XXXXXXXXX)")
    
    # Начинается с +7
    elif value.startswith('+7'):
        if len(cleaned) == 11:
            return cleaned
        else:
            raise ValidationError("Российский номер должен быть 11 цифр (+7XXXXXXXXXX)")
    
    else:
        raise ValidationError("Неверный формат номера телефона. Поддерживаемые форматы:\n- Узбекистан: 998XXXXXXXXX, +998XXXXXXXXX\n- Россия: 8XXXXXXXXXX, 7XXXXXXXXXX, +7XXXXXXXXXX")


class PhoneNumberSerializer(serializers.Serializer):
    """Сериализатор для номера телефона"""
    phone_number = serializers.CharField(max_length=15, required=True)
    
    def validate_phone_number(self, value):
        """Проверка и форматирование номера телефона"""
        return validate_phone_number_format(value)


class SMSVerificationSerializer(serializers.Serializer):
    """Сериализатор для проверки SMS кода"""
    phone_number = serializers.CharField(max_length=15, required=True)
    sms_code = serializers.CharField(max_length=4, min_length=4, required=True)
    
    def validate_phone_number(self, value):
        """Проверка и форматирование номера телефона"""
        return validate_phone_number_format(value)
    
    def validate_sms_code(self, value):
        """Проверка SMS кода"""
        if not value:
            raise ValidationError("SMS код не введен")
        
        # Должен содержать только цифры
        if not value.isdigit():
            raise ValidationError("SMS код должен содержать только цифры")
        
        # Должен быть 4-значным
        if len(value) != 4:
            raise ValidationError("SMS код должен быть 4-значным")
        
        return value


class UserSerializer(serializers.ModelSerializer):
    """Сериализатор для данных пользователя"""
    
    class Meta:
        model = CustomUser
        fields = ['id', 'phone_number', 'first_name', 'last_name', 'email', 'is_verified', 'created_at']
        read_only_fields = ['id', 'created_at']


class TokenResponseSerializer(serializers.Serializer):
    """Сериализатор для ответа с токеном"""
    success = serializers.BooleanField()
    message = serializers.CharField()
    user = UserSerializer()
    tokens = serializers.DictField()
    
    class Meta:
        fields = ['success', 'message', 'user', 'tokens']


class SMSResponseSerializer(serializers.Serializer):
    """Сериализатор для ответа отправки SMS"""
    success = serializers.BooleanField()
    message = serializers.CharField()
    phone = serializers.CharField()
    
    class Meta:
        fields = ['success', 'message', 'phone']
