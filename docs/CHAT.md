# Chat (REST + WebSocket) — dokumentatsiya

Bu hujjat `CheckAvto` loyihasidagi chat qanday **ochilishi**, **WS/REST** orqali qanday ishlashi, va `sender_type` qanday hisoblanishini tushuntiradi.

## 1) Как запустить (локально)

Убедитесь, что запускаете именно **ASGI**, а не WSGI.

### Вариант A (рекомендуется): Daphne

```bash
py manage.py runserver 8002
```

Если у вас настроен Daphne/Channels, `runserver` поднимет ASGI (в логах будет упоминание Daphne).

### Вариант B: явный Daphne

```bash
daphne -b 0.0.0.0 -p 8002 config.asgi:application
```

## 2) Room qachon yaratiladi va `room_id`

Chatning asosiy entitisi — `ChatRoom` (ID = `ChatRoom.id`).

### 2.1 Order accept bo‘lganda avtomatik

`POST /api/order/<order_id>/accept/` dan keyin backend:
- `initiator` = master user
- `participants` = master user + order.user
- `order.chat_room = room` qilib bog‘laydi

Order details (`GET /api/order/<id>/`) javobida:
- **`room_id`** chiqadi (bu `order.chat_room_id`, ya’ni `ChatRoom.id`)

### 2.2 Manual (REST)

`POST /api/chat/rooms/` body:

```json
{ "participant_id": 5 }
```

## 3) REST endpoints (chat)

Chat REST router: `apps/chat/urls.py`

- **Rooms list/create**:
  - `GET /api/chat/rooms/`
  - `POST /api/chat/rooms/` body: `{ "participant_id": <user_id> }`
- **Room detail**:
  - `GET /api/chat/rooms/<room_id>/`
- **Messages (history + send multipart)**:
  - `GET /api/chat/rooms/<room_id>/messages/` (paginatsiya: `page`, `page_size`)
  - `POST /api/chat/rooms/<room_id>/messages/` (multipart/form-data: `message_type`, `text`, `file|image|audio`)
- **Mark read**:
  - `POST /api/chat/rooms/<room_id>/mark-read/`

## 3) WebSocket URL (aniq)

`apps/chat/routing.py` bo‘yicha aniq path:

```text
ws://<host>/ws/chat/<room_id>/
```

Пример (локально):

```text
ws://127.0.0.1:8002/ws/chat/<room_id>/
```

## 4) WebSocket auth (JWT)

Bizda `config/asgi.py` ichida `TokenAuthMiddleware` turibdi, shuning uchun WS token query orqali beriladi:

```text
ws://<host>/ws/chat/<room_id>/?token=<JWT>
```

## 4.1 WS close code’lar

`apps/chat/consumers.py` (`ChatConsumer.connect()`):
- **4001** — token yo‘q yoki token noto‘g‘ri (user anonymous)
- **4003** — user shu room participant emas (access denied)

## 5) WS payload format (`apps/chat/consumers.py`)

### 5.1 Connect response (server → client)

```json
{
  "type": "connection_established",
  "message": "Successfully connected to chat"
}
```

### 5.2 Yuborish (client → server)

```json
{
  "type": "chat_message",
  "message_type": "text",
  "text": "Salom, yo‘ldaman."
}
```

### 5.2.1 WS orqali base64 attachment yuborish

Image:

```json
{
  "type": "chat_message",
  "message_type": "image",
  "text": "caption (optional)",
  "image_name": "1.jpg",
  "image_base64": "<BASE64 yoki data:image/...;base64,...>"
}
```

File:

```json
{
  "type": "chat_message",
  "message_type": "file",
  "file_name": "doc.pdf",
  "file_base64": "<BASE64>"
}
```

Audio:

```json
{
  "type": "chat_message",
  "message_type": "audio",
  "audio_name": "voice.mp3",
  "audio_base64": "<BASE64>"
}
```

### 5.2.2 Gallery (batch images)

```json
{
  "type": "chat_message",
  "message_type": "image",
  "text": "caption (optional)",
  "images": [
    { "name": "1.jpg", "base64": "<BASE64>" },
    { "name": "2.jpg", "base64": "<BASE64>" }
  ]
}
```

Server event:

```json
{ "type": "chat_message_batch", "messages": [ { "...": "..." }, { "...": "..." } ] }
```

### 5.2.3 REST upload → WS broadcast (`message_id`)

Agar attachment’ni REST bilan yuborsangiz:
- `POST /api/chat/rooms/<room_id>/messages/` (multipart)

Backend message’ni DBga yozadi va **o‘zi WS’ga ham broadcast qiladi**.

Qo‘shimcha variant: agar REST response’dan `id` olib WS’da broadcast qilmoqchi bo‘lsangiz:

```json
{ "type": "chat_message", "message_id": 555 }
```

### 5.3 Keladigan message (server → client)

```json
{
  "type": "chat_message",
  "message": {
    "id": 123,
    "room_id": 15,
    "sender": {
      "id": 4,
      "full_name": "Master Name",
      "email": "master@example.com",
      "avatar": "/media/avatars/a.png"
    },
    "sender_type": "initiator",
    "message_type": "text",
    "text": "Salom, yo‘ldaman.",
    "file": null,
    "image": null,
    "audio": null,
    "is_read": false,
    "created_at": "2026-05-05T12:22:00+00:00"
  }
}
```

`sender_type` ma’nosi (asosiy qoida):
- `initiator` — **current user** (shu WS ulanish egasi) yuborgan message (“men yubordim”)
- `receiver` — boshqa participant yuborgan message (“u yubordi”)

### 5.4 Typing (client → server) / (server → client)

```json
{ "type": "typing", "is_typing": true }
```

Server boshqalarga shunday yuboradi:

```json
{ "type": "typing", "user_id": 4, "is_typing": true }
```

### 5.5 Read receipt (client → server)

```json
{ "type": "read_receipt", "message_id": 123 }
```

Server event:

```json
{ "type": "read_receipt", "message_id": 123, "user_id": 8 }
```

## 6) Частые проблемы

- **Поднят WSGI вместо ASGI**: WebSocket не работает вообще. Запускайте через ASGI (Daphne/Channels).
- **CORS/Origin**: если клиент — web, проверьте `AllowedHosts` и настройки origin для WS (если есть).
- **Redis**: если используете channel layer через Redis, он должен быть запущен.

## 7) End-to-end (mobil uchun qisqa flow)

### 7.1 Order’dan chatga kirish
- `GET /api/order/<id>/` → `room_id` oling
- WS connect:
  - `ws://<host>/ws/chat/<room_id>/?token=<JWT>`

### 7.2 History olish
- `GET /api/chat/rooms/<room_id>/messages/`

### 7.3 Yuborish
- Text (WS): `type=chat_message`, `message_type=text`
- Attachment:
  - WS base64 (image/file/audio) **yoki**
  - REST multipart `POST /api/chat/rooms/<room_id>/messages/` (backend o‘zi WS’ga broadcast qiladi)

