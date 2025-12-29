from rest_framework import serializers
from .models import Master, MasterService, MasterImage, MasterServiceItems, MasterInMaster
from apps.categories.models import Category
from apps.order.models import Rating


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
    master_in_master_data = serializers.SerializerMethodField()
    rating_data = serializers.SerializerMethodField()
    
    class Meta:
        model = Master
        fields = [
            'id', 'user_info', 'city', 'address', 
            'latitude', 'longitude', 'phone', 'working_time', 'services',
            'card_number', 'card_expiry_month', 'card_expiry_year', 
            'card_cvv', 'balance', 'reserved_amount', 'description', 'images', 
            'category_data', 'master_in_master_data', 'rating_data', 'created_at', 'updated_at', 
            'last_activity'
        ]
        read_only_fields = ['id', 'user', 'created_at', 'updated_at', 'last_activity']
    
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
    
    def get_master_in_master_data(self, obj):
        """Получить данные мастеров в мастере"""
        master_in_masters = MasterInMaster.objects.filter(master=obj)
        request = self.context.get('request')
        return [
            {
                'id': mim.id,
                'masterinmaster_data': {
                    'id': mim.masterinmaster.id,
                    'full_name': mim.masterinmaster.get_full_name(),
                    'phone_number': mim.masterinmaster.phone_number,
                    'email': mim.masterinmaster.email,
                    'first_name': mim.masterinmaster.first_name,
                    'last_name': mim.masterinmaster.last_name
                },
                'category_data': {
                    'id': mim.category.id,
                    'name': mim.category.name,
                    'icon': request.build_absolute_uri(mim.category.icon.url) if mim.category and mim.category.icon and request else None
                } if mim.category else None,
                'rating_data': self._get_rating_data_for_master_in_master(mim.masterinmaster),
                'created_at': mim.created_at,
                'updated_at': mim.updated_at
            }
            for mim in master_in_masters
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
    
    def _get_rating_data_for_master_in_master(self, master_in_master_user):
        """Получить данные рейтинга для мастера в мастере"""
        ratings = Rating.objects.filter(master_in_master=master_in_master_user)
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
            'city', 'address', 'latitude', 'longitude', 'services', 'category',
            'card_number', 'card_expiry_month', 'card_expiry_year', 
            'card_cvv'
        ]
    
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
        services_data = validated_data.pop('services', [])
        category_ids = validated_data.pop('category', [])
        validated_data['user'] = self.context['request'].user
        
        master = super().create(validated_data)
        
        # Добавляем категории
        if category_ids:
            master.category.set(category_ids)
        
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


class MasterInMasterSerializer(serializers.ModelSerializer):
    """Сериализатор для мастера в мастере"""
    masterinmaster_name = serializers.CharField(source='masterinmaster.get_full_name', read_only=True)
    masterinmaster_phone = serializers.CharField(source='masterinmaster.phone_number', read_only=True)
    masterinmaster_id = serializers.IntegerField(source='masterinmaster.id', read_only=True)
    category_data = serializers.SerializerMethodField()
    
    class Meta:
        model = MasterInMaster
        fields = [
            'id', 'master', 'masterinmaster_id', 'masterinmaster_name', 
            'masterinmaster_phone', 'category', 'category_data', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def get_category_data(self, obj):
        """Получить данные категории (icon, name)"""
        if not obj.category:
            return None
        
        request = self.context.get('request')
        return {
            'id': obj.category.id,
            'name': obj.category.name,
            'icon': request.build_absolute_uri(obj.category.icon.url) if obj.category.icon and request else None
        }


