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

**Authentication:**
- WebSocket token orqali authenticate qiladi
- Token query parameter sifatida yuboriladi: `?token=YOUR_JWT_TOKEN`
- Token noto'g'ri yoki yo'q bo'lsa, connection yopiladi

---

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

### 5️⃣ File yuborish

```bash
POST /api/chat/rooms/1/messages/
Authorization: Bearer YOUR_TOKEN
Content-Type: multipart/form-data

message_type: file
file: <file>
```

---

## 📡 WebSocket Message Formats

### ⚠️ IMPORTANT: File/Image/Audio yuborish

WebSocket orqali **to'g'ridan-to'g'ri file yuborish MUMKIN EMAS!**

File, image va audio yuborish uchun **REST API** ishlatish kerak.

---

### 📤 Text Message (WebSocket)

**Send:**
```json
{
  "type": "chat_message",
  "message_type": "text",
  "text": "Salom! Qalaysiz?"
}
```

**Response (from server):**
```json
{
  "type": "chat_message",
  "message": {
    "id": 1,
    "sender": {
      "id": 3,
      "full_name": "Ivan Petrov",
      "email": "ivan@example.com",
      "avatar": "http://localhost:8000/media/avatars/user.jpg"
    },
    "message_type": "text",
    "text": "Salom! Qalaysiz?",
    "image_url": null,
    "file_url": null,
    "audio_url": null,
    "is_read": false,
    "created_at": "2026-01-31T10:00:00Z"
  }
}
```

---

### ✏️ Typing Indicator (WebSocket)

**Start typing:**
```json
{
  "type": "typing",
  "is_typing": true
}
```

**Stop typing:**
```json
{
  "type": "typing",
  "is_typing": false
}
```

**Response:**
```json
{
  "type": "typing",
  "user_id": 5,
  "is_typing": true
}
```

---

### ✔️ Read Receipt (WebSocket)

**Send:**
```json
{
  "type": "read_receipt",
  "message_id": 123
}
```

**Response:**
```json
{
  "type": "read_receipt",
  "message_id": 123,
  "user_id": 3
}
```

---

## 📤 REST API File Uploads

### Image Upload

```http
POST /api/chat/rooms/{room_id}/messages/
Authorization: Bearer YOUR_TOKEN
Content-Type: multipart/form-data

message_type: image
image: <binary file>
```

**Response:**
```json
{
  "id": 2,
  "room": 1,
  "sender": {
    "id": 3,
    "full_name": "Ivan Petrov",
    "email": "ivan@example.com",
    "avatar": "http://localhost:8000/media/avatars/user.jpg"
  },
  "message_type": "image",
  "text": null,
  "image_url": "http://localhost:8000/media/chat/images/image_abc123.jpg",
  "file_url": null,
  "audio_url": null,
  "is_read": false,
  "created_at": "2026-01-31T10:05:00Z"
}
```

---

### File Upload

```http
POST /api/chat/rooms/{room_id}/messages/
Authorization: Bearer YOUR_TOKEN
Content-Type: multipart/form-data

message_type: file
file: <binary file>
```

**Response:**
```json
{
  "id": 3,
  "message_type": "file",
  "file_url": "http://localhost:8000/media/chat/files/document_xyz789.pdf",
  ...
}
```

---

### Audio Upload

```http
POST /api/chat/rooms/{room_id}/messages/
Authorization: Bearer YOUR_TOKEN
Content-Type: multipart/form-data

message_type: audio
audio: <binary file>
```

**Response:**
```json
{
  "id": 4,
  "message_type": "audio",
  "audio_url": "http://localhost:8000/media/chat/audio/voice_def456.m4a",
  ...
}
```

---

## 🧪 Curl Test Examples

### Yangi chat yaratish

```bash
curl -X POST "http://localhost:8000/api/chat/rooms/" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"participant_id": 5}'
```

### Text message yuborish

