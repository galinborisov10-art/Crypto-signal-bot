# ============================================
# DEPLOYMENT GUIDE - DigitalOcean
# ============================================

## 🚀 МЕТОД 1: GitHub Actions (Автоматичен)

### Настройка на GitHub Secrets:
1. Отиди на GitHubRepo → Settings → Secrets and variables → Actions
2. Добави следните secrets:
   - `DO_HOST` - IP адрес на сървъра (напр. 159.89.123.456)
   - `DO_USERNAME` - потребителско име (обикновено "root")
   - `DO_SSH_KEY` - SSH private key (цялото съдържание на ~/.ssh/id_rsa)
   - `DO_PORT` - SSH порт (по подразбиране 22)

### Автоматично deployment:
- При всеки `git push` към `main` branch
- Или ръчно от GitHub → Actions → "Auto Deploy to DigitalOcean" → Run workflow

---

## 🔄 МЕТОД 2: Server Script (update_bot.sh)

### На сървъра:
```bash
cd ~/Crypto-signal-bot  # или твоята директория
./update_bot.sh
```

### Какво прави:
1. Backup на конфигурация
2. Git pull от GitHub
3. Update на dependencies
4. Restart на PM2

---

## 📱 МЕТОД 3: Telegram Command

### В Telegram:
1. Влез като админ: `/admin_login`
2. Изпълни update: `/auto_update`

### Изисквания:
- Трябва да си admin (парола: 8109)
- update_bot.sh трябва да съществува на сървъра
- PM2 трябва да е инсталиран

---

## ⚙️ ПЪРВОНАЧАЛНА НАСТРОЙКА НА СЪРВЪРА

### 1. Инсталация на зависимости:
```bash
# Node.js и PM2
curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
sudo apt-get install -y nodejs
sudo npm install -g pm2

# Python и pip
sudo apt-get update
sudo apt-get install -y python3 python3-pip git

# Clone проекта
cd ~
git clone https://github.com/galinborisov10-art/Crypto-signal-bot.git
cd Crypto-signal-bot
```

### 2. Инсталация на Python dependencies:
```bash
pip3 install -r requirements.txt
```

### 3. Конфигуриране на .env файл:
```bash
nano .env
```

Попълни:
```
TELEGRAM_BOT_TOKEN=your_token_here
OWNER_CHAT_ID=your_chat_id
```

### 4. Стартиране с PM2:
```bash
pm2 start ecosystem.config.js
pm2 save
pm2 startup
```

### 5. Направи update_bot.sh изпълним:
```bash
chmod +x update_bot.sh
chmod +x install_dependencies.sh
```

---

## 🔐 SSH SETUP за GitHub Actions

### Генериране на SSH ключ:
```bash
ssh-keygen -t rsa -b 4096 -C "github-actions"
```

### Добави публичния ключ към сървъра:
```bash
cat ~/.ssh/id_rsa.pub >> ~/.ssh/authorized_keys
```

### Копирай private key за GitHub:
```bash
cat ~/.ssh/id_rsa
```

Копирай OUTPUT и го постави в GitHub Secret `DO_SSH_KEY`

---

## 📊 МОНИТОРИНГ

### PM2 команди:
```bash
pm2 list              # Виж статус
pm2 logs crypto-bot   # Виж логове
pm2 restart crypto-bot # Рестартирай
pm2 stop crypto-bot   # Спри
pm2 monit             # Real-time monitoring
```

### Проверка на логове:
```bash
tail -f logs/pm2-combined.log
tail -f bot.log
```

---

## ✅ ТЕСТВАНЕ

### Тест на update скрипта:
```bash
./update_bot.sh
```

### Тест на GitHub Actions:
1. Направи промяна в README
2. Commit и push
3. Провери GitHub Actions tab

### Тест на Telegram команда:
1. `/admin_login` → въведи 8109
2. `/auto_update`
3. Чакай за нотификация

---

## 🚨 TROUBLESHOOTING

### Проблем: PM2 не е инсталиран
```bash
sudo npm install -g pm2
```

### Проблем: Python модули липсват
```bash
./install_dependencies.sh
```

### Проблем: Git конфликти
```bash
git stash
git pull
git stash pop
```

### Проблем: Permission denied
```bash
chmod +x update_bot.sh
chmod +x install_dependencies.sh
```

---

## 🎯 ВСИЧКИ 3 МЕТОДА РАБОТЯТ НЕЗАВИСИМО!

✅ GitHub Actions - автоматично при push
✅ update_bot.sh - ръчно от сървъра
✅ /auto_update - от Telegram

Избери метода, който ти е най-удобен! 🚀
