# Документация API Accounts

## SMS Authentication API

Доступно только 2 API endpoint:

### 1. Login (отправка SMS кода)
**POST** `/api/accounts/login/`

Отправка 4-значного SMS кода на номер телефона.

#### Request Body:
```json
{
    "phone_number": "7914180518"
}
```

#### Response (Success):
```json
{
    "success": true,
    "message": "SMS код отправлен",
    "phone": "7914180518"
}
```

#### Response (Error):
```json
{
    "success": false,
    "errors": {
        "phone_number": ["Неверный формат номера телефона. Введите российский номер (8XXXXXXXXXX, +7XXXXXXXXXX, 7XXXXXXXXXX)"]
    }
}
```

---

### 2. Check SMS Code (проверка SMS кода)
**POST** `/api/accounts/check-sms-code/`

Проверка SMS кода и выдача JWT токена.

#### Request Body:
```json
{
    "phone_number": "7914180518",
    "sms_code": "1234"
}
```

#### Response (Success):
```json
{
    "success": true,
    "message": "Успешный вход",
    "user": {
        "id": 1,
        "phone_number": "7914180518",
        "first_name": "User",
        "last_name": "7914180518",
        "email": "7914180518@example.com",
        "is_verified": true,
        "created_at": "2024-01-01T12:00:00Z"
    },
    "tokens": {
        "access": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
        "refresh": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..."
    }
}
```

#### Response (Error):
```json
{
    "success": false,
    "error": "Неверный SMS код"
}
```

---

## Форматы номеров телефонов

Поддерживаемые форматы:

### Узбекские номера:
- `998XXXXXXXXX` → `998XXXXXXXXX` (правильно)
- `+998XXXXXXXXX` → `998XXXXXXXXX`

### Российские номера:
- `8XXXXXXXXXX` → `7XXXXXXXXXX`
- `+7XXXXXXXXXX` → `7XXXXXXXXXX`
- `7XXXXXXXXXX` → `7XXXXXXXXXX` (правильно)

## Коды ошибок

- `400` - Bad Request (Неверные данные)
- `408` - Request Timeout (Время ожидания SMS сервиса истекло)
- `500` - Internal Server Error (Ошибка сервера)

## Возможности

- ✅ **4-значный** SMS код
- ✅ **Российские номера** поддерживаются
- ✅ **5 минут** срок действия кода
- ✅ **JWT токен** выдается
- ✅ **Автоматическое создание пользователя**
- ✅ **Clean code** и **error handling**
- ✅ **Serializer validation**
- ✅ **APIView** class-based views
