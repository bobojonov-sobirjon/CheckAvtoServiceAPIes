# Swagger Authentication Guide

## Swagger UI'da Login Qilish

Endi Swagger UI'da "Authorize" tugmasini bosib, to'g'ridan-to'g'ri email va parol bilan login qilishingiz mumkin.

## Qadamlar:

### 1. Swagger UI'ni oching
- `http://localhost:8000/swagger/` ga o'ting

### 2. "Authorize" tugmasini bosing
- Swagger UI'ning yuqori o'ng burchagida "Authorize" tugmasini bosing

### 3. Email va parol kiriting
- OAuth2 bo'limida:
  - **Username**: Email manzilingiz (masalan: `user@example.com`)
  - **Password**: Parolingiz
  - **Client ID**: `swagger` (avtomatik to'ldiriladi)
  - **Client Secret**: `swagger-secret` (avtomatik to'ldiriladi)

### 4. "Authorize" tugmasini bosing
- Ma'lumotlarni to'ldirgach, "Authorize" tugmasini bosing
- Agar email va parol to'g'ri bo'lsa, avtomatik ravishda JWT token olinadi

### 5. API'larni ishlatish
- Endi barcha API endpoint'larini ishlatishingiz mumkin
- Token avtomatik ravishda barcha so'rovlarga qo'shiladi

## Muammolar:

### Login ishlamayapti
- Email manzil to'g'ri ekanligiga ishonch hosil qiling
- Parol to'g'ri ekanligiga ishonch hosil qiling
- Foydalanuvchi tizimda mavjud ekanligiga ishonch hosil qiling

### Token ishlamayapti
- "Authorize" tugmasini qayta bosing
- Yangi email/parol bilan qayta urining

## API Endpoint'lar:

- `POST /api/auth/oauth/token/` - OAuth2 token endpoint (Swagger tomonidan ishlatiladi)
- `POST /api/auth/login/` - SMS kod yuborish
- `POST /api/auth/check-sms-code/` - SMS kod tekshirish
- `GET /api/auth/sms-status/` - SMS servis holati

## Misol:

1. Swagger UI'da "Authorize" tugmasini bosing
2. Username: `test@example.com`
3. Password: `your_password`
4. "Authorize" tugmasini bosing
5. Endi barcha API'larni ishlatishingiz mumkin!
