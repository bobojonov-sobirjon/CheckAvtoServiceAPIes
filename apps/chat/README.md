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
  text: 'Salom! Qalaysiz?'
}));
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
    "text_url": null,
    "image_url": null,
    "file_url": null,
    "audio_url": null,
    "is_read": false,
    "created_at": "2026-01-31T10:00:00Z"
  }
}
```

---

### ⚠️ **IMPORTANT: File/Image/Audio yuborish**

WebSocket orqali **to'g'ridan-to'g'ri file yuborish MUMKIN EMAS!**

File, image va audio yuborish uchun **REST API** ishlatish kerak:

#### **1️⃣ REST API orqali file yuborish (tavsiya etiladi):**

```bash
POST /api/chat/rooms/{room_id}/messages/
Authorization: Bearer YOUR_TOKEN
Content-Type: multipart/form-data

message_type: image
image: <file>
```

**WebSocket orqali faqat notification olinadi.**

---

#### **2️⃣ Base64 orqali file yuborish (kichik fayllar uchun):**

**⚠️ Warning:** Katta fayllar uchun tavsiya etilmaydi! Faqat kichik icon, emoji uchun.

**Send Image (Base64):**
```javascript
// 1. Image'ni Base64'ga convert qiling
const fileInput = document.getElementById('imageInput');
const file = fileInput.files[0];

const reader = new FileReader();
reader.onload = (e) => {
  const base64Data = e.target.result; // data:image/png;base64,...
  
  // 2. WebSocket orqali yuboring
  socket.send(JSON.stringify({
    type: 'chat_message',
    message_type: 'image',
    image_base64: base64Data,
    filename: file.name
  }));
};
reader.readAsDataURL(file);
```

**Send File (Base64):**
```javascript
const fileInput = document.getElementById('fileInput');
const file = fileInput.files[0];

const reader = new FileReader();
reader.onload = (e) => {
  const base64Data = e.target.result;
  
  socket.send(JSON.stringify({
    type: 'chat_message',
    message_type: 'file',
    file_base64: base64Data,
    filename: file.name
  }));
};
reader.readAsDataURL(file);
```

**Send Audio (Base64):**
```javascript
const audioInput = document.getElementById('audioInput');
const audioFile = audioInput.files[0];

const reader = new FileReader();
reader.onload = (e) => {
  const base64Data = e.target.result;
  
  socket.send(JSON.stringify({
    type: 'chat_message',
    message_type: 'audio',
    audio_base64: base64Data,
    filename: audioFile.name
  }));
};
reader.readAsDataURL(audioFile);
```

**Response:**
```json
{
  "type": "chat_message",
  "message": {
    "id": 2,
    "sender": {...},
    "message_type": "image",
    "text": null,
    "image_url": "http://localhost:8000/media/chat/images/photo_123.jpg",
    "file_url": null,
    "audio_url": null,
    "created_at": "2026-01-31T10:05:00Z"
  }
}
```

---

### 📤 **REST API orqali yuborish (tavsiya etiladi)**

WebSocket o'rniga REST API ishlatish yaxshiroq:

**Image yuborish:**
```javascript
const formData = new FormData();
formData.append('message_type', 'image');
formData.append('image', imageFile);

fetch(`http://localhost:8000/api/chat/rooms/${roomId}/messages/`, {
  method: 'POST',
  headers: {
    'Authorization': `Bearer ${token}`
  },
  body: formData
})
.then(res => res.json())
.then(data => {
  console.log('✅ Image uploaded:', data);
  // WebSocket'dan notification keladi
});
```

**File yuborish:**
```javascript
const formData = new FormData();
formData.append('message_type', 'file');
formData.append('file', pdfFile);

fetch(`http://localhost:8000/api/chat/rooms/${roomId}/messages/`, {
  method: 'POST',
  headers: {
    'Authorization': `Bearer ${token}`
  },
  body: formData
});
```

**Audio yuborish:**
```javascript
const formData = new FormData();
formData.append('message_type', 'audio');
formData.append('audio', audioFile);

