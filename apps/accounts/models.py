from django.contrib.auth.models import AbstractUser
from django.db import models
from django.db import transaction
from django.utils import timezone
from decimal import Decimal
import random
import uuid


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
    telegram_chat_id = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        verbose_name="Telegram Chat ID",
        help_text="Необязательно. Введите ваш Telegram Chat ID для получения SMS."
    )
    private_id = models.CharField(
        max_length=6,
        unique=True,
        blank=True,
        null=True,
        verbose_name="Private ID",
        help_text="Уникальный 6-значный идентификатор пользователя. Генерируется автоматически."
    )
    description = models.TextField(
        blank=True,
        null=True,
        verbose_name="Описание",
        help_text="Необязательно. Введите ваше описание."
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
        full_name = f"{self.first_name} {self.last_name}".strip()
        if full_name:
            return full_name
        # Fallbacks: username -> email
        if getattr(self, 'username', None):
            return self.username
        return self.email
    
    def _generate_unique_private_id(self):
        """Генерация уникального 6-значного private_id"""
        while True:
            # Генерируем случайное 6-значное число
            private_id = str(random.randint(100000, 999999))
            
            # Проверяем, что такой ID еще не существует
            if not CustomUser.objects.filter(private_id=private_id).exists():
                return private_id
    
    def save(self, *args, **kwargs):
        """Override save для автоматической генерации private_id"""
        if not self.private_id:
            self.private_id = self._generate_unique_private_id()
        super().save(*args, **kwargs)

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
    
    def get_role_name(self):
        """
        Return the role name based on user groups.
        """
        groups = self.groups.all()
        if groups.exists():
            # Return the first group name
            return groups.first().name
        return 'Нет роли'


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


class SbpPaymentIntent(models.Model):
    """
    Намерение пополнения по СБП: после оплаты статус меняется на completed (webhook или админ).
    Статический QR НСПК не передаёт intent_id в банк — привязка только через сумму/время ненадёжна;
    для авто-зачисления банк должен дергать webhook или оператор подтверждает в админке.
    """

    STATUS_PENDING = 'pending'
    STATUS_COMPLETED = 'completed'
    STATUS_EXPIRED = 'expired'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        'accounts.CustomUser',
        on_delete=models.CASCADE,
        related_name='sbp_intents',
        verbose_name='Пользователь',
    )
    amount = models.DecimalField(max_digits=12, decimal_places=2, verbose_name='Сумма, ₽')
    status = models.CharField(max_length=20, default=STATUS_PENDING, verbose_name='Статус')
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    bank_reference = models.CharField(
        max_length=256, blank=True, default='', verbose_name='Референс банка',
    )

    class Meta:
        verbose_name = 'СБП: намерение оплаты'
        verbose_name_plural = 'СБП: намерения оплаты'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'status', '-created_at']),
        ]

    def __str__(self):
        return f'{self.id} {self.user_id} {self.amount} ₽ {self.status}'

    @classmethod
    def complete_pending(
        cls,
        intent_id,
        *,
        bank_reference: str = '',
        expected_amount: Decimal | None = None,
    ) -> tuple[str, 'SbpPaymentIntent | None']:
        """
        Идемпотентное зачисление. Возвращает (код, intent).
        Коды: ok, already_completed, not_found, not_pending, amount_mismatch
        """
        with transaction.atomic():
            try:
                obj = cls.objects.select_for_update().get(pk=intent_id)
            except cls.DoesNotExist:
                return 'not_found', None
            if obj.status == cls.STATUS_COMPLETED:
                return 'already_completed', obj
            if obj.status != cls.STATUS_PENDING:
                return 'not_pending', obj
            if expected_amount is not None and obj.amount != expected_amount:
                return 'amount_mismatch', obj
            balance = UserBalance.get_or_create_balance(obj.user)
            balance.add_amount(obj.amount)
            obj.status = cls.STATUS_COMPLETED
            obj.completed_at = timezone.now()
            obj.bank_reference = (bank_reference or '')[:256]
            obj.save(update_fields=['status', 'completed_at', 'bank_reference'])
            return 'ok', obj


