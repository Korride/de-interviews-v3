# -*- coding: utf-8 -*-
"""Единый источник истины для бизнес-констант проекта.

Здесь собраны все «магические» значения: коды валют, границы категорий
(вес/объём), коды причин карантина, группы кузова, параметры ML и списки
колонок. Модули `etl/` и `ml/` импортируют значения отсюда.

Синхронизация с SQL
-------------------
Часть констант продублирована в БД, чтобы SQL-витрины тоже не содержали
«магических» литералов (см. `sql/ddl_core.sql`):

* таблица `core.ref_body_group(std_id, body_group)`   — группы кузова;
* таблица `core.etl_params(param, value)`             — `as_of_date`,
  пороги надёжности, `rub_min_price`, `volume_ftl_max` и fallback-имена.

Ключи `PARAM_*` ниже совпадают с именами в `core.etl_params`.
"""

# =============================================================================
# 1. Параметры снимка и хронологического разбиения (Question 3)
#    NB: это дата снимка задания, а НЕ системная дата.
# =============================================================================
AS_OF_DATE = "2026-10-26"        # дата снимка `as_of`
TRAIN_START = "2026-07-26"       # [TRAIN_START, TEST_START) — train, включительно
TEST_START = "2026-10-05"        # [TEST_START, TEST_END] — test, включительно
TEST_END = AS_OF_DATE            # граница 2026-10-05 входит только в test

# =============================================================================
# 2. Валюты (Question 1)
# =============================================================================
CURRENCY_RUB = "643"
CURRENCY_USD = "840"
CURRENCY_EUR = "978"
RUB_RATE = 1.0                                     # курс рубля к самому себе
FOREIGN_CURRENCIES = frozenset({CURRENCY_USD, CURRENCY_EUR})

# =============================================================================
# 3. Правила Data Quality (Question 1)
#    Коды причин применяются в порядке приоритета: первая подходящая побеждает.
# =============================================================================
REASON_INVALID_PRICE = "INVALID_PRICE"            # price <= PRICE_MIN_EXCLUSIVE
REASON_RUB_PRICE_TOO_LOW = "RUB_PRICE_TOO_LOW"    # RUB и price <= RUB_MIN_PRICE
REASON_INVALID_DISTANCE = "INVALID_DISTANCE"      # distance <= DISTANCE_MIN_EXCLUSIVE
REASON_INVALID_WEIGHT_VOLUME = "INVALID_WEIGHT_VOLUME"  # weight < 0 или volume < 0
REASON_UNKNOWN_CITY = "UNKNOWN_CITY"              # город отсутствует в справочнике
REASON_MISSING_RATE = "MISSING_RATE"              # валюта без точного курса

REASON_PRIORITY = (
    REASON_INVALID_PRICE,
    REASON_RUB_PRICE_TOO_LOW,
    REASON_INVALID_DISTANCE,
    REASON_INVALID_WEIGHT_VOLUME,
    REASON_UNKNOWN_CITY,
    REASON_MISSING_RATE,
)

PRICE_MIN_EXCLUSIVE = 0.0        # price <= 0 невалиден
RUB_MIN_PRICE = 1000.0           # source-validation порог для RUB
DISTANCE_MIN_EXCLUSIVE = 0.0     # distance <= 0 невалиден
WEIGHT_MIN = 0.0                 # total_weight < 0 невалиден
VOLUME_MIN = 0.0                 # total_volume < 0 невалиден
PRICE_RUB_DECIMALS = 2           # округление price_rub

# =============================================================================
# 4. Категории груза (Question 1)
#    Границы проверяются СВЕРХУ ВНИЗ, после округления веса до 0.1 т.
# =============================================================================
WEIGHT_ROUND_DECIMALS = 1
WEIGHT_CATEGORY_DEFAULT = "OTH"
#: (нижняя граница, включительно) -> метка
WEIGHT_CATEGORY_BOUNDS = (
    (30.0, "G20T"),
    (10.0, "FTL"),
    (5.0, "10T"),
    (2.5, "5T"),
    (0.5, "L5T"),
)

