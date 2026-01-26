from rest_framework import serializers
from .models import Master, MasterService, MasterImage, MasterServiceItems, MasterEmployee
from apps.categories.models import Category
from apps.order.models import Rating
from django.contrib.auth import get_user_model

User = get_user_model()

# Import UserDetailsSerializer for master employees
from apps.accounts.serializers import UserDetailsSerializer


class MasterImageSerializer(serializers.ModelSerializer):
    """Сериализатор для изображений мастера"""
    
    class Meta:
        model = MasterImage
        fields = ['id', 'image', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']


class MasterSerializer(serializers.ModelSerializer):
    """Сериализатор для мастера"""
    user_info = serializers.SerializerMethodField()
    services = serializers.SerializerMethodField()
    images = serializers.SerializerMethodField()
    category_data = serializers.SerializerMethodField()
    rating_data = serializers.SerializerMethodField()
    masters = serializers.SerializerMethodField()
    distance = serializers.SerializerMethodField()
    
    class Meta:
        model = Master
        fields = [
            'id', 'user_info', 'name', 'city', 'address', 
            'latitude', 'longitude', 'phone', 'working_time', 'services',
            'card_number', 'card_expiry_month', 'card_expiry_year', 
            'card_cvv', 'balance', 'reserved_amount', 'description', 'images', 
            'category_data', 'rating_data', 'masters', 'distance', 'created_at', 'updated_at', 
            'last_activity'
        ]
        read_only_fields = ['id', 'user', 'created_at', 'updated_at', 'last_activity', 'distance']
    
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
    
    def get_images(self, obj):
        """Получить изображения мастера"""
        master_images = MasterImage.objects.filter(master=obj)
        return MasterImageSerializer(master_images, many=True, context=self.context).data
    
    def get_category_data(self, obj):
        """Получить данные категорий (id, name, icon, type_category)"""
        categories = obj.category.all()
        request = self.context.get('request')
        return [
            {
                'id': category.id,
                'name': category.name,
                'type_category': category.type_category,
                'type_category_display': category.get_type_category_display(),
                'icon': request.build_absolute_uri(category.icon.url) if category.icon and request else None
            }
            for category in categories
        ]
    
    def get_rating_data(self, obj):
        """Получить данные рейтинга для мастера"""
        return self._get_rating_data_for_master(obj)
    
    def _get_rating_data_for_master(self, master):
        """Получить данные рейтинга для мастера"""
        ratings = Rating.objects.filter(master=master)
        if not ratings.exists():
            return {
                'average_rating': 0,
                'total_ratings': 0,
                'ratings': []
            }
        
        total_ratings = ratings.count()
        average_rating = sum(r.rating for r in ratings) / total_ratings
        
        return {
            'average_rating': round(average_rating, 2),
            'total_ratings': total_ratings,
            'ratings': [
                {
                    'id': r.id,
                    'rating': r.rating,
                    'comment': r.comment,
                    'user_name': r.user.get_full_name(),
                    'created_at': r.created_at
                }
                for r in ratings[:10]  # Последние 10 рейтингов
            ]
        }
    
    def get_masters(self, obj):
        """Получить всех сотрудников мастерской (сначала владелец, потом добавленные)"""
        request = self.context.get('request')
        masters_list = []
        
        # Сначала добавляем владельца (который создал мастерскую)
        owner_data = UserDetailsSerializer(obj.user, context={'request': request}).data
        owner_data['is_owner'] = True
        owner_data['added_at'] = obj.created_at
        masters_list.append(owner_data)
        
        # Затем добавляем всех сотрудников
        employees = MasterEmployee.objects.filter(master=obj).select_related('employee')
        for emp in employees:
            employee_data = UserDetailsSerializer(emp.employee, context={'request': request}).data
            employee_data['is_owner'] = False
            employee_data['added_at'] = emp.added_at
            masters_list.append(employee_data)
        
        return masters_list
    
    def get_distance(self, obj):
        """Получить расстояние от пользователя (если было вычислено)"""
        # Если расстояние было добавлено во view, возвращаем его
        return getattr(obj, 'distance', None)
    
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
        write_only=True,
        help_text="Список услуг мастера. Пример: [{'name': 'Замена масла', 'price_from': 1000, 'price_to': 2000, 'category': 1}]"
    )
    category = serializers.ListField(
        child=serializers.IntegerField(),
        required=False,
        allow_empty=True,
        write_only=True,
        help_text="Список ID категорий [1, 2, 3, ...]. Категории должны быть типа 'by_master'"
    )
    images = serializers.ListField(
        child=serializers.ImageField(),
        required=False,
        allow_empty=True,
        write_only=True,
        help_text="Список изображений мастерской (multiple files)"
    )
    
    class Meta:
        model = Master
        fields = [
            'name', 'city', 'address', 'latitude', 'longitude', 'phone', 'working_time',
            'description', 'services', 'category', 'images', 'card_number', 
            'card_expiry_month', 'card_expiry_year', 'card_cvv'
        ]
        extra_kwargs = {
            'name': {'required': False, 'allow_blank': True},
            'city': {'required': False, 'allow_blank': True},
            'address': {'required': False, 'allow_blank': True},
            'latitude': {'required': False},
            'longitude': {'required': False},
            'phone': {'required': False, 'allow_blank': True},
            'working_time': {'required': False, 'allow_blank': True},
            'description': {'required': False, 'allow_blank': True, 'allow_null': True},
            'card_number': {'required': False, 'allow_blank': True},
            'card_expiry_month': {'required': False},
            'card_expiry_year': {'required': False},
            'card_cvv': {'required': False, 'allow_blank': True},
        }
    
    def to_internal_value(self, data):
        """Преобразование данных из multipart/form-data"""
        import json
        from decimal import Decimal, InvalidOperation
        from django.http import QueryDict
        
        # Создаем обычный dict из данных для возможности модификации
        # QueryDict позволяет множественные значения, но для наших полей это не нужно
        if isinstance(data, QueryDict):
            # Конвертируем QueryDict в dict, беря последнее значение для каждого ключа
            # (кроме images, которые уже обработаны в view)
            data_dict = {}
            for key in data.keys():
                if key == 'images':
                    # Для images используем getlist, так как их может быть несколько
                    data_dict[key] = data.getlist(key)
                else:
                    # Для остальных полей берем последнее значение
                    value = data.get(key)
                    if value is not None:
                        data_dict[key] = value
            data = data_dict
        elif hasattr(data, 'copy'):
            data = data.copy()
        else:
            data = dict(data)
        
        # Обрабатываем latitude и longitude (могут быть строкой с запятой или точкой)
        if 'latitude' in data:
            lat_value = data.get('latitude')
            if isinstance(lat_value, str):
                try:
                    # Заменяем запятую на точку для float
                    lat_str = lat_value.replace(',', '.')
                    # Конвертируем в Decimal для точности
                    data['latitude'] = str(Decimal(lat_str))
                except (ValueError, AttributeError, InvalidOperation):
                    # Если конвертация не удалась, оставляем как есть для стандартной валидации
                    pass
        
        if 'longitude' in data:
            lon_value = data.get('longitude')
            if isinstance(lon_value, str):
                try:
                    # Заменяем запятую на точку для float
                    lon_str = lon_value.replace(',', '.')
                    # Конвертируем в Decimal для точности
                    data['longitude'] = str(Decimal(lon_str))
                except (ValueError, AttributeError, InvalidOperation):
                    # Если конвертация не удалась, оставляем как есть для стандартной валидации
                    pass
        
        # Обрабатываем services (может быть JSON строкой или списком)
        if 'services' in data:
            services_value = data.get('services')
            if isinstance(services_value, str):
                # Удаляем пробелы и проверяем, не пустая ли строка
                services_value = services_value.strip()
                if services_value:
                    try:
                        # Пробуем распарсить как JSON
                        parsed = json.loads(services_value)
                        if isinstance(parsed, list):
                            data['services'] = parsed
                        else:
                            # Если не список, делаем пустым списком
                            data['services'] = []
                    except (json.JSONDecodeError, TypeError):
                        # Если не JSON, делаем пустым списком
                        data['services'] = []
                else:
                    data['services'] = []
            elif not isinstance(services_value, list):
                # Если это не список и не строка, делаем пустым списком
                data['services'] = []
        
        # Обрабатываем category (может быть строкой или JSON строкой)
        if 'category' in data:
            category_value = data.get('category')
            if isinstance(category_value, str):
                category_value = category_value.strip()
                if category_value:
                    try:
                        # Пробуем распарсить как JSON массив
                        parsed = json.loads(category_value)
                        if isinstance(parsed, list):
                            data['category'] = parsed
                        else:
                            # Если это просто число, делаем список
                            data['category'] = [int(parsed)]
                    except (json.JSONDecodeError, ValueError, TypeError):
                        # Если не JSON, пробуем как число
                        try:
                            data['category'] = [int(category_value)]
                        except (ValueError, TypeError):
                            data['category'] = []
                else:
                    data['category'] = []
            elif not isinstance(category_value, list):
                # Если это не список и не строка, пробуем преобразовать
                try:
                    data['category'] = [int(category_value)]
                except (ValueError, TypeError):
                    data['category'] = []
        
        return super().to_internal_value(data)
    
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
        
        # Фильтруем пустые словари и None значения
        value = [s for s in value if s and isinstance(s, dict) and s]
        
        # Проверяем, что каждый элемент - это объект с name, price_from, price_to и category
        for idx, service in enumerate(value):
            if not isinstance(service, dict):
                raise serializers.ValidationError({
                    str(idx): "Каждая услуга должна быть объектом"
                })
            
            # Проверяем наличие обязательных полей
            required_fields = ['name', 'price_from', 'price_to', 'category']
            missing_fields = [field for field in required_fields if field not in service or service[field] is None]
            
            if missing_fields:
                raise serializers.ValidationError({
                    str(idx): f"Услуга должна содержать поля: {', '.join(missing_fields)}"
                })
            
            # Проверяем, что категория существует
            try:
                Category.objects.get(id=service['category'])
            except Category.DoesNotExist:
                raise serializers.ValidationError({
                    str(idx): f"Категория с ID {service['category']} не найдена"
                })
            except (ValueError, TypeError):
                raise serializers.ValidationError({
                    str(idx): f"Категория должна быть числом, получено: {type(service['category']).__name__}"
                })
        
        return value
    
    def validate_category(self, value):
        """Валидация категорий"""
        if not isinstance(value, list):
            raise serializers.ValidationError("Категории должны быть списком ID")
        
        # Проверяем, что все категории существуют
        category_ids = set(value)
        existing_categories = Category.objects.filter(id__in=category_ids)
        if existing_categories.count() != len(category_ids):
            raise serializers.ValidationError("Некоторые категории не найдены")
        
        return value
    
    def create(self, validated_data):
        """Создание мастера с автоматическим назначением пользователя"""
        from django.contrib.auth.models import Group
        from .models import MasterImage
        
        services_data = validated_data.pop('services', [])
        category_ids = validated_data.pop('category', [])
        images_data = validated_data.pop('images', [])
        user = self.context['request'].user
        validated_data['user'] = user
        
        master = super().create(validated_data)
        
        # Добавляем пользователя в группу Master (если еще не в ней)
        master_group, created = Group.objects.get_or_create(name='Master')
        if not user.groups.filter(name='Master').exists():
            user.groups.add(master_group)
        
        # Добавляем категории
        if category_ids:
            master.category.set(category_ids)
        
        # Создаем изображения мастера
        if images_data:
            for image in images_data:
                MasterImage.objects.create(master=master, image=image)
        
        # Создаем услуги мастера
        if services_data:
            # Создаем один MasterService для всех items
            master_service = MasterService.objects.create(master=master)
            
            # Создаем MasterServiceItems для каждой услуги
            for service_data in services_data:
                MasterServiceItems.objects.create(
                    master_service=master_service,
                    name=service_data['name'],
                    price_from=service_data['price_from'],
                    price_to=service_data['price_to'],
                    category_id=service_data['category']
                )
        
        return master