```bash
curl -X POST "http://localhost:8000/api/chat/rooms/1/messages/" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "message_type": "text",
    "text": "Salom! Qalaysiz?"
  }'
```

### Rasm yuborish

```bash
curl -X POST "http://localhost:8000/api/chat/rooms/1/messages/" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -F "message_type=image" \
  -F "image=@/path/to/image.jpg"
```

### File yuborish

```bash
curl -X POST "http://localhost:8000/api/chat/rooms/1/messages/" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -F "message_type=file" \
  -F "file=@/path/to/document.pdf"
```

### Audio yuborish

```bash
curl -X POST "http://localhost:8000/api/chat/rooms/1/messages/" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -F "message_type=audio" \
  -F "audio=@/path/to/voice.m4a"
```

---

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

---

### Outgoing (Client → Server)

#### Send Text Message
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

---

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

---

## 📱 Flutter Integration Example

### WebSocket Connection

```dart
import 'package:web_socket_channel/web_socket_channel.dart';
import 'dart:convert';

final token = await storage.read(key: 'access_token');
final roomId = 1;

final channel = WebSocketChannel.connect(
  Uri.parse('ws://31.128.43.149:6060/ws/chat/$roomId/?token=$token'),
);

// Listen to messages
channel.stream.listen((message) {
  final data = jsonDecode(message);
  
  if (data['type'] == 'chat_message') {
    print('New message: ${data['message']['text']}');
  }
  
  if (data['type'] == 'typing') {
    print('User is typing: ${data['is_typing']}');
  }
});

// Send text message
void sendMessage(String text) {
  channel.sink.add(jsonEncode({
    'type': 'chat_message',
    'message_type': 'text',
    'text': text,
  }));
}

// Send typing indicator
void sendTyping(bool isTyping) {
  channel.sink.add(jsonEncode({
    'type': 'typing',
    'is_typing': isTyping,
  }));
}
```

---

### File/Image/Audio Upload (REST API)

```dart
import 'package:http/http.dart' as http;
import 'package:image_picker/image_picker.dart';
import 'package:file_picker/file_picker.dart';
import 'dart:io';

// Send Image
Future<void> sendImage(File imageFile, int roomId) async {
  final token = await storage.read(key: 'access_token');
  final uri = Uri.parse('http://31.128.43.149:6060/api/chat/rooms/$roomId/messages/');
  
  var request = http.MultipartRequest('POST', uri);
  request.headers['Authorization'] = 'Bearer $token';
  request.fields['message_type'] = 'image';
  request.files.add(await http.MultipartFile.fromPath('image', imageFile.path));
  
  try {
    var response = await request.send();
    if (response.statusCode == 201) {
      print('✅ Image sent successfully');
      // WebSocket'dan notification keladi avtomatik
    }
  } catch (e) {
    print('❌ Error: $e');
  }
}

// Send File
Future<void> sendFile(File file, int roomId) async {
  final token = await storage.read(key: 'access_token');
  final uri = Uri.parse('http://31.128.43.149:6060/api/chat/rooms/$roomId/messages/');
  
  var request = http.MultipartRequest('POST', uri);
  request.headers['Authorization'] = 'Bearer $token';
  request.fields['message_type'] = 'file';
  request.files.add(await http.MultipartFile.fromPath('file', file.path));
  
  var response = await request.send();
}

// Send Audio
Future<void> sendAudio(File audioFile, int roomId) async {
  final token = await storage.read(key: 'access_token');
  final uri = Uri.parse('http://31.128.43.149:6060/api/chat/rooms/$roomId/messages/');
  
  var request = http.MultipartRequest('POST', uri);
  request.headers['Authorization'] = 'Bearer $token';
  request.fields['message_type'] = 'audio';
  request.files.add(await http.MultipartFile.fromPath('audio', audioFile.path));
  
  var response = await request.send();
}
```

---

### Image Picker