VOLUME_MIN_EXCLUSIVE = 0.0
VOLUME_FTL_MAX = 120.0
VOLUME_CATEGORY_FTL = "FTL"
VOLUME_CATEGORY_DEFAULT = "OTH"

# =============================================================================
# 5. Группы кузова (Questions 2, 3)
#    Источник: `raw.body_types.std_id`; непокрытые коды -> BODY_GROUP_OTHER,
#    отсутствие кузова -> BODY_GROUP_UNKNOWN.
# =============================================================================
STD_ID_TENT = 56
STD_ID_REFRIGERATOR = 4
STD_ID_ISOTHERM = 2
STD_ID_BOARD = 15

BODY_GROUP_TENT = "Тент"
BODY_GROUP_REFRIGERATOR = "Рефрижератор"
BODY_GROUP_ISOTHERM = "Изотерм"
BODY_GROUP_BOARD = "Борт"
BODY_GROUP_OTHER = "Прочие"
BODY_GROUP_UNKNOWN = "Не указан"

#: std_id -> имя бизнес-группы (используется для join'а с core.ref_body_group)
BODY_GROUP_BY_STD_ID = {
    STD_ID_TENT: BODY_GROUP_TENT,
    STD_ID_REFRIGERATOR: BODY_GROUP_REFRIGERATOR,
    STD_ID_ISOTHERM: BODY_GROUP_ISOTHERM,
    STD_ID_BOARD: BODY_GROUP_BOARD,
}

# =============================================================================
# 6. Периоды циклического кодирования дат (Question 3)
# =============================================================================
PERIOD_MONTHS = 12.0
PERIOD_WEEKDAYS = 7.0
PERIOD_YEAR_DAYS = 365.25

# =============================================================================
# 7. Признаки модели (Question 3)
# =============================================================================
TARGET = "price_rub"

NUMERIC_FEATURES = (
    "distance", "total_weight", "total_volume",
    "origin_lat", "origin_lon", "dest_lat", "dest_lon",
    "year",
    "month_sin", "month_cos",
    "dow_sin", "dow_cos",
    "doy_sin", "doy_cos",
)

CATEGORICAL_FEATURES = (
    "body_group", "weight_category", "volume_category",
    "origin_region", "dest_region",
)

FEATURE_COLUMNS = NUMERIC_FEATURES + CATEGORICAL_FEATURES

# =============================================================================
# 8. Параметры ML (Question 3)
# =============================================================================
RANDOM_SEED = 42
MODEL_NAME = "CatBoostRegressor"
PERCENT = 100.0                  # перевод доли в проценты

CATBOOST_PARAMS = {
    "iterations": 1500,
    "learning_rate": 0.08,
    "depth": 8,
    "l2_leaf_reg": 3.0,
    "loss_function": "RMSE",
    "verbose": False,
}

RIDGE_PARAMS = {"alpha": 1.0}
DECISION_TREE_PARAMS = {"max_depth": 10, "min_samples_leaf": 10}

# =============================================================================
# 9. Списки колонок для загрузки/выгрузки (Question 1, 3)
# =============================================================================
#: Колонки core.fact_prices в порядке вставки (UPDATE всех, кроме ключа).
CORE_FACT_COLUMNS = (
    "price_id", "loading_date", "end_loading_date",
    "loading_city_gcid", "unloading_city_gcid",
    "loading_city_id", "unloading_city_id",
    "distance", "total_weight", "total_volume", "body_type",
    "currency_code", "price_original", "exchange_rate", "price_rub",
    "price_type", "is_fact", "complex", "organization_id",
    "subscriber_id", "outlier_mark", "weight_category",
    "volume_category", "source",
)

#: Колонки core.dq_quarantine_prices.
QUARANTINE_COLUMNS = ("price_id", "reason_code", "description")

#: Колонки mart.ml_price_predictions.
PREDICTION_COLUMNS = (
    "price_id", "loading_date", "loading_city_gcid", "unloading_city_gcid",
    "body_group", "actual_price_rub", "predicted_price_rub",
    "abs_error_rub", "ape_pct", "model_name",
)

