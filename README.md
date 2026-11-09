# Платформа аналитики и прогнозирования тарифов грузоперевозок

> Тестовое задание **Middle Data Engineer** («Умная Логистика», ul.su).
> Сквозной прототип: **ETL → DWH → ML** на приближённых к боевым данным.

Решение реализует три связанных этапа в классической слоистой схеме:

```
raw  (источник: schema.sql + synthetic.sql, 300 000 сделок)
        │  Вопрос 1: ETL & Data Quality
        ▼
core (очищенные факты, справочники, карантин DQ, журнал прогонов)
        │  Вопрос 2: витрины
        ▼
mart (route_card — коридор P25/P50/P75 + доказательная база)
        │  Вопрос 3: ML (features, time-split, CatBoost)
        ▼
mart.ml_price_predictions (факт vs прогноз тарифа)
```

Полное описание задания — в [`docs/TASK.md`](docs/TASK.md).

---

## Стек и обоснование

| Компонент | Выбор | Почему |
|---|---|---|
| Хранилище | **PostgreSQL 17** | Требование задания; схемы `raw → core → mart`, оконные функции `percentile_cont`, `FILTER`. |
| ETL | **Python 3.11 + pandas + psycopg2** | Очистка/валидация на pandas, пакетная вставка `execute_values` (без построчного INSERT). |
| Витрины | **SQL** (CTE + агрегаты) | `percentile_cont`, `stddev_samp`, self-join для MoM/YoY — идиоматично и прозрачно. |
| ML | **CatBoost** | Нативная работа с категориями, лучший R² (рекомендация из `ml-report.md`). |
| Оркестрация | `docker compose` | Базовое решение разворачивается одной командой; бонусные Airflow/Superset/ClickHouse не включены. |

### Слои и схемы

| Схема | Содержимое |
|---|---|
| `raw` | Исходные таблицы задания (`prices`, `cities`, `body_types`, `price_body_types`, `price_dates`, `exchange_rates`, `price_group_stats`, `price_participants`, `selected_directions`, `favorite_directions`, `migrations`) |
| `core` | `fact_prices`, `dim_city`, `price_body_group`, `dq_quarantine_prices`, `etl_batch_log` |
| `mart` | `route_card`, `ml_price_predictions` |

---

## Структура репозитория

```
├── docker-compose.yml        # postgres:17 + one-shot pipeline service
├── Dockerfile                # образ пайплайна (python + psql)
├── .env.example              # шаблон переменных окружения
├── requirements*.txt
├── pytest.ini
├── sql/                      # DDL и SQL-витрины
│   ├── schema.sql            #   эталонный DDL источника (входной материал)
│   ├── synthetic.sql         #   генератор данных (входной материал)
│   ├── ddl_core.sql          #   схема core + карантин DQ
│   ├── ddl_mart.sql          #   схема mart: route_card + ml_price_predictions
│   ├── populate_dim_city.sql #   дедупликация городов
│   ├── body_groups.sql       #   унификация групп кузова
│   ├── build_mart.sql        #   расчёт карточки маршрута / коридора
│   └── verify_*.sql          #   SQL-проверки (чистый SQL, запускаются в DBeaver/psql)
├── etl/                      # Вопрос 1: пайплайн очистки
│   ├── dq.py                 #   правила DQ и категории
│   ├── pipeline.py           #   extract → clean → convert → load
│   ├── load.py               #   идемпотентная загрузка (execute_values)
│   ├── mart.py               #   Вопрос 2: пересчёт витрин
│   └── main.py               #   CLI: python -m etl.main [--start/--end] [--with-mart]
├── ml/                       # Вопрос 3: ML
│   ├── features.py           #   feature pipeline + циклическое время
│   ├── train.py              #   time-split + CatBoost + метрики
│   ├── score.py              #   batch inference → mart.ml_price_predictions
│   └── main.py               #   CLI: python -m ml.main
├── tests/                    # pytest (правила DQ, утечки, идемпотентность)
└── docs/                     # материалы задания + демо-дашборд
```

---

## Запуск

### Одной командой

```bash
docker compose up --build
```

Сервис `pipeline` последовательно: создаёт схемы → загружает источник (`schema.sql` + `synthetic.sql` в `raw`) → создаёт `core`/`mart` → выполняет ETL → строит витрины → обучает модель и пишет прогнозы.

**Повторный запуск безопасен**: если `raw.prices` уже есть, загрузка источника пропускается, а все дальнейшие шаги идемпотентны (UPSERT / атомарная перезапись). Команда отрабатывает и на существующем volume.

### Ручной запуск (для разработки)

```bash
# 1. Схемы и источник
psql -U postgres -d deals_bigdata -c 'CREATE SCHEMA IF NOT EXISTS raw; CREATE SCHEMA IF NOT EXISTS core; CREATE SCHEMA IF NOT EXISTS mart;'
psql -U postgres -d deals_bigdata -v ON_ERROR_STOP=1 -c 'SET search_path TO raw;' \
     -v n_prices=300000 -f sql/schema.sql -f sql/synthetic.sql

# 2. Аналитический слой
psql -U postgres -d deals_bigdata -f sql/ddl_core.sql -f sql/ddl_mart.sql -f sql/populate_dim_city.sql

# 3. ETL + витрины (идемпотентно, параметризуется окном дат)
python -m etl.main --with-mart

# 4. ML
python -m ml.main
```

Подключение и имена схем — через `.env` (см. `.env.example`): `DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_RAW_SCHEMA`, `DB_CORE_SCHEMA`, `DB_MART_SCHEMA`.

---

## Вопрос 1 — ETL и Data Quality

Пайплайн читает окно дат (`--start-date`/`--end-date`) из `raw.prices`, валидирует и очищает, конвертирует валюту, обогащает категории и идемпотентно загружает в `core.fact_prices`.

**Правила карантина** (`core.dq_quarantine_prices`, причина `reason_code`):

| Правило | reason_code |
|---|---|
| `price <= 0` | `INVALID_PRICE` |
| RUB и `price <= 1000` | `RUB_PRICE_TOO_LOW` |
| `distance <= 0` | `INVALID_DISTANCE` |
| `total_weight < 0` или `total_volume < 0` | `INVALID_WEIGHT_VOLUME` |
| город отсутствует в `raw.cities` | `UNKNOWN_CITY` |
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

- **Дедупликация городов** (`core.dim_city`): `gc_id` не уникален — берётся строка с минимальным `cities.id` (42 → 40 городов).
- **Унификация кузовов** (`core.price_body_group`): `price_body_types` → `body_types.std_id` → бизнес-группа, с фолбэком на `prices.body_type` и `Не указан`; без дублей одной сделки внутри одной группы.

| Группа | Сделок |
|---|---|
| Тент | 165 141 |
| Рефрижератор | 62 942 |
| Борт | 43 162 |
| Прочие | 30 130 |
| Изотерм | 28 020 |
| Не указан | 5 910 |

**Витрина `mart.route_card`** — 203 644 ячейки, grain: `месяц × город отправления × город назначения × группа кузова × весовая категория`. Месяц — из `raw.price_dates.price_date` (долгосрочные заявки в нескольких месяцах).

Метрики: `p25/median/p75/avg` в `руб./рейс` и `руб./км`, `trips_count`, `carriers_count`, `cv_rate`, `mom_pct`/`yoy_pct`, `reliability_level` (`HIGH`/`MEDIUM`/`LOW_DATA`).

Фильтры выборки: `is_fact` (`price_type IN (1,2,3,4,5,9)`), `complex=false`, `price_rub>0`, `distance>0`, `outlier_mark=false`, будущие месяцы (`> 2026-10-26`) исключены.

**Примеры SQL для проверки:**

```sql
-- Карточка маршрута Москва → Казань (Тент, FTL)
SELECT month, trips_count, carriers_count, median_trip, median_km,
       p25_trip, p75_trip, mom_pct, yoy_pct, reliability_level
FROM mart.route_card
WHERE loading_city_gcid = 1001 AND unloading_city_gcid = 1003
  AND body_group = 'Тент' AND weight_category = 'FTL'
ORDER BY month DESC;

-- Топ направлений по числу рейсов
SELECT loading_city_name, unloading_city_name, body_group,
       sum(trips_count) AS trips
FROM mart.route_card
GROUP BY 1, 2, 3
ORDER BY trips DESC
LIMIT 10;
```