fetch(`http://localhost:8000/api/chat/rooms/${roomId}/messages/`, {
  method: 'POST',
  headers: {
    'Authorization': `Bearer ${token}`
  },
  body: formData
});
```

---

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

**Response:**
```json
{
  "type": "typing",
  "user_id": 5,
  "is_typing": true
}
```

---

### Read Receipt

```javascript
socket.send(JSON.stringify({
  type: 'read_receipt',
  message_id: 123
}));
```

**Response:**
```json
{
  "type": "read_receipt",
  "message_id": 123,
  "user_id": 3
}
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
  "text_url": null,
  "image_url": "http://localhost:8000/media/chat/images/image_abc123.jpg",
  "file_url": null,
  "audio_url": null,
  "is_read": false,
  "created_at": "2026-01-31T10:05:00Z"
}
```

### Curl - File yuborish

```bash
curl -X POST "http://localhost:8000/api/chat/rooms/1/messages/" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -F "message_type=file" \
  -F "file=@/path/to/document.pdf"
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

### Curl - Audio yuborish

```bash
curl -X POST "http://localhost:8000/api/chat/rooms/1/messages/" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -F "message_type=audio" \
  -F "audio=@/path/to/voice.m4a"
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

// ========================================
// 📤 FILE/IMAGE/AUDIO YUBORISH (REST API)
// ========================================

// Send Image
const sendImage = async (imageUri) => {
  const token = await AsyncStorage.getItem('access_token');
  const formData = new FormData();
  
  formData.append('message_type', 'image');
  formData.append('image', {
    uri: imageUri,
    type: 'image/jpeg',
    name: 'photo.jpg',
  });
  
  try {
    const response = await fetch(
      `http://31.128.43.149:6060/api/chat/rooms/${roomId}/messages/`,
      {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
        },
        body: formData,
      }
    );
    
    const data = await response.json();
    console.log('✅ Image sent:', data);
    // WebSocket'dan notification keladi avtomatik
    
  } catch (error) {
    console.error('❌ Error sending image:', error);
  }
};

// Send File
const sendFile = async (fileUri, fileName) => {
  const token = await AsyncStorage.getItem('access_token');
  const formData = new FormData();
  
  formData.append('message_type', 'file');
  formData.append('file', {
    uri: fileUri,
    type: 'application/pdf', // yoki boshqa file type
    name: fileName,
  });
  
  try {
    const response = await fetch(
      `http://31.128.43.149:6060/api/chat/rooms/${roomId}/messages/`,
      {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
        },
        body: formData,
      }
    );
    
    const data = await response.json();
    console.log('✅ File sent:', data);
    
  } catch (error) {
    console.error('❌ Error sending file:', error);
  }
};

// Send Audio
const sendAudio = async (audioUri) => {
  const token = await AsyncStorage.getItem('access_token');
  const formData = new FormData();
  
  formData.append('message_type', 'audio');
  formData.append('audio', {
    uri: audioUri,
    type: 'audio/mp4', // yoki audio/mpeg
    name: 'voice.m4a',
  });
  
  try {
    const response = await fetch(
      `http://31.128.43.149:6060/api/chat/rooms/${roomId}/messages/`,
      {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
        },
        body: formData,
      }
    );
    
    const data = await response.json();
    console.log('✅ Audio sent:', data);
    
  } catch (error) {
    console.error('❌ Error sending audio:', error);
  }
};

// ========================================
// 📸 IMAGE PICKER EXAMPLE
// ========================================
import * as ImagePicker from 'expo-image-picker';

const pickImage = async () => {
  const result = await ImagePicker.launchImageLibraryAsync({
    mediaTypes: ImagePicker.MediaTypeOptions.Images,
    quality: 0.8,
  });
  
  if (!result.canceled) {
    await sendImage(result.assets[0].uri);
  }
};

// ========================================
// 🎤 AUDIO RECORDER EXAMPLE
// ========================================
import { Audio } from 'expo-av';

const [recording, setRecording] = useState(null);

const startRecording = async () => {
  const { granted } = await Audio.requestPermissionsAsync();
  if (!granted) return;
  
  const { recording } = await Audio.Recording.createAsync(
    Audio.RecordingOptionsPresets.HIGH_QUALITY
  );
  setRecording(recording);
};

