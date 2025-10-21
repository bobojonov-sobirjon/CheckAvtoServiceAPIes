from django.contrib.auth.models import AbstractUser
from django.db import models
from decimal import Decimal


class CustomUser(AbstractUser):
    """
    Custom User model that extends Django's AbstractUser
    """
    email = models.EmailField(
        unique=True,
        verbose_name="Электронная почта",
        help_text="Обязательно. Введите действительный адрес электронной почты."
    )
    phone_number = models.CharField(
        max_length=15,
        blank=True,
        null=True,
        verbose_name="Номер телефона",
        help_text="Необязательно. Введите ваш номер телефона."
    )
    date_of_birth = models.DateField(
        blank=True,
        null=True,
        verbose_name="Дата рождения",
        help_text="Необязательно. Введите вашу дату рождения."
    )
    avatar = models.ImageField(
        upload_to='avatars/',
        blank=True,
        null=True,
        verbose_name="Аватар",
        help_text="Необязательно. Загрузите ваше фото профиля."
    )
    address = models.TextField(
        blank=True,
        null=True,
        verbose_name="Адрес",
        help_text="Необязательно. Введите ваш адрес."
    )
    longitude = models.DecimalField(
        max_digits=10,
        decimal_places=7,
        blank=True,
        null=True,
        verbose_name="Долгота",
        help_text="Необязательно. Долгота вашего местоположения."
    )
    latitude = models.DecimalField(
        max_digits=10,
        decimal_places=7,
        blank=True,
        null=True,
        verbose_name="Широта",
        help_text="Необязательно. Широта вашего местоположения."
    )
    is_verified = models.BooleanField(
        default=False,
        verbose_name="Email подтвержден",
        help_text="Указывает, подтвержден ли email этого пользователя."
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Дата создания"
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name="Дата обновления"
    )

    # Use email as the username field
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username', 'first_name', 'last_name']

    class Meta:
        verbose_name = "Пользователь"
        verbose_name_plural = "Пользователи"
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.email} ({self.get_full_name()})"

    def get_full_name(self):
        """
        Return the first_name plus the last_name, with a space in between.
        """
        full_name = f"{self.first_name} {self.last_name}".strip()
        return full_name if full_name else self.email

    def get_short_name(self):
        """
        Return the short name for the user.
        """
        return self.first_name if self.first_name else self.email


class UserBalance(models.Model):
    """
    User balance model for managing user's financial balance
    """
    user = models.OneToOneField(
        CustomUser,
        on_delete=models.CASCADE,
        related_name='balance',
        verbose_name="Пользователь"
    )
    amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0.00,
        verbose_name="Сумма баланса",
        help_text="Текущий баланс пользователя в рублях"
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Дата создания"
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name="Дата обновления"
    )

    class Meta:
        verbose_name = "Баланс пользователя"
        verbose_name_plural = "Балансы пользователей"
        ordering = ['-updated_at']

    def __str__(self):
        return f"Баланс {self.user.get_full_name()}: {self.amount} ₽"

    def has_minimum_balance(self, minimum=1000):
        """
        Проверяет, есть ли у пользователя минимальный баланс
        """
        return self.amount >= Decimal(str(minimum))

    def can_afford_order(self, order_cost=200):
        """
        Проверяет, может ли пользователь позволить себе заказ
        """
        return self.amount >= Decimal(str(order_cost))

    def deduct_amount(self, amount):
        """
        Списывает сумму с баланса
        """
        if self.can_afford_order(amount):
            self.amount -= Decimal(str(amount))
            self.save()
            return True
        return False

    def add_amount(self, amount):
        """
        Добавляет сумму к балансу
        """
        self.amount += Decimal(str(amount))
        self.save()

    @classmethod
    def get_or_create_balance(cls, user):
        """
        Получает или создает баланс для пользователя
        """
        balance, created = cls.objects.get_or_create(
            user=user,
            defaults={'amount': 0.00}
        )
        return balance