> **Решение по «свежести»**: ячейка считается свежей, если `(as_of − начало_месяца) ≤ 30 дней` (для `HIGH`). Зафиксировано в `sql/build_mart.sql`.

> **Важно про суммы**: `trips_count` нельзя суммировать между группами кузова — сделка с несколькими типами кузова учитывается в каждой группе (это свойство моста many-to-many). Внутри одной группы дублей нет.

---

## Вопрос 3 — ML: прогноз тарифа

**Признаки** (без утечек):
- маршрут/гео: `distance`, регионы отправления/назначения, координаты;
- груз/транспорт: `total_weight`, `total_volume`, `body_group`, категории;
- циклическое время: `year` + sin/cos(месяц T=12, день недели T=7, день года T=365.25).

**Защита от утечек**: исключены производные таргета (`price_with_vat`, `price/distance`, `price/weight`), агрегаты `price_group_stats`, а `outlier_mark` используется только для очистки таргета, не как признак. Признаки читаются с `ORDER BY price_id` — это фиксирует порядок строк и делает обучение воспроизводимым (CatBoost чувствителен к порядку).

**Time-Based Split** (без `shuffle`, `as_of = 2026-10-26`):
```
train = [2026-07-26, 2026-10-05)   → 24 226 строк
test  = [2026-10-05, 2026-10-26]   → 12 808 строк
```

**Метрики на test** (`random_seed=42`):

| Модель | R² | MAPE, % | RMSE, ₽ | MAE, ₽ |
|---|---|---|---|---|
| **CatBoost** | **0.9106** | **16.78** | 57 207 | 29 795 |
| DecisionTree | 0.9015 | 16.79 | 60 044 | 31 570 |
| Ridge | 0.8112 | 45.96 | 83 128 | 51 750 |

**Batch inference** → `mart.ml_price_predictions` (17 699 строк):
- 12 808 — отложенный тестовый период (факт + прогноз + `abs_error_rub` + `ape_pct`);
- 4 891 — будущие плановые заявки (`loading_date > 2026-10-26`) с `actual/abs_error/ape = NULL`.

```sql
-- Факт vs прогноз по группам кузова
SELECT body_group, count(*),
       round(avg(ape_pct)::numeric, 2) AS mean_ape_pct
FROM mart.ml_price_predictions
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

Покрывают: правила DQ и категории, отсутствие таргет-утечек в признаках, границы time-split, корректность циклического кодирования, идемпотентность (отсутствие дублей в `core.fact_prices`, `mart.route_card`, `mart.ml_price_predictions`) и `NULL`-ошибки для будущих заявок. **14 тестов, все проходят.**

---

## Проверочные SQL-скрипты

`sql/verify_*.sql` — чистый SQL (без psql-мета-команд), запускается целиком или по одному запросу в DBeaver и в `psql`:

```bash
psql -U postgres -d deals_bigdata -f sql/verify_etl.sql
psql -U postgres -d deals_bigdata -f sql/verify_mart.sql
psql -U postgres -d deals_bigdata -f sql/verify_ml.sql
```

---

## Известные решения и ограничения

1. **`outlier_mark` на 2026-10-26**: самые свежие сделки за день снимка ещё не прошли ночной джоб разметки и имеют `outlier_mark=false` по умолчанию — это ограничение исходных данных (зафиксировано в задании), в базовом решении флаг не пересчитывается.
2. **`loading_city = unloading_city`**: не отбраковывается (не является production-DQ-правилом — исходный джоб сохраняет такую пару и расстояние).
3. **ML-группа кузова**: для модели используется основная группа (по `prices.body_type`), а не fan-out `core.price_body_group` (таргет один на сделку).
4. **`RUB_PRICE_TOO_LOW = 0`** в синтетике: минимальная положительная цена ≈ 1 671 ₽, поэтому диапазона `0 < price ≤ 1000` в данных нет (правило реализовано, но не срабатывает).
5. **Партиционирование** `core.fact_prices`/`raw.price_dates` не сделано: на 300 тыс. сделок не требуется, при росте до миллионов — следующий шаг.
