# Production Server Setup Guide

## Muammo (Problem)

Localda kod zo'r ishlayapti, lekin serverda SMS kodini tekshirishda xatolik:
```
"Срок действия SMS кода истек или код не найден"
```

### Sabab (Root Cause)

Serverda Django multiple worker processlarda ishlayapti (Gunicorn/uvicorn bilan). 
`LocMemCache` har bir worker alohida cache ega. Shuning uchun:
- SMS kodni worker A saglaydi
- Kodni tekshirishni worker B qabul qildi  
- Worker B cache da kodni topolmaydi ❌

### Yechim (Solution)

Database cache backend ishlatish (hamma workers uchun umumiy).

## Serverda Quyidagi Amallarni Bajaring:

### 1. .env faylga qo'shing:
```bash
USE_DB_CACHE=True
```

### 2. Cache table yarating:
```bash
python manage.py createcachetable
```

### 3. Django-ni qayta ishga tushiring:
```bash
sudo systemctl restart gunicorn
# yoki
sudo supervisorctl restart checkavto
```

### 4. Ko'rib chiqing ki server ishlayapti:
```bash
sudo systemctl status gunicorn
```

## Alternative: Redis Ishlatish (Eng Yaxshi Yechim)

Agar Redis o'rnatilgan bo'lsa:

### 1. Redis o'rnating (agar yo'q bo'lsa):
```bash
sudo apt update
sudo apt install redis-server
sudo systemctl start redis
sudo systemctl enable redis
```

### 2. Python package o'rnating:
```bash
source /path/to/your/venv/bin/activate
pip install django-redis
pip install redis
```

### 3. .env faylga qo'shing:
```bash
USE_REDIS_CACHE=True
REDIS_URL=redis://127.0.0.1:6379/1
```

### 4. requirements.txt ga qo'shing:
```
django-redis==5.4.0
redis==5.0.1
```

### 5. Django-ni qayta ishga tushiring:
```bash
sudo systemctl restart gunicorn
```

## Tekshirish

Kod yuborish:
```bash
curl -X POST http://31.128.43.149:6060/api/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{"identifier": "test@example.com", "role": "Driver"}'
```

Kodni tekshirish (darhol keyin):
```bash
curl -X POST http://31.128.43.149:6060/api/auth/check-sms-code/ \
  -H "Content-Type: application/json" \
  -d '{"identifier": {"value": "test@example.com", "type": "email"}, "sms_code": "1234", "role": "Driver"}'
```

## Izoh (Note)

`LocMemCache` faqat development uchun yaxshi (single process). 
Production uchun Database cache yoki Redis cache ishlatish kerak!

