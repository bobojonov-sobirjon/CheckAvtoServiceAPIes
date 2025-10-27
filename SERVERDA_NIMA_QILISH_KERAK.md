# Serverda SMS Kod Muammosini Hal Qilish

## Muammo
✅ Localda: Hammasi zo'r ishlaydi
❌ Serverda: "Срок действия SMS кода истек или код не найден" xatosi

## Sababi
Serverda Django bir nechta worker processlarda ishlaydi. Har bir process o'z cache'iga SMS kodni yozadi, lekin keyin boshqa process tekshiradi va kod yo'q edi.

## Yechim - Faqat 3 Qadam!

### Variant 1: Database Cache (Oddiy) ✅

**Serverda .env faylga qo'shing:**
```bash
echo "USE_DB_CACHE=True" >> .env
```

**Cache table yarating:**
```bash
python manage.py createcachetable
```

**Server-ni qayta ishga tushiring:**
```bash
sudo systemctl restart gunicorn
```

**Tayyor!** ✅

---

### Variant 2: Redis (Yanada Yaxshi) 🚀

**1. Redis o'rnating:**
```bash
sudo apt update
sudo apt install redis-server
sudo systemctl start redis
sudo systemctl enable redis
```

**2. Python paketlarni o'rnating:**
```bash
source venv/bin/activate
pip install -r requirements.txt
```

**3. .env faylga qo'shing:**
```bash
USE_REDIS_CACHE=True
REDIS_URL=redis://127.0.0.1:6379/1
```

**4. Server-ni qayta ishga tushiring:**
```bash
sudo systemctl restart gunicorn
```

**Tayyor!** ✅

---

## Tekshirish

```bash
# 1. Kod so'rang
curl -X POST http://31.128.43.149:6060/api/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{"identifier": "test@example.com", "role": "Driver"}'

# 2. Kodni tekshiring (darhol keyin!)
curl -X POST http://31.128.43.149:6060/api/auth/check-sms-code/ \
  -H "Content-Type: application/json" \
  -d '{"identifier": {"value": "test@example.com", "type": "email"}, "sms_code": "1234", "role": "Driver"}'
```

Endi ishlaydi! 🎉