```dart
import 'package:image_picker/image_picker.dart';

Future<void> pickAndSendImage(int roomId) async {
  final picker = ImagePicker();
  final XFile? image = await picker.pickImage(
    source: ImageSource.gallery,
    imageQuality: 80,
  );
  
  if (image != null) {
    await sendImage(File(image.path), roomId);
  }
}
```

---

### File Picker

```dart
import 'package:file_picker/file_picker.dart';

Future<void> pickAndSendFile(int roomId) async {
  FilePickerResult? result = await FilePicker.platform.pickFiles();
  
  if (result != null) {
    File file = File(result.files.single.path!);
    await sendFile(file, roomId);
  }
}
```

---

### Audio Recorder

```dart
import 'package:record/record.dart';

final record = Record();

Future<void> startRecording() async {
  if (await record.hasPermission()) {
    await record.start(
      path: 'audio_message.m4a',
      encoder: AudioEncoder.aacLc,
    );
  }
}

Future<void> stopAndSendRecording(int roomId) async {
  String? path = await record.stop();
  if (path != null) {
    await sendAudio(File(path), roomId);
  }
}
```

---

## 📋 Message Types Comparison

| Type | WebSocket | REST API | Tavsiya |
|------|-----------|----------|---------|
| **Text** | ✅ JSON format | ✅ POST + JSON | **WebSocket** (tezroq) |
| **Image** | ❌ | ✅ `multipart/form-data` | **REST API** |
| **File** | ❌ | ✅ `multipart/form-data` | **REST API** |
| **Audio** | ❌ | ✅ `multipart/form-data` | **REST API** |

---

## 🌐 Server URLs

### Development
- **REST API:** `http://localhost:8000/api/chat/`
- **WebSocket:** `ws://localhost:8000/ws/chat/{room_id}/?token={token}`
- **Swagger:** `http://localhost:8000/api/schema/swagger-ui/`

### Production
- **REST API:** `http://31.128.43.149:6060/api/chat/`
- **WebSocket:** `ws://31.128.43.149:6060/ws/chat/{room_id}/?token={token}`
- **Swagger:** `http://31.128.43.149:6060/api/schema/swagger-ui/`

---

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

---

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

---

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

---

## ⚡ Performance Tips

- WebSocket'lar uchun InMemoryChannelLayer ishlatiladi
- Production uchun Redis Channel Layer tavsiya etiladi
- Message'lar pagination bilan yuboriladi
- Barcha querylar optimized (select_related, prefetch_related)

---

## 📋 JSON Format Quick Reference

### Text Message (WebSocket)
```json
{
  "type": "chat_message",
  "message_type": "text",
  "text": "Salom!"
}
```

### Typing Indicator (WebSocket)
```json
{
  "type": "typing",
  "is_typing": true
}
```

### Read Receipt (WebSocket)
```json
{
  "type": "read_receipt",
  "message_id": 123
}
```

### Image Upload (REST API)
```http
POST /api/chat/rooms/{room_id}/messages/
Content-Type: multipart/form-data

message_type: image
image: <binary file>
```

### File Upload (REST API)
```http
POST /api/chat/rooms/{room_id}/messages/
Content-Type: multipart/form-data

message_type: file
file: <binary file>
```

### Audio Upload (REST API)
```http
POST /api/chat/rooms/{room_id}/messages/
Content-Type: multipart/form-data

message_type: audio
audio: <binary file>
```

---

## 🎯 Key Points

1. ✅ **Text messages** → WebSocket (tezroq, real-time)
2. ✅ **Image/File/Audio** → REST API (multipart/form-data)
3. ✅ WebSocket faqat real-time notifications uchun
4. ✅ Token query parameter orqali yuboriladi: `?token=...`
5. ✅ Har qanday message yuborilgandan keyin WebSocket'dan notification keladi

---

## 📞 Support

Swagger documentation: `http://localhost:8000/api/schema/swagger-ui/`

Tag: **Chat**
