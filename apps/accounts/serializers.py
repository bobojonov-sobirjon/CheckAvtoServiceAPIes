from rest_framework import serializers
from django.core.exceptions import ValidationError
import re
from .models import CustomUser, FAQ


def validate_email_format(value):
    """Проверка формата email"""
    if not value:
        raise ValidationError("Email не введен")
    
    # Простая проверка формата email
    email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    if not re.match(email_pattern, value):
        raise ValidationError("Неверный формат email адреса")
    
    return value.lower().strip()


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


class IdentifierSerializer(serializers.Serializer):
    """Сериализатор для идентификатора (email или номер телефона)"""
    identifier = serializers.CharField(max_length=255, required=True)
    role = serializers.ChoiceField(
        choices=['Driver', 'Master'],
        required=True,
        help_text="Роль пользователя: Driver или Master (обязательно)."
    )
    
    def validate_identifier(self, value):
        """Проверка и определение типа идентификатора"""
        if not value:
            raise ValidationError("Идентификатор не введен")
        
        value = value.strip()
        
        # Проверяем, является ли это email
        if '@' in value and '.' in value:
            return {
                'type': 'email',
                'value': validate_email_format(value)
            }
        # Проверяем, является ли это номер телефона
        elif any(char.isdigit() for char in value):
            return {
                'type': 'phone',
                'value': validate_phone_number_format(value)
            }
        else:
            raise ValidationError("Неверный формат. Введите email или номер телефона")
    
    def validate_role(self, value):
        """Проверка роли пользователя"""
        if value and value not in ['Driver', 'Master']:
            raise ValidationError("Роль должна быть 'Driver' или 'Master'")
        return value


class PhoneNumberSerializer(serializers.Serializer):
    """Сериализатор для номера телефона"""
    phone_number = serializers.CharField(max_length=15, required=True)
    
    def validate_phone_number(self, value):
        """Проверка и форматирование номера телефона"""
        return validate_phone_number_format(value)


class SMSVerificationSerializer(serializers.Serializer):
    """Сериализатор для проверки SMS кода"""
    identifier = serializers.CharField(max_length=255, required=True)
    sms_code = serializers.CharField(max_length=4, min_length=4, required=True)
    role = serializers.ChoiceField(
        choices=['Driver', 'Master'],
        required=True,
        help_text="Роль пользователя: Driver или Master (обязательно)."
    )
    
    def validate_identifier(self, value):
        """Проверка и определение типа идентификатора"""
        if not value:
            raise ValidationError("Идентификатор не введен")
        
        value = value.strip()
        
        # Проверяем, является ли это email
        if '@' in value and '.' in value:
            return {
                'type': 'email',
                'value': validate_email_format(value)
            }
        # Проверяем, является ли это номер телефона
        elif any(char.isdigit() for char in value):
            return {
                'type': 'phone',
                'value': validate_phone_number_format(value)
            }
        else:
            raise ValidationError("Неверный формат. Введите email или номер телефона")
    
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
    
    def validate_role(self, value):
        """Проверка роли пользователя"""
        if value and value not in ['Driver', 'Master']:
            raise ValidationError("Роль должна быть 'Driver' или 'Master'")
        return value


class UserSerializer(serializers.ModelSerializer):
    """Сериализатор для данных пользователя"""
    roles = serializers.SerializerMethodField()
    
    class Meta:
        model = CustomUser
        fields = ['id', 'phone_number', 'first_name', 'last_name', 'email', 'description', 'is_verified', 'created_at', 'roles']
        read_only_fields = ['id', 'created_at', 'roles']
    
    def get_roles(self, obj):
        """Получение всех ролей пользователя"""
        # Check if obj is a model instance (not a dictionary)
        if hasattr(obj, 'groups'):
            try:
                groups = obj.groups.all()
                if groups.exists():
                    return [group.name for group in groups]
            except Exception as e:
                # Log the error for debugging
                import logging
                logger = logging.getLogger(__name__)
                logger.error(f"Error getting roles for user {obj.id}: {str(e)}")
        return []


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


class UserDetailsSerializer(serializers.ModelSerializer):
    """Сериализатор для детальной информации о пользователе (только чтение)"""
    roles = serializers.SerializerMethodField()
    avatar = serializers.ImageField(use_url=True, read_only=True)
    
    class Meta:
        model = CustomUser
        fields = [
            'id', 'username', 'email', 'phone_number', 'first_name', 
            'last_name', 'date_of_birth', 'avatar', 'address', 
            'longitude', 'latitude', 'is_verified', 'roles',
            'created_at', 'updated_at', 'description'
        ]
        read_only_fields = [
            'id', 'email', 'phone_number', 'is_verified', 'roles',
            'created_at', 'updated_at'
        ]
    
    def get_roles(self, obj):
        """Получение всех ролей пользователя"""
        # Check if obj is a model instance (not a dictionary)
        if hasattr(obj, 'groups'):
            try:
                groups = obj.groups.all()
                if groups.exists():
                    return [group.name for group in groups]
            except Exception as e:
                # Log the error for debugging
                import logging
                logger = logging.getLogger(__name__)
                logger.error(f"Error getting roles for user {obj.id}: {str(e)}")
        return []


class UserUpdateSerializer(serializers.ModelSerializer):
    """Сериализатор для обновления информации о пользователе"""
    avatar = serializers.ImageField(
        use_url=True, 
        required=False, 
        allow_null=True,
        help_text="Загрузите файл изображения для аватара"
    )
    roles = serializers.ListField(
        child=serializers.ChoiceField(choices=['Driver', 'Master']),
        required=False,
        allow_empty=True,
        write_only=True,
        help_text="Список ролей пользователя (можно выбрать несколько): Driver, Master. Пример: ['Driver', 'Master']"
    )
    
    class Meta:
        model = CustomUser
        fields = [
            'username', 'first_name', 'last_name', 'date_of_birth', 
            'avatar', 'address', 'longitude', 'latitude', 'roles', 'description'
        ]
        extra_kwargs = {
            'username': {'required': False},
            'first_name': {'required': False},
            'last_name': {'required': False},
            'date_of_birth': {'required': False},
            'address': {'required': False},
            'longitude': {'required': False},
            'latitude': {'required': False},
            'description': {'required': False},
        }
    
    def update(self, instance, validated_data):
        """Обновление пользователя с поддержкой изменения нескольких ролей (групп)"""
        from django.contrib.auth.models import Group
        
        # Обработка ролей (групп)
        roles = validated_data.pop('roles', None)
        
        # Обновление остальных полей
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        
        instance.save()
        
        # Обновление групп пользователя
        if roles is not None:  # Проверяем, что roles передан (даже если пустой список)
            # Удаление из всех текущих групп
            instance.groups.clear()
            # Добавление в новые группы
            for role_name in roles:
                group, created = Group.objects.get_or_create(name=role_name)
                instance.groups.add(group)
        
        return instance


class FAQSerializer(serializers.ModelSerializer):
    """Сериализатор для FAQ"""
    
    class Meta:
        model = FAQ
        fields = ['id', 'question', 'answer', 'order', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']

