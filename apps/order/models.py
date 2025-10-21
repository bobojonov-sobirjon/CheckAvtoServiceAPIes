from django.db import models
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.utils import timezone
from datetime import timedelta

User = get_user_model()


class OrderStatus(models.TextChoices):
    """Статусы заказа"""
    PENDING = 'pending', 'Ожидает'
    IN_PROGRESS = 'in_progress', 'В работе'
    COMPLETED = 'completed', 'Завершен'
    CANCELLED = 'cancelled', 'Отменен'
    REJECTED = 'rejected', 'Отклонен'
    

class OrderPriority(models.TextChoices):
    """Приоритеты заказа"""
    LOW = 'low', 'Низкий'
    HIGH = 'high', 'Высокий'


class Order(models.Model):
    """Модель заказа"""
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='orders',
        verbose_name='Пользователь'
    )
    text = models.TextField(
        verbose_name='Описание заказа',
        help_text='Подробное описание проблемы или услуги'
    )
    status = models.CharField(
        max_length=20,
        choices=OrderStatus.choices,
        default=OrderStatus.PENDING,
        verbose_name='Статус заказа'
    )
    priority = models.CharField(
        max_length=20,
        choices=OrderPriority.choices,
        default=OrderPriority.LOW,
        verbose_name='Приоритет заказа'
    )
    data = models.JSONField(
        default=dict,
        blank=True,
        verbose_name='Дополнительные данные',
        help_text='Дополнительная информация о заказе'
    )
    location = models.TextField(
        verbose_name='Местоположение',
        help_text='Адрес или описание места'
    )
    latitude = models.DecimalField(
        max_digits=10,
        decimal_places=7,
        null=True,
        blank=True,
        verbose_name='Широта',
        help_text='Широта местоположения'
    )
    longitude = models.DecimalField(
        max_digits=10,
        decimal_places=7,
        null=True,
        blank=True,
        verbose_name='Долгота',
        help_text='Долгота местоположения'
    )
    master = models.ForeignKey(
        'master.Master',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='orders',
        verbose_name='Мастер'
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Дата создания'
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name='Дата обновления'
    )
    expiration_time = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='Время истечения',
        help_text='Время истечения заказа (1 день с момента создания)'
    )

    class Meta:
        verbose_name = 'Заказ'
        verbose_name_plural = 'Заказы'
        ordering = ['-created_at']

    def __str__(self):
        return f"Заказ #{self.id} - {self.user.get_full_name()} ({self.get_status_display()})"

    def clean(self):
        """Валидация модели"""
        if self.latitude is not None and (self.latitude < -90 or self.latitude > 90):
            raise ValidationError({'latitude': 'Широта должна быть между -90 и 90'})
        
        if self.longitude is not None and (self.longitude < -180 or self.longitude > 180):
            raise ValidationError({'longitude': 'Долгота должна быть между -180 и 180'})

    def save(self, *args, **kwargs):
        # Автоматически устанавливаем время истечения при создании
        if not self.pk and not self.expiration_time:
            self.expiration_time = timezone.now() + timedelta(days=1)
        self.clean()
        super().save(*args, **kwargs)

    def is_expired(self):
        """
        Проверяет, истек ли заказ
        """
        if self.expiration_time:
            return timezone.now() > self.expiration_time
        return False

    def mark_as_cancelled_if_expired(self):
        """
        Отмечает заказ как отмененный, если он истек
        """
        if self.is_expired() and self.status == OrderStatus.PENDING:
            self.status = OrderStatus.CANCELLED
            self.save()
            return True
        return False