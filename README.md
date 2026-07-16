# PRODAFLT Multi-Agent Gambling Creative System

## Архитектура

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   Router    │────▶│ 7 Domain    │────▶│   Parser    │
│  (Kimi Claw)│     │  Agents     │     │   Bot       │
└─────────────┘     └─────────────┘     └─────────────┘
       │                   │                   │
       └───────────────────┼───────────────────┘
                           ▼
              ┌────────────────────┐
              │  Neon PostgreSQL   │
              │  (prodaflt_registry)│
              └────────────────────┘
                           │
              ┌────────────┼────────────┐
              ▼            ▼            ▼
         ┌────────┐  ┌────────┐  ┌────────┐
         │ FastAPI│  │  Web   │  │ Alert  │
         │  API   │  │Service │  │ Engine │
         └────────┘  └────────┘  └────────┘
```

## Компоненты

| Компонент | Технология | Статус |
|-----------|-----------|--------|
| **Router** | Kimi Claw | Нужно создать в kimi.com |
| **Researcher** | Kimi Claw + skill | Нужно создать в kimi.com |
| **Compliance** | Kimi Claw | Нужно создать в kimi.com |
| **Creative** | Kimi Claw + skill | Нужно создать в kimi.com |
| **Meta Master** | Kimi Claw | Нужно создать в kimi.com |
| **Data Analyst** | Kimi Claw + skill | Нужно создать в kimi.com |
| **Tech Lead** | Kimi Claw | Нужно создать в kimi.com |
| **Parser Bot** | Python + python-telegram-bot | Код готов |
| **FastAPI** | Python + FastAPI | Код готов |
| **Alert Engine** | Python | Код готов |
| **База данных** | Neon PostgreSQL | ✅ Готова |

## Быстрый старт

### 1. Настройка окружения

```bash
cp .env.example .env
# Отредактируй .env — вставь реальные токены
```

### 2. Установка зависимостей

```bash
pip install -r requirements.txt
```

### 3. Проверка подключения

```bash
python prodaflt/scripts/health_check.py
```

### 4. Запуск Parser Bot

```bash
python -m prodaflt.bots.parser.bot
```

### 5. Запуск FastAPI

```bash
uvicorn prodaflt.api.app.main:app --reload --port 8080
```

### 6. Запуск Alert Engine

```bash
python -m prodaflt.bots.alert_engine.main
```

## Kimi Claw — создание агентов

1. Открой [kimi.com/bot](https://kimi.com/bot)
2. Создай 7 ботов по именам из `.env.example`
3. Вставь Soul Prompt из `prodaflt/prompts/`
4. Подключи Telegram токены
5. Настрой HEARTBEAT через `/cron`

## Структура проекта

```
prodaflt/
├── api/                    # FastAPI сервис
│   ├── app/
│   │   ├── main.py
│   │   ├── routers/
│   │   └── models.py
├── bots/
│   ├── parser/             # Parser Bot
│   └── alert_engine/       # Alert Engine
├── config/                 # Настройки
├── models/                 # SQLAlchemy ORM
├── prompts/                # Soul Prompts для Claw
├── scripts/                # Утилиты
└── skills/
    └── content_researcher/ # Pipeline скрапинга
```

## База данных

- **Проект:** `prodaflt-orchestrator` (Neon)
- **Таблицы:** `users`, `links`, `content_analysis`, `tz_specs`, `patterns`, `campaign_metrics`, `alerts_log`
- **Существующие:** `agents`, `tasks`, `metrics`, `workflows`, `messages`

## Команда

| Роль | Пользователь |
|------|-------------|
| Admin / TeamLead | durovscales |
| Bayer | chernov_1, danilorrel, gfftra |
| Design | only1showbizschool, mitrafq, Nepenthese |

## Лицензия

Private — для команды PRODAFLT.
