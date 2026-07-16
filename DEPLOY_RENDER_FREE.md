# PRODAFLT — Деплой на Render (Free Tier)

> **Затраты:** $0. Время: ~15 минут.

---

## 📋 Что будет развёрнуто

| Сервис | Тип | Статус на Free |
|---|---|---|
| `prodaflt-api` | Web (FastAPI) | Free (sleep после 15 мин idle) |
| `prodaflt-parser` | Background Worker | Free (24/7, не засыпает!) |
| `prodaflt-alerts` | Background Worker | Free (24/7, не засыпает!) |

**Background Workers на Render Free работают круглосуточно** — это главное преимущество.

Web Service (API) "засыпает" после 15 минут без запросов, но Kimi Claw агенты делают запросы регулярно (каждые 5–30 минут), так что API почти всегда "бодрствует".

---

## 🔧 Шаг 1. Запушь проект на GitHub

### 1.1 Создай репозиторий на GitHub

1. Открой [github.com/new](https://github.com/new)
2. Название: `prodaflt`
3. **Обязательно:** выбери **Public** (иначе Render не подключится на Free)
4. Нажми **Create repository**

### 1.2 Запушь код

```bash
# В папке проекта (D:\ProdAFLT\ProdAFLT)
git init
git add .
git commit -m "PRODAFLT v0.1.0 — Render Free deploy"

# Замени YOUR_USERNAME на свой ник GitHub
git remote add origin https://github.com/YOUR_USERNAME/prodaflt.git
git branch -M main
git push -u origin main
```

> 💡 **Важно:** Файл `.env` уже в `.gitignore`, он не попадёт в GitHub. Секреты будем вводить в Render отдельно.

---

## 🚀 Шаг 2. Регистрация на Render

1. Перейди на [render.com](https://render.com)
2. Нажми **Get Started for Free**
3. Выбери **Sign up with GitHub**
4. Дай доступ Render к своим репозиториям (выбирай только `prodaflt` для безопасности)

---

## 🚀 Шаг 3. Деплой через Blueprint

### 3.1 Создай Blueprint

1. В дашборде Render нажми **New +** → **Blueprint**
2. Выбери репозиторий `YOUR_USERNAME/prodaflt`
3. Render найдёт файл `render.yaml` и покажет 3 сервиса:
   - `prodaflt-api` (Web)
   - `prodaflt-parser` (Worker)
   - `prodaflt-alerts` (Worker)
4. Нажми **Apply**

### 3.2 Дождись первого деплоя

Render автоматически:
- Установит Python 3.11
- Установит зависимости из `requirements.txt`
- Запустит сервисы

Это занимает 3–5 минут. Статус сервисов станет **Live** (зелёный кружок).

---

## 🔐 Шаг 4. Добавь Environment Variables

**Это самый важный шаг!** Без переменных окружения боты не запустятся.

### 4.1 Открой каждый сервис

В дашборде Render кликни на сервис → вкладка **Environment**.

### 4.2 Добавь переменные для ВСЕХ трёх сервисов

Скопируй все строки из файла `.env` и вставь как Environment Variables.

**Минимальный набор (обязательно для всех сервисов):**

| Ключ | Значение |
|---|---|
| `DATABASE_URL` | `postgresql://neondb_owner:npg_vNClUtuM20EQ@ep-bitter-waterfall-ajf1xpzc-pooler.c-3.us-east-2.aws.neon.tech/neondb?channel_binding=require&sslmode=require` |
| `ROUTER_BOT_TOKEN` | `8748643129:AAEo00K8I97uM4MsM_d0-qxZi3Vo4s09dk4` |
| `RESEARCHER_BOT_TOKEN` | `8914645414:AAGv0-qDxdfB6p6f6Fxb8L5NTq5KkhYVxmE` |
| `COMPLIANCE_BOT_TOKEN` | `8761428013:AAGXQs3VMbl3T9PCElLsQUdjwuRXnhiTTXA` |
| `CREATIVE_BOT_TOKEN` | `8738935313:AAH6vzsejIV3-Zv6lUprOirXIwxFSmb6PWk` |
| `META_BOT_TOKEN` | `8884365881:AAHcXgsRV223jlVPbwHb_2uYtbi4GaU4qfU` |
| `DATA_BOT_TOKEN` | `8742741388:AAEvnLIYlhimoqkVm_hQyiHKlYdsJDVfYN0` |
| `TECH_BOT_TOKEN` | `8742741388:AAEvnLIYlhimoqkVm_hQyiHKlYdsJDVfYN0` |
| `PARSER_BOT_TOKEN` | `8660148436:AAEvXL93FfwfBHh9TZ_6wqtG40TYJUAJLWY` |
| `ADMIN_CHAT_ID` | `841697832` |
| `GROUP_CHAT_ID` | `-5408190148` |
| `KIMI_API_KEY` | `sk-kimi-6lY448FWbhJrOmWCcQxUO5d04EfWiCHYrMpyI0JCrlhjTtvKKWPoJ1FaSRoDdfWr` |
| `KIMI_API_BASE_URL` | `https://api.moonshot.cn/v1` |
| `PROJECT_ENVIRONMENT` | `production` |

### 4.3 Перезапусти сервисы

После добавления переменных Render автоматически перезапустит сервисы.

---

## ✅ Шаг 5. Проверка деплоя

### 5.1 Проверь API

Открой URL `prodaflt-api` (вида `https://prodaflt-api.onrender.com`):

```
https://prodaflt-api.onrender.com/health
```

Должно вернуть:
```json
{"status": "ok"}
```

### 5.2 Проверь Parser Bot

1. Отправь ссылку в рабочую группу Telegram (`-5408190148`)
2. В Render Dashboard → `prodaflt-parser` → **Logs** должно появиться:
   ```
   [INFO] parser_bot: Link detected: https://instagram.com/...
   ```

### 5.3 Проверь Alert Engine

Через API создай тестовую метрику:

```bash
curl -X POST https://prodaflt-api.onrender.com/api/campaign-metrics \
  -H "Content-Type: application/json" \
  -d '{
    "creative_code": "TEST-RENDER",
    "spend": 250.00,
    "clicks": 120,
    "installs": 30,
    "cpi": 6.00,
    "roi": 0.25
  }'
```

В логах `prodaflt-alerts` должно появиться:
```
[ALERT] RED (KILL) — TEST-RENDER: CPI $6.00 ≥ $5.00
```

---

## 🔄 Шаг 6. Автодеплой при обновлении

Render автоматически перезапускает сервисы при каждом `git push` в `main`.

```bash
# Локально внеси изменения
git add .
git commit -m "Обновление: новый алгоритм скоринга"
git push origin main
# Render автоматически пересоберёт и перезапустит всё
```

---

## 🐛 Troubleshooting

### "Build failed" — ошибка сборки

**Решение:** Проверь логи сборки (Build Logs). Частые причины:
- Отсутствует `requirements.txt` в корне
- Какой-то пакет требует системных библиотек

**Фикс:** В `requirements.txt` убери `psycopg2-binary`, оставь только `asyncpg` (уже есть).

### Parser Bot не видит сообщения

**Решение:**
1. Проверь `PARSER_BOT_TOKEN` в Environment Variables
2. Убедись, что бот `@prodaflt_parser_bot` добавлен в группу и имеет права администратора
3. В @BotFather проверь, что **Privacy Mode ВЫКЛЮЧЕН**

### API возвращает 502 Bad Gateway

**Решение:** Web Service "заснул" из-за отсутствия запросов. Подожди 30 секунд — он проснётся.

**Профилактика:** Kimi агенты делают запросы каждые 5–30 минут, так что API редко засыпает.

---

## 📊 Лимиты Render Free

| Ресурс | Лимит |
|---|---|
| Web Service | 1 (sleep после 15 мин idle) |
| Background Workers | Неограничено (Free tier) |
| RAM | 512 MB на сервис |
| Диск | 1 GB |
| Трафик | 100 GB/мес |

---

## 🎯 Следующие шаги

1. **Настрой Kimi Claw агентов** — по инструкции `LAUNCH_GUIDE.md` (Шаг 3)
2. **Укажи URL API в Soul Prompts** — замени `localhost:8000` на `https://prodaflt-api.onrender.com`
3. **Добавь мониторинг** — Render отправляет email при падении сервиса

---

*PRODAFLT on Render — Free Tier Deploy*
