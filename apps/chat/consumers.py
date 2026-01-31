import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth import get_user_model
from .models import ChatRoom, ChatMessage

User = get_user_model()


class ChatConsumer(AsyncWebsocketConsumer):
    """
    WebSocket consumer для real-time chat
    """
    
    async def connect(self):
        """При подключении к WebSocket"""
        self.room_id = self.scope['url_route']['kwargs']['room_id']
        self.room_group_name = f'chat_{self.room_id}'
        self.user = self.scope['user']
        
        # Проверяем авторизацию
        if not self.user or not self.user.is_authenticated:
            await self.close()
            return
        
        # Проверяем доступ к комнате
        has_access = await self.check_room_access()
        if not has_access:
            await self.close()
            return
        
        # Присоединяемся к группе комнаты
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        
        await self.accept()
        
        # Отправляем подтверждение подключения
        await self.send(text_data=json.dumps({
            'type': 'connection_established',
            'message': 'Successfully connected to chat'
        }))
    
    async def disconnect(self, close_code):
        """При отключении от WebSocket"""
        # Покидаем группу комнаты
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )
    
    async def receive(self, text_data):
        """Получение сообщения от клиента"""
        try:
            data = json.loads(text_data)
            message_type = data.get('type')
            
            if message_type == 'chat_message':
                # Сохраняем сообщение в БД
                message = await self.save_message(data)
                
                # Отправляем сообщение всем в группе
                await self.channel_layer.group_send(
                    self.room_group_name,
                    {
                        'type': 'chat_message',
                        'message': await self.message_to_dict(message)
                    }
                )
            
            elif message_type == 'typing':
                # Уведомление о наборе текста
                await self.channel_layer.group_send(
                    self.room_group_name,
                    {
                        'type': 'typing_indicator',
                        'user_id': self.user.id,
                        'is_typing': data.get('is_typing', False)
                    }
                )
            
            elif message_type == 'read_receipt':
                # Отметка о прочтении
                message_id = data.get('message_id')
                if message_id:
                    await self.mark_as_read(message_id)
                    await self.channel_layer.group_send(
                        self.room_group_name,
                        {
                            'type': 'read_receipt',
                            'message_id': message_id,
                            'user_id': self.user.id
                        }
                    )
        
        except Exception as e:
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': str(e)
            }))
    
    async def chat_message(self, event):
        """Отправка сообщения в WebSocket"""
        await self.send(text_data=json.dumps({
            'type': 'chat_message',
            'message': event['message']
        }))
    
    async def typing_indicator(self, event):
        """Отправка индикатора набора текста"""
        # Не отправляем себе
        if event['user_id'] != self.user.id:
            await self.send(text_data=json.dumps({
                'type': 'typing',
                'user_id': event['user_id'],
                'is_typing': event['is_typing']
            }))
    
    async def read_receipt(self, event):
        """Отправка подтверждения прочтения"""
        await self.send(text_data=json.dumps({
            'type': 'read_receipt',
            'message_id': event['message_id'],
            'user_id': event['user_id']
        }))
    
    @database_sync_to_async
    def check_room_access(self):
        """Проверка доступа к комнате"""
        try:
            room = ChatRoom.objects.get(id=self.room_id)
            return room.participants.filter(id=self.user.id).exists()
        except ChatRoom.DoesNotExist:
            return False
    
    @database_sync_to_async
    def save_message(self, data):
        """Сохранение сообщения в БД"""
        room = ChatRoom.objects.get(id=self.room_id)
        message = ChatMessage.objects.create(
            room=room,
            sender=self.user,
            message_type=data.get('message_type', 'text'),
            text=data.get('text', '')
        )
        # Обновляем время последнего обновления комнаты
        room.save()
        return message
    
    @database_sync_to_async
    def message_to_dict(self, message):
        """Конвертация сообщения в dict"""
        return {
            'id': message.id,
            'room_id': message.room.id,
            'sender': {
                'id': message.sender.id,
                'full_name': message.sender.get_full_name() or message.sender.email,
                'email': message.sender.email,
                'avatar': message.sender.avatar.url if message.sender.avatar else None
            },
            'sender_type': 'initiator',  # WebSocket'da yuboruvchi doim initiator
            'message_type': message.message_type,
            'text': message.text,
            'file': message.file.url if message.file else None,
            'image': message.image.url if message.image else None,
            'audio': message.audio.url if message.audio else None,
            'is_read': message.is_read,
            'created_at': message.created_at.isoformat()
        }
    
    @database_sync_to_async
    def mark_as_read(self, message_id):
        """Отметка сообщения как прочитанного"""
        try:
            message = ChatMessage.objects.get(id=message_id)
            if message.sender != self.user:
                message.is_read = True
                message.save()
        except ChatMessage.DoesNotExist:
            pass