const stopRecording = async () => {
  await recording.stopAndUnloadAsync();
  const uri = recording.getURI();
  await sendAudio(uri);
  setRecording(null);
};
```

---

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

// ========================================
// 📤 FILE/IMAGE/AUDIO YUBORISH (REST API)
// ========================================
import 'package:http/http.dart' as http;
import 'package:image_picker/image_picker.dart';
import 'package:file_picker/file_picker.dart';

// Send Image
Future<void> sendImage(File imageFile) async {
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
      // WebSocket'dan notification keladi
    }
  } catch (e) {
    print('❌ Error sending image: $e');
  }
}

// Send File
Future<void> sendFile(File file, String fileName) async {
  final token = await storage.read(key: 'access_token');
  final uri = Uri.parse('http://31.128.43.149:6060/api/chat/rooms/$roomId/messages/');
  
  var request = http.MultipartRequest('POST', uri);
  request.headers['Authorization'] = 'Bearer $token';
  request.fields['message_type'] = 'file';
  request.files.add(await http.MultipartFile.fromPath('file', file.path));
  
  try {
    var response = await request.send();
    if (response.statusCode == 201) {
      print('✅ File sent successfully');
    }
  } catch (e) {
    print('❌ Error sending file: $e');
  }
}

// Send Audio
Future<void> sendAudio(File audioFile) async {
  final token = await storage.read(key: 'access_token');
  final uri = Uri.parse('http://31.128.43.149:6060/api/chat/rooms/$roomId/messages/');
  
  var request = http.MultipartRequest('POST', uri);
  request.headers['Authorization'] = 'Bearer $token';
  request.fields['message_type'] = 'audio';
  request.files.add(await http.MultipartFile.fromPath('audio', audioFile.path));
  
  try {
    var response = await request.send();
    if (response.statusCode == 201) {
      print('✅ Audio sent successfully');
    }
  } catch (e) {
    print('❌ Error sending audio: $e');
  }
}

// ========================================
// 📸 IMAGE PICKER EXAMPLE
// ========================================
Future<void> pickAndSendImage() async {
  final picker = ImagePicker();
  final XFile? image = await picker.pickImage(
    source: ImageSource.gallery,
    imageQuality: 80,
  );
  
  if (image != null) {
    await sendImage(File(image.path));
  }
}

// ========================================
// 📁 FILE PICKER EXAMPLE
// ========================================
Future<void> pickAndSendFile() async {
  FilePickerResult? result = await FilePicker.platform.pickFiles();
  
  if (result != null) {
    File file = File(result.files.single.path!);
    await sendFile(file, result.files.single.name);
  }
}

// ========================================
// 🎤 AUDIO RECORDER EXAMPLE
// ========================================
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

Future<void> stopAndSendRecording() async {
  String? path = await record.stop();
  if (path != null) {
    await sendAudio(File(path));
  }
}
```

---

### 📋 **Message Types Cheat Sheet**

| Type | WebSocket | REST API | Tavsiya |
|------|-----------|----------|---------|
| **Text** | ✅ `{type: 'chat_message', message_type: 'text', text: '...'}` | ✅ `POST /messages/` + JSON | WebSocket (tezroq) |
| **Image** | ⚠️ Base64 (kichik faqat) | ✅ `multipart/form-data` | **REST API** |
| **File** | ❌ Yo'q | ✅ `multipart/form-data` | **REST API** |
| **Audio** | ⚠️ Base64 (kichik faqat) | ✅ `multipart/form-data` | **REST API** |

**Xulosa:**
- ✅ Text → WebSocket
- ✅ Image/File/Audio → REST API
- ✅ WebSocket faqat notification uchun

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

---

## 🎯 Complete Chat App Example (React Native)

To'liq ishlaydigan chat app example:

