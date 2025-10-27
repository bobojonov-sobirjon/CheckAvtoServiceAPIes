# Serverda Database Permission Xatosini Tuzatish

## Xatolik
```
{"error": "attempt to write a readonly database"}
```

## Sababi
Serverda Django application user (gunicorn/nginx) database faylni yozish huquqiga ega emas.

## Yechim - Serverda Quyidagi Buyruqlarni Bajaring:

### 1. Database Faylga Huquq Berish

```bash
# CheckAvto project papkasiga kiring
cd /path/to/CheckAvto

# Database faylni o'qiydigan va yozadigan qilib qiling
sudo chmod 664 db.sqlite3

# Paspka huquqini tekshiring
sudo chmod 755 /path/to/CheckAvto

# Database fayl va papkani www-data useriga tegishli qiling
sudo chown www-data:www-data db.sqlite3
sudo chown -R www-data:www-data /path/to/CheckAvto

# Yoki agar gunicorn boshqa user-da ishlasa:
sudo chown gunicorn:gunicorn db.sqlite3
sudo chown -R gunicorn:gunicorn /path/to/CheckAvto
```

### 2. Logs Papkasiga Huquq Berish

```bash
# Logs papkasini yarating (agar yo'q bo'lsa)
mkdir -p /path/to/CheckAvto/logs

# Logs papkasiga huquq bering
sudo chmod 775 /path/to/CheckAvto/logs
sudo chown www-data:www-data /path/to/CheckAvto/logs

# Log faylini yarating va huquq bering
touch /path/to/CheckAvto/logs/django.log
sudo chmod 664 /path/to/CheckAvto/logs/django.log
sudo chown www-data:www-data /path/to/CheckAvto/logs/django.log
```

### 3. Staticfiles Papkasiga Huquq Berish

```bash
# Staticfiles papkasiga huquq bering
sudo chmod 755 /path/to/CheckAvto/staticfiles
sudo chown -R www-data:www-data /path/to/CheckAvto/staticfiles
```

### 4. Cache Table Yaratish

Agar DatabaseCache ishlatmoqchi bo'lsangiz:

```bash
cd /path/to/CheckAvto
source venv/bin/activate  # virtual environmentni faollashtiring
python manage.py createcachetable
```

Cache table yaratilganidan keyin huquq bering:

```bash
sudo chown www-data:www-data db.sqlite3
```

### 5. Server-ni Qayta Ishga Tushiring

```bash
sudo systemctl restart gunicorn
sudo systemctl restart nginx
```

## Tekshirish

```bash
# Database fayl huquqlarini ko'rish
ls -la /path/to/CheckAvto/db.sqlite3

# Logs papkasi huquqlarini ko'rish
ls -la /path/to/CheckAvto/logs/

# Gunicorn log-ni ko'rish
sudo journalctl -u gunicorn -f
```

## Umumiy Cheklov Bir Qadar:

### User Toping

```bash
# Kim run qilmoqda Django-ni?
ps aux | grep gunicorn

# yoki
ps aux | grep python | grep manage.py
```

### Huquqlar Bering

```bash
# Hozirgi userni toping va uni huquqlarini bering
CURRENT_USER=$(whoami)
sudo chown -R $CURRENT_USER:$CURRENT_USER /path/to/CheckAvto

# Yoki joriy user-ru run qiling
sudo chmod 664 db.sqlite3
sudo chmod -R 755 /path/to/CheckAvto
```

### Alternative: SQLite O'rniga PostgreSQL yoki MySQL

Agar bu muammolar takrorlansa, PostgreSQL yoki MySQL ishlatish maslahat beriladi.

```bash
# PostgreSQL o'rnating
sudo apt install postgresql postgresql-contrib

# Database yarating
sudo -u postgres psql
CREATE DATABASE checkavto_db;
CREATE USER checkavto_user WITH PASSWORD 'your_password';
GRANT ALL PRIVILEGES ON DATABASE checkavto_db TO checkavto_user;
\q

# settings.py ni yangilang
```

## Important Notes

⚠️ **Boshlang'ich**: Barcha fayl va papkalarga nashr huquqlarini bering
⚠️ **Xavfsizlik**: Faqat zarur huquqlarni bering
⚠️ **Backup**: O'zgarishlardan oldin backup oling

