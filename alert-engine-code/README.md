# PRODAFLT Alert Engine

Модуль автоматической оценки метрик кампаний и отправки алертов в Telegram.

## Архитектура

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   main.py   │────▶│   engine.py │────▶│  notifier.py│
│  (runner)   │     │ (evaluator) │     │  (telegram) │
└──────┬──────┘     └──────┬──────┘     └─────────────┘
       │                   │
       └───────────────────┘
              │
       ┌──────▼──────┐
       │  database.py│
       │  (Neon Pg)  │
       └─────────────┘
```

## Установка

```bash
cd alert-engine-code
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

## Конфигурация

```bash
cp .env.example .env
# Заполни реальные значения в .env — токены НЕ коммить!
```

## Использование

### Разовый запуск
```bash
python main.py run-once
```

### Демон (каждые 5 минут по умолчанию)
```bash
python main.py daemon
```

### Тест Telegram
```bash
python main.py test-alert
```

## Бизнес-логика

| Флаг   | Условия                                        | Действие               |
|--------|------------------------------------------------|------------------------|
| 🔴 RED | CPI ≥ $5  OR  CPC ≥ $2.5  OR  uEPC ≥ $8      | KILL / PAUSE           |
| 🟢 GREEN| uEPC < $4  AND  CPI ≤ $5  AND  ROI > 0      | SCALE — увеличить бюджет|
| 🟡 YELLOW| uEPC 4–8  OR  CPI подходит к $5             | WATCH — мониторить     |
| ⚪ WHITE| Недостаточно данных (< $20 spend, < 10 clicks)| Пропустить             |

## Confidence Levels

- **100%** — большая выборка (>$100 spend, >50 clicks), сигналы совпадают
- **95%** — хорошая выборка, уверенность высокая
- **85%** — средняя выборка, возможны колебания
- **70%** — малый объём данных, высокая неопределённость

## Deduplication

Одинаковые алерты (тот же campaign + тот же flag) не отправляются чаще чем раз в 30 минут — чтобы не спамить чат.

## Файлы

| Файл           | Назначение                          |
|----------------|-------------------------------------|
| `main.py`      | CLI: run-once / daemon / test-alert |
| `engine.py`    | RED/GREEN/YELLOW/WHITE evaluator    |
| `notifier.py`  | Telegram HTML-форматирование        |
| `database.py`  | SQLAlchemy ORM + helpers            |
| `models.py`    | Pydantic models                     |
| `config.py`    | pydantic-settings (.env)            |
| `.env.example` | Шаблон конфигурации (без токенов)   |
