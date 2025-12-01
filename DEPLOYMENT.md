# 🚀 Deployment Guide - DigitalOcean

## Опция 1: Автоматичен Deploy (Препоръчвам)

### Стъпка 1: Създайте Droplet
1. Влезте в [DigitalOcean](https://cloud.digitalocean.com/)
2. Create → Droplets
3. Изберете:
   - **Image:** Ubuntu 22.04 LTS
   - **Plan:** Basic - $6/месец (1GB RAM)
   - **Datacenter:** Frankfurt/Amsterdam
   - **Authentication:** SSH keys или Password

### Стъпка 2: Изпълнете deployment скрипта
```bash
# От вашия локален компютър или GitHub Codespace
chmod +x deploy-digitalocean.sh
./deploy-digitalocean.sh
```

Скриптът ще ви попита за IP адреса на сървъра и автоматично ще:
- ✅ Инсталира Python 3.12
- ✅ Клонира проекта от GitHub
- ✅ Инсталира всички зависимости
- ✅ Създаде systemd service
- ✅ Стартира бота

---

## Опция 2: Ръчен Deploy

### 1. Свържете се към сървъра
```bash
ssh root@YOUR_DROPLET_IP
```

### 2. Инсталирайте зависимости
```bash
apt update && apt upgrade -y
apt install -y python3.12 python3.12-venv python3-pip git build-essential
```

### 3. Клонирайте проекта
```bash
cd /root
git clone https://github.com/galinborisov10-art/Crypto-signal-bot.git
cd Crypto-signal-bot
```

### 4. Създайте virtual environment
```bash
python3.12 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 5. Създайте systemd service
```bash
nano /etc/systemd/system/crypto-bot.service
```

Копирайте следното:
```ini
[Unit]
Description=Crypto Signal Bot
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/root/Crypto-signal-bot
Environment="PATH=/root/Crypto-signal-bot/venv/bin"
ExecStart=/root/Crypto-signal-bot/venv/bin/python3 bot.py
Restart=always
RestartSec=10
StandardOutput=append:/root/Crypto-signal-bot/bot.log
StandardError=append:/root/Crypto-signal-bot/bot.log

[Install]
WantedBy=multi-user.target
```

### 6. Активирайте и стартирайте
```bash
systemctl daemon-reload
systemctl enable crypto-bot
systemctl start crypto-bot
```

### 7. Проверете статус
```bash
systemctl status crypto-bot
journalctl -u crypto-bot -f
```

---

## 📋 Управление на бота

### Основни команди
```bash
# Старт
systemctl start crypto-bot

# Стоп
systemctl stop crypto-bot

# Рестарт
systemctl restart crypto-bot

# Статус
systemctl status crypto-bot

# Логове (real-time)
journalctl -u crypto-bot -f

# Логове (последни 100 реда)
journalctl -u crypto-bot -n 100
```

### Update на кода
```bash
cd /root/Crypto-signal-bot
git pull
systemctl restart crypto-bot
```

---

## 🔒 Сигурност

### 1. Настройте firewall
```bash
ufw allow OpenSSH
ufw allow 443/tcp
ufw enable
```

### 2. Деактивирайте root login
```bash
nano /etc/ssh/sshd_config
# Променете: PermitRootLogin no
systemctl restart sshd
```

### 3. Инсталирайте fail2ban
```bash
apt install fail2ban -y
systemctl enable fail2ban
systemctl start fail2ban
```

---

## 📊 Мониторинг

### Проверка на ресурси
```bash
# RAM
free -h

# CPU
htop

# Disk
df -h

# Процеси
ps aux | grep python
```

### Bot логове
```bash
# Real-time
tail -f /root/Crypto-signal-bot/bot.log

# Последни 50 реда
tail -50 /root/Crypto-signal-bot/bot.log
```

---

## 🐳 Docker Deploy (Алтернатива)

### 1. Инсталирайте Docker
```bash
curl -fsSL https://get.docker.com -o get-docker.sh
sh get-docker.sh
```

### 2. Build образа
```bash
cd /root/Crypto-signal-bot
docker build -t crypto-bot .
```

### 3. Стартирайте контейнера
```bash
docker run -d \
  --name crypto-bot \
  --restart unless-stopped \
  -v /root/Crypto-signal-bot/data:/app/data \
  crypto-bot
```

### 4. Управление
```bash
# Логове
docker logs -f crypto-bot

# Стоп
docker stop crypto-bot

# Старт
docker start crypto-bot

# Рестарт
docker restart crypto-bot
```

---

## ❓ Troubleshooting

### Ботът не стартира
```bash
# Проверете логове
journalctl -u crypto-bot -n 50

# Проверете конфигурацията
cat /root/Crypto-signal-bot/bot.py | grep BOT_TOKEN

# Тествайте ръчно
cd /root/Crypto-signal-bot
source venv/bin/activate
python3 bot.py
```

### Out of Memory
```bash
# Добавете swap space
fallocate -l 2G /swapfile
chmod 600 /swapfile
mkswap /swapfile
swapon /swapfile
echo '/swapfile none swap sw 0 0' >> /etc/fstab
```

### Bot логове не се записват
```bash
# Проверете permissions
ls -la /root/Crypto-signal-bot/bot.log
chmod 644 /root/Crypto-signal-bot/bot.log
```

---

## 💰 Цени

| План | RAM | CPU | Storage | Цена/месец |
|------|-----|-----|---------|------------|
| Basic | 1GB | 1 | 25GB SSD | $6 |
| Basic | 2GB | 1 | 50GB SSD | $12 |
| Basic | 4GB | 2 | 80GB SSD | $24 |

**Препоръка:** Basic 1GB е напълно достатъчен за този бот.

---

## 📞 Поддръжка

За проблеми с deployment:
1. Проверете логове: `journalctl -u crypto-bot -f`
2. Тествайте ръчно: `python3 bot.py`
3. Проверете мрежата: `ping api.telegram.org`

Успех! 🚀
