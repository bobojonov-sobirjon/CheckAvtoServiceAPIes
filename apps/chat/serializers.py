from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import ChatRoom, ChatMessage

User = get_user_model()


class ChatParticipantSerializer(serializers.ModelSerializer):
    """Сериализатор для участника чата"""
    full_name = serializers.SerializerMethodField()
    
    class Meta:
        model = User
        fields = ['id', 'email', 'first_name', 'last_name', 'full_name', 'avatar']
    
    def get_full_name(self, obj):
        return obj.get_full_name() or obj.email


class ChatMessageSerializer(serializers.ModelSerializer):
    """Сериализатор для сообщения"""
    sender = ChatParticipantSerializer(read_only=True)
    file_url = serializers.SerializerMethodField()
    image_url = serializers.SerializerMethodField()
    audio_url = serializers.SerializerMethodField()
    
    class Meta:
        model = ChatMessage
        fields = [
            'id', 'room', 'sender', 'message_type', 'text',
            'file', 'file_url', 'image', 'image_url', 'audio', 'audio_url',
            'is_read', 'created_at'
        ]
        read_only_fields = ['id', 'sender', 'created_at']
    
    def get_file_url(self, obj):
        if obj.file:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.file.url)
            return obj.file.url
        return None
    
    def get_image_url(self, obj):
        if obj.image:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.image.url)
            return obj.image.url
        return None
    
    def get_audio_url(self, obj):
        if obj.audio:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.audio.url)
            return obj.audio.url
        return None


class ChatRoomSerializer(serializers.ModelSerializer):
    """Сериализатор для чат комнаты"""
    participants = ChatParticipantSerializer(many=True, read_only=True)
    last_message = serializers.SerializerMethodField()
    unread_count = serializers.SerializerMethodField()
    other_participant = serializers.SerializerMethodField()
    
    class Meta:
        model = ChatRoom
        fields = [
            'id', 'participants', 'other_participant', 'last_message',
            'unread_count', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def get_last_message(self, obj):
        last_msg = obj.messages.order_by('-created_at').first()
        if last_msg:
            return ChatMessageSerializer(last_msg, context=self.context).data
        return None
    
    def get_unread_count(self, obj):
        request = self.context.get('request')
        if request and request.user:
            return obj.messages.filter(is_read=False).exclude(sender=request.user).count()
        return 0
    
    def get_other_participant(self, obj):
        request = self.context.get('request')
        if request and request.user:
            other = obj.get_other_participant(request.user)
            if other:
                return ChatParticipantSerializer(other, context=self.context).data
        return None


class CreateChatRoomSerializer(serializers.Serializer):
    """Сериализатор для создания чат комнаты"""
    participant_id = serializers.IntegerField(
        help_text='ID другого пользователя для создания чата'
    )
    
    def validate_participant_id(self, value):
        try:
            User.objects.get(id=value)
        except User.DoesNotExist:
            raise serializers.ValidationError(f'Пользователь с ID {value} не найден')
        return value


class SendMessageSerializer(serializers.ModelSerializer):
    """Сериализатор для отправки сообщения"""
    
    class Meta:
        model = ChatMessage
        fields = ['room', 'message_type', 'text', 'file', 'image', 'audio']
    
    def validate(self, data):
        message_type = data.get('message_type')
        
        if message_type == 'text' and not data.get('text'):
            raise serializers.ValidationError({'text': 'Текст сообщения обязателен для типа "text"'})
        
        if message_type == 'file' and not data.get('file'):
            raise serializers.ValidationError({'file': 'Файл обязателен для типа "file"'})
        
        if message_type == 'image' and not data.get('image'):
            raise serializers.ValidationError({'image': 'Изображение обязательно для типа "image"'})
        
        if message_type == 'audio' and not data.get('audio'):
            raise serializers.ValidationError({'audio': 'Аудио обязательно для типа "audio"'})
        
        return data
