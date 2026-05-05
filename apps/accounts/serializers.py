from rest_framework import serializers
from django.core.exceptions import ValidationError
from decimal import Decimal, ROUND_HALF_UP
import re
from .models import CustomUser, FAQ, UserDevice

MIN_SBP_TOPUP_RUB = Decimal('5')


class TelegramChatIdSerializer(serializers.Serializer):
    """Сериализатор для обновления Telegram Chat ID"""
    chat_id = serializers.CharField(
        max_length=50,
        required=True,
        help_text="Ваш Telegram Chat ID"
    )
    
    def validate_chat_id(self, value):
        """Валидация Chat ID"""
        if not value:
            raise ValidationError("Chat ID обязателен")
        
        # Простая валидация - Chat ID должен быть числом или начинаться с @
        if not (value.isdigit() or value.startswith('@')):
            raise ValidationError("Неверный формат Chat ID. Используйте числовой ID или @username")
        
        return value


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
        choices=['Driver', 'Master', 'Owner'],
        required=True,
        help_text="Роль пользователя: Driver, Master или Owner (обязательно)."
    )
    
    def validate_identifier(self, value):
        """Проверка и определение типа идентификатора"""
        if not value:
            raise ValidationError("Идентификатор не введен")
        
        value = value.strip()
        
        # Проверяем, является ли это email
        if '@' in value:
            return {
                'type': 'email',
                'value': validate_email_format(value)
            }
        # Проверяем, является ли это номер телефона (начинается с +, 7, 8, 9 или содержит только цифры)
        elif value.startswith(('+', '7', '8', '9')) or (value.replace('+', '').replace(' ', '').replace('-', '').isdigit()):
            return {
                'type': 'phone',
                'value': validate_phone_number_format(value)
            }
        else:
            raise ValidationError("Неверный формат. Введите email или номер телефона")
    
    def validate_role(self, value):
        """Проверка роли пользователя"""
        if value and value not in ['Driver', 'Master', 'Owner']:
            raise ValidationError("Неверная роль")
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
        choices=['Driver', 'Master', 'Owner'],
        required=True,
        help_text="Роль пользователя: Driver, Master или Owner (обязательно)."
    )
    
    def validate_identifier(self, value):
        """Проверка и определение типа идентификатора"""
        if not value:
            raise ValidationError("Идентификатор не введен")
        
        value = value.strip()
        
        # Проверяем, является ли это email
        if '@' in value:
            return {
                'type': 'email',
                'value': validate_email_format(value)
            }
        # Проверяем, является ли это номер телефона (начинается с +, 7, 8, 9 или содержит только цифры)
        elif value.startswith(('+', '7', '8', '9')) or (value.replace('+', '').replace(' ', '').replace('-', '').isdigit()):
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
        if value and value not in ['Driver', 'Master', 'Owner']:
            raise ValidationError("Неверная роль")
        return value


class UserSerializer(serializers.ModelSerializer):
    """Сериализатор для данных пользователя"""
    roles = serializers.SerializerMethodField()
    balance = serializers.SerializerMethodField()
    
    class Meta:
        model = CustomUser
        fields = ['id', 'private_id', 'phone_number', 'first_name', 'last_name', 'email', 'description', 'is_verified', 'created_at', 'roles', 'balance']
        read_only_fields = ['id', 'private_id', 'created_at', 'roles', 'balance']
    
    def get_roles(self, obj):
        """Получение всех ролей пользователя с полной информацией"""
        # Check if obj is a model instance (not a dictionary)
        if hasattr(obj, 'groups'):
            try:
                groups = obj.groups.all()
                if groups.exists():
                    return [
                        {
                            'id': group.id,
                            'name': group.name
                        }
                        for group in groups
                    ]
            except Exception as e:
                # Log the error for debugging
                import logging
                logger = logging.getLogger(__name__)
                logger.error(f"Error getting roles for user {obj.id}: {str(e)}")
        return []
    
    def get_balance(self, obj):
        """Получение баланса пользователя"""
        try:
            from .models import UserBalance
            balance = UserBalance.get_or_create_balance(obj)
            return {
                'amount': str(balance.amount),
                'updated_at': balance.updated_at
            }
        except Exception as e:
            # Log the error for debugging
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Error getting balance for user {obj.id}: {str(e)}")
            return {
                'amount': '0.00',
                'updated_at': None
            }


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


class UserDeviceSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserDevice
        fields = ['id', 'user', 'device_token', 'device_type', 'is_active', 'created_at', 'updated_at']
        read_only_fields = ['id', 'user', 'created_at', 'updated_at']


