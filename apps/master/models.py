from django.db import models
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from apps.categories.models import Category

User = get_user_model()


class Master(models.Model):
    """Модель мастера"""
    user = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name='master_profiles',
        verbose_name='Пользователь'
    )
    
    name = models.CharField(
        max_length=255, 
        blank=True, 
        default='', 
        verbose_name='Название мастерской',
        help_text='Название мастерской (например: "СТО Авто-Сервис")'
    )
    
    category = models.ManyToManyField(
        Category,
        verbose_name='Категория',
        related_name='master_categories'
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
    
    description = models.TextField(blank=True, verbose_name='Описание', null=True)
    
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


class MasterImage(models.Model):
    """Изображение мастера"""
    master = models.ForeignKey(
        Master, 
        on_delete=models.CASCADE, 
        related_name='master_images',
        verbose_name='Мастер'
    )
    image = models.ImageField(upload_to='master_images/', verbose_name='Изображение')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Дата добавления')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Дата обновления')
    
    class Meta:
        verbose_name = 'Изображение мастера'
        verbose_name_plural = 'Изображения мастеров'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.master} - {self.image.name}"


class MasterService(models.Model):
    """Услуги мастера с ценами"""
    master = models.ForeignKey(
        Master, 
        on_delete=models.CASCADE, 
        related_name='master_services',
        verbose_name='Мастер'
    )
    
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Дата добавления')
    
    class Meta:
        verbose_name = 'Услуга мастера'
        verbose_name_plural = 'Услуги мастеров'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.master} - {self.id}"


class MasterServiceItems(models.Model):
    """Items услуги мастера"""
    master_service = models.ForeignKey(
        MasterService,
        on_delete=models.CASCADE,
        related_name='master_service_items',
        verbose_name='Услуга мастера'
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
    category = models.ForeignKey(
        Category,
        on_delete=models.CASCADE,
        related_name='master_service_items',
        verbose_name='Категория'
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Дата добавления')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Дата обновления')
    
    class Meta:
        verbose_name = 'Услуги'
        verbose_name_plural = 'Услуги'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.master_service} - {self.name}: {self.price_from}-{self.price_to}"


class MasterEmployee(models.Model):
    """Сотрудники мастерской"""
    master = models.ForeignKey(
        Master,
        on_delete=models.CASCADE,
        related_name='employees',
        verbose_name='Мастер'
    )
    employee = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='master_employments',
        verbose_name='Сотрудник'
    )
    added_at = models.DateTimeField(auto_now_add=True, verbose_name='Дата добавления')
    
    class Meta:
        verbose_name = 'Сотрудник мастерской'
        verbose_name_plural = 'Сотрудники мастерских'
        unique_together = ['master', 'employee']
        ordering = ['added_at']
    
    def __str__(self):
        return f"{self.master} - {self.employee.email}"


