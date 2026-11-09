#!/usr/bin/env bash
# One-shot pipeline: init raw/core/mart, run ETL, build marts, run ML.
# Safe to re-run against an existing volume: the source-loading step is skipped
# when raw.prices is already present; every downstream step is idempotent.
set -euo pipefail

export PGPASSWORD="${DB_PASSWORD:-root}"
SQL_DIR="${SQL_DIR:-/app/sql}"
RAW="${DB_RAW_SCHEMA:-raw}"
CORE="${DB_CORE_SCHEMA:-core}"
MART="${DB_MART_SCHEMA:-mart}"

PSQL=(psql -h "${DB_HOST}" -p "${DB_PORT}" -U "${DB_USER}" -d "${DB_NAME}" -v ON_ERROR_STOP=1)

echo "==> [1/6] create schemas: ${RAW}, ${CORE}, ${MART}"
"${PSQL[@]}" -c "CREATE SCHEMA IF NOT EXISTS ${RAW}; CREATE SCHEMA IF NOT EXISTS ${CORE}; CREATE SCHEMA IF NOT EXISTS ${MART};"

exists=$("${PSQL[@]}" -tAc "SELECT count(*) FROM information_schema.tables WHERE table_schema = '${RAW}' AND table_name = 'prices'")
if [ "${exists}" = "1" ]; then
    echo "==> [2/6] source already initialized (${RAW}.prices exists) — skip load"
else
    echo "==> [2/6] load source DDL + synthetic data (${N_PRICES:-300000} deals)"
    "${PSQL[@]}" -c "SET search_path TO ${RAW};" \
        -v "n_prices=${N_PRICES:-300000}" \
        -f "${SQL_DIR}/schema.sql" \
        -f "${SQL_DIR}/synthetic.sql"
fi

echo "==> [3/6] create analytical layer (core + mart DDL, dim_city)"
"${PSQL[@]}" \
    -f "${SQL_DIR}/ddl_core.sql" \
    -f "${SQL_DIR}/ddl_mart.sql" \
    -f "${SQL_DIR}/populate_dim_city.sql"

echo "==> [4/6] run ETL (question 1)"
python -m etl.main

echo "==> [5/6] build marts (question 2)"
python -m etl.mart

echo "==> [6/6] run ML (question 3)"
python -m ml.main

echo "==> pipeline finished OK"
