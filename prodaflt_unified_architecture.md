# PRODAFLT: Сравнительный анализ двух подходов + Единая структура реализации

> Дата: 13 июля 2026
> Статус: Анализ завершен, структура на утверждение

---

## Часть 1. Идентификация двух подходов

### Подход A: "v3 / Claw-архитектура" (файлы 01-08)
**Концепция:** 7 Kimi Claw-агентов + 1 Python Parser Bot, облачная AI-инфраструктура
**Целевая аудитория:** Даниил (админ) + команда через Telegram
**Философия:** Максимально использовать готовые AI-возможности Kimi Claw (persistent memory, /cron, web search), минимум кода

### Подход B: "SCALE / Mercurio Group" (файлы scale_master, creative_brief, data_analyst, content_researcher, tech_lead)
**Концепция:** 5 Python Telegram-ботов + веб-сервис, self-hosted AI через Kimi API
**Целевая аудитория:** Danil / Phil / Afanasy + buyers + дизайнеры
**Философия:** Полный контроль над инфраструктурой, промышленная БД, автоматизация скрапинга, skills-based архитектура

---

## Часть 2. Матрица отличий (критические различия)

| Аспект | Подход A (v3/Claw) | Подход B (SCALE) | Вердикт |
|--------|-------------------|------------------|---------|
| **AI-движок** | Kimi Claw (облако, persistent memory) | Kimi API (moonshot-v1-8k, self-managed) | A проще, B контролируемее |
| **База данных** | Google Sheets (7 листов) | Neon PostgreSQL + SQLAlchemy ORM | B — промышленное решение |
| **Router/Orchestrator** | Router Bot (классификация + маршрутизация) | Orchestrator (распределение задач) | A четче по UX |
| **Количество ботов** | 7 Claw + 1 Parser | 5 Python ботов | A — доменная специализация |
| **Content Parser** | Python-бот в группе → Sheets | Content Bot (админ в ЛС → БД) | A — групповой сбор |
| **Бизнес-логика** | Общая архитектура | Детальные пороги (CPC≤2.5, CPI≤5, uEPC 4-6) | B — глубже |
| **Alert Engine** | Kill/Keep в Data Analyst | RED/GREEN/YELLOW + confidence levels + OCR | B — продвинутее |
| **Skills** | Soul Prompts + HEARTBEAT | 7 .skill файлов + Python-скрипты | B — модульнее |
| **API** | Нет (только Telegram + Sheets) | Flask API + REST endpoints | B — интегрируемее |
| **Веб-интерфейс** | Нет | React + TS + Tailwind + Telegram OAuth | B — масштабируемее |
| **Хостинг** | Claw в облаке, Parser на Railway | Railway + Docker + PostgreSQL + Redis | B — единая среда |
| **Коды контента** | Гибкий формат (любой) | Строгий (EN0017-92) | A — гибче, B — строже |
| **HEARTBEAT** | /cron в Claw | crontab + Python-скрипты | A — проще настроить |
| **Content Research** | 8 паттернов, ручной поиск | 9 форматов, скоринг, авто-скрапинг | B — автоматизированнее |
| **Compliance** | Отдельный агент от Meta Master | Есть, но менее детализирован | A — правильное разделение |
| **ТЗ** | P0/P1/P2 + гибкие коды | Frame-by-frame + strict codes | B — детальнее |
| **Meta Ads** | Meta Master (алгоритмы, CBO, CAPI) | Facebook Bot (отдельный) | A — встроен в домен |
| **Team UX** | Префиксы (!факт, !проект, !сайт) | Команды (/link, /tz, /metrics) | A — интуитивнее для новичков |
| **Деплой** | Создать бота в Kimi + токен | Docker + Makefile + scripts | B — воспроизводимее |
| **Стоимость** | Только хостинг Parser | Kimi API + Railway + Neon | A дешевле на старте |

---

## Часть 3. Лучшие решения из каждого подхода

### 🏆 Из Подхода A (v3/Claw) — что обязательно сохранить:

1. **Router как единая точка входа**
   - Проблема SCALE: 5 ботов с равным доступом → команда путается
   - Решение v3: Все запросы → Router → он решает куда → конкретный агент
   - Почему лучше: Не теряется контекст, централизованная маршрутизация, префиксы команд

2. **Разделение Compliance и Meta Master**
   - Проблема SCALE: Compliance + Meta сливаются в одном боте
   - Решение v3: Compliance = policy/баны/слова, Meta = алгоритмы/CBO/CAPI
   - Почему лучше: Разные домены не перегружают память, четкий фокус

3. **HEARTBEAT через /cron (встроенный)**
   - Проблема SCALE: Внешние crontab, нужен сервер
   - Решение v3: Каждый Claw сам выполняет по расписанию
   - Почему лучше: Нет инфраструктурных зависимостей, self-contained

4. **Гибкие коды контента (Name: ??? + любой ответ)**
   - Проблема SCALE: Строгий формат EN0017-92, админ вручную прописывает
   - Решение v3: Бот спрашивает, пользователь отвечает любым форматом
   - Почему лучше: Нет трения, работает с любой системой нейминга команды

5. **Матрица связей (8×8)**
   - Проблема SCALE: Неявные связи через БД
   - Решение v3: Таблица кто с кем общается и как
   - Почему лучше: Прозрачность архитектуры, onboarding новых членов команды

6. **Parser Bot отдельно от Claw**
   - Проблема SCALE: Content Bot читает только админа (в ЛС)
   - Решение v3: Parser в групповом чате, batch-запись, не ломается при спаме
   - Почему лучше: Команда кидает ссылки естественно, не думая о боте

7. **Team Brief с префиксами**
   - `!факт` — быстрый вопрос
   - `!проект` — архитектура/анализ
   - `!сайт` — создание файла
   - `!batch` — массовая задача
   - Почему лучше: Команда не учит сложные команды, использует естественный язык

### 🏆 Из Подхода B (SCALE) — что обязательно перенять:

1. **PostgreSQL вместо Google Sheets**
   - Проблема v3: Sheets = медленно, нет связей, нет транзакций, лимит 5M ячеек
   - Решение SCALE: SQLAlchemy ORM, foreign keys, enum types, JSONB
   - Почему лучше: Масштабируемость, целостность данных, сложные запросы

2. **Alert Engine (RED/GREEN/YELLOW + Confidence)**
   - Проблема v3: Kill/Keep — бинарное решение
   - Решение SCALE: 3 уровня + confidence (100%, 95%, 85%, 70%) + форматы алертов
   - Почему лучше: Градация риска, понятно когда нужен human override

3. **OCR Workflow для скриншотов**
   - Проблема v3: Ручной ввод метрик или чтение Sheets
   - Решение SCALE: Скрин → Image Analysis → Data Extraction → Validation → JSON
   - Почему лучше: Buyer's кидают скрин → система сама читает метрики

4. **Skills (.skill файлы)**
   - Проблема v3: Soul Prompts — монолитный текст
   - Решение SCALE: 7 отдельных skill'ов (content-researcher, video-scene-analysis и т.д.)
   - Почему лучше: Модульность, версионирование, переиспользование

5. **Content Research Pipeline (9 форматов + скоринг)**
   - Проблема v3: 8 паттернов, но без скоринга
   - Решение SCALE: Virality Score (0-10) × 0.6 + Adaptation Potential (0-10) × 0.4 = Final Score
   - Почему лучше: Автоматический отбор топ-15, не нужно вручную сортировать

6. **Frame-by-frame ТЗ с таймкодами**
   - Проблема v3: Общее описание ТЗ
   - Решение SCALE: Каждый кадр с таймкодом, описанием визуала, движений, эмоций, субтитров
   - Почему лучше: Дизайнеры получают точную инструкцию, меньше итераций

7. **Веб-сервис (Dashboard + Telegram OAuth)**
   - Проблема v3: Только Telegram, нет визуализации
   - Решение SCALE: React + карточки метрик + графики + таблицы + фильтры
   - Почему лучше: Команда видит статус всего пайплайна, не листает чаты

8. **Docker + Makefile + единый деплой**
   - Проблема v3: Создавать 7 ботов вручную через BotFather
   - Решение SCALE: `make install → make start → make bots-start`
   - Почему лучше: Воспроизводимость, onboarding за 5 минут

9. **Детальные бизнес-метрики (Hard thresholds)**
   - Проблема v3: Общие рекомендации
   - Решение SCALE: CPI ≥ $5 = kill, CPC ≥ $2.5 = kill, uEPC < $4 = scale, ABO $45-60, CBO $200-250
   - Почему лучше: Buyer's знают точные цифры, нет дискуссий

10. **Video Scene Analysis (ffmpeg + whisper + frames)**
    - Проблема v3: Ручной анализ референсов
    - Решение SCALE: Авто-скачивание → извлечение кадров → транскрипция → анализ hook/pacing/CTA
    - Почему лучше: Автоматизация 80% ручной работы Content Researcher

---

## Часть 4. Единая оптимальная архитектура (гибрид)

### 4.1 Концепция: "SCALE v3" — лучшее из обоих миров

```
┌─────────────────────────────────────────────────────────────┐
│                    ДАНИИЛ (Admin)                           │
│              Единая точка входа: @prodaflt_router_bot      │
└─────────────────────┬───────────────────────────────────────┘
                      │
        ┌─────────────┼─────────────┐
        │             │             │
   ┌────▼────┐   ┌────▼────┐   ┌────▼────┐
   │ Router  │   │ Domain  │   │ Parser  │
   │ (Claw)  │   │ Agents  │   │ (Python)│
   └────┬────┘   │ (Claw)  │   └────┬────┘
        │        └────┬────┘        │
        │             │             │
        └─────────────┼─────────────┘
                      │
        ┌─────────────▼─────────────┐
        │    Neon PostgreSQL        │
        │    (единая БД)            │
        │                           │
        │  • agents        • users  │
        │  • links         • tz     │
        │  • creatives     • metrics│
        │  • patterns      • alerts │
        │  • workflows     • tasks  │
        └─────────────┬─────────────┘
                      │
        ┌─────────────┼─────────────┐
        │             │             │
   ┌────▼────┐   ┌────▼────┐   ┌────▼────┐
   │  Web    │   │  API    │   │ Skills  │
   │Service  │   │(FastAPI)│   │ (.skill)│
   │(React)  │   │         │   │         │
   └─────────┘   └─────────┘   └─────────┘
```

### 4.2 Компоненты (9 ботов + сервис)

| # | Компонент | Тип | Технология | Откуда взято |
|---|-----------|-----|------------|-------------|
| 1 | **Router** | Claw | Kimi Claw + Soul Prompt | A — единая точка входа |
| 2 | **Researcher** | Claw | Kimi Claw + skill | A + B pipeline |
| 3 | **Compliance** | Claw | Kimi Claw + Soul Prompt | A — отдельный от Meta |
| 4 | **Creative** | Claw | Kimi Claw + skill | A + B frame-by-frame |
| 5 | **Meta Master** | Claw | Kimi Claw + Soul Prompt | A — алгоритмы/CBO |
| 6 | **Data Analyst** | Claw | Kimi Claw + skill | A + B Alert Engine |
| 7 | **Tech Lead** | Claw | Kimi Claw + Soul Prompt | A — инфраструктура |
| 8 | **Parser Bot** | Python | python-telegram-bot | A — групповой сбор |
| 9 | **API + Web** | Python + TS | FastAPI + React | B — промышленный стек |

### 4.3 База данных (гибридная схема)

Объединяем 7 листов Sheets (A) + 9 таблиц PostgreSQL (B):

```sql
-- Общие
agents (id, name, status, bot_username, specialization, heartbeat, soul_version)
users (telegram_id, username, role, team_role, is_active)

-- Content pipeline (от Parser → Creative)
links (link_id, url, platform, title, status, submitted_by, preview_url)
content_analysis (link_id, pattern, researcher_comment, compliance_status, creative_potential)
tz_specs (code_content, title, description, script[JSONB], visual_refs[JSONB], status)

-- Patterns & Research
patterns (name, description, examples[JSONB], frequency, week_of, metrics[JSONB])

-- Metrics & Alerts (от Data Analyst)
metrics (code_content, spend, clicks, installs, deposits, cpc, cpi, uepc, roi, status)
alerts_log (campaign_id, alert_type, flag, triggered_metrics, confidence, decision)
thresholds_config (metric_name, threshold_value, operator, action, flag)

-- Tasks & Workflows
tasks (title, description, status, agent_name, created_by)
workflows (name, status, steps[JSONB])
```

