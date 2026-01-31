# 💬 Real-Time Chat System

Django Channels bilan real-time chat sistema - text, image, file, audio qo'llab-quvvatlaydi.

## 🚀 Features

✅ Real-time messaging (WebSocket)
✅ Text messages
✅ Image uploads
✅ File uploads
✅ Audio messages
✅ Read receipts
✅ Typing indicators
✅ User-to-user private chats

## 📋 API Endpoints

### REST API (HTTP)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/chat/rooms/` | Barcha chat roomlar ro'yxati |
| POST | `/api/chat/rooms/` | Yangi chat room yaratish |
| GET | `/api/chat/rooms/{id}/` | Chat room detali |
| GET | `/api/chat/rooms/{id}/messages/` | Chat messagelar ro'yxati |
| POST | `/api/chat/rooms/{id}/messages/` | Yangi message yuborish |
| POST | `/api/chat/rooms/{id}/mark-read/` | Messagelarni o'qilgan deb belgilash |

### WebSocket

**URL:** `ws://localhost:8000/ws/chat/{room_id}/?token={YOUR_JWT_TOKEN}`

**Connection:**
```javascript
const token = "your_jwt_access_token_here";
const roomId = 1;
const socket = new WebSocket(`ws://localhost:8000/ws/chat/${roomId}/?token=${token}`);
```

**Authentication:**
- WebSocket token orqali authenticate qiladi
- Token query parameter sifatida yuboriladi: `?token=YOUR_JWT_TOKEN`
- Token noto'g'ri yoki yo'q bo'lsa, connection yopiladi

## 🔄 REST API Usage

### 1️⃣ Yangi Chat Room yaratish

```bash
POST /api/chat/rooms/
Authorization: Bearer YOUR_TOKEN
Content-Type: application/json

{
  "participant_id": 5
}
```

**Response:**
```json
{
  "id": 1,
  "participants": [
    {"id": 1, "full_name": "Ivan", "email": "ivan@example.com"},
    {"id": 5, "full_name": "Alex", "email": "alex@example.com"}
  ],
  "other_participant": {...},
  "last_message": null,
  "unread_count": 0,
  "created_at": "2026-01-31T10:00:00Z"
}
```

### 2️⃣ Chat Rooms ro'yxati

```bash
GET /api/chat/rooms/
Authorization: Bearer YOUR_TOKEN
```

**Response:** Barcha chat roomlar (oxirgi message bilan)

### 3️⃣ Message yuborish (Text)

```bash
POST /api/chat/rooms/1/messages/
Authorization: Bearer YOUR_TOKEN
Content-Type: application/json

{
  "message_type": "text",
  "text": "Salom! Qalaysiz?"
}
```

### 4️⃣ Rasm yuborish

```bash
POST /api/chat/rooms/1/messages/
Authorization: Bearer YOUR_TOKEN
Content-Type: multipart/form-data

message_type: image
image: <file>
```

### 5️⃣ Audio yuborish

```bash
POST /api/chat/rooms/1/messages/
Authorization: Bearer YOUR_TOKEN
Content-Type: multipart/form-data

message_type: audio
audio: <file>
```

### 6️⃣ File yuborish

```bash
POST /api/chat/rooms/1/messages/
Authorization: Bearer YOUR_TOKEN
Content-Type: multipart/form-data

message_type: file
file: <file>
```

## 📡 WebSocket Usage

### Connect to WebSocket

```javascript
const roomId = 1;
const token = 'YOUR_JWT_ACCESS_TOKEN';
const socket = new WebSocket(`ws://localhost:8000/ws/chat/${roomId}/?token=${token}`);

socket.onopen = () => {
  console.log('✅ Connected to chat');
};

socket.onmessage = (event) => {
  const data = JSON.parse(event.data);
  console.log('📩 Received:', data);
  
  // Handle different message types
  switch(data.type) {
    case 'connection_established':
      console.log('🔌 Connection confirmed');
      break;
    case 'chat_message':
      console.log('💬 New message:', data.message);
      break;
    case 'typing_indicator':
      console.log('✏️ User is typing...');
      break;
    case 'read_receipt':
      console.log('✔️ Message read');
      break;
  }
};

socket.onerror = (error) => {
  console.error('❌ WebSocket error:', error);
};

socket.onclose = (event) => {
  console.log('🔌 Connection closed:', event.code, event.reason);
};
```

### Send Text Message

```javascript
socket.send(JSON.stringify({
  type: 'chat_message',
  message_type: 'text',
  text: 'Salom!'
}));
```

### Typing Indicator

```javascript
// Start typing
socket.send(JSON.stringify({
  type: 'typing',
  is_typing: true
}));

// Stop typing
socket.send(JSON.stringify({
  type: 'typing',
  is_typing: false
}));
```

### Read Receipt

```javascript
socket.send(JSON.stringify({
  type: 'read_receipt',
  message_id: 123
}));
```

## 📊 Message Types

| Type | Field | Description |
|------|-------|-------------|
| `text` | `text` | Oddiy text xabar |
| `image` | `image` | Rasm (jpg, png, gif) |
| `file` | `file` | Har qanday file |
| `audio` | `audio` | Audio xabar (mp3, ogg, m4a) |

## 🧪 Test Examples

### Curl - Yangi chat yaratish

```bash
curl -X POST "http://localhost:8000/api/chat/rooms/" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"participant_id": 5}'
```

### Curl - Text message yuborish

```bash
curl -X POST "http://localhost:8000/api/chat/rooms/1/messages/" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "message_type": "text",
    "text": "Salom! Qalaysiz?"
  }'
```

### Curl - Rasm yuborish

```bash
curl -X POST "http://localhost:8000/api/chat/rooms/1/messages/" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -F "message_type=image" \
  -F "image=@/path/to/image.jpg"
```

## 🌐 WebSocket Events

### Incoming (Server → Client)

#### `connection_established`
```json
{
  "type": "connection_established",
  "message": "Successfully connected to chat"
}
```

#### `chat_message`
```json
{
  "type": "chat_message",
  "message": {
    "id": 1,
    "sender": {...},
    "message_type": "text",
    "text": "Salom!",
    "created_at": "2026-01-31T10:00:00Z"
  }
}
```

#### `typing`
```json
{
  "type": "typing",
  "user_id": 5,
  "is_typing": true
}
```

#### `read_receipt`
```json
{
  "type": "read_receipt",
  "message_id": 123,
  "user_id": 5
}
```

### Outgoing (Client → Server)

#### Send Message
```json
{
  "type": "chat_message",
  "message_type": "text",
  "text": "Your message here"
}
```

#### Typing Indicator
```json
{
  "type": "typing",
  "is_typing": true
}
```

#### Read Receipt
```json
{
  "type": "read_receipt",
  "message_id": 123
}
```

## 🔐 Authentication

### WebSocket Authentication

WebSocket'lar uchun JWT token query parameter orqali yuboriladi:

**Format:**
```
ws://localhost:8000/ws/chat/{room_id}/?token={YOUR_JWT_ACCESS_TOKEN}
```

**Qanday ishlaydi:**
1. ✅ Client WebSocket connection ochganda `?token=...` yuboradi
2. ✅ Server token'ni validate qiladi (JWT)
3. ✅ Token to'g'ri bo'lsa - connection accept qilinadi
4. ❌ Token noto'g'ri yoki yo'q bo'lsa - connection yopiladi

**Token olish:**
```bash
POST /api/accounts/login/
Content-Type: application/json

{
  "phone_number": "+998901234567",
  "password": "yourpassword"
}
```

**Response:**
```json
{
  "access": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "refresh": "eyJ0eXAiOiJKV1QiLCJhbGc..."
}
```

Ushbu `access` token'ni WebSocket URL'da ishlatish kerak.

## 🎯 Mobile App Integration

### React Native Example

```javascript
import { WebSocket } from 'react-native';
import AsyncStorage from '@react-native-async-storage/async-storage';

// Get JWT token from storage
const token = await AsyncStorage.getItem('access_token');
const roomId = 1;

const chatSocket = new WebSocket(
  `ws://31.128.43.149:6060/ws/chat/${roomId}/?token=${token}`
);

chatSocket.onopen = () => {
  console.log('✅ Connected to chat');
};

chatSocket.onmessage = (e) => {
  const data = JSON.parse(e.data);
  
  if (data.type === 'connection_established') {
    console.log('🔌 Connection confirmed');
  }
  
  if (data.type === 'chat_message') {
    // Add message to UI
    addMessageToChat(data.message);
  }
  
  if (data.type === 'typing') {
    // Show typing indicator
    setIsTyping(data.is_typing);
  }
};

chatSocket.onerror = (error) => {
  console.error('❌ WebSocket error:', error);
};

chatSocket.onclose = () => {
  console.log('🔌 Connection closed');
};

// Send message
const sendMessage = (text) => {
  chatSocket.send(JSON.stringify({
    type: 'chat_message',
    message_type: 'text',
    text: text
  }));
};

// Send typing indicator
const sendTyping = (isTyping) => {
  chatSocket.send(JSON.stringify({
    type: 'typing',
    is_typing: isTyping
  }));
};
```

### Flutter Example

```dart
import 'package:web_socket_channel/web_socket_channel.dart';

final token = await storage.read(key: 'access_token');
final roomId = 1;

final channel = WebSocketChannel.connect(
  Uri.parse('ws://31.128.43.149:6060/ws/chat/$roomId/?token=$token'),
);

// Listen to messages
channel.stream.listen((message) {
  final data = jsonDecode(message);
  
  if (data['type'] == 'chat_message') {
    // Handle new message
    print('New message: ${data['message']['text']}');
  }
});

// Send message
void sendMessage(String text) {
  channel.sink.add(jsonEncode({
    'type': 'chat_message',
    'message_type': 'text',
    'text': text,
  }));
}
```

## 🌐 Server URLs

### Development
- **REST API:** `http://localhost:8000/api/chat/`
- **WebSocket:** `ws://localhost:8000/ws/chat/{room_id}/?token={token}`
- **Swagger:** `http://localhost:8000/api/schema/swagger-ui/`

### Production
- **REST API:** `http://31.128.43.149:6060/api/chat/`
- **WebSocket:** `ws://31.128.43.149:6060/ws/chat/{room_id}/?token={token}`
- **Swagger:** `http://31.128.43.149:6060/api/schema/swagger-ui/`

## 📚 Swagger Documentation

Swagger'da "Chat" tag'ida barcha REST API'lar dokumentatsiya bilan mavjud:
```
http://localhost:8000/api/schema/swagger-ui/
```

**Chat endpoints:**
- `GET /api/chat/rooms/` - Chat roomlar ro'yxati
- `POST /api/chat/rooms/` - Yangi chat yaratish
- `GET /api/chat/rooms/{id}/` - Chat detali
- `GET /api/chat/rooms/{id}/messages/` - Messagelar ro'yxati
- `POST /api/chat/rooms/{id}/messages/` - Message yuborish
- `POST /api/chat/rooms/{id}/mark-read/` - O'qilgan belgilash

## 🚀 Running

### Development
```bash
python manage.py runserver
```

Server ASGI mode'da ishga tushadi (Daphne bilan).

### Production (Daphne)
```bash
daphne -b 0.0.0.0 -p 8000 config.asgi:application
```

## 📁 Models

### ChatRoom
- `participants` (ManyToMany) - Chat ishtirokchilari
- `created_at` - Yaratilgan vaqti
- `updated_at` - Oxirgi yangilangan vaqti

### ChatMessage
- `room` (ForeignKey) - Chat room
- `sender` (ForeignKey) - Yuboruvchi
- `message_type` - text/image/file/audio
- `text` - Text xabar
- `image` - Rasm
- `file` - File
- `audio` - Audio
- `is_read` - O'qilganmi
- `created_at` - Yuborilgan vaqti

## ⚡ Performance Tips

- WebSocket'lar uchun InMemoryChannelLayer ishlatiladi
- Production uchun Redis Channel Layer tavsiya etiladi
- Message'lar pagination bilan yuboriladi
- Barcha querylar optimized (select_related, prefetch_related)