```javascript
import React, { useState, useEffect, useRef } from 'react';
import { View, Text, TextInput, Button, FlatList, Image } from 'react-native';
import AsyncStorage from '@react-native-async-storage/async-storage';
import * as ImagePicker from 'expo-image-picker';

const ChatScreen = ({ roomId }) => {
  const [messages, setMessages] = useState([]);
  const [inputText, setInputText] = useState('');
  const [isTyping, setIsTyping] = useState(false);
  const [connected, setConnected] = useState(false);
  const socketRef = useRef(null);
  const typingTimeoutRef = useRef(null);
  
  const API_URL = 'http://31.128.43.149:6060';
  
  // ========================================
  // 🔌 WebSocket Connection
  // ========================================
  useEffect(() => {
    connectWebSocket();
    
    return () => {
      if (socketRef.current) {
        socketRef.current.close();
      }
    };
  }, [roomId]);
  
  const connectWebSocket = async () => {
    const token = await AsyncStorage.getItem('access_token');
    const wsUrl = `ws://31.128.43.149:6060/ws/chat/${roomId}/?token=${token}`;
    
    const socket = new WebSocket(wsUrl);
    
    socket.onopen = () => {
      console.log('✅ Connected to WebSocket');
      setConnected(true);
    };
    
    socket.onmessage = (e) => {
      const data = JSON.parse(e.data);
      
      switch (data.type) {
        case 'connection_established':
          console.log('🔌 Connection confirmed');
          break;
          
        case 'chat_message':
          setMessages(prev => [...prev, data.message]);
          break;
          
        case 'typing':
          setIsTyping(data.is_typing);
          break;
          
        case 'read_receipt':
          updateMessageReadStatus(data.message_id);
          break;
      }
    };
    
    socket.onerror = (error) => {
      console.error('❌ WebSocket error:', error);
    };
    
    socket.onclose = () => {
      console.log('🔌 Connection closed');
      setConnected(false);
    };
    
    socketRef.current = socket;
  };
  
  // ========================================
  // 📤 Send Text Message (WebSocket)
  // ========================================
  const sendTextMessage = () => {
    if (!inputText.trim() || !socketRef.current) return;
    
    socketRef.current.send(JSON.stringify({
      type: 'chat_message',
      message_type: 'text',
      text: inputText
    }));
    
    setInputText('');
    stopTyping();
  };
  
  // ========================================
  // ✏️ Typing Indicator
  // ========================================
  const handleTyping = (text) => {
    setInputText(text);
    
    if (!socketRef.current) return;
    
    // Start typing
    socketRef.current.send(JSON.stringify({
      type: 'typing',
      is_typing: true
    }));
    
    // Clear previous timeout
    if (typingTimeoutRef.current) {
      clearTimeout(typingTimeoutRef.current);
    }
    
    // Stop typing after 1 second
    typingTimeoutRef.current = setTimeout(() => {
      stopTyping();
    }, 1000);
  };
  
  const stopTyping = () => {
    if (socketRef.current) {
      socketRef.current.send(JSON.stringify({
        type: 'typing',
        is_typing: false
      }));
    }
  };
  
  // ========================================
  // 📸 Send Image (REST API)
  // ========================================
  const pickAndSendImage = async () => {
    const result = await ImagePicker.launchImageLibraryAsync({
      mediaTypes: ImagePicker.MediaTypeOptions.Images,
      quality: 0.8,
    });
    
    if (result.canceled) return;
    
    const token = await AsyncStorage.getItem('access_token');
    const formData = new FormData();
    
    formData.append('message_type', 'image');
    formData.append('image', {
      uri: result.assets[0].uri,
      type: 'image/jpeg',
      name: 'photo.jpg',
    });
    
    try {
      const response = await fetch(
        `${API_URL}/api/chat/rooms/${roomId}/messages/`,
        {
          method: 'POST',
          headers: {
            'Authorization': `Bearer ${token}`,
          },
          body: formData,
        }
      );
      
      if (response.ok) {
        console.log('✅ Image sent');
        // WebSocket'dan notification keladi avtomatik
      }
    } catch (error) {
      console.error('❌ Error sending image:', error);
    }
  };
  
  // ========================================
  // 🎤 Send Audio (REST API)
  // ========================================
  const sendAudioMessage = async (audioUri) => {
    const token = await AsyncStorage.getItem('access_token');
    const formData = new FormData();
    
    formData.append('message_type', 'audio');
    formData.append('audio', {
      uri: audioUri,
      type: 'audio/m4a',
      name: 'voice.m4a',
    });
    
    try {
      const response = await fetch(
        `${API_URL}/api/chat/rooms/${roomId}/messages/`,
        {
          method: 'POST',
          headers: {
            'Authorization': `Bearer ${token}`,
          },
          body: formData,
        }
      );
      
      if (response.ok) {
        console.log('✅ Audio sent');
      }
    } catch (error) {
      console.error('❌ Error sending audio:', error);
    }
  };
  
  // ========================================
  // ✔️ Mark as Read
  // ========================================
  const markAsRead = (messageId) => {
    if (socketRef.current) {
      socketRef.current.send(JSON.stringify({
        type: 'read_receipt',
        message_id: messageId
      }));
    }
  };
  
  const updateMessageReadStatus = (messageId) => {
    setMessages(prev => 
      prev.map(msg => 
        msg.id === messageId ? { ...msg, is_read: true } : msg
      )
    );
  };
  
  // ========================================
  // 🎨 Render Message
  // ========================================
  const renderMessage = ({ item }) => {
    const isMyMessage = item.sender.id === myUserId; // O'zingizning user ID
    
    return (
      <View style={{
        alignSelf: isMyMessage ? 'flex-end' : 'flex-start',
        backgroundColor: isMyMessage ? '#dcf8c6' : '#fff',
        padding: 10,
        margin: 5,
        borderRadius: 8,
        maxWidth: '80%',
      }}>
        {!isMyMessage && (
          <Text style={{ fontWeight: 'bold', marginBottom: 5 }}>
            {item.sender.full_name}
          </Text>
        )}
        
        {item.message_type === 'text' && (
          <Text>{item.text}</Text>
        )}
        
        {item.message_type === 'image' && (
          <Image 
            source={{ uri: item.image_url }} 
            style={{ width: 200, height: 200, borderRadius: 8 }}
          />
        )}
        
        {item.message_type === 'audio' && (
          <Text>🎤 Audio message</Text>
        )}
        
        {item.message_type === 'file' && (
          <Text>📎 {item.file_url?.split('/').pop()}</Text>
        )}
        
        <Text style={{ fontSize: 10, color: '#999', marginTop: 5 }}>
          {new Date(item.created_at).toLocaleTimeString()}
          {isMyMessage && (item.is_read ? ' ✔✔' : ' ✔')}
        </Text>
      </View>
    );
  };
  
  // ========================================
  // 🎨 Render UI
  // ========================================
  return (
    <View style={{ flex: 1, backgroundColor: '#ece5dd' }}>
      {/* Header */}
      <View style={{ backgroundColor: '#075e54', padding: 15 }}>
        <Text style={{ color: 'white', fontSize: 18, fontWeight: 'bold' }}>
          Chat Room {roomId}
        </Text>
        <Text style={{ color: 'white', fontSize: 12 }}>
          {connected ? '🟢 Connected' : '🔴 Disconnected'}
        </Text>
      </View>
      
      {/* Messages List */}
      <FlatList
        data={messages}
        renderItem={renderMessage}
        keyExtractor={(item) => item.id.toString()}
        contentContainerStyle={{ padding: 10 }}
        onEndReached={() => {
          // Load more messages
        }}
      />
      
      {/* Typing Indicator */}
      {isTyping && (
        <Text style={{ padding: 10, fontStyle: 'italic', color: '#666' }}>
          ✏️ Typing...
        </Text>
      )}
      
      {/* Input Area */}
      <View style={{ 
        flexDirection: 'row', 
        padding: 10, 
        backgroundColor: 'white',
        borderTopWidth: 1,
        borderTopColor: '#ddd'
      }}>
        <Button title="📸" onPress={pickAndSendImage} />
        <Button title="🎤" onPress={() => {/* Start recording */}} />
        
        <TextInput
          style={{
            flex: 1,
            marginHorizontal: 10,
            padding: 10,
            backgroundColor: '#f0f0f0',
            borderRadius: 20,
          }}
          value={inputText}
          onChangeText={handleTyping}
          placeholder="Type a message..."
          onSubmitEditing={sendTextMessage}
        />
        
        <Button title="📤" onPress={sendTextMessage} />
      </View>
    </View>
  );
};