class MasterUpdateSerializer(serializers.ModelSerializer):
    """Сериализатор для обновления мастера (частичное обновление)"""
    images = serializers.ListField(
        child=serializers.ImageField(),
        required=False,
        allow_empty=True,
        write_only=True
    )
    category = serializers.ListField(
        child=serializers.IntegerField(),
        required=False,
        allow_empty=True,
        write_only=True,
        help_text="Список ID категорий [1, 2, 3, ...]"
    )
    
    class Meta:
        model = Master
        fields = [
            'city', 'address', 'latitude', 'longitude', 'phone', 'working_time', 
            'card_number', 'card_expiry_month', 'card_expiry_year', 
            'card_cvv', 'description', 'images', 'category'
        ]
        extra_kwargs = {
            'city': {'required': False},
            'address': {'required': False},
            'latitude': {'required': False},
            'longitude': {'required': False},
            'phone': {'required': False},
            'working_time': {'required': False},
            'card_number': {'required': False},
            'card_expiry_month': {'required': False},
            'card_expiry_year': {'required': False},
            'card_cvv': {'required': False},
            'description': {'required': False, 'allow_blank': True, 'allow_null': True},
        }
    
    def to_internal_value(self, data):
        """Преобразование данных из multipart/form-data"""
        import json
        from decimal import Decimal, InvalidOperation
        from django.http import QueryDict
        
        # Создаем обычный dict из данных для возможности модификации
        # QueryDict позволяет множественные значения, но для наших полей это не нужно
        if isinstance(data, QueryDict):
            # Конвертируем QueryDict в dict, беря последнее значение для каждого ключа
            # (кроме images, которые уже обработаны в view)
            data_dict = {}
            for key in data.keys():
                if key == 'images':
                    # Для images используем getlist, так как их может быть несколько
                    data_dict[key] = data.getlist(key)
                else:
                    # Для остальных полей берем последнее значение
                    value = data.get(key)
                    if value is not None:
                        data_dict[key] = value
            data = data_dict
        elif hasattr(data, 'copy'):
            data = data.copy()
        else:
            data = dict(data)
        
        # Обрабатываем latitude и longitude (могут быть строкой с запятой или точкой)
        if 'latitude' in data:
            lat_value = data.get('latitude')
            if isinstance(lat_value, str):
                try:
                    # Заменяем запятую на точку для float
                    lat_str = lat_value.replace(',', '.')
                    # Конвертируем в Decimal для точности
                    data['latitude'] = str(Decimal(lat_str))
                except (ValueError, AttributeError, InvalidOperation):
                    # Если конвертация не удалась, оставляем как есть для стандартной валидации
                    pass
        
        if 'longitude' in data:
            lon_value = data.get('longitude')
            if isinstance(lon_value, str):
                try:
                    # Заменяем запятую на точку для float
                    lon_str = lon_value.replace(',', '.')
                    # Конвертируем в Decimal для точности
                    data['longitude'] = str(Decimal(lon_str))
                except (ValueError, AttributeError, InvalidOperation):
                    # Если конвертация не удалась, оставляем как есть для стандартной валидации
                    pass
        
        # Обрабатываем category (может быть строкой или JSON строкой)
        if 'category' in data:
            category_value = data.get('category')
            if isinstance(category_value, str):
                category_value = category_value.strip()
                if category_value:
                    try:
                        # Пробуем распарсить как JSON массив
                        parsed = json.loads(category_value)
                        if isinstance(parsed, list):
                            data['category'] = parsed
                        else:
                            # Если это просто число, делаем список
                            data['category'] = [int(parsed)]
                    except (json.JSONDecodeError, ValueError, TypeError):
                        # Если не JSON, пробуем как число
                        try:
                            data['category'] = [int(category_value)]
                        except (ValueError, TypeError):
                            data['category'] = []
                else:
                    data['category'] = []
            elif not isinstance(category_value, list):
                # Если это не список и не строка, пробуем преобразовать
                try:
                    data['category'] = [int(category_value)]
                except (ValueError, TypeError):
                    data['category'] = []
        
        # Обрабатываем images - убеждаемся, что это список
        if 'images' in data:
            images_value = data.get('images')
            # Если images уже список файлов, оставляем как есть
            if not isinstance(images_value, list):
                # Если это не список, делаем список
                if images_value is not None:
                    data['images'] = [images_value]
                else:
                    data['images'] = []
        
        return super().to_internal_value(data)
    
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
    
    def validate_category(self, value):
        """Валидация категорий"""
        if not isinstance(value, list):
            raise serializers.ValidationError("Категории должны быть списком ID")
        
        # Проверяем, что все категории существуют
        category_ids = set(value)
        existing_categories = Category.objects.filter(id__in=category_ids)
        if existing_categories.count() != len(category_ids):
            raise serializers.ValidationError("Некоторые категории не найдены")
        
        return value
    
    def update(self, instance, validated_data):
        """Обновление мастера с обработкой изображений и категорий"""
        images_data = validated_data.pop('images', None)
        category_ids = validated_data.pop('category', None)
        
        # Обновляем основные поля
        instance = super().update(instance, validated_data)
        
        # Если переданы категории, обновляем их
        if category_ids is not None:
            instance.category.set(category_ids)
        
        # Если переданы изображения, удаляем старые и создаем новые
        if images_data is not None:
            # Удаляем старые изображения
            MasterImage.objects.filter(master=instance).delete()
            
            # Создаем новые изображения
            for image in images_data:
                MasterImage.objects.create(master=instance, image=image)
        
        return instance


