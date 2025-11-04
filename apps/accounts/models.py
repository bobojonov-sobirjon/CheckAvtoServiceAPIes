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


class UserSMSCode(models.Model):
    """
    Model for storing SMS codes with created_by tracking
    """
    code = models.CharField(
        max_length=10,
        verbose_name="SMS код",
        help_text="Код подтверждения"
    )
    identifier = models.CharField(
        max_length=255,
        verbose_name="Идентификатор",
        help_text="Номер телефона или email"
    )
    identifier_type = models.CharField(
        max_length=10,
        choices=[('phone', 'Телефон'), ('email', 'Email')],
        verbose_name="Тип идентификатора",
        help_text="Тип идентификатора: телефон или email"
    )
    created_by = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        related_name='sms_codes',
        null=True,
        blank=True,
        verbose_name="Создатель",
        help_text="Пользователь, который запросил код (если зарегистрирован)"
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Дата создания"
    )
    expires_at = models.DateTimeField(
        verbose_name="Срок действия"
    )
    is_used = models.BooleanField(
        default=False,
        verbose_name="Использован",
        help_text="Указывает, был ли код использован"
    )
    used_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Дата использования"
    )

    class Meta:
        verbose_name = "SMS код"
        verbose_name_plural = "SMS коды"
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['identifier', 'identifier_type']),
            models.Index(fields=['code', 'identifier']),
            models.Index(fields=['is_used', 'expires_at']),
        ]

    def __str__(self):
        return f"SMS код {self.code} для {self.identifier}"

    def is_expired(self):
        """Проверяет, истек ли срок действия кода"""
        from django.utils import timezone
        return timezone.now() > self.expires_at

    def mark_as_used(self):
        """Помечает код как использованный"""
        from django.utils import timezone
        self.is_used = True
        self.used_at = timezone.now()
        self.save(update_fields=['is_used', 'used_at'])


class FAQ(models.Model):
    """
    FAQ (Frequently Asked Questions) model
    """
    question = models.TextField(
        verbose_name="Вопрос",
        help_text="Часто задаваемый вопрос"
    )
    answer = models.TextField(
        verbose_name="Ответ",
        help_text="Ответ на вопрос"
    )
    order = models.IntegerField(
        default=0,
        verbose_name="Порядок",
        help_text="Порядок отображения (меньшее число - выше)"
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name="Активен",
        help_text="Отображать ли вопрос в списке"
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
        verbose_name = "FAQ"
        verbose_name_plural = "FAQ"
        ordering = ['order', '-created_at']

    def __str__(self):
        return f"{self.question[:50]}..."


