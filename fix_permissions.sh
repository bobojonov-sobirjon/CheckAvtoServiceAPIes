#!/bin/bash
# Serverda Database Permission Xatosini Avtomatik Tuzatish

# CheckAvto project papkasini o'zgartiring
PROJECT_PATH="/path/to/CheckAvto"  # BU YERNI O'ZINING PATHI BILAN O'ZGARTIRING!

# Joriy userni toping
CURRENT_USER=$(whoami)
echo "Joriy user: $CURRENT_USER"

# Database fayl huquqlarini tuzatish
echo "Database huquqlarini tuzatyapman..."
cd "$PROJECT_PATH"
sudo chmod 664 db.sqlite3
sudo chown $CURRENT_USER:$CURRENT_USER db.sqlite3

# Logs papkasi yaratish va huquq berish
echo "Logs papkasini yaratish..."
mkdir -p logs
touch logs/django.log
chmod 775 logs
chmod 664 logs/django.log

# Staticfiles papkasiga huquq berish
echo "Staticfiles huquqlarini tuzatyapman..."
mkdir -p staticfiles
chmod 755 staticfiles

# Cache table yaratish (agar DatabaseCache ishlatilsa)
if grep -q "USE_DB_CACHE=True" .env 2>/dev/null || grep -q "USE_DB_CACHE=True" .env.example 2>/dev/null; then
    echo "Cache table yaratish..."
    source venv/bin/activate 2>/dev/null || source env/bin/activate 2>/dev/null
    python manage.py createcachetable
    chmod 664 db.sqlite3
fi

# Barcha fayllarga huquq berish
echo "Barcha fayllarga huquq beryapman..."
chmod -R 755 "$PROJECT_PATH"
chmod -R u+w "$PROJECT_PATH"

# Database fayl va logs fayllarini maxsus huquqlar bilan
chmod 664 db.sqlite3
chmod 664 logs/django.log 2>/dev/null || true

echo "✅ Huquqlar tuzatildi!"

# Server-ni qayta ishga tushirish (agar kerak bo'lsa)
read -p "Server-ni qayta ishga tushirsam? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    sudo systemctl restart gunicorn
    sudo systemctl restart nginx
    echo "✅ Server qayta ishga tushirildi!"
fi

echo "✅ Tayyor! Endi admin panel ishlashi kerak."

