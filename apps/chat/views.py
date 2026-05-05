from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.pagination import PageNumberPagination
from django.db.models import Q, Max
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from drf_spectacular.utils import extend_schema, OpenApiParameter
from drf_spectacular.types import OpenApiTypes

from .models import ChatRoom, ChatMessage
from .serializers import (
    ChatRoomSerializer, ChatMessageSerializer,
    CreateChatRoomSerializer, SendMessageSerializer
)


class ChatPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100


class ChatRoomListCreateView(APIView):
    """
    API для получения списка чатов и создания нового чата
    """
    permission_classes = [IsAuthenticated]
    pagination_class = ChatPagination
    
    @extend_schema(
        summary="Получить список чатов",
        description="""
## Получить список всех чатов текущего пользователя

Возвращает список чат-комнат с:
- Участниками
- Последним сообщением
- Количеством непрочитанных сообщений
- Сортировка по последней активности

## Response:
```json
[
  {
    "id": 1,
    "participants": [...],
    "other_participant": {
      "id": 5,
      "full_name": "Алексей",
      "avatar": "..."
    },
    "last_message": {
      "text": "Привет! Как дела?",
      "created_at": "2026-01-31T10:00:00Z"
    },
    "unread_count": 3,
    "created_at": "2026-01-30T10:00:00Z"
  }
]
```
        """,
        tags=['Chat'],
        responses={
            200: ChatRoomSerializer(many=True),
            401: {'description': 'Не авторизован'}
        }
    )
    def get(self, request):
        """Получить список чатов"""
        rooms = ChatRoom.objects.filter(
            participants=request.user
        ).prefetch_related('participants', 'messages').distinct()
        
        # Применяем пагинацию
        paginator = self.pagination_class()
        page = paginator.paginate_queryset(rooms, request)
        if page is not None:
            serializer = ChatRoomSerializer(page, many=True, context={'request': request})
            return paginator.get_paginated_response(serializer.data)
        
        serializer = ChatRoomSerializer(rooms, many=True, context={'request': request})
        return Response(serializer.data)
    
    @extend_schema(
        summary="Создать новый чат",
        description="""
## Создать новую чат-комнату

Создает чат между текущим пользователем и указанным участником.
Если чат уже существует, возвращает существующий чат.

## Request Body:
```json
{
  "participant_id": 5
}
```

## Response:
```json
{
  "id": 1,
  "participants": [...],
  "other_participant": {...},
  "last_message": null,
  "unread_count": 0,
  "created_at": "2026-01-31T10:00:00Z"
}
```
        """,
        tags=['Chat'],
        request=CreateChatRoomSerializer,
        responses={
            201: ChatRoomSerializer,
            400: {'description': 'Ошибка валидации'},
            401: {'description': 'Не авторизован'}
        }
    )
    def post(self, request):
        """Создать новый чат"""
        serializer = CreateChatRoomSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        participant_id = serializer.validated_data['participant_id']
        
        # Проверяем, существует ли уже чат между этими пользователями
        existing_room = ChatRoom.objects.filter(
            participants=request.user
        ).filter(
            participants=participant_id
        ).first()
        
        if existing_room:
            result_serializer = ChatRoomSerializer(existing_room, context={'request': request})
            return Response(result_serializer.data, status=status.HTTP_200_OK)
        
        # Создаем новую комнату
        room = ChatRoom.objects.create(initiator=request.user)
        room.participants.add(request.user, participant_id)
        
        result_serializer = ChatRoomSerializer(room, context={'request': request})
        return Response(result_serializer.data, status=status.HTTP_201_CREATED)


class ChatRoomDetailView(APIView):
    """
    API для получения детальной информации о чате
    """
    permission_classes = [IsAuthenticated]
    
    @extend_schema(
        summary="Получить детали чата",
        description="Возвращает информацию о чат-комнате",
        tags=['Chat'],
        responses={
            200: ChatRoomSerializer,
            403: {'description': 'Нет доступа'},
            404: {'description': 'Чат не найден'}
        }
    )
    def get(self, request, room_id):
        """Получить детали чата"""
        try:
            room = ChatRoom.objects.get(id=room_id)
            
            # Проверяем доступ
            if not room.participants.filter(id=request.user.id).exists():
                return Response(
                    {'error': 'У вас нет доступа к этому чату'},
                    status=status.HTTP_403_FORBIDDEN
                )
            
            serializer = ChatRoomSerializer(room, context={'request': request})
            return Response(serializer.data)
        
        except ChatRoom.DoesNotExist:
            return Response(
                {'error': 'Чат не найден'},
                status=status.HTTP_404_NOT_FOUND
            )


