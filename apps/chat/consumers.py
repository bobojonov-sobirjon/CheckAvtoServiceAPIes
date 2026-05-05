import base64
import json
import uuid
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
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
        
        print(f"[DEBUG] WebSocket connect attempt: room_id={self.room_id}, user={self.user}")
        
        # Проверяем авторизацию
        if not self.user or not self.user.is_authenticated:
            print(f"[DEBUG] Authentication failed: user={self.user}")
            await self.close(code=4001)
            return
        
        # Проверяем доступ к комнате
        has_access = await self.check_room_access()
        print(f"[DEBUG] Room access check: has_access={has_access}")
        
        if not has_access:
            print(f"[DEBUG] Access denied to room {self.room_id} for user {self.user.id}")
            await self.close(code=4003)
            return
        
        # Присоединяемся к группе комнаты
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        
        await self.accept()
        
        print(f"[DEBUG] User {self.user.id} successfully connected to room {self.room_id}")
        
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
            print(f"[DEBUG] Received data: {text_data[:100]}")  # First 100 chars
            
            # Check if text_data is empty or whitespace
            if not text_data or not text_data.strip():
                print("[DEBUG] Empty message received, ignoring")
                return
            
            data = json.loads(text_data)
            message_type = data.get('type')
            
            print(f"[DEBUG] Message type: {message_type}")
            
            if message_type == 'chat_message':
                # Вариант 1: broadcast существующего сообщения (REST upload → WS)
                msg_id = data.get('message_id')
                if msg_id:
                    message = await self.get_message_if_allowed(msg_id)
                    if not message:
                        await self.send(text_data=json.dumps({'type': 'error', 'message': 'Message not found / not allowed'}))
                        return
                    await self.channel_layer.group_send(
                        self.room_group_name,
                        {'type': 'chat_message', 'message': await self.message_to_dict(message)},
                    )
                    return

                # Вариант 2: gallery/batch images (images: [{name, base64}, ...])
                images = data.get('images')
                if isinstance(images, list) and images:
                    messages = await self.save_gallery_images(data)
                    await self.channel_layer.group_send(
                        self.room_group_name,
                        {'type': 'chat_message_batch', 'messages': [await self.message_to_dict(m) for m in messages]},
                    )
                    return

                # Вариант 3: single message (text / file / image / audio via base64)
                message = await self.save_message(data)
                await self.channel_layer.group_send(
                    self.room_group_name,
                    {'type': 'chat_message', 'message': await self.message_to_dict(message)},
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
        
        except json.JSONDecodeError as e:
            error_msg = f"Invalid JSON format: {str(e)}"
            print(f"[DEBUG] JSON decode error: {error_msg}")
            print(f"[DEBUG] Received text: {text_data}")
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': error_msg
            }))
        
        except Exception as e:
            error_msg = f"Error processing message: {str(e)}"
            print(f"[DEBUG] General error: {error_msg}")
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': error_msg
            }))
    
    async def chat_message(self, event):
        """Отправка сообщения в WebSocket"""
        msg = event.get('message') or {}
        try:
            sender_id = (msg.get('sender') or {}).get('id')
            sender_type = 'initiator' if sender_id == self.user.id else 'receiver'
            msg = {**msg, 'sender_type': sender_type}
        except Exception:
            msg = {**msg, 'sender_type': 'initiator'}
        await self.send(text_data=json.dumps({
            'type': 'chat_message',
            'message': msg
        }))

    async def chat_message_batch(self, event):
        """Batch/gallery: Отправка нескольких сообщений"""
        raw = event.get('messages') or []
        out = []
        for msg in raw:
            try:
                sender_id = (msg.get('sender') or {}).get('id')
                sender_type = 'initiator' if sender_id == self.user.id else 'receiver'
                out.append({**msg, 'sender_type': sender_type})
            except Exception:
                out.append({**msg, 'sender_type': 'initiator'})
        await self.send(text_data=json.dumps({'type': 'chat_message_batch', 'messages': out}))
    
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
            participants = room.participants.all()
            participant_ids = [p.id for p in participants]
            
            print(f"[DEBUG] Room {self.room_id} participants: {participant_ids}")
            print(f"[DEBUG] Current user ID: {self.user.id}")
            
            has_access = room.participants.filter(id=self.user.id).exists()
            print(f"[DEBUG] Access result: {has_access}")
            
            return has_access
        except ChatRoom.DoesNotExist:
            print(f"[DEBUG] Room {self.room_id} does not exist")
            return False
    
    @database_sync_to_async
    def save_message(self, data):
        """Сохранение сообщения в БД"""
        room = ChatRoom.objects.get(id=self.room_id)
        msg_type = (data.get('message_type') or 'text').strip() or 'text'
        text = data.get('text') or ''

        # WS base64 attachments support
        file_cf = None
        img_cf = None
        audio_cf = None

        def _decode_b64(b64: str) -> bytes:
            # support "data:...;base64,...."
            if ',' in b64 and b64.strip().lower().startswith('data:'):
                b64 = b64.split(',', 1)[1]
            return base64.b64decode(b64)

        if msg_type == 'image' and data.get('image_base64'):
            name = (data.get('image_name') or f'{uuid.uuid4().hex}.jpg').strip()
            img_cf = ContentFile(_decode_b64(str(data.get('image_base64'))), name=name)
        elif msg_type == 'file' and data.get('file_base64'):
            name = (data.get('file_name') or f'{uuid.uuid4().hex}.bin').strip()
            file_cf = ContentFile(_decode_b64(str(data.get('file_base64'))), name=name)
        elif msg_type == 'audio' and data.get('audio_base64'):
            name = (data.get('audio_name') or f'{uuid.uuid4().hex}.mp3').strip()
            audio_cf = ContentFile(_decode_b64(str(data.get('audio_base64'))), name=name)

        message = ChatMessage.objects.create(
            room=room,
            sender=self.user,
            message_type=msg_type,
            text=text,
            file=file_cf,
            image=img_cf,
            audio=audio_cf,
        )
        # Обновляем время последнего обновления комнаты
        room.save()
        return message

    @database_sync_to_async
    def save_gallery_images(self, data):
        """Сохранить несколько изображений (WS gallery) как несколько ChatMessage."""
        room = ChatRoom.objects.get(id=self.room_id)
        text = data.get('text') or ''
        images = data.get('images') or []

        def _decode_b64(b64: str) -> bytes:
            if ',' in b64 and b64.strip().lower().startswith('data:'):
                b64 = b64.split(',', 1)[1]
            return base64.b64decode(b64)

        out = []
        for it in images[:10]:
            if not isinstance(it, dict):
                continue
            b64 = it.get('base64')
            if not b64:
                continue
            name = (it.get('name') or f'{uuid.uuid4().hex}.jpg').strip()
            img_cf = ContentFile(_decode_b64(str(b64)), name=name)
            out.append(ChatMessage.objects.create(room=room, sender=self.user, message_type='image', text=text, image=img_cf))
        room.save()
        return out

    @database_sync_to_async
    def get_message_if_allowed(self, message_id):
        """Получить сообщение по id, если оно принадлежит этой комнате."""
        try:
            msg = ChatMessage.objects.select_related('room', 'sender').get(id=message_id)
        except ChatMessage.DoesNotExist:
            return None
        if str(msg.room_id) != str(self.room_id):
            return None
        return msg
    
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