class UserDetailsSerializer(serializers.ModelSerializer):
    """Сериализатор для детальной информации о пользователе (только чтение)"""
    roles = serializers.SerializerMethodField()
    balance = serializers.SerializerMethodField()
    avatar = serializers.ImageField(use_url=True, read_only=True)
    reviews = serializers.SerializerMethodField()
    rating = serializers.SerializerMethodField()
    reviews_count = serializers.SerializerMethodField()
    completed_orders = serializers.SerializerMethodField()
    recommendation_percentage = serializers.SerializerMethodField()
    
    class Meta:
        model = CustomUser
        fields = [
            'id', 'private_id', 'username', 'email', 'phone_number', 'first_name', 
            'last_name', 'date_of_birth', 'avatar', 'address', 
            'longitude', 'latitude', 'is_verified', 'roles', 'balance',
            'reviews', 'rating', 'reviews_count', 'completed_orders', 'recommendation_percentage',
            'created_at', 'updated_at', 'description'
        ]
        read_only_fields = [
            'id', 'private_id', 'email', 'phone_number', 'is_verified', 'roles', 'balance',
            'reviews', 'rating', 'reviews_count', 'completed_orders', 'recommendation_percentage',
            'created_at', 'updated_at'
        ]
    
    def get_roles(self, obj):
        """Получение всех ролей пользователя с полной информацией"""
        # Check if obj is a model instance (not a dictionary)
        if hasattr(obj, 'groups'):
            try:
                groups = obj.groups.all()
                if groups.exists():
                    return [
                        {
                            'id': group.id,
                            'name': group.name
                        }
                        for group in groups
                    ]
            except Exception as e:
                # Log the error for debugging
                import logging
                logger = logging.getLogger(__name__)
                logger.error(f"Error getting roles for user {obj.id}: {str(e)}")
        return []
    
    def get_balance(self, obj):
        """Получение баланса пользователя"""
        try:
            from .models import UserBalance
            balance = UserBalance.get_or_create_balance(obj)
            return {
                'amount': str(balance.amount),
                'updated_at': balance.updated_at
            }
        except Exception as e:
            # Log the error for debugging
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Error getting balance for user {obj.id}: {str(e)}")
            return {
                'amount': '0.00',
                'updated_at': None
            }
        return []
    
    def get_reviews(self, obj):
        """Получение всех отзывов о пользователе (как мастере)"""
        try:
            from apps.order.models import Review, Order
            
            # Находим все заказы, где user был мастером
            orders_as_main_master = Order.objects.filter(master__user=obj)
            orders_as_assigned_master = Order.objects.filter(masters=obj)
            
            # Объединяем ID
            all_order_ids = set(orders_as_main_master.values_list('id', flat=True)) | \
                           set(orders_as_assigned_master.values_list('id', flat=True))
            
            # Получаем отзывы для этих заказов
            reviews = Review.objects.filter(order_id__in=all_order_ids).order_by('-created_at')
            
            return [
                {
                    'id': review.id,
                    'rating': review.rating,
                    'comment': review.comment,
                    'tag': review.tag,
                    'tag_display': review.get_tag_display(),
                    'reviewer': {
                        'id': review.reviewer.id,
                        'full_name': review.reviewer.get_full_name(),
                        'avatar': review.reviewer.avatar.url if review.reviewer.avatar else None
                    },
                    'order_id': review.order.id,
                    'created_at': review.created_at
                }
                for review in reviews
            ]
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Error getting reviews for user {obj.id}: {str(e)}")
            return []
    
    def get_rating(self, obj):
        """Получение среднего рейтинга пользователя"""
        try:
            from apps.order.models import UserRating
            
            user_rating = UserRating.objects.filter(user=obj).first()
            if user_rating:
                return float(user_rating.average_rating)
            return 0.0
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Error getting rating for user {obj.id}: {str(e)}")
            return 0.0
    
    def get_reviews_count(self, obj):
        """Получение количества отзывов о пользователе (как мастере)"""
        try:
            from apps.order.models import Review, Order
            
            # Находим все заказы, где user был мастером
            orders_as_main_master = Order.objects.filter(master__user=obj)
            orders_as_assigned_master = Order.objects.filter(masters=obj)
            
            # Объединяем ID
            all_order_ids = set(orders_as_main_master.values_list('id', flat=True)) | \
                           set(orders_as_assigned_master.values_list('id', flat=True))
            
            # Считаем отзывы для этих заказов
            reviews_count = Review.objects.filter(order_id__in=all_order_ids).count()
            return reviews_count
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Error getting reviews count for user {obj.id}: {str(e)}")
            return 0
    
    def get_completed_orders(self, obj):
        """Получение количества выполненных заказов"""
        try:
            from apps.order.models import Order, OrderStatus
            
            # Заказы где user - главный мастер
            orders_as_main_master = Order.objects.filter(
                master__user=obj,
                status=OrderStatus.COMPLETED
            ).count()
            
            # Заказы где user в списке masters
            orders_as_assigned_master = Order.objects.filter(
                masters=obj,
                status=OrderStatus.COMPLETED
            ).count()
            
            # Получаем уникальные заказы
            from django.db.models import Q
            total_orders = Order.objects.filter(
                Q(master__user=obj) | Q(masters=obj),
                status=OrderStatus.COMPLETED
            ).distinct().count()
            
            return total_orders
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Error getting completed orders for user {obj.id}: {str(e)}")
            return 0
    
    def get_recommendation_percentage(self, obj):
        """Получение процента рекомендаций (отзывы с рейтингом 4-5)"""
        try:
            from apps.order.models import Review, Order
            
            # Находим все заказы, где user был мастером
            orders_as_main_master = Order.objects.filter(master__user=obj)
            orders_as_assigned_master = Order.objects.filter(masters=obj)
            
            # Объединяем ID
            all_order_ids = set(orders_as_main_master.values_list('id', flat=True)) | \
                           set(orders_as_assigned_master.values_list('id', flat=True))
            
            # Получаем все отзывы
            all_reviews = Review.objects.filter(order_id__in=all_order_ids)
            total_reviews = all_reviews.count()
            
            if total_reviews == 0:
                return 0
            
            # Считаем отзывы с рейтингом 4 и 5
            positive_reviews = all_reviews.filter(rating__gte=4).count()
            
            # Вычисляем процент
            percentage = round((positive_reviews / total_reviews) * 100)
            return percentage
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Error getting recommendation percentage for user {obj.id}: {str(e)}")
            return 0