class AlfaSbpTemplateSnapshot(models.Model):
    """
    Копия ответа createTemplate: если getTemplateDetails даёт errorCode 5, отдаём из БД.
    """

    user = models.ForeignKey(
        'accounts.CustomUser',
        on_delete=models.CASCADE,
        related_name='alfa_sbp_template_snapshots',
        verbose_name='Пользователь',
    )
    template_id = models.CharField(max_length=40, verbose_name='templateId шлюза')
    gateway_response = models.JSONField(verbose_name='Ответ шлюза (create)')
    generated_meta = models.JSONField(null=True, blank=True, verbose_name='Поля quick-create')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Снимок шаблона СБП (Альфа)'
        verbose_name_plural = 'Снимки шаблонов СБП'
        ordering = ['-created_at']
        constraints = [
            models.UniqueConstraint(fields=['user', 'template_id'], name='alfa_sbp_snapshot_user_template'),
        ]

    def __str__(self):
        return f'{self.template_id} user={self.user_id}'


class PaymentStatus(models.TextChoices):
    PENDING = 'pending', 'Ожидает оплаты'
    PAID = 'paid', 'Оплачено'
    FAILED = 'failed', 'Ошибка'


class PaymentKind(models.TextChoices):
    ORDER = 'order', 'Оплата заказа'
    MASTER_TOPUP = 'master_topup', 'Пополнение баланса мастера'


class PaymentTransaction(models.Model):
    """
    Универсальная транзакция оплаты (order payment / top-up).
    Держим alfa_order_id/number + intent_id для проверки статуса и автопроведения.
    """

    kind = models.CharField(max_length=32, choices=PaymentKind.choices, verbose_name='Тип')
    status = models.CharField(max_length=20, choices=PaymentStatus.choices, default=PaymentStatus.PENDING, db_index=True)

    # Кто инициировал оплату (например Owner), и кто получатель средств (user у intent)
    initiated_by = models.ForeignKey(
        'accounts.CustomUser',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='initiated_payments',
        verbose_name='Инициатор',
    )
    beneficiary = models.ForeignKey(
        'accounts.CustomUser',
        on_delete=models.CASCADE,
        related_name='beneficiary_payments',
        verbose_name='Получатель',
    )

    amount = models.DecimalField(max_digits=12, decimal_places=2, verbose_name='Сумма, ₽')
    intent = models.OneToOneField(
        'accounts.SbpPaymentIntent',
        on_delete=models.CASCADE,
        related_name='payment_tx',
        verbose_name='Intent',
    )

    alfa_order_id = models.CharField(max_length=64, blank=True, default='', db_index=True)
    alfa_order_number = models.CharField(max_length=64, blank=True, default='', db_index=True)
    form_url = models.TextField(blank=True, default='')

    order = models.ForeignKey(
        'order.Order',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='payment_transactions',
        verbose_name='Заказ',
    )
    master = models.ForeignKey(
        'master.Master',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='payment_transactions',
        verbose_name='Мастер',
    )

    gateway_last_response = models.JSONField(null=True, blank=True, verbose_name='Последний ответ шлюза')
    last_checked_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Платёж'
        verbose_name_plural = 'Платежи'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status', '-created_at']),
            models.Index(fields=['kind', 'status', '-created_at']),
        ]

    def __str__(self):
        return f'{self.kind} {self.status} {self.amount}₽ intent={self.intent_id}'


class MasterAvailableBalance(models.Model):
    """
    Доступный баланс мастера (зачисления с оплаченных заказов).
    Отдельно от UserBalance (гарантийный / списания за принятие заказов).
    """

    user = models.OneToOneField(
        'accounts.CustomUser',
        on_delete=models.CASCADE,
        related_name='master_available_balance',
        verbose_name='Мастер (пользователь)',
    )
    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name='Доступно, ₽',
    )
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Доступный баланс мастера'
        verbose_name_plural = 'Доступные балансы мастеров'

    def __str__(self):
        return f'{self.user_id}: {self.amount} ₽'

    @classmethod
    def get_or_create_for(cls, user) -> 'MasterAvailableBalance':
        obj, _ = cls.objects.get_or_create(user=user, defaults={'amount': Decimal('0.00')})
        return obj

    @classmethod
    def add_amount(cls, user, amount: Decimal) -> None:
        if amount <= 0:
            return
        with transaction.atomic():
            bal = cls.objects.select_for_update().get_or_create(user=user, defaults={'amount': Decimal('0.00')})[0]
            bal.amount = bal.amount + Decimal(str(amount))
            bal.save(update_fields=['amount', 'updated_at'])

    @classmethod
    def try_reserve_for_withdrawal(cls, user, amount: Decimal) -> tuple[bool, str | None]:
        """Списать сумму с доступного баланса (заявка на вывод)."""
        if amount <= 0:
            return False, 'Сумма должна быть больше 0'
        with transaction.atomic():
            bal = cls.objects.select_for_update().get_or_create(user=user, defaults={'amount': Decimal('0.00')})[0]
            if bal.amount < amount:
                return False, 'Недостаточно средств на доступном балансе'
            bal.amount -= amount
            bal.save(update_fields=['amount', 'updated_at'])
        return True, None


