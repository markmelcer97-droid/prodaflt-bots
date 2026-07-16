# PRODAFLT — Деплой в облако

> **Быстрый старт:** 10 минут до рабочей системы в облаке. Локальный Python не нужен.

---

## 🛤️ Вариант 1: Railway (рекомендуется)

Railway — самый простой способ деплоя Python-приложений. Поддерживает автоскейлинг, приватные сети, managed PostgreSQL.

### Шаг 1. Подготовь репозиторий

```bash
# В корне проекта
git init
git add .
git commit -m "PRODAFLT v0.1.0 — ready for cloud deploy"
```

Создай пустой репозиторий на [GitHub](https://github.com/new) и запушь:

```bash
git remote add origin https://github.com/ТВОЙ_НИК/prodaflt.git
git branch -M main
git push -u origin main
```

### Шаг 2. Подключи Railway

1. Зарегистрируйся на [railway.app](https://railway.app) (через GitHub)
2. Нажми **"New Project"** → **"Deploy from GitHub repo"**
3. Выбери репозиторий `prodaflt`
4. Railway автоматически найдёт `railway.json` и `requirements.txt`

### Шаг 3. Добавь переменные окружения

В дашборде Railway → вкладка **"Variables"** добавь все из `.env`:

```
DATABASE_URL=postgresql://neondb_owner:... (твоя Neon строка)
ROUTER_BOT_TOKEN=8748643129:AAEo00K8I97uM4MsM_d0-qxZi3Vo4s09dk4
RESEARCHER_BOT_TOKEN=8914645414:AAGv0-qDxdfB6p6f6Fxb8L5NTq5KkhYVxmE
...
ADMIN_CHAT_ID=841697832
GROUP_CHAT_ID=-5408190148
KIMI_API_KEY=sk-kimi-...
```

> ⚠️ **Не коммить `.env` в Git!** Railway хранит секреты отдельно.

### Шаг 4. Добавь worker'ы (Parser + Alerts)

Railway создаст только web-сервис (FastAPI). Для ботов нужно добавить worker'ы:

```bash
# В дашборде Railway:
# 1. Нажми "New" → "Empty Service"
# 2. Выбери тот же GitHub-репозиторий
# 3. В настройках сервиса:
#    - Name: prodaflt-parser
#    - Start Command: python -m prodaflt.bots.parser.bot
# 4. Повтори для Alert Engine:
#    - Name: prodaflt-alerts
#    - Start Command: python -m prodaflt.bots.alert_engine.main
```

### Шаг 5. Проверь деплой

1. Открой URL web-сервиса (вида `https://prodaflt-api.up.railway.app`)
2. Перейди на `/health` — должно вернуть `{"status":"ok"}`
3. Parser Bot начнёт слушать группу автоматически

### Стоимость Railway

| Компонент | План | Цена |
|---|---|---|
| Web (FastAPI) | Starter | ~$5/мес |
| Parser Bot | Starter | ~$5/мес |
| Alert Engine | Starter | ~$5/мес |
| PostgreSQL | Neon (внешний) | Бесплатно (до 500 MB) |
| **Итого** | | **~$15/мес** |

---

## 🎨 Вариант 2: Render (бесплатный tier)

Render предлагает бесплатные worker'ы с ограничением: сервис "засыпает" после 15 минут без запросов (для web). Для ботов (background workers) — это не проблема.

### Шаг 1. Подготовь репозиторий

То же самое, что и для Railway:

```bash
git init && git add . && git commit -m "PRODAFLT v0.1.0"
# Push на GitHub
```

### Шаг 2. Создай сервисы через Blueprint

1. Зарегистрируйся на [render.com](https://render.com)
2. В дашборде нажми **"New"** → **"Blueprint"**
3. Подключи GitHub-репозиторий
4. Render найдёт `render.yaml` и создаст все сервисы автоматически:
   - `prodaflt-api` (Web Service)
   - `prodaflt-parser` (Background Worker)
   - `prodaflt-alerts` (Background Worker)

### Шаг 3. Добавь переменные окружения

Для каждого сервиса в дашборде Render → **"Environment"** добавь переменные из `.env`.

### Шаг 4. Перезапусти сервисы

Render автоматически деплоит при каждом push в `main`. Для первого запуска нажми **"Manual Deploy"**.

### Стоимость Render

| Компонент | План | Цена |
|---|---|---|
| Web Service | Free | $0 (засыпает через 15 мин) |
| Background Worker | Free | $0 (работает 24/7!) |
| PostgreSQL | Free | $0 (до 1 GB, 90 дней) |
| **Итого** | | **$0** |

> ⚠️ **Free Web Service** "засыпает" после 15 минут без запросов и просыпается ~30 секунд при первом запросе. Если это критично — апгрейд до Starter ($7/мес).

---

## 🐳 Вариант 3: Docker (любой хостинг / VPS)

Если есть свой сервер (VPS) или хочешь максимальный контроль:

### Шаг 1. Установи Docker

```bash
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER
```

### Шаг 2. Скопируй проект на сервер

```bash
scp -r D:/ProdAFLT/ProdAFLT user@your-server:/opt/prodaflt
ssh user@your-server
cd /opt/prodaflt
```

### Шаг 3. Запусти

```bash
# Создай .env на сервере (скопируй содержимое)
nano .env

# Запусти всё
docker-compose -f docker-compose.prod.yml up -d

# Проверь статус
docker-compose -f docker-compose.prod.yml ps
docker-compose -f docker-compose.prod.yml logs -f parser
```

### Шаг 4. Настрой reverse proxy (опционально)

Если нужен HTTPS + домен:

```bash
# Установи nginx + certbot
sudo apt install nginx certbot python3-certbot-nginx

# Конфиг nginx
sudo nano /etc/nginx/sites-available/prodaflt
```

```nginx
server {
    listen 80;
    server_name api.prodaflt.com;

    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

```bash
sudo ln -s /etc/nginx/sites-available/prodaflt /etc/nginx/sites-enabled/
sudo certbot --nginx -d api.prodaflt.com
sudo systemctl restart nginx
```

---

## 📊 Сравнение платформ

| Платформа | Сложность | Цена | Надёжность | Рекомендация |
|---|---|---|---|---|
| **Railway** | ⭐ Просто | $15/мес | ⭐⭐⭐⭐⭐ | Для production |
| **Render** | ⭐ Просто | $0 | ⭐⭐⭐☆☆ | Для старта / тестов |
| **VPS + Docker** | ⭐⭐⭐ Сложно | $5-10/мес | ⭐⭐⭐⭐☆ | Для гиков |
| **Heroku** | ⭐ Просто | $7/мес | ⭐⭐⭐⭐☆ | Альтернатива Railway |

---

## 🚀 Чек-лист после деплоя

- [ ] FastAPI отвечает на `/health`
- [ ] Parser Bot видит ссылки в группе
- [ ] Alert Engine отправляет тестовый алерт
- [ ] Kimi Claw агенты подключены к Telegram
- [ ] База данных доступна (Neon)

---

## 🆘 Troubleshooting

### "Build failed" на Railway/Render
**Решение:** Проверь `requirements.txt` — возможно, какой-то пакет требует системных библиотек. Добавь в `Dockerfile`:
```dockerfile
RUN apt-get update && apt-get install -y gcc libpq-dev
```

### Parser Bot не подключается к Telegram
**Решение:** Проверь `PARSER_BOT_TOKEN` в переменных окружения. Токен должен быть валидным и бот не должен быть заблокирован.

### База данных недоступна
**Решение:** Убедись, что `DATABASE_URL` содержит `?sslmode=require` для Neon. Проверь firewall (должен разрешать исходящие на порт 5432).

---

*PRODAFLT Cloud Deploy v0.1.0*  
*Railway / Render / Docker*
