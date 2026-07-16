# PRODAFLT — Руководство по запуску

> **Цель:** Запустить полноценную систему PRODAFLT (7 Telegram-ботов + FastAPI + Alert Engine + Neon PostgreSQL) за 60 минут.
>
> ☁️ **Деплой в облако без локального Python:** см. [`DEPLOY_CLOUD.md`](DEPLOY_CLOUD.md) — Railway, Render, Docker

---

## 📋 Чек-лист перед стартом

- [ ] Python 3.11+ установлен (`python --version`) — *не нужно для облачного деплоя*
- [ ] Git установлен (`git --version`)
- [ ] Доступ к 7 токенам Telegram BotFather (ниже)
- [ ] Аккаунт на [kimi.com](https://kimi.com) (для создания Claw-агентов)
- [ ] Проект склонирован или распакован в рабочую папку

---

## 📋 Чек-лист перед стартом

- [ ] Python 3.11+ установлен (`python --version`)
- [ ] Git установлен (`git --version`)
- [ ] Доступ к 7 токенам Telegram BotFather (ниже)
- [ ] Аккаунт на [kimi.com](https://kimi.com) (для создания Claw-агентов)
- [ ] Проект склонирован или распакован в рабочую папку

**Токены ботов (уже получены):**

| Бот | Токен | Роль |
|---|---|---|
| Router | `8748643129:AAEo00K8I97uM4MsM_d0-qxZi3Vo4s09dk4` | Маршрутизатор задач |
| Researcher | `8914645414:AAGv0-qDxdfB6p6f6Fxb8L5NTq5KkhYVxmE` | Исследование креативов |
| Compliance | `8761428013:AAGXQs3VMbl3T9PCElLsQUdjwuRXnhiTTXA` | Проверка на бан/забастовки |
| Creative | `8738935313:AAH6vzsejIV3-Zv6lUprOirXIwxFSmb6PWk` | Генерация креативов |
| Meta | `8884365881:AAHcXgsRV223jlVPbwHb_2uYtbi4GaU4qfU` | Мета-анализ и дайджесты |
| Data | `8742741388:AAEvnLIYlhimoqkVm_hQyiHKlYdsJDVfYN0` | Аналитика отчётов |
| Tech | `8742741388:AAEvnLIYlhimoqkVm_hQyiHKlYdsJDVfYN0` | Техлид и архитектура |
| Parser | `8660148436:AAEvXL93FfwfBHh9TZ_6wqtG40TYJUAJLWY` | Сбор ссылок из чатов |

**API-ключи:**
- Kimi API: `sk-kimi-6lY448FWbhJrOmWCcQxUO5d04EfWiCHYrMpyI0JCrlhjTtvKKWPoJ1FaSRoDdfWr`
- Neon DB: уже в `.env`

---

## 🔧 Шаг 1. Подготовка окружения

### 1.1 Перейди в папку проекта

```bash
cd D:\ProdAFLT\ProdAFLT
# или
cd /d/ProdAFLT/ProdAFLT
```

### 1.2 Создай виртуальное окружение

```bash
python -m venv venv
```

**Windows:**
```bash
venv\Scripts\activate
```

**macOS/Linux:**
```bash
source venv/bin/activate
```

### 1.3 Установи зависимости

```bash
pip install -r requirements.txt
```

> Если ошибка — попробуй `pip install --upgrade pip` и повтори.

---

## 🔐 Шаг 2. Проверка `.env` (уже заполнен)

Файл `.env` создан и заполнён в корне проекта. **Все значения уже на месте:**

| Переменная | Значение |
|---|---|
| `PARSER_BOT_TOKEN` | `8660148436:AAEvXL93FfwfBHh9TZ_6wqtG40TYJUAJLWY` |
| `ADMIN_CHAT_ID` | `841697832` |
| `GROUP_CHAT_ID` | `-5408190148` |

> ⚠️ **НЕ коммить `.env` в Git!** Он уже в `.gitignore`.

---

## 🤖 Шаг 3. Создание 7 Kimi Claw агентов

Для каждого из 7 агентов (Router, Researcher, Compliance, Creative, Meta, Data, Tech) выполни одну и ту же последовательность на [kimi.com/bot](https://kimi.com/bot).

### 3.1 Общий порядок для каждого агента

```
kimi.com/bot
    ↓
Нажми "Create" (создать нового бота)
    ↓
Вкладка "Identity" (Личность)
    ↓
Вставь Soul Prompt из файла (см. таблицу ниже)
    ↓
Вкладка "Telegram"
    ↓
Вставь токен бота
    ↓
Нажми "Connect"
    ↓
В чате с ботом напиши: /cron
    ↓
Вставь HEARTBEAT-расписание (см. ниже)
    ↓
Готово!
```

### 3.2 Soul Prompts — откуда брать

Soul Prompt для каждого агента лежит в папке `prodaflt/prompts/`:

| Агент | Файл Soul Prompt |
|---|---|
| Router | `prodaflt/prompts/router_soul.md` |
| Researcher | `prodaflt/prompts/researcher_soul.md` |
| Compliance | `prodaflt/prompts/compliance_soul.md` |
| Creative | `prodaflt/prompts/creative_soul.md` |
| Meta | `prodaflt/prompts/meta_master_soul.md` |
| Data | `prodaflt/prompts/data_analyst_soul.md` |
| Tech | `prodaflt/prompts/tech_lead_soul.md` |

**Как вставить:** открой файл → скопируй ВЕСЬ текст → вставь в поле Soul Prompt на kimi.com.

### 3.3 HEARTBEAT — периодические задачи

Для каждого агента в чате с ботом отправь команду `/cron` и вставь соответствующее расписание:

#### 🤖 Router (Маршрутизатор)
```
Каждые 5 минут — проверь очередь задач в таблице tasks.
Если есть задачи со статусом new — распредели их по агентам
(используй /api/tasks/assign через FastAPI).
```

#### 🔍 Researcher (Исследователь)
```
Каждые 30 минут — проверь таблицу links.
Если есть ссылки со статусом new — проанализируй их:
1. Скачай видео/скриншот
2. Определи платформу, жанр, хуки
3. Запиши результат в content_analysis
4. Обнови статус ссылки на analyzed
```

#### 🛡️ Compliance (Комплаенс)
```
Вторник и четверг в 12:00 — аудит:
1. Проверь все активные креативы на риск бана
2. Проверь актуальность гео-ограничений
3. Отправь отчёт в ADMIN_CHAT
```

#### 🎨 Creative (Креативщик)
```
Каждый день в 09:17 — утренний бриф:
1. Возьми топ-5 креативов из links (по score)
2. Сгенерируй 3 новых варианта под каждый
3. Запиши в таблицу creative_requests
```

#### 🧠 Meta (Мета-аналитик)
```
Каждый понедельник в 10:00 — дайджест:
1. Собери статистику за неделю
2. Найди паттерны в успешных креативах
3. Отправь стратегический отчёт в ADMIN_CHAT
```

#### 📊 Data (Аналитик)
```
Каждый день в 07:00 — утренний отчёт:
1. Подгрузи метрики из campaign_metrics
2. Рассчитай CPI, CPC, uEPC, ROI
3. Отправь дашборд в ADMIN_CHAT
```

#### 🔧 Tech (Техлид)
```
Каждую пятницу в 18:00 — аудит инфраструктуры:
1. Проверь статус всех ботов (ping)
2. Проверь размер таблиц, наличие бэкапов
3. Отправь infra-отчёт в ADMIN_CHAT
```

---

## 🚀 Шаг 4. Запуск Parser Bot

Parser Bot — это единственный бот, который работает как standalone Python-приложение (не через Kimi Claw). Он слушает сообщения в Telegram-группе и сохраняет ссылки в БД.

### 4.1 Добавь Parser Bot в рабочую группу

1. Найди бота `@prodaflt_parser_bot` (или как назвал)
2. Добавь его в рабочую группу `GROUP_CHAT_ID`
3. Выдай права администратора (чтобы видел все сообщения)

### 4.2 Запусти Parser Bot

```bash
# Из корня проекта, с активированным venv
python -m prodaflt.bots.parser.bot
```

**Ожидаемый вывод:**
```
2025-07-16 10:00:00 [INFO] parser_bot: Bot prodaflt_parser_bot started
2025-07-16 10:00:00 [INFO] parser_bot: Listening for links in group -1001234567890
```

### 4.3 Проверь работу

1. Отправь любую ссылку в рабочую группу (например, `https://instagram.com/reel/ABC123`)
2. В логах должно появиться:
   ```
   [INFO] parser_bot: Link detected: https://instagram.com/reel/ABC123
   [INFO] parser_bot: Enqueued link for user @username
   ```
3. Через 30 секунд (batch timeout) ссылка появится в БД:
   ```sql
   SELECT * FROM links WHERE url LIKE '%instagram%';
   ```

---

## 🌐 Шаг 5. Запуск FastAPI (Backend)

FastAPI предоставляет REST API для всех агентов: задачи, ссылки, метрики, алерты.

### 5.1 Запуск

```bash
# Из корня проекта
uvicorn prodaflt.api.app.main:app --host 0.0.0.0 --port 8000 --reload
```

**Ожидаемый вывод:**
```
INFO:     Started server process [12345]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to stop)
```

### 5.2 Проверь endpoints

Открой в браузере или используй curl:

```bash
# Health check
curl http://localhost:8000/health

# Swagger UI (документация API)
open http://localhost:8000/docs

# Список пользователей
curl http://localhost:8000/api/users/

# Статистика дашборда
curl http://localhost:8000/api/stats/dashboard

# Создать задачу
curl -X POST http://localhost:8000/api/tasks \
  -H "Content-Type: application/json" \
  -d '{"title":"Test task","assignee":"researcher","priority":"high"}'
```

---

## 🔔 Шаг 6. Запуск Alert Engine

Alert Engine анализирует метрики кампаний и отправляет алерты (KILL / SCALE / WATCH) в Telegram.

### 6.1 Запуск

```bash
python -m prodaflt.bots.alert_engine.main
```

### 6.2 Проверь тесты

```bash
cd prodaflt/bots/alert_engine
python -m pytest tests.py -v
```

**Ожидаемый результат:**
```
test_red_cpi_kill PASSED
test_red_cpc_kill PASSED
test_red_uepc_kill PASSED
test_red_roi_kill PASSED
test_green_scale PASSED
test_yellow_watch_uepc PASSED
test_white_low_spend PASSED
...
```

### 6.3 Проверь алерты вручную

```bash
# Добавь тестовые метрики через API
curl -X POST http://localhost:8000/api/campaign-metrics \
  -H "Content-Type: application/json" \
  -d '{
    "creative_code": "TEST-001",
    "spend": 250.00,
    "clicks": 120,
    "installs": 30,
    "cpi": 6.00,
    "cpc": 1.50,
    "uepc": 3.50,
    "roi": 0.25
  }'
```

Alert Engine должен отправить сообщение в ADMIN_CHAT:  
**"🚨 RED (KILL) — TEST-001: CPI $6.00 ≥ $5.00 (confidence: 100%)"**

---

## ✅ Шаг 7. Финальная проверка

### 7.1 Проверь все компоненты

| Компонент | Команда проверки | Ожидаемый результат |
|---|---|---|
| Neon DB | `psql $DATABASE_URL -c "SELECT COUNT(*) FROM users;"` | `7` |
| Parser Bot | `python -m prodaflt.bots.parser.bot` | Стартует, слушает группу |
| FastAPI | `curl http://localhost:8000/health` | `{"status":"ok"}` |
| Alert Engine | `python -m pytest tests.py` | Все тесты PASSED |
| Kimi Claw агенты | Напиши каждому боту `/start` | Ответ с именем агента |

### 7.2 End-to-end тест

1. Отправь ссылку в рабочую группу → Parser Bot сохраняет её
2. Researcher (по крону) анализирует ссылку
3. Creative (по крону) генерирует варианты
4. Data (по крону) считает метрики
5. Alert Engine реагирует на аномалии

---

## 🐛 Troubleshooting

### Проблема: Parser Bot не видит сообщения в группе
**Решение:** Убедись, что бот добавлен в группу И имеет права администратора. Privacy Mode в @BotFather должен быть **ВЫКЛЮЧЕН**.

### Проблема: FastAPI не подключается к БД
**Решение:** Проверь `DATABASE_URL` в `.env`. Убедись, что в URL есть `?sslmode=require`.

### Проблема: Kimi Claw агент не отвечает
**Решение:** Проверь, что токен введён правильно на kimi.com. Пересоздай подключение Telegram.

### Проблема: Alert Engine не отправляет алерты
**Решение:** Проверь `ADMIN_CHAT_ID` в `.env`. Убедись, что бот может писать в личку (напиши ему `/start`).

---

## 📁 Структура проекта (для справки)

```
D:\ProdAFLT\ProdAFLT\
├── .env                          # Секреты (НЕ коммитить!)
├── requirements.txt              # Python-зависимости
├── pyproject.toml               # Конфигурация проекта
│
├── prodaflt/
│   ├── api/app/                  # FastAPI сервер
│   │   ├── main.py              # Точка входа
│   │   ├── routers/             # API endpoints
│   │   └── models.py            # Pydantic модели
│   │
│   ├── bots/
│   │   ├── parser/              # Parser Bot (standalone)
│   │   │   ├── bot.py
│   │   │   ├── link_parser.py
│   │   │   └── database.py
│   │   └── alert_engine/        # Alert Engine
│   │       ├── engine.py
│   │       ├── tests.py
│   │       └── notifier.py
│   │
│   ├── prompts/                 # Soul Prompts для Kimi Claw
│   │   ├── router_soul.md
│   │   ├── researcher_soul.md
│   │   ├── creative_soul.md
│   │   ├── meta_master_soul.md
│   │   ├── data_analyst_soul.md
│   │   ├── tech_lead_soul.md
│   │   └── compliance_soul.md
│   │
│   ├── skills/                  # Пайплайны агентов
│   │   └── content_researcher/
│   │
│   └── config/                  # Настройки
│       ├── settings.py
│       └── database.py
│
└── scripts/
    ├── seed_database.py         # Заполнение тестовыми данными
    └── health_check.py          # Проверка здоровья системы
```

---

## 🎯 Следующие шаги после запуска

1. **Подключи Keitaro / Facebook Ads API** — для автоматической загрузки метрик
2. **Настрой CI/CD** — GitHub Actions для автодеплоя
3. **Добавь мониторинг** — Sentry для отслеживания ошибок
4. **Масштабируй** — Railway / VPS для 24/7 работы

---

*PRODAFLT v0.1.0 — Система управления гемблинг-креативами*  
*Запущено: ___ дата ___*  
*Ответственный: Даниил*