---

## Часть 5. Структура реализации (по шагам)

### 🔷 ФАЗА 0: Фундамент (День 1-3)

**Цель:** Инфраструктура, БД, Router, Parser

#### Шаг 0.1: Создать Neon PostgreSQL
```
1. Создать проект в Neon (prodaflt-db)
2. Создать базу prodaflt_registry
3. Выполнить SQL-миграцию (все таблицы из раздела 4.3)
4. Получить DATABASE_URL
5. Сохранить в .env
```
**Результат:** Единая БД для всех ботов и веб-сервиса.

#### Шаг 0.2: Создать 8 Telegram-ботов
```
1. @prodaflt_router_bot (Router)
2. @prodaflt_research_bot (Researcher)
3. @prodaflt_compliance_bot (Compliance)
4. @prodaflt_creative_bot (Creative)
5. @prodaflt_meta_bot (Meta Master)
6. @prodaflt_data_bot (Data Analyst)
7. @prodaflt_tech_bot (Tech Lead)
8. @prodaflt_parser_bot (Parser)
```
**Результат:** 8 токенов сохранены в .env.

#### Шаг 0.3: Развернуть Router (Claw)
```
1. kimi.com/bot → Create
2. Identity: Name = Router, Profession = Dispatcher
3. Soul: из 02_soul_prompts_v3.md (Router) + ссылка на Neon БД
4. Telegram: Settings → Chat Channels → токен router_bot
5. HEARTBEAT: /cron → daily 9:17 (брифинг)
6. Тест: написать "сделай ТЗ" → маршрутизация на Creative
```
**Результат:** Единая точка входа работает.

#### Шаг 0.4: Развернуть Parser Bot (Python)
```
1. Tech Lead (Claw) пишет код по spec 08_parser_spec.md
2. Но вместо Google Sheets → пишет в PostgreSQL (links таблица)
3. Batch-запись: buffer 10 msg или 30 сек
4. Деплой: Railway / VPS
5. Добавить в групповой чат команды
6. Тест: скинуть ссылку → через 30 сек в БД
```
**Результат:** Команда кидает ссылки, они попадают в БД.

---

### 🔷 ФАЗА 1: Domain Agents (День 4-7)

**Цель:** 6 специализированных агентов с skills

#### Шаг 1.1: Researcher (Claw + skill)
```
1. Создать Kimi Claw: @prodaflt_research_bot
2. Soul: из 02_soul_prompts_v3.md + skill content-researcher
3. Добавить pipeline: scrape → classify → score → filter
4. HEARTBEAT: daily 10:00 (тренды)
5. Интеграция: читает links из БД, пишет в content_analysis + patterns
```
**Результат:** Ежедневно 15 референсов с автоматическим скорингом.

#### Шаг 1.2: Compliance (Claw)
```
1. Создать Kimi Claw: @prodaflt_compliance_bot
2. Soul: из 02_soul_prompts_v3.md (Compliance)
3. Память: policy Meta/GEM, запрещенные слова, история банов
4. HEARTBEAT: Tue/Thu 12:00 (аудит)
5. Интеграция: читает links, пишет compliance_status
```
**Результат:** Pre-moderation перед созданием ТЗ.

#### Шаг 1.3: Creative (Claw + skill)
```
1. Создать Kimi Claw: @prodaflt_creative_bot
2. Soul: из 02_soul_prompts_v3.md + skill script-template-engine
3. Формат ТЗ: frame-by-frame с таймкодами (из SCALE)
4. Гибкие коды: Name: ??? (из v3)
5. HEARTBEAT: Mon 9:00 (аудит пайплайна)
6. Интеграция: пишет в tz_specs
```
**Результат:** ТЗ генерируются с детальным разбором кадров.

#### Шаг 1.4: Meta Master (Claw)
```
1. Создать Kimi Claw: @prodaflt_meta_bot
2. Soul: из 02_soul_prompts_v3.md (Meta)
3. Память: Andromeda, CBO, CAPI, cloaking, PWA
4. HEARTBEAT: Mon 10:00 (дайджест обновлений)
```
**Результат:** Экспертиза по запускам и алгоритмам.

