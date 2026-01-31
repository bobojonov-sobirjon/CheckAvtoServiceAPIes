# CheckAvto Deployment Guide

## 📦 Prerequisites

- Ubuntu/Debian server
- Python 3.8+
- PostgreSQL
- Nginx
- Virtual environment

---

## 🚀 Deployment Steps

### 1. Update Service Files

**Edit `avto-chat.service`:**

```bash
sudo nano avto-chat.service
```

**Change these values:**
- `User=your_user` → your Linux username
- `WorkingDirectory=/path/to/CheckAvto` → full path to project
- `Environment="PATH=/path/to/venv/bin"` → path to venv
- `ExecStart=/path/to/venv/bin/daphne` → full path to daphne

**Example:**
```ini
User=ubuntu
WorkingDirectory=/home/ubuntu/CheckAvto
Environment="PATH=/home/ubuntu/CheckAvto/venv/bin"
ExecStart=/home/ubuntu/CheckAvto/venv/bin/daphne \
    -u /run/avto-chat.sock \
    config.asgi:application
```

---

### 2. Copy Files to System

```bash
# Copy socket file
sudo cp avto-chat.socket /etc/systemd/system/

# Copy service file
sudo cp avto-chat.service /etc/systemd/system/

# Set permissions
sudo chmod 644 /etc/systemd/system/avto-chat.socket
sudo chmod 644 /etc/systemd/system/avto-chat.service
```

---

### 3. Update Nginx Configuration

**Edit `nginx-avto-chat.conf`:**

```bash
nano nginx-avto-chat.conf
```

**Change these values:**
- `server_name your_domain.com` → your domain
- `/path/to/CheckAvto/staticfiles/` → full path to static
- `/path/to/CheckAvto/media/` → full path to media

**Copy to Nginx:**

```bash
# Copy to sites-available
sudo cp nginx-avto-chat.conf /etc/nginx/sites-available/avto

# Create symlink to sites-enabled
sudo ln -s /etc/nginx/sites-available/avto /etc/nginx/sites-enabled/

# Remove default if exists
sudo rm /etc/nginx/sites-enabled/default

# Test nginx config
sudo nginx -t

# If OK, reload nginx
sudo systemctl reload nginx
```

---

### 4. Start Daphne Service

```bash
# Reload systemd
sudo systemctl daemon-reload

# Start and enable socket
sudo systemctl start avto-chat.socket
sudo systemctl enable avto-chat.socket

# Start and enable service
sudo systemctl start avto-chat.service
sudo systemctl enable avto-chat.service

# Check status
sudo systemctl status avto-chat.socket
sudo systemctl status avto-chat.service
```

---

### 5. Restart Existing Services

```bash
# Restart Django/Gunicorn
sudo systemctl restart avto

# Restart Nginx
sudo systemctl restart nginx
```

---

## 🔍 Troubleshooting

### Check Logs

```bash
# Daphne service logs
sudo journalctl -u avto-chat.service -f

# Nginx error logs
sudo tail -f /var/log/nginx/error.log

# Nginx access logs
sudo tail -f /var/log/nginx/access.log
```

---

### Check Socket Status

```bash
# Check if socket exists
ls -la /run/avto-chat.sock

# Check socket permissions
sudo ls -la /run/avto-chat.sock
```

---

### Common Issues

**1. Socket permission denied:**
```bash
# Add nginx user to your group
sudo usermod -aG your_user www-data

# Or change socket user in avto-chat.socket
SocketUser=your_user
```

**2. Service won't start:**
```bash
# Check for Python errors
sudo journalctl -u avto-chat.service --no-pager

# Verify paths in service file
which daphne  # Should match ExecStart path
```

**3. WebSocket connection refused:**
```bash
# Check if Daphne is running
sudo systemctl status avto-chat.service

# Check if socket exists
ls -la /run/avto-chat.sock

# Check Nginx upstream
sudo nginx -t
```

**4. 502 Bad Gateway:**
```bash
# Check if socket is accessible
sudo -u www-data test -r /run/avto-chat.sock && echo "OK" || echo "FAIL"

# Check SELinux (if enabled)
sudo setsebool -P httpd_can_network_connect 1
```

---

## 📋 Quick Commands

```bash
# Restart everything
sudo systemctl restart avto
sudo systemctl restart avto-chat.service
sudo systemctl restart nginx

# Stop everything
sudo systemctl stop avto
sudo systemctl stop avto-chat.service
sudo systemctl stop nginx

# View all logs
sudo journalctl -u avto.service -u avto-chat.service -f
```

---

## ✅ Verify Deployment

### 1. Check WebSocket

```bash
# Test WebSocket connection
wscat -c ws://your_domain.com/ws/chat/1/?token=YOUR_JWT_TOKEN
```

### 2. Check HTTP

```bash
# Test regular API
curl http://your_domain.com/api/accounts/user/
```

### 3. Check Static Files

```bash
# Visit in browser
http://your_domain.com/static/admin/css/base.css
```

---

## 🔄 Update Code (After Changes)

```bash
# Pull latest code
git pull origin main

# Activate venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Collect static files
python manage.py collectstatic --noinput

# Run migrations
python manage.py migrate

# Restart services
sudo systemctl restart avto
sudo systemctl restart avto-chat.service

# Check status
sudo systemctl status avto
sudo systemctl status avto-chat.service
```

---

## 🎯 WebSocket URLs

- **Development:** `ws://localhost:8000/ws/chat/{room_id}/?token={jwt_token}`
- **Production:** `wss://your_domain.com/ws/chat/{room_id}/?token={jwt_token}`

**Note:** Use `wss://` (secure) in production with SSL certificate!

---

## 🔐 SSL Certificate (Optional but Recommended)

```bash
# Install Certbot
sudo apt install certbot python3-certbot-nginx

# Get certificate
sudo certbot --nginx -d your_domain.com

# Auto-renewal is set up automatically
```

After SSL, Nginx will automatically redirect HTTP to HTTPS and WebSocket will use `wss://` instead of `ws://`.

---

## 📊 Monitoring

```bash
# Monitor resource usage
htop

# Monitor specific process
sudo systemctl status avto-chat.service

# Monitor connections
sudo ss -tuln | grep :80
```

---

## 🆘 Emergency Rollback

```bash
# Stop new service
sudo systemctl stop avto-chat.service
sudo systemctl disable avto-chat.service

# Remove nginx config
sudo rm /etc/nginx/sites-enabled/avto

# Restore old config if needed
sudo ln -s /etc/nginx/sites-available/old_avto /etc/nginx/sites-enabled/

# Reload nginx
sudo systemctl reload nginx
```
