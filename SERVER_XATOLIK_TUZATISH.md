# Serverda "CLIENT_CLASS" Xatosini Tuzatish

## Xatolik
```json
{
  "success": false,
  "error": "Неожиданная ошибка: AbstractConnection.__init__() got an unexpected keyword argument 'CLIENT_CLASS'"
}
```

## Sababi
Serverda Redis ishlatilmoqda, lekin `django-redis` to'g'ri o'rnatilmagan yoki conflict bor.

## Yechim - 2 Variant

### Variant 1: DatabaseCache Ishlatish ✅ (Oddiy va Ishonchli)

**Serverda SSH orqali:**

```bash
# 1. .env faylga yozing (USE_REDIS_CACHE emas, USE_DB_CACHE):
cd /var/www/CheckAvto
echo "USE_DB_CACHE=True" >> .env

# 2. Cache table yarating:
source venv/bin/activate
python manage.py createcachetable

# 3. Database huquqlarini tuzating:
sudo chmod 664 db.sqlite3
sudo chown $USER:$USER db.sqlite3

# 4. Server-ni qayta ishga tushiring:
sudo systemctl restart gunicorn
```

✅ **Tayyor!**

---

### Variant 2: LocMemCache Qaytarish (FAQQAT TEST UCHUN)

⚠️ **Eslatma:** Bu production uchun yaxshi emas! Faqat test uchun.

```bash
# .env fayldan Redis o'chiring:
cd /var/www/CheckAvto
# .env faylni oching:
nano .env

# USE_REDIS_CACHE=True ni comment qiling yoki o'chiring:
# USE_REDIS_CACHE=True

# Yoki butunlay o'chiring:
sed -i '/USE_REDIS_CACHE/d' .env

# Server-ni qayta ishga tushiring:
sudo systemctl restart gunicorn
```

⚠️ **Bu ishlaydi, lekin productionda maslahat berilmaydi!**

---

## Eng Yaxshi Yechim: DatabaseCache

DatabaseCache eng oddiy va ishonchli yechim. Redissiz ishlaydi.

### To'liq Qo'llanma:

```bash
# SSH orqali serverga kiring
ssh user@31.128.43.149

# Project papkasiga o'ting
cd /var/www/CheckAvto  # yoki qayerga deploy qilgan bo'lsangiz

# .env faylga DatabaseCache qo'shing
cat > .env << 'EOF'
USE_DB_CACHE=True
SECRET_KEY=your-secret-key
DEBUG=False
EOF

# Virtual environmentni faollashtirish
source venv/bin/activate  # yoki env/bin/activate

# Cache table yaratish
python manage.py createcachetable

# Database huquqlarini bering
sudo chmod 664 db.sqlite3
sudo chown $USER:$USER db.sqlite3

# Server-ni qayta ishga tushirish
sudo systemctl restart gunicorn

# Nginx-ni ham qayta ishga tushirish (agar kerak)
sudo systemctl restart nginx

# Loglarni ko'rish
sudo journalctl -u gunicorn -f
```

## Tekshirish

```bash
# API-ni test qiling
curl -X POST http://31.128.43.149:6060/api/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{"identifier": "test@example.com", "role": "Driver"}'
```

Agar 200 OK qaytsa, hammasi ishlayapti! ✅

## Log-ni Ko'rish

```bash
# Gunicorn log
sudo journalctl -u gunicorn -n 50

# Django log
tail -f /var/www/CheckAvto/logs/django.log

# Nginx log
tail -f /var/log/nginx/error.log
```

