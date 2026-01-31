# 🚀 Quick Setup - Daphne with Nginx

## ⚡ Step-by-Step Commands

### 1. Edit Service File (If Needed)

**Default paths (matching your Gunicorn setup):**
- User: `www-data`
- WorkingDirectory: `/var/www/CheckAvtoServiceAPIes`
- ExecStart: `/var/www/CheckAvtoServiceAPIes/env/bin/daphne`
- Socket: `/run/avto/avto-chat.sock`

**No changes needed if your paths match!**

If your paths are different:
```bash
nano avto-chat.service
```

Change these lines:
- Line 7: `User=www-data`
- Line 9: `WorkingDirectory=/var/www/CheckAvtoServiceAPIes`
- Line 10: `ExecStart=/var/www/CheckAvtoServiceAPIes/env/bin/daphne \`
- Line 11: `-u /run/avto/avto-chat.sock \`

---

### 2. Edit Nginx Config (If Needed)

```bash
nano nginx-avto-chat.conf
```

**Change these if needed:**
- Line 13: `server_name YOUR_DOMAIN;` (or use IP)
- Line 19: `alias /var/www/CheckAvtoServiceAPIes/staticfiles/;`
- Line 24: `alias /var/www/CheckAvtoServiceAPIes/media/;`

---

### 3. Copy Files

```bash
# Copy systemd files
sudo cp avto-chat.socket /etc/systemd/system/
sudo cp avto-chat.service /etc/systemd/system/

# Copy nginx config
sudo cp nginx-avto-chat.conf /etc/nginx/sites-available/avto

# Create symlink
sudo ln -sf /etc/nginx/sites-available/avto /etc/nginx/sites-enabled/
```

---

### 4. Start Services

```bash
# Reload systemd
sudo systemctl daemon-reload

# Start Daphne
sudo systemctl start avto-chat.socket
sudo systemctl enable avto-chat.socket
sudo systemctl start avto-chat.service
sudo systemctl enable avto-chat.service

# Test nginx
sudo nginx -t

# Restart nginx
sudo systemctl restart nginx

# Restart Django
sudo systemctl restart avto
```

---

### 5. Check Status

```bash
# Check all services
sudo systemctl status avto.service
sudo systemctl status avto-chat.service
sudo systemctl status nginx

# Check logs
sudo journalctl -u avto-chat.service -f
```

---

## ✅ Test WebSocket

```bash
# Replace with your JWT token
wscat -c ws://localhost/ws/chat/1/?token=YOUR_JWT_TOKEN
```

**Or use curl:**
```bash
curl --include \
     --no-buffer \
     --header "Connection: Upgrade" \
     --header "Upgrade: websocket" \
     --header "Sec-WebSocket-Key: SGVsbG8sIHdvcmxkIQ==" \
     --header "Sec-WebSocket-Version: 13" \
     http://localhost/ws/chat/1/?token=YOUR_JWT_TOKEN
```

---

## 🔍 If Something Goes Wrong

```bash
# View Daphne logs
sudo journalctl -u avto-chat.service --no-pager

# View Nginx error log
sudo tail -50 /var/log/nginx/error.log

# Check socket
ls -la /run/avto/avto-chat.sock

# Check all sockets
ls -la /run/avto/

# Restart everything
sudo systemctl restart avto
sudo systemctl restart avto-chat.service
sudo systemctl restart nginx
```

---

## 📱 Production URLs

- **API:** `http://your-domain.com/api/`
- **WebSocket:** `ws://your-domain.com/ws/chat/{room_id}/?token={jwt}`
- **Admin:** `http://your-domain.com/admin/`

**With SSL (Recommended):**
- **API:** `https://your-domain.com/api/`
- **WebSocket:** `wss://your-domain.com/ws/chat/{room_id}/?token={jwt}`
- **Admin:** `https://your-domain.com/admin/`

---

## 🎯 Done!

Your CheckAvto app now runs with:
- **Gunicorn** → HTTP requests (via `avto.service`)
- **Daphne** → WebSocket connections (via `avto-chat.service`)
- **Nginx** → Routes traffic to correct service
