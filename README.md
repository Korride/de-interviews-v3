# Платформа аналитики и прогнозирования тарифов грузоперевозок

> Тестовое задание **Middle Data Engineer** («Умная Логистика», ul.su).
> Сквозной прототип: **ETL → DWH → ML** на приближённых к боевым данных.

Решение реализует три связанных этапа:

```
Источник (PostgreSQL, 300 000 сделок)
        │  Вопрос 1: ETL & Data Quality
        ▼
Core DWH (очищенные факты + карантин DQ)
        │  Вопрос 2: витрины (mart)
        ▼
mart_route_card (коридор ставок P25/P50/P75 + доказательная база)
        │  Вопрос 3: ML (features, time-split, CatBoost)
        ▼
ml_price_predictions (факт vs прогноз тарифа)
```

Полное описание задания — в [`docs/TASK.md`](docs/TASK.md).

---

## Стек и обоснование

| Компонент | Выбор | Почему |
|---|---|---|
| Хранилище | **PostgreSQL 17** | Требование задания; единое хранилище `raw → core → mart`, оконные функции `percentile_cont`, `FILTER`. |
| ETL | **Python 3.11 + pandas + psycopg2** | Требование задания; очистка/валидация на pandas, пакетная вставка `execute_values` (без построчного INSERT). |
| Витрины | **SQL** (CTE + агрегаты) | `percentile_cont`, `stddev_samp`, self-join для MoM/YoY — идиоматично и прозрачно. |
| ML | **CatBoost** | Нативная работа с категориальными признаками, лучший R² (рекомендация из `ml-report.md`). |
| Оркестрация | `docker compose` (бонусные Airflow/Superset/ClickHouse — не включены) | Базовое решение разворачивается одной командой. |

---

## Структура репозитория

```
├── docker-compose.yml        # один сервис БД + сервис пайплайна
├── Dockerfile                # образ пайплайна (python + psql)
├── .env.example              # шаблон переменных окружения
├── requirements*.txt
├── pytest.ini
├── sql/                      # DDL и SQL-витрины
│   ├── schema.sql            #   эталонный DDL источника (входной материал)
│   ├── synthetic.sql         #   генератор данных (входной материал)
│   ├── ddl_core.sql          #   Core DWH + карантин DQ
│   ├── ddl_mart.sql          #   mart_route_card + ml_price_predictions
│   ├── populate_dim_city.sql #   дедупликация городов
│   ├── body_groups.sql       #   унификация групп кузова
│   ├── build_mart.sql        #   расчёт карточки маршрута / коридора
│   └── verify_*.sql          #   smoke-проверки
├── etl/                      # Вопрос 1: пайплайн очистки
│   ├── dq.py                 #   правила DQ и категории
│   ├── pipeline.py           #   extract → clean → convert → load
│   ├── load.py               #   идемпотентная загрузка (execute_values)
│   ├── mart.py               #   Вопрос 2: пересчёт витрин
│   └── main.py               #   CLI: python -m etl.main [--start/--end] [--with-mart]
├── ml/                       # Вопрос 3: ML
│   ├── features.py           #   feature pipeline + циклическое время
│   ├── train.py              #   time-split + CatBoost + метрики
│   ├── score.py              #   batch inference → ml_price_predictions
│   └── main.py               #   CLI: python -m ml.main
├── tests/                    # pytest (правила DQ, утечки, идемпотентность)
└── docs/                     # материалы задания + демо-дашборд
```

---

## Запуск

### Один командой (production-путь)

```bash
docker compose up --build
```

Сервис `pipeline` последовательно: создаёт схему → загружает источник (`schema.sql` + `synthetic.sql`) → создаёт аналитический слой → выполняет ETL → строит витрины → обучает модель и пишет прогнозы. По завершении в БД готовы все таблицы.

### Ручной запуск (для разработки)

