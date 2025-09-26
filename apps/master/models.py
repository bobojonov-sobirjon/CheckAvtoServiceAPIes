from django.db import models
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError

User = get_user_model()


class ServiceType(models.TextChoices):
    """Статические типы услуг"""
    DIAGNOSTICS = 'diagnostics', 'Диагностика электроники'
    SERVICE = 'service', 'Сервис и ТО'
    TIRE_REPAIR = 'tire_repair', 'Шиномонтаж'
    TOWING = 'towing', 'Буксировка'
    CAR_WASH = 'car_wash', 'Автомойка'
    ROAD_HELP = 'road_help', 'Помощь на дороге'


class Master(models.Model):
    """Модель мастера"""
    user = models.OneToOneField(
        User, 
        on_delete=models.CASCADE, 
        related_name='master_profile',
        verbose_name='Пользователь'
    )
    
    # Местоположение
    city = models.CharField(max_length=100, verbose_name='Город')
    
    # Услуги (множественный выбор)
    services = models.JSONField(
        default=list,
        verbose_name='Предоставляемые услуги',
        help_text='Список выбранных услуг'
    )
    
    # Банковские данные
    card_number = models.CharField(max_length=19, blank=True, verbose_name='Номер карты')
    card_expiry_month = models.PositiveIntegerField(null=True, blank=True, verbose_name='Месяц истечения')
    card_expiry_year = models.PositiveIntegerField(null=True, blank=True, verbose_name='Год истечения')
    card_cvv = models.CharField(max_length=4, blank=True, verbose_name='CVV/CVC')
    
    
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
    def services_list(self):
        """Список услуг в виде строки"""
        service_names = []
        for service_code in self.services:
            for choice in ServiceType.choices:
                if choice[0] == service_code:
                    service_names.append(choice[1])
                    break
        return ', '.join(service_names)
    
    def get_services_display(self):
        """Получить отображаемые названия услуг"""
        return [choice[1] for choice in ServiceType.choices if choice[0] in self.services]
    
    def add_service(self, service_code):
        """Добавить услугу"""
        if service_code not in self.services:
            self.services.append(service_code)
            self.save(update_fields=['services'])
    
    def remove_service(self, service_code):
        """Удалить услугу"""
        if service_code in self.services:
            self.services.remove(service_code)
            self.save(update_fields=['services'])
    
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