class UserUpdateSerializer(serializers.ModelSerializer):
    """Сериализатор для обновления информации о пользователе"""
    avatar = serializers.ImageField(
        use_url=True, 
        required=False, 
        allow_null=True,
        help_text="Загрузите файл изображения для аватара"
    )
    roles = serializers.CharField(
        required=False,
        allow_blank=True,
        write_only=True,
        help_text="Роли пользователя. Можно указать одну роль или несколько через запятую. Примеры: 'Driver', 'Driver,Owner', 'Driver,Master,Owner'"
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
    
    def validate_roles(self, value):
        """Валидация и преобразование ролей из строки в список"""
        if not value:
            return []
        
        # Если это строка, разбиваем по запятой
        if isinstance(value, str):
            roles_list = [role.strip() for role in value.split(',') if role.strip()]
        elif isinstance(value, list):
            roles_list = value
        else:
            raise serializers.ValidationError("Роли должны быть строкой или списком")
        
        # Валидация каждой роли
        valid_roles = ['Driver', 'Master', 'Owner']
        for role in roles_list:
            if role not in valid_roles:
                raise serializers.ValidationError(f"Неверная роль: {role}. Допустимые роли: {', '.join(valid_roles)}")
        
        return roles_list
    
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
            # Если roles пустой список, просто очищаем группы
            if not roles:
                instance.groups.clear()
            else:
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


class SbpBalanceQrSerializer(serializers.Serializer):
    """Сумма пополнения (₽) для отображения пользователю; QR ведёт на статический СБП."""

    price = serializers.DecimalField(
        max_digits=12, decimal_places=2, required=True, min_value=MIN_SBP_TOPUP_RUB,
    )


class SbpWebhookSerializer(serializers.Serializer):
    """Подтверждение оплаты (сервер-сервер). intent_id — из ответа POST .../sbp-qr/."""

    intent_id = serializers.UUIDField()
    amount = serializers.DecimalField(
        max_digits=12, decimal_places=2, required=False,
        help_text='Если передано, должно совпадать с суммой намерения.',
    )
    bank_reference = serializers.CharField(max_length=256, required=False, allow_blank=True, default='')


class SbpConfirmByTrxSerializer(serializers.Serializer):
    """
    Резервный вариант для ручного подтверждения через API,
    когда банк не отправляет наш intent_id в callback.

    trx_id берётся из админки/кабинета банка (например, ALFA TRX_ID).
    """

    trx_id = serializers.CharField(max_length=256)
    amount = serializers.DecimalField(max_digits=12, decimal_places=2, required=False)


class AlfaOrderStatusExtendedSerializer(serializers.Serializer):
    """
    Проверить статус заказа в Альфа-шлюзе (getOrderStatusExtended).

    Для привязки к нашему intent: передайте intent_id.
    """

    alfa_order_id = serializers.CharField(max_length=64, required=False, allow_blank=True)
    alfa_order_number = serializers.CharField(max_length=64, required=False, allow_blank=True)
    intent_id = serializers.UUIDField(required=False)
    amount = serializers.DecimalField(max_digits=12, decimal_places=2, required=False)

    def validate(self, attrs):
        oid = (attrs.get("alfa_order_id") or "").strip()
        onum = (attrs.get("alfa_order_number") or "").strip()
        if not oid and not onum:
            raise serializers.ValidationError("Передайте alfa_order_id или alfa_order_number.")
        attrs["alfa_order_id"] = oid
        attrs["alfa_order_number"] = onum
        return attrs


class OwnerTopUpMasterBalanceSerializer(serializers.Serializer):
    """Owner: пополнить баланс мастера через Alfa dynamic order."""

    master_id = serializers.IntegerField()
    price = serializers.DecimalField(max_digits=12, decimal_places=2, min_value=Decimal('1000'))


class MasterWithdrawSerializer(serializers.Serializer):
    """Мастер: заявка на вывод с доступного баланса (сумма резервируется сразу)."""

    price = serializers.DecimalField(max_digits=12, decimal_places=2, min_value=Decimal('0.01'))