#### Шаг 1.5: Data Analyst (Claw + skill)
```
1. Создать Kimi Claw: @prodaflt_data_bot
2. Soul: из 02_soul_prompts_v3.md + skill creative-metrics-analyzer
3. Alert Engine: RED/GREEN/YELLOW + confidence (из SCALE)
4. Kill thresholds: CPI≥$5, CPC≥$2.5, uEPC≥$8 (из SCALE)
5. HEARTBEAT: daily 7:00 (morning report) + daily 18:00 (metrics check)
6. OCR: скриншоты → метрики (pipeline из SCALE)
7. Тройное сравнение: исходник + ТЗ + готовый материал (из v3)
```
**Результат:** Автоматические алерты на kill/scale/watch.

#### Шаг 1.6: Tech Lead (Claw)
```
1. Создать Kimi Claw: @prodaflt_tech_bot
2. Soul: из 02_soul_prompts_v3.md (Tech)
3. Память: архитектура, API, код скиллов, деплой-конфиги
4. HEARTBEAT: Fri 18:00 (инфра аудит)
5. Задачи: поддержка Parser Bot, API, интеграции
```
**Результат:** Техническая поддержка всей системы.

---

### 🔷 ФАЗА 2: API + Skills (День 8-10)

**Цель:** Промышленный API и модульные skills

#### Шаг 2.1: FastAPI сервис
```
1. Tech Lead пишет FastAPI приложение (api/main.py)
2. Endpoints:
   - POST /api/links — добавить ссылку
   - GET /api/links — список с фильтрами
   - PATCH /api/links/{id} — обновить статус
   - POST /api/tz — создать ТЗ
   - POST /api/metrics — загрузить метрики
   - GET /api/metrics/top — топ креативов
   - GET /api/alerts/active — активные алерты
   - GET /api/stats — агрегированная статистика
3. Docker + Railway деплой
```
**Результат:** REST API для интеграций.

#### Шаг 2.2: Python Skills (7 штук)
```
Переносим из tech_lead/skills/:
1. content-researcher — скрапинг + классификация + скоринг
2. creative-metrics-analyzer — расчет метрик + thresholds
3. gambling-creative-workflow — pipeline Link→TZ→Creative→Metrics
4. media-downloader — скачивание с 3 платформ
5. script-template-engine — шаблоны ТЗ (newsjacking, podcast, ugc...)
6. trend-competitor-monitor — тренды 3x/неделю + конкуренты
7. video-scene-analysis — ffmpeg + whisper + frame extraction
```
**Результат:** Модульные, версионируемые компоненты.

#### Шаг 2.3: Alert Engine (Python)
```
1. Модуль alerts/engine.py
2. Логика:
   IF Install ≥ 5 OR CPC ≥ 2.5 OR uEPC ≥ 8 → RED (KILL)
   ELIF uEPC < 4 AND CPI ≤ 5 → GREEN (SCALE)
   ELIF uEPC > 6 AND uEPC < 8 → YELLOW (WATCH)
3. Confidence levels: 100%, 95%, 85%, 70%
4. Форматы сообщений (telegram) из Data Analyst brief
5. Отправка через Router Bot
```
**Результат:** Автоматические алерты с градацией риска.

---

### 🔷 ФАЗА 3: Автоматизация + HEARTBEAT (День 11-12)

**Цель:** Все боты работают по расписанию

#### Шаг 3.1: HEARTBEAT таблица
| Агент | Время | Что делает | Тип |
|-------|-------|-----------|-----|
| Data Analyst | 07:00 daily | Morning Report | Claw /cron |
| Router | 09:17 daily | Брифинг по гемблингу | Claw /cron |
| Researcher | 10:00 daily | Тренды вирусного контента | Claw /cron |
| Compliance | 12:00 Tue/Thu | Compliance Audit | Claw /cron |
| Creative | 09:00 Mon | Аудит креативного пайплайна | Claw /cron |
| Meta | 10:00 Mon | Дайджест обновлений Meta | Claw /cron |
| Data Analyst | 18:00 daily | CHECK METRICS | Claw /cron |
| Tech Lead | 18:00 Fri | Инфра аудит | Claw /cron |
| Content Researcher (skill) | 09:00 UTC daily | Авто-скрапинг 15 ссылок | crontab |
| Trend Monitor (skill) | 18:00 Mon/Wed/Fri | Трендовый отчет | crontab |