class MasterNearbySerializer(serializers.ModelSerializer):
    """Сериализатор для мастеров поблизости"""
    user_name = serializers.ReadOnlyField(source='user.get_full_name')
    user_phone = serializers.ReadOnlyField(source='user.phone_number')
    services_display = serializers.SerializerMethodField()
    distance = serializers.SerializerMethodField()
    images = serializers.SerializerMethodField()
    
    class Meta:
        model = Master
        fields = [
            'id', 'user_name', 'user_phone', 'city', 'address', 
            'latitude', 'longitude', 'services', 'services_display', 
            'distance', 'description', 'images'
        ]
    
    def get_services_display(self, obj):
        """Получить отображаемые названия услуг"""
        master_services = MasterService.objects.filter(master=obj)
        return [service.name for service in master_services]
    
    def get_distance(self, obj):
        """Получить расстояние (будет установлено в view)"""
        return getattr(obj, 'calculated_distance', None)
    
    def get_images(self, obj):
        """Получить изображения мастера"""
        master_images = MasterImage.objects.filter(master=obj)
        return MasterImageSerializer(master_images, many=True, context=self.context).data


class MasterServiceItemsSerializer(serializers.ModelSerializer):
    """Сериализатор для элементов услуги мастера"""
    category_name = serializers.CharField(source='category.name', read_only=True)
    
    class Meta:
        model = MasterServiceItems
        fields = [
            'id', 'name', 'price_from', 'price_to', 'category', 'category_name',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class MasterServiceSerializer(serializers.ModelSerializer):
    """Сериализатор для услуг мастера"""
    master_service_items = serializers.SerializerMethodField()
    master_items = serializers.ListField(
        child=serializers.DictField(),
        required=False,
        allow_empty=True,
        write_only=True,
        help_text="Список элементов услуги [{'name': '...', 'price_from': ..., 'price_to': ..., 'category': category_id}, ...]"
    )
    master_id = serializers.IntegerField(write_only=True, required=False)
    
    class Meta:
        model = MasterService
        fields = [
            'id', 'master_service_items', 'master_items', 'master_id', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']
    
    def get_master_service_items(self, obj):
        """Получить элементы услуги мастера, сгруппированные по категориям"""
        items = MasterServiceItems.objects.filter(master_service=obj).select_related('category').order_by('category__name', 'name')
        
        # Группируем по категориям
        grouped_items = {}
        for item in items:
            category_id = item.category.id
            category_name = item.category.name
            
            if category_id not in grouped_items:
                grouped_items[category_id] = {
                    'category_id': category_id,
                    'category_name': category_name,
                    'items': []
                }
            
            grouped_items[category_id]['items'].append(
                MasterServiceItemsSerializer(item, context=self.context).data
            )
        
        # Преобразуем в список
        return list(grouped_items.values())
    
    def validate_master_items(self, value):
        """Валидация элементов услуги"""
        if not isinstance(value, list):
            raise serializers.ValidationError("master_items должен быть списком")
        
        for item in value:
            if not isinstance(item, dict):
                raise serializers.ValidationError("Каждый элемент должен быть объектом")
            required_fields = ['name', 'price_from', 'price_to', 'category']
            for field in required_fields:
                if field not in item:
                    raise serializers.ValidationError(f"Каждый элемент должен содержать '{field}'")
            
            # Проверяем, что категория существует
            try:
                Category.objects.get(id=item['category'])
            except Category.DoesNotExist:
                raise serializers.ValidationError(f"Категория с ID {item['category']} не найдена")
        
        return value
    
    def validate_master_id(self, value):
        """Валидация master_id"""
        if value:
            try:
                from .models import Master
                Master.objects.get(id=value)
            except Master.DoesNotExist:
                raise serializers.ValidationError(f"Мастер с ID {value} не найден")
        return value
    
    def create(self, validated_data):
        """Создание услуги мастера с элементами"""
        master_items_data = validated_data.pop('master_items', [])
        validated_data.pop('master_id', None)  # Удаляем master_id, он только для валидации
        master_service = super().create(validated_data)
        
        # Создаем элементы услуги
        for item_data in master_items_data:
            MasterServiceItems.objects.create(
                master_service=master_service,
                name=item_data['name'],
                price_from=item_data['price_from'],
                price_to=item_data['price_to'],
                category_id=item_data['category']
            )
        
        return master_service
    
    def update(self, instance, validated_data):
        """Обновление услуги мастера с элементами"""
        master_items_data = validated_data.pop('master_items', None)
        
        # Если переданы новые элементы, удаляем старые и создаем новые
        if master_items_data is not None:
            # Удаляем старые элементы
            MasterServiceItems.objects.filter(master_service=instance).delete()
            
            # Создаем новые элементы
            for item_data in master_items_data:
                MasterServiceItems.objects.create(
                    master_service=instance,
                    name=item_data['name'],
                    price_from=item_data['price_from'],
                    price_to=item_data['price_to'],
                    category_id=item_data['category']
                )
        
        return super().update(instance, validated_data)


class MasterEmployeeCreateSerializer(serializers.Serializer):
    """Сериализатор для добавления сотрудника к мастерской"""
    master_id = serializers.IntegerField(
        required=True,
        help_text="ID мастерской"
    )
    user_id = serializers.IntegerField(
        required=True,
        help_text="ID пользователя для добавления"
    )
    
    def validate_master_id(self, value):
        """Валидация master_id"""
        try:
            Master.objects.get(id=value)
        except Master.DoesNotExist:
            raise serializers.ValidationError("Мастерская не найдена")
        return value
    
    def validate_user_id(self, value):
        """Валидация user_id"""
        try:
            User.objects.get(id=value)
        except User.DoesNotExist:
            raise serializers.ValidationError("Пользователь не найден")
        return value
    
    def validate(self, attrs):
        """Дополнительная валидация"""
        master_id = attrs.get('master_id')
        user_id = attrs.get('user_id')
        
        master = Master.objects.get(id=master_id)
        user = User.objects.get(id=user_id)
        
        # Проверка, что пользователь не является владельцем
        if master.user.id == user.id:
            raise serializers.ValidationError({
                'user_id': 'Владелец уже добавлен автоматически'
            })
        
        # Проверка, что сотрудник еще не добавлен в эту мастерскую
        if MasterEmployee.objects.filter(master=master, employee=user).exists():
            raise serializers.ValidationError({
                'user_id': 'Этот пользователь уже добавлен в эту мастерскую'
            })
        
        # Проверка, что пользователь не работает в другой мастерской
        existing_employment = MasterEmployee.objects.filter(employee=user).exclude(master=master).first()
        if existing_employment:
            owner_name = existing_employment.master.user.get_full_name() or existing_employment.master.user.phone_number
            raise serializers.ValidationError({
                'user_id': f'Этот пользователь уже является сотрудником мастерской "{owner_name}". '
                          f'Один пользователь может работать только в одной мастерской.'
            })
        
        return attrs