class MasterOrderEarningCredit(models.Model):
    """Идемпотентная запись: заказ уже зачислен на доступный баланс мастера."""

    order = models.OneToOneField(
        'order.Order',
        on_delete=models.CASCADE,
        related_name='master_earning_credit',
        verbose_name='Заказ',
    )
    master_user = models.ForeignKey(
        'accounts.CustomUser',
        on_delete=models.CASCADE,
        related_name='master_order_earning_credits',
        verbose_name='Мастер',
    )
    amount = models.DecimalField(max_digits=12, decimal_places=2, verbose_name='Сумма, ₽')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Зачисление с заказа (мастер)'
        verbose_name_plural = 'Зачисления с заказов'

    def __str__(self):
        return f'order={self.order_id} +{self.amount}'


class MasterWithdrawalStatus(models.TextChoices):
    PENDING = 'pending', 'Ожидает проверки'
    REVIEWING = 'reviewing', 'На рассмотрении'
    PROCESSING = 'processing', 'В обработке'
    COMPLETED = 'completed', 'Выплачено'
    REJECTED = 'rejected', 'Отклонено'


class MasterWithdrawalRequest(models.Model):
    """Заявка мастера на вывод средств (сумма сразу резервируется с доступного баланса)."""

    master_user = models.ForeignKey(
        'accounts.CustomUser',
        on_delete=models.CASCADE,
        related_name='master_withdrawal_requests',
        verbose_name='Мастер',
    )
    amount = models.DecimalField(max_digits=12, decimal_places=2, verbose_name='Сумма, ₽')
    status = models.CharField(
        max_length=20,
        choices=MasterWithdrawalStatus.choices,
        default=MasterWithdrawalStatus.PENDING,
        db_index=True,
        verbose_name='Статус',
    )
    admin_note = models.TextField(blank=True, default='', verbose_name='Заметка админа')
    refunded_at = models.DateTimeField(null=True, blank=True, verbose_name='Возврат на баланс')
    completed_at = models.DateTimeField(null=True, blank=True, verbose_name='Выплата подтверждена')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Заявка на вывод (мастер)'
        verbose_name_plural = 'Заявки на вывод'
        ordering = ['-created_at']

    def __str__(self):
        return f'#{self.pk} {self.master_user_id} {self.amount} {self.status}'


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


class MasterCustomUser(CustomUser):
    """
    Proxy model для мастеров
    """
    class Meta:
        proxy = True
        verbose_name = "Мастер"
        verbose_name_plural = "03. Мастера"


class CarOwner(CustomUser):
    """
    Proxy model для автовладельцев
    """
    class Meta:
        proxy = True
        verbose_name = "Автовладелец"
        verbose_name_plural = "01. Автовладельцы"


class Owner(CustomUser):
    """
    Proxy model для владельцев
    """
    class Meta:
        proxy = True
        verbose_name = "Владелец"
        verbose_name_plural = "02. Владельцы"


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
        verbose_name_plural = "04. FAQ"
        ordering = ['order', '-created_at']

    def __str__(self):
        return f"{self.question[:50]}..."


class UserDevice(models.Model):
    """
    Firebase push uchun user device tokenlar.
    """

    DEVICE_ANDROID = 'android'
    DEVICE_IOS = 'ios'
    DEVICE_WEB = 'web'

    DEVICE_TYPE_CHOICES = [
        (DEVICE_ANDROID, 'Android'),
        (DEVICE_IOS, 'iOS'),
        (DEVICE_WEB, 'Web'),
    ]

    user = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        related_name='devices',
        verbose_name='Пользователь',
    )
    device_token = models.TextField(verbose_name='FCM token')
    device_type = models.CharField(
        max_length=20,
        choices=DEVICE_TYPE_CHOICES,
        default=DEVICE_ANDROID,
        verbose_name='Тип устройства',
    )
    is_active = models.BooleanField(default=True, verbose_name='Активен')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Устройство пользователя'
        verbose_name_plural = 'Устройства пользователей'
        ordering = ['-updated_at']
        indexes = [
            models.Index(fields=['user', 'is_active', '-updated_at']),
        ]
        constraints = [
            models.UniqueConstraint(fields=['user', 'device_token'], name='uniq_user_device_token'),
        ]

    def __str__(self):
        return f'{self.user_id} {self.device_type} active={self.is_active}'