```bash
# 1. БД (или используйте существующую), схема + источник
psql -U postgres -d deals_bigdata -c 'CREATE SCHEMA IF NOT EXISTS "TEST_V3";'
psql -U postgres -d deals_bigdata -v ON_ERROR_STOP=1 -f sql/schema.sql
psql -U postgres -d deals_bigdata -v ON_ERROR_STOP=1 -f sql/synthetic.sql
psql -U postgres -d deals_bigdata -f sql/ddl_core.sql -f sql/ddl_mart.sql -f sql/populate_dim_city.sql

# 2. ETL + витрины (идемпотентно, параметризуется окном дат)
python -m etl.main --with-mart

# 3. ML
python -m ml.main
```

Параметры подключения — через `.env` (см. `.env.example`): `DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_SCHEMA`.

---

## Вопрос 1 — ETL и Data Quality

Пайплайн читает окно дат (`--start-date`/`--end-date`) из `prices`, валидирует и очищает, конвертирует валюту, обогащает категории и идемпотентно загружает в `core_fact_prices`.

**Правила карантина** (`dq_quarantine_prices`, причина `reason_code`):

| Правило | reason_code |
|---|---|
| `price <= 0` | `INVALID_PRICE` |
| RUB и `price <= 1000` | `RUB_PRICE_TOO_LOW` |
| `distance <= 0` | `INVALID_DISTANCE` |
| `total_weight < 0` или `total_volume < 0` | `INVALID_WEIGHT_VOLUME` |
| город отсутствует в `cities` | `UNKNOWN_CITY` |
| USD/EUR без точного курса по `nearest_rate_date` | `MISSING_RATE` |

**Конвертация валют**: RUB → курс 1.0; USD/EUR → курс ЦБ по `nearest_rate_date` (без fallback по `loading_date`). **Категории**: `weight_category` (G20T/FTL/10T/5T/L5T/OTH, округление до 0.1 т), `volume_category` (FTL при 0<V≤120, иначе OTH).

**Результаты** (300 000 записей источника):
```
rows read        : 300 000
rows loaded      : 299 797
rows quarantined : 203   (INVALID_PRICE=164, MISSING_RATE=39)
```

**Идемпотентность**: `INSERT … ON CONFLICT (price_id) DO UPDATE` (core) и `ON CONFLICT (price_id, reason_code) DO NOTHING` (карантин); повторный прогон того же окна не задваивает строки (проверено автотестами).

---

## Вопрос 2 — DWH и аналитические витрины

Устранены структурные аномалии измерений:

- **Дедупликация городов** (`core_dim_city`): `cities.gc_id` не уникален — берётся строка с минимальным `cities.id` (42 → 40 городов).
- **Унификация кузовов** (`core_price_body_group`): `price_body_types` → `body_types.std_id` → бизнес-группа, с фолбэком на `prices.body_type` и `Не указан`; без дублей одной сделки внутри одной группы.

| Группа | Сделок |
|---|---|
| Тент | 165 141 |
| Рефрижератор | 62 942 |
| Борт | 43 162 |
| Прочие | 30 130 |
| Изотерм | 28 020 |
| Не указан | 5 910 |

**Витрина `mart_route_card`** — 203 644 ячейки, grain: `месяц × город отправления × город назначения × группа кузова × весовая категория`. Месяц — из `price_dates.price_date` (долгосрочные заявки в нескольких месяцах).

Метрики: `p25/median/p75/avg` в `руб./рейс` и `руб./км`, `trips_count`, `carriers_count`, `cv_rate`, `mom_pct`/`yoy_pct`, `reliability_level` (`HIGH`/`MEDIUM`/`LOW_DATA`).

Фильтры выборки: `is_fact` (`price_type IN (1,2,3,4,5,9)`), `complex=false`, `price_rub>0`, `distance>0`, `outlier_mark=false`, будущие месяцы (`> 2026-10-26`) исключены.

**Примеры SQL для проверки:**

```sql
-- Карточка маршрута Москва → Казань (Тент, FTL)
SELECT month, trips_count, carriers_count, median_trip, median_km,
       p25_trip, p75_trip, mom_pct, yoy_pct, reliability_level
FROM mart_route_card
WHERE loading_city_gcid = 1001 AND unloading_city_gcid = 1003
  AND body_group = 'Тент' AND weight_category = 'FTL'
ORDER BY month DESC;

-- Топ направлений по числу рейсов
SELECT loading_city_name, unloading_city_name, body_group,
       sum(trips_count) AS trips
FROM mart_route_card
GROUP BY 1, 2, 3
ORDER BY trips DESC
LIMIT 10;
```

> **Решение по «свежести»**: ячейка считается свежей, если `(as_of − начало_месяца) ≤ 30 дней` (для `HIGH`). Зафиксировано в `sql/build_mart.sql`.

---

## Вопрос 3 — ML: прогноз тарифа

**Признаки** (без утечек):
- маршрут/гео: `distance`, регионы отправления/назначения, координаты;
- груз/транспорт: `total_weight`, `total_volume`, `body_group`, категории;
- циклическое время: `year` + sin/cos(месяц T=12, день недели T=7, день года T=365.25).

**Защита от утечек**: исключены производные таргета (`price_with_vat`, `price/distance`, `price/weight`), агрегаты `price_group_stats`, а `outlier_mark` используется только для очистки таргета, не как признак.

**Time-Based Split** (без `shuffle`, `as_of = 2026-10-26`):
```
train = [2026-07-26, 2026-10-05)   → 24 226 строк
test  = [2026-10-05, 2026-10-26]   → 12 808 строк
```

**Метрики на test** (`random_seed=42`):

| Модель | R² | MAPE, % | RMSE, ₽ | MAE, ₽ |
|---|---|---|---|---|
| **CatBoost** | **0.912** | **16.7** | 56 797 | 29 768 |
| DecisionTree | 0.902 | 16.0 | 59 784 | 30 589 |
| Ridge | 0.818 | 46.8 | 81 599 | 50 716 |

**Batch inference** → `ml_price_predictions` (17 699 строк):
- 12 808 — отложенный тестовый период (факт + прогноз + `abs_error_rub` + `ape_pct`);
- 4 891 — будущие плановые заявки (`loading_date > 2026-10-26`) с `actual/abs_error/ape = NULL`.

```sql
-- Факт vs прогноз по тестовому периоду
SELECT body_group, count(*),
       round(avg(ape_pct)::numeric, 2) AS mean_ape_pct
FROM ml_price_predictions
WHERE actual_price_rub IS NOT NULL
GROUP BY body_group
ORDER BY mean_ape_pct;
```

---

## Тесты

```bash
pip install -r requirements-dev.txt
pytest                       # все тесты
pytest -m "not integration"  # только юнит-тесты (без БД)
```

Покрывают: правила DQ и категории, отсутствие таргет-утечек в признаках, границы time-split, корректность циклического кодирования, идемпотентность (отсутствие дублей в `core_fact_prices`, `mart_route_card`, `ml_price_predictions`) и `NULL`-ошибки для будущих заявок. Бадж: **14 пройдено**.

---

## Известные решения и ограничения

1. **`outlier_mark` на 2026-10-26**: самые свежие сделки за день снимка ещё не прошли ночной джоб разметки и имеют `outlier_mark=false` по умолчанию — это ограничение исходных данных (зафиксировано в задании), в базовом решении флаг не пересчитывается.
2. **`loading_city = unloading_city`**: не отбраковывается (не является production-DQ-правилом — исходный джоб сохраняет такую пару и расстояние).
3. **ML-группа кузова**: для модели используется основная группа (по `prices.body_type`), а не fan-out `core_price_body_group` (таргет один на сделку).
4. **`RUB_PRICE_TOO_LOW = 0`** в синтетике: минимальная положительная цена ≈ 6000 ₽, поэтому диапазона `0 < price ≤ 1000` в данных нет (правило реализовано, но не срабатывает).