#### Шаг 3.2: Morning Report Pipeline
```
[07:00] Data Analyst (HEARTBEAT):
  1. Читает БД: links за вчера, tz_specs, metrics
  2. Для каждого active user: links | approve/reject | activity %
  3. Total: links | approve % | trend vs previous day
  4. Формирует отчет (текстовый)
  5. Отправляет Даниилу через Router
```

---

### 🔷 ФАЗА 4: Веб-сервис (День 13-18)

**Цель:** Визуальный интерфейс для команды

#### Шаг 4.1: Telegram OAuth
```
1. Кнопка "Войти через Telegram" на landing page
2. Callback: получаем telegram_id, username, first_name
3. JWT токен → localStorage
4. Записываем/обновляем users в БД
```

#### Шаг 4.2: Dashboard (React + Tailwind)
```
Вкладка "Общие":
  - 4 карточки: ссылок обработано | ТЗ создано | креативов на проверке | approve-рейтинг
  - График активности команды (7 дней)
  - Топ-5 пользователей по активности
  - Таблица последних действий с бейджами статусов

Вкладка "Ссылки" (из SCALE):
  - Таблица всех ссылок с фильтрами (платформа, статус, пользователь)
  - Статусы: NEW (желтый), CHECKING (синий), APPROVED (зеленый), REJECTED (красный)
  - Быстрые действия: просмотр / аппрув / реджект
  - Выезжающая панель деталей с превью и timeline статусов

Вкладка "ТЗ" (из SCALE):
  - Двухколоночный layout: список слева, детали справа
  - Вкладки: Описание / Скрипт / Визуал / Метрики / История
  - Код контента: гибкий (как в v3)

Вкладка "Метрики":
  - Таблица кампаний с сортировкой по ROI/CPI/uEPC
  - Алерты: RED/GREEN/YELLOW бейджи
  - График spend vs revenue по дням
```

#### Шаг 4.3: Цветовая схема (из SCALE)
```
Фон основной: #0A1628 (темно-синий)
Фон карточек: #111D32 (приподнятый синий)
Акцент: #D4AF37 (золотой)
Текст: #FFFFFF / #6B7B94
Успех: #4CAF50 / Опасность: #E74C3C
```

---

### 🔷 ФАЗА 5: Интеграции (День 19-21)

**Цель:** Соединение с внешними сервисами

#### Шаг 5.1: Keitaro API
```
1. Синхронизация метрик из Keitaro → PostgreSQL
2. Авто-расчет derived metrics (CPC, CPI, uEPC, ROI)
3. Запуск Alert Engine при обновлении
```

#### Шаг 5.2: Meta Marketing API (через Tech Lead)
```
1. Получение данных кампаний (spend, clicks, installs)
2. Авто-загрузка в metrics таблицу
3. Связь с creative_code
```

#### Шаг 5.3: Asana (заглушка → реализация)
```
1. Поле asana_task_id в tz_specs
2. Кнопка "Отправить в Asana" в веб-сервисе
3. Этап 1: заглушка (opacity 0.5, tooltip "В разработке")
4. Этап 2: полная интеграция через Asana API
```

#### Шаг 5.4: OCR Pipeline
```
1. Buyer's кидают скриншот Ads Manager / Keitaro в Telegram
2. Data Analyst Bot: запускает OCR (EasyOCR / Tesseract)
3. Извлекает: campaign_id, clicks, installs, spend, revenue
4. Валидация: clicks ≥ unique_clicks, conversions ≤ clicks
5. Авто-запись в БД + запуск Alert Engine
```

---

### 🔷 ФАЗА 6: Тестирование + Go-Live (День 22-25)

#### Шаг 6.1: End-to-end тест
```
Сценарий: Команда скидывает ссылку → ТЗ → Запуск
[1] Команда в группу: "https://instagram.com/reel/... — найти ориг"
[2] Parser Bot → БД (links, status=new)
[3] Даниил пишет Router: "проверь новые ссылки"
[4] Router → Researcher + Compliance
[5] Researcher: анализ → БД (content_analysis)
[6] Compliance: PASS → БД
[7] Даниил: "сделай ТЗ на одобренные"
[8] Router → Creative
[9] Creative: "Name: ???" → Даниил: "EN0391-99-1"
[10] Creative генерирует ТЗ → БД (tz_specs)
[11] Даниил: "проанализируй ТЗ EN0391-99-1"
[12] Router → Data: тройное сравнение
[13] Даниил: "как запустить?"
[14] Router → Meta: структура кампании
```

