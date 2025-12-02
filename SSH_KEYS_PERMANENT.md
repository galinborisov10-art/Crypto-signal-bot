# 🔑 PERMANENT SSH KEYS - НЕ СМЕНЯЙ!

## ⚠️ ВАЖНО: Тези ключове са ПОСТОЯННИ! Използвай ги винаги!

---

## 🔑 PUBLIC KEY (добави на DigitalOcean сървъра)

Изпълни на сървъра **САМО ВЕДНЪЖ**:

```bash
ssh root@YOUR_SERVER_IP

# Добави този public key:
echo "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIAVuikGhIXeO5UHmInzqK6dK55s3RSQIMbSHdr6XBEsb github-actions-permanent" >> ~/.ssh/authorized_keys

chmod 600 ~/.ssh/authorized_keys

echo "✅ Public key добавен!"

exit
```

---

## 🔐 PRIVATE KEY (сложи в GitHub Secret DO_SSH_KEY)

1. Отиди на: https://github.com/galinborisov10-art/Crypto-signal-bot/settings/secrets/actions
2. Намери **DO_SSH_KEY** → Update
3. Копирай ТОЧНО това (с BEGIN/END):

```
-----BEGIN OPENSSH PRIVATE KEY-----
b3BlbnNzaC1rZXktdjEAAAAABG5vbmUAAAAEbm9uZQAAAAAAAAABAAAAMwAAAAtzc2gtZW
QyNTUxOQAAACAFbopBoSF3juVB5iJ86iunSuebN0UkCDG0h3a+lwRLGwAAAKBwDE4DcAxO
AwAAAAtzc2gtZWQyNTUxOQAAACAFbopBoSF3juVB5iJ86iunSuebN0UkCDG0h3a+lwRLGw
AAAECKfyQLSYtxEHnLm4DRxA70Qkl0vatCFqDqx3UN3CCOIwVuikGhIXeO5UHmInzqK6dK
55s3RSQIMbSHdr6XBEsbAAAAGGdpdGh1Yi1hY3Rpb25zLXBlcm1hbmVudAECAwQF
-----END OPENSSH PRIVATE KEY-----
```

4. Save

---

## ✅ СЛЕД ТОВА:

Направи тестов push:

```bash
echo "# Test" >> README.md
git add README.md
git commit -m "Test auto-deploy"
git push
```

Auto-deploy ще работи! 🚀

---

## 📌 ВАЖНО:

- **НЕ ИЗТРИВАЙ** този файл
- **НЕ СМЕНЯЙ** ключовете
- Ако трябва да ги добавиш отново, **използвай тези СЪЩИТЕ** ключове
- Ако загубиш файла, генерирай нови и започни отново

---

**Дата на генериране:** 2025-12-02
