from rest_framework import serializers
from django.core.exceptions import ValidationError
import re
from .models import CustomUser


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
        required=False,
        allow_blank=True,
        help_text="Роль пользователя: Driver или Master. Обязательно только при создании нового пользователя."
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
        required=False,
        allow_blank=True,
        help_text="Роль пользователя: Driver или Master. Обязательно только при создании нового пользователя."
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
    role = serializers.SerializerMethodField()
    
    class Meta:
        model = CustomUser
        fields = ['id', 'phone_number', 'first_name', 'last_name', 'email', 'is_verified', 'created_at', 'role']
        read_only_fields = ['id', 'created_at', 'role']
    
    def get_role(self, obj):
        """Получение роли пользователя"""
        # Check if obj is a model instance (not a dictionary)
        if hasattr(obj, 'groups'):
            try:
                groups = obj.groups.all()
                if groups.exists():
                    return groups.first().name
            except Exception as e:
                # Log the error for debugging
                import logging
                logger = logging.getLogger(__name__)
                logger.error(f"Error getting role for user {obj.id}: {str(e)}")
        return None


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
    role = serializers.SerializerMethodField()
    
    class Meta:
        model = CustomUser
        fields = [
            'id', 'username', 'email', 'phone_number', 'first_name', 
            'last_name', 'date_of_birth', 'avatar', 'address', 
            'longitude', 'latitude', 'is_verified', 'role',
            'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'email', 'phone_number', 'is_verified', 'role',
            'created_at', 'updated_at'
        ]
    
    def get_role(self, obj):
        """Получение роли пользователя"""
        # Check if obj is a model instance (not a dictionary)
        if hasattr(obj, 'groups'):
            try:
                groups = obj.groups.all()
                if groups.exists():
                    return groups.first().name
            except Exception as e:
                # Log the error for debugging
                import logging
                logger = logging.getLogger(__name__)
                logger.error(f"Error getting role for user {obj.id}: {str(e)}")
        return None


class UserUpdateSerializer(serializers.ModelSerializer):
    """Сериализатор для обновления информации о пользователе с условным обновлением email и phone_number"""
    
    class Meta:
        model = CustomUser
        fields = [
            'username', 'first_name', 'last_name', 'date_of_birth', 'avatar',
            'address', 'longitude', 'latitude', 'email', 'phone_number'
        ]
        extra_kwargs = {
            'email': {'required': False, 'allow_blank': True},
            'phone_number': {'required': False, 'allow_blank': True},
            'longitude': {'required': False, 'allow_null': True},
            'latitude': {'required': False, 'allow_null': True}
        }
    
    def validate_username(self, value):
        """Проверка уникальности username"""
        if self.instance and self.instance.username == value:
            return value
        
        if CustomUser.objects.filter(username=value).exists():
            raise serializers.ValidationError("Пользователь с таким именем пользователя уже существует.")
        return value
    
    def validate_email(self, value):
        """Проверка email - можно добавить только если у пользователя нет email"""
        if not value or value.strip() == '':
            return value
            
        # Если у пользователя уже есть email, не позволяем его изменить
        if self.instance and self.instance.email and self.instance.email != value:
            raise serializers.ValidationError("Email нельзя изменить. Можно только добавить email, если его нет.")
        
        # Проверяем уникальность email
        if CustomUser.objects.filter(email=value).exclude(pk=self.instance.pk if self.instance else None).exists():
            raise serializers.ValidationError("Пользователь с таким email уже существует.")
        
        return value
    
    def validate_phone_number(self, value):
        """Проверка phone_number - можно добавить только если у пользователя нет phone_number"""
        if not value or value.strip() == '':
            return value
            
        # Если у пользователя уже есть phone_number, не позволяем его изменить
        if self.instance and self.instance.phone_number and self.instance.phone_number != value:
            raise serializers.ValidationError("Номер телефона нельзя изменить. Можно только добавить номер, если его нет.")
        
        # Проверяем уникальность phone_number
        if CustomUser.objects.filter(phone_number=value).exclude(pk=self.instance.pk if self.instance else None).exists():
            raise serializers.ValidationError("Пользователь с таким номером телефона уже существует.")
        
        return value
    
    def validate_longitude(self, value):
        """Проверка долготы"""
        if value is not None:
            if value < -180 or value > 180:
                raise serializers.ValidationError("Долгота должна быть между -180 и 180 градусами.")
        return value
    
    def validate_latitude(self, value):
        """Проверка широты"""
        if value is not None:
            if value < -90 or value > 90:
                raise serializers.ValidationError("Широта должна быть между -90 и 90 градусами.")
        return value
    
    def validate(self, attrs):
        """Дополнительная валидация"""
        # Проверяем, что пользователь пытается добавить хотя бы один идентификатор
        email = attrs.get('email')
        phone_number = attrs.get('phone_number')
        
        # Очищаем пустые строки
        if email and email.strip() == '':
            email = None
        if phone_number and phone_number.strip() == '':
            phone_number = None
        
        if self.instance:
            # Если у пользователя уже есть и email и phone_number, не позволяем их изменять
            if self.instance.email and self.instance.phone_number:
                if email or phone_number:
                    raise serializers.ValidationError("У вас уже есть и email и номер телефона. Их нельзя изменить.")
            
            # Если у пользователя есть только email, можно добавить phone_number
            elif self.instance.email and not self.instance.phone_number:
                if email:
                    raise serializers.ValidationError("У вас уже есть email. Можно только добавить номер телефона.")
                # Не требуем обязательного добавления phone_number при обновлении других полей
                # if not phone_number:
                #     raise serializers.ValidationError("У вас есть только email. Пожалуйста, добавьте номер телефона.")
            
            # Если у пользователя есть только phone_number, можно добавить email
            elif self.instance.phone_number and not self.instance.email:
                if phone_number:
                    raise serializers.ValidationError("У вас уже есть номер телефона. Можно только добавить email.")
                # Не требуем обязательного добавления email при обновлении других полей
                # if not email:
                #     raise serializers.ValidationError("У вас есть только номер телефона. Пожалуйста, добавьте email.")
        
        return attrs