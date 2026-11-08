#!/usr/bin/env bash
# One-shot pipeline: init schema + data, run ETL, build marts, run ML.
set -euo pipefail

export PGPASSWORD="${DB_PASSWORD:-root}"
SQL_DIR="${SQL_DIR:-/app/sql}"
SCHEMA="TEST_V3"

PSQL=(psql -h "${DB_HOST}" -p "${DB_PORT}" -U "${DB_USER}" -d "${DB_NAME}" -v ON_ERROR_STOP=1)

echo "==> [1/6] create schema ${SCHEMA}"
"${PSQL[@]}" -c "CREATE SCHEMA IF NOT EXISTS \"${SCHEMA}\";"

echo "==> [2/6] load source DDL + synthetic data (300k deals)"
"${PSQL[@]}" -f "${SQL_DIR}/schema.sql"
"${PSQL[@]}" -f "${SQL_DIR}/synthetic.sql"

echo "==> [3/6] create analytical layer (core + mart DDL)"
"${PSQL[@]}" -f "${SQL_DIR}/ddl_core.sql"
"${PSQL[@]}" -f "${SQL_DIR}/ddl_mart.sql"
"${PSQL[@]}" -f "${SQL_DIR}/populate_dim_city.sql"

echo "==> [4/6] run ETL (question 1)"
python -m etl.main

echo "==> [5/6] build marts (question 2)"
python -m etl.mart

echo "==> [6/6] run ML (question 3)"
python -m ml.main

echo "==> pipeline finished OK"