class ChatMessagesView(APIView):
    """
    API для получения сообщений чата и отправки новых
    """
    permission_classes = [IsAuthenticated]
    pagination_class = ChatPagination
    
    @extend_schema(
        summary="Получить сообщения чата",
        description="""
## Получить историю сообщений чата

Возвращает список сообщений с поддержкой пагинации.

## Query Parameters:
- `page`: Номер страницы (default: 1)
- `page_size`: Количество сообщений на странице (default: 20, max: 100)

## Response:
```json
{
  "count": 150,
  "next": "...",
  "previous": "...",
  "results": [
    {
      "id": 1,
      "sender": {...},
      "message_type": "text",
      "text": "Привет!",
      "is_read": true,
      "created_at": "2026-01-31T10:00:00Z"
    }
  ]
}
```
        """,
        tags=['Chat'],
        responses={
            200: ChatMessageSerializer(many=True),
            403: {'description': 'Нет доступа'},
            404: {'description': 'Чат не найден'}
        }
    )
    def get(self, request, room_id):
        """Получить сообщения чата"""
        try:
            room = ChatRoom.objects.get(id=room_id)
            
            # Проверяем доступ
            if not room.participants.filter(id=request.user.id).exists():
                return Response(
                    {'error': 'У вас нет доступа к этому чату'},
                    status=status.HTTP_403_FORBIDDEN
                )
            
            messages = room.messages.select_related('sender').order_by('-created_at')
            
            # Применяем пагинацию
            paginator = self.pagination_class()
            page = paginator.paginate_queryset(messages, request)
            if page is not None:
                serializer = ChatMessageSerializer(page, many=True, context={'request': request})
                return paginator.get_paginated_response(serializer.data)
            
            serializer = ChatMessageSerializer(messages, many=True, context={'request': request})
            return Response(serializer.data)
        
        except ChatRoom.DoesNotExist:
            return Response(
                {'error': 'Чат не найден'},
                status=status.HTTP_404_NOT_FOUND
            )
    
    @extend_schema(
        summary="Отправить сообщение",
        description="""
## Отправить новое сообщение в чат

Поддерживаемые типы сообщений:
- `text`: Текстовое сообщение
- `image`: Изображение
- `file`: Файл
- `audio`: Аудио сообщение

## Request Body (FormData for files):
```
room: 1
message_type: "text"
text: "Привет!"
```

Or for image:
```
room: 1
message_type: "image"
image: <file>
```
        """,
        tags=['Chat'],
        request=SendMessageSerializer,
        responses={
            201: ChatMessageSerializer,
            400: {'description': 'Ошибка валидации'},
            403: {'description': 'Нет доступа'},
            404: {'description': 'Чат не найден'}
        }
    )
    def post(self, request, room_id):
        """Отправить сообщение"""
        try:
            room = ChatRoom.objects.get(id=room_id)
            
            # Проверяем доступ
            if not room.participants.filter(id=request.user.id).exists():
                return Response(
                    {'error': 'У вас нет доступа к этому чату'},
                    status=status.HTTP_403_FORBIDDEN
                )
            
            # Создаем сообщение
            data = request.data.copy()
            data['room'] = room.id
            
            serializer = SendMessageSerializer(data=data, context={'request': request})
            if not serializer.is_valid():
                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
            
            message = serializer.save(sender=request.user)
            
            # Обновляем время последнего обновления комнаты
            room.save()

            # WS broadcast (REST upload → realtime)
            try:
                channel_layer = get_channel_layer()
                payload = ChatMessageSerializer(message, context={'request': request}).data
                async_to_sync(channel_layer.group_send)(
                    f'chat_{room.id}',
                    {'type': 'chat_message', 'message': payload},
                )
            except Exception:
                pass
            
            result_serializer = ChatMessageSerializer(message, context={'request': request})
            return Response(result_serializer.data, status=status.HTTP_201_CREATED)
        
        except ChatRoom.DoesNotExist:
            return Response(
                {'error': 'Чат не найден'},
                status=status.HTTP_404_NOT_FOUND
            )


class MarkAsReadView(APIView):
    """
    API для отметки сообщений как прочитанных
    """
    permission_classes = [IsAuthenticated]
    
    @extend_schema(
        summary="Отметить сообщения как прочитанные",
        description="""
## Отметить все сообщения чата как прочитанные

Отмечает все непрочитанные сообщения в чате как прочитанные.
        """,
        tags=['Chat'],
        responses={
            200: {'description': 'Сообщения отмечены как прочитанные'},
            403: {'description': 'Нет доступа'},
            404: {'description': 'Чат не найден'}
        }
    )
    def post(self, request, room_id):
        """Отметить как прочитанное"""
        try:
            room = ChatRoom.objects.get(id=room_id)
            
            # Проверяем доступ
            if not room.participants.filter(id=request.user.id).exists():
                return Response(
                    {'error': 'У вас нет доступа к этому чату'},
                    status=status.HTTP_403_FORBIDDEN
                )
            
            # Отмечаем все сообщения как прочитанные (кроме своих)
            updated_count = room.messages.filter(
                is_read=False
            ).exclude(
                sender=request.user
            ).update(is_read=True)
            
            return Response({
                'message': f'{updated_count} сообщений отмечено как прочитанные'
            })
        
        except ChatRoom.DoesNotExist:
            return Response(
                {'error': 'Чат не найден'},
                status=status.HTTP_404_NOT_FOUND
            )