#### Шаг 6.2: Нагрузочный тест Parser
```
- 50 ссылок за 1 минуту в группу
- Проверить: batch-запись не ломается
- Проверить: нет дубликатов в БД
```

#### Шаг 6.3: Alert Engine тест
```
- Тест 1: KILL (CPI $5.3, uEPC $8.2) → RED алерт
- Тест 2: SCALE (uEPC $3.1, ROI 158%) → GREEN алерт
- Тест 3: WATCH (uEPC $6.5) → YELLOW алерт
- Тест 4: INSUFFICIENT ($12 spend, 8 clicks) → белый статус
```

---

## Часть 6. Финальный чек-лист

### Инфраструктура
- [ ] Neon PostgreSQL создана, миграции выполнены
- [ ] 8 Telegram ботов созданы, токены сохранены
- [ ] Router (Claw) работает, маршрутизирует 6 направлений
- [ ] Parser Bot деплоен, пишет в БД
- [ ] FastAPI деплоен, endpoints работают
- [ ] Docker + Railway конфиги готовы

### AI-агенты (Claw)
- [ ] 7 Claw созданы, Soul вставлен, Telegram подключен
- [ ] HEARTBEAT настроен в каждом (7 расписаний)
- [ ] Skills подключены (7 .skill файлов)
- [ ] Alert Engine тестирован (4 тест-кейса)

### Данные
- [ ] Parser Bot: ссылка из группы → появляется в БД через 30 сек
- [ ] Researcher: ежедневно 15 референсов с скорингом
- [ ] Creative: ТЗ с frame-by-frame и таймкодами
- [ ] Data Analyst: morning report в 07:00, алерты мгновенно
- [ ] Compliance: pre-moderation перед ТЗ

### Веб-сервис
- [ ] Telegram OAuth работает
- [ ] Dashboard: 4 карточки + график активности
- [ ] Вкладка "Ссылки": таблица, фильтры, быстрые действия
- [ ] Вкладка "ТЗ": двухколоночный layout, код контента
- [ ] Вкладка "Метрики": алерты, сортировка, графики

### Команда
- [ ] Team Brief v3 отправлен каждому
- [ ] Все знают: запросы только в @prodaflt_router_bot
- [ ] Префиксы команд известны: !факт, !проект, !сайт, !batch
- [ ] Инструкция по скидыванию ссылок в группу

---

## Часть 7. Риски и mitigations

| Риск | Вероятность | Влияние | Mitigation |
|------|-------------|---------|------------|
| Kimi Claw /cron не стабилен | Средняя | Высокое | Fallback: crontab на сервере + Python-скрипты |
| Neon PostgreSQL лимиты | Низкая | Среднее | Мониторинг, при росте — апгрейд плана |
| Parser Bot бан в Telegram | Средняя | Высокое | Rate limiting, batch-запись, резервный бот |
| OCR неточный (скрины) | Средняя | Среднее | Human override для confidence < 85% |
| Команда не пишет в Router | Высокая | Среднее | Обучение, напоминания, Router игнорирует прямые сообщения |
| Meta API блокирует | Средняя | Среднее | Fallback: ручной ввод через OCR + Telegram |

---

## Часть 8. Следующие шаги (после запуска)

1. **Неделя 2:** Интеграция Keitaro API (авто-метрики)
2. **Неделя 3:** Meta Marketing API (авто-загрузка кампаний)
3. **Неделя 4:** Asana интеграция (ТЗ → задачи дизайнерам)
4. **Месяц 2:** Предиктивная аналитика (паттерны успешных крео)
5. **Месяц 2-3:** Auto-kill (остановка кампаний без участия Даниила)
6. **Месяц 3:** AI-генерация креативов (Midjourney/Runway интеграция)

---

*Документ составлен на основе анализа 12 файлов из двух независимых чатов.*
*Принцип: Все фундаментальные решения — из обоих подходов. Лучшее усиливает лучшее.*
