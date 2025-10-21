from django.db import models
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError

User = get_user_model()


class ServiceType(models.TextChoices):
    """Статические типы услуг"""
    DIAGNOSTICS = 'diagnostics', 'Диагностика электроники'
    SERVICE = 'service', 'Сервис и СТО'
    TIRE_REPAIR = 'tire_repair', 'Шиномонтаж'
    TOWING = 'towing', 'Буксировка'
    CAR_WASH = 'car_wash', 'Автомойка'
    ROAD_HELP = 'road_help', 'Помощь на дороге'


class Master(models.Model):
    """Модель мастера"""
    user = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name='master_profiles',
        verbose_name='Пользователь'
    )
    
    # Местоположение
    city = models.CharField(max_length=100, blank=True, default='', verbose_name='Город')
    address = models.TextField(blank=True, verbose_name='Адрес')
    latitude = models.DecimalField(
        max_digits=12, 
        decimal_places=9, 
        null=True, 
        blank=True, 
        verbose_name='Широта'
    )
    longitude = models.DecimalField(
        max_digits=12, 
        decimal_places=9, 
        null=True, 
        blank=True, 
        verbose_name='Долгота'
    )
    phone = models.CharField(max_length=20, default='', verbose_name='Телефон')
    working_time = models.CharField(max_length=100, default='', verbose_name='Рабочее время')
    
    service_type = models.CharField(max_length=100, default='', verbose_name='Тип услуги', choices=ServiceType.choices)
    
    # Банковские данные
    card_number = models.CharField(max_length=19, blank=True, verbose_name='Номер карты')
    card_expiry_month = models.PositiveIntegerField(null=True, blank=True, verbose_name='Месяц истечения')
    card_expiry_year = models.PositiveIntegerField(null=True, blank=True, verbose_name='Год истечения')
    card_cvv = models.CharField(max_length=4, blank=True, verbose_name='CVV/CVC')
    
    # Баланс мастера
    balance = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        default=0.00, 
        verbose_name='Баланс мастера'
    )
    
    # Резерв средств
    reserved_amount = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        default=0.00, 
        verbose_name='Зарезервированная сумма'
    )
    
    # Временные метки
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Дата создания')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Дата обновления')
    last_activity = models.DateTimeField(null=True, blank=True, verbose_name='Последняя активность')
    
    class Meta:
        verbose_name = 'Мастер'
        verbose_name_plural = 'Мастера'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Мастер {self.user.get_full_name() or self.user.phone_number}"
    
    
    @property
    def full_name(self):
        """Полное имя мастера"""
        return self.user.get_full_name() or self.user.phone_number
    
    @property
    def phone_number(self):
        """Номер телефона мастера"""
        return self.user.phone_number
    
    
    @property
    def completion_rate(self):
        """Процент выполнения заказов"""
        return 0  # Поле удалено, всегда возвращаем 0
    
    def can_take_order(self, amount=200):
        """Может ли мастер взять заказ (проверка резерва)"""
        return self.reserved_amount >= amount
    
    def reserve_amount(self, amount):
        """Зарезервировать сумму"""
        self.reserved_amount += amount
        self.save(update_fields=['reserved_amount'])
    
    def release_amount(self, amount):
        """Освободить зарезервированную сумму"""
        self.reserved_amount = max(0, self.reserved_amount - amount)
        self.save(update_fields=['reserved_amount'])


class MasterService(models.Model):
    """Услуги мастера с ценами"""
    master = models.ForeignKey(
        Master, 
        on_delete=models.CASCADE, 
        related_name='master_services',
        verbose_name='Мастер'
    )
    name = models.CharField(max_length=200, default='', verbose_name='Название услуги')
    price_from = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        default=0.00,
        verbose_name='Цена от'
    )
    price_to = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        default=0.00,
        verbose_name='Цена до'
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Дата добавления')
    
    class Meta:
        verbose_name = 'Услуга мастера'
        verbose_name_plural = 'Услуги мастеров'
        ordering = ['name']
    
    def __str__(self):
        return f"{self.master} - {self.name}: {self.price_from}-{self.price_to}"