export default ChatScreen;
```

---

## 📋 JSON Format Reference

### **Text Message (WebSocket):**
```json
{
  "type": "chat_message",
  "message_type": "text",
  "text": "Salom! Qalaysiz?"
}
```

### **Image Message (REST API - multipart/form-data):**
```http
POST /api/chat/rooms/1/messages/
Content-Type: multipart/form-data

message_type: image
image: <binary file>
```

### **File Message (REST API - multipart/form-data):**
```http
POST /api/chat/rooms/1/messages/
Content-Type: multipart/form-data

message_type: file
file: <binary file>
```

### **Audio Message (REST API - multipart/form-data):**
```http
POST /api/chat/rooms/1/messages/
Content-Type: multipart/form-data

message_type: audio
audio: <binary file>
```

### **Typing Indicator (WebSocket):**
```json
{
  "type": "typing",
  "is_typing": true
}
```

### **Read Receipt (WebSocket):**
```json
{
  "type": "read_receipt",
  "message_id": 123
}
```

---

## 🎯 Key Points

1. ✅ **Text messages** → WebSocket (tezroq)
2. ✅ **Image/File/Audio** → REST API (multipart/form-data)
3. ✅ WebSocket faqat real-time notifications uchun
4. ✅ Token query parameter orqali yuboriladi: `?token=...`
5. ✅ Har qanday message yuborilgandan keyin WebSocket'dan notification keladi
