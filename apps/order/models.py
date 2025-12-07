from django.db import models
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.utils import timezone
from datetime import timedelta

from apps.accounts.models import CustomUser
from apps.car.models import Car
from apps.categories.models import Category

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
    car = models.ManyToManyField(
        Car,
        related_name='orders',
        verbose_name='Машина'
    )
    category = models.ManyToManyField(
        Category,
        related_name='orders',
        verbose_name='Категория'
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
    master_in_master = models.ManyToManyField(
        CustomUser, related_name='orders_master_in_master', verbose_name='Мастер в мастере', blank=True
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


class Rating(models.Model):
    """Модель рейтинга для мастеров"""
    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name='ratings',
        verbose_name='Заказ'
    )
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='given_ratings',
        verbose_name='Пользователь (оценивающий)'
    )
    master = models.ForeignKey(
        'master.Master',
        on_delete=models.CASCADE,
        related_name='ratings',
        null=True,
        blank=True,
        verbose_name='Мастер'
    )
    master_in_master = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='ratings_as_master_in_master',
        null=True,
        blank=True,
        verbose_name='Мастер в мастере'
    )
    rating = models.PositiveIntegerField(
        verbose_name='Рейтинг',
        help_text='Рейтинг от 1 до 5'
    )
    comment = models.TextField(
        blank=True,
        null=True,
        verbose_name='Комментарий',
        help_text='Комментарий к рейтингу'
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Дата создания'
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name='Дата обновления'
    )

    class Meta:
        verbose_name = 'Рейтинг'
        verbose_name_plural = 'Рейтинги'
        ordering = ['-created_at']
        unique_together = [
            ['order', 'user', 'master'],
            ['order', 'user', 'master_in_master']
        ]

    def __str__(self):
        if self.master:
            return f"Рейтинг {self.rating} для мастера {self.master} от {self.user}"
        elif self.master_in_master:
            return f"Рейтинг {self.rating} для мастера в мастере {self.master_in_master} от {self.user}"
        return f"Рейтинг {self.rating} от {self.user}"

    def clean(self):
        """Валидация модели"""
        if self.rating < 1 or self.rating > 5:
            raise ValidationError({'rating': 'Рейтинг должен быть от 1 до 5'})
        
        if not self.master and not self.master_in_master:
            raise ValidationError('Должен быть указан либо мастер, либо мастер в мастере')
        
        if self.master and self.master_in_master:
            raise ValidationError('Нельзя указать одновременно и мастер, и мастер в мастере')

    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)