#: Колонки core.fact_prices, читаемые в feature pipeline.
ML_FACT_COLUMNS = (
    "price_id", "loading_date", "loading_city_gcid", "unloading_city_gcid",
    "distance", "total_weight", "total_volume", "body_type",
    "weight_category", "volume_category", "price_rub",
    "is_fact", "complex", "outlier_mark",
)

#: Колонки core.dim_city, читаемые в feature pipeline.
ML_CITY_COLUMNS = ("gc_id", "latitude", "longitude", "region")

# =============================================================================
# 10. Имена таблиц (raw / core / mart)
# =============================================================================
TABLE_PRICES = "prices"
TABLE_EXCHANGE_RATES = "exchange_rates"
TABLE_PRICE_DATES = "price_dates"
TABLE_CITIES = "cities"

TABLE_FACT_PRICES = "fact_prices"
TABLE_DIM_CITY = "dim_city"
TABLE_PRICE_BODY_GROUP = "price_body_group"
TABLE_QUARANTINE = "dq_quarantine_prices"
TABLE_BATCH_LOG = "etl_batch_log"
TABLE_REF_BODY_GROUP = "ref_body_group"
TABLE_ETL_PARAMS = "etl_params"

TABLE_ROUTE_CARD = "route_card"
TABLE_ML_PREDICTIONS = "ml_price_predictions"

# =============================================================================
# 11. SQL-артефакты и транзакционные ключевые слова
# =============================================================================
SQL_BODY_GROUPS = "body_groups.sql"
SQL_BUILD_MART = "build_mart.sql"
SQL_STEPS = (SQL_BODY_GROUPS, SQL_BUILD_MART)

#: Строки-маркеры, которые вырезаются при запуске SQL из Python
#: (атомарность обеспечивает транзакция SQLAlchemy).
TXN_KEYWORDS = frozenset({"BEGIN;", "COMMIT;", "ROLLBACK;", "BEGIN", "COMMIT"})

# =============================================================================
# 12. Ключи core.etl_params (совпадают с sql/ddl_core.sql)
# =============================================================================
PARAM_AS_OF_DATE = "as_of_date"
PARAM_FRESHNESS_DAYS = "freshness_days"
PARAM_RELIABILITY_HIGH_TRIPS = "reliability_high_trips"
PARAM_RELIABILITY_HIGH_CARRIERS = "reliability_high_carriers"
PARAM_RELIABILITY_MEDIUM_TRIPS = "reliability_medium_trips"
PARAM_RELIABILITY_HIGH = "reliability_level_high"
PARAM_RELIABILITY_MEDIUM = "reliability_level_medium"
PARAM_RELIABILITY_LOW = "reliability_level_low"
PARAM_RUB_MIN_PRICE = "rub_min_price"
PARAM_VOLUME_FTL_MAX = "volume_ftl_max"
PARAM_BODY_GROUP_OTHER = "body_group_other"
PARAM_BODY_GROUP_UNKNOWN = "body_group_unknown"

#: Значения этих параметров задаются в `sql/ddl_core.sql`
#: (таблица `core.etl_params`) — SQL-витрины читают их оттуда, чтобы не
#: содержать «магических» литералов. Python-код использует константы выше.
#: При изменении бизнес-правил синхронизируйте оба места.

# =============================================================================
# 13. Производительность и значения по умолчанию
# =============================================================================
BATCH_PAGE_SIZE = 10000          # размер страницы execute_values (запись)
ETL_READ_CHUNK_ROWS = 10000      # размер чанка при чтении источника (память O(chunk))

DEFAULT_DB_HOST = "localhost"
DEFAULT_DB_PORT = "5434"
DEFAULT_DB_NAME = "postgres"
DEFAULT_DB_USER = "postgres"
DEFAULT_DB_PASSWORD = "root"
DEFAULT_RAW_SCHEMA = "raw"
DEFAULT_CORE_SCHEMA = "core"
DEFAULT_MART_SCHEMA = "mart"
