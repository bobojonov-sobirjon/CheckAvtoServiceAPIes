from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone

User = get_user_model()


class ChatRoom(models.Model):
    """
    Chat xonasi - ikki user o'rtasidagi chat
    """
    initiator = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='initiated_chats',
        verbose_name='Инициатор',
        help_text='Пользователь, создавший чат',
        null=True,
        blank=True
    )
    participants = models.ManyToManyField(
        User,
        related_name='chat_rooms',
        verbose_name='Участники'
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
        verbose_name = 'Чат комната'
        verbose_name_plural = 'Чат комнаты'
        ordering = ['-updated_at']

    def __str__(self):
        participants_names = ', '.join([p.get_full_name() or p.email for p in self.participants.all()[:2]])
        return f"Chat #{self.id}: {participants_names}"

    def get_other_participant(self, user):
        """Получить другого участника чата"""
        return self.participants.exclude(id=user.id).first()
    
    def get_sender_type(self, user):
        """Определить тип отправителя относительно текущего пользователя"""
        # Если initiator не установлен, используем первого участника
        if self.initiator is None:
            first_participant = self.participants.first()
            if first_participant and first_participant == user:
                return 'initiator'
            return 'receiver'
        
        if self.initiator == user:
            return 'initiator'
        return 'receiver'


class ChatMessage(models.Model):
    """
    Chat xabari - text, file, image, audio
    """
    MESSAGE_TYPE_CHOICES = [
        ('text', 'Текст'),
        ('image', 'Изображение'),
        ('file', 'Файл'),
        ('audio', 'Аудио'),
    ]

    room = models.ForeignKey(
        ChatRoom,
        on_delete=models.CASCADE,
        related_name='messages',
        verbose_name='Комната'
    )
    sender = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='sent_messages',
        verbose_name='Отправитель'
    )
    message_type = models.CharField(
        max_length=10,
        choices=MESSAGE_TYPE_CHOICES,
        default='text',
        verbose_name='Тип сообщения'
    )
    text = models.TextField(
        blank=True,
        null=True,
        verbose_name='Текст сообщения'
    )
    file = models.FileField(
        upload_to='chat/files/%Y/%m/%d/',
        blank=True,
        null=True,
        verbose_name='Файл'
    )
    image = models.ImageField(
        upload_to='chat/images/%Y/%m/%d/',
        blank=True,
        null=True,
        verbose_name='Изображение'
    )
    audio = models.FileField(
        upload_to='chat/audio/%Y/%m/%d/',
        blank=True,
        null=True,
        verbose_name='Аудио'
    )
    is_read = models.BooleanField(
        default=False,
        verbose_name='Прочитано'
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Дата отправки',
        db_index=True
    )

    class Meta:
        verbose_name = 'Сообщение'
        verbose_name_plural = 'Сообщения'
        ordering = ['created_at']

    def __str__(self):
        return f"Message from {self.sender.get_full_name()} at {self.created_at}"
