# -*- coding: utf-8 -*-
"""Question 2: build analytical marts (body-group bridge + route-card mart).

The canonical SQL lives in sql/body_groups.sql and sql/build_mart.sql and is
also runnable via psql. Here the same files are executed inside a single
transaction (BEGIN/COMMIT lines stripped; atomicity is provided by the
SQLAlchemy transaction) so the mart rebuild is idempotent and part of the
pipeline.
"""
import logging
from pathlib import Path

from sqlalchemy import create_engine, text

from constants import (
    SQL_STEPS,
    TABLE_PRICE_BODY_GROUP,
    TABLE_ROUTE_CARD,
    TXN_KEYWORDS,
)
from etl.config import config

logger = logging.getLogger("etl.mart")

SQL_DIR = Path(__file__).resolve().parent.parent / "sql"
CORE = config.core
MART = config.mart


def _load_sql(name: str) -> str:
    sql = (SQL_DIR / name).read_text(encoding="utf-8")
    lines = [ln for ln in sql.splitlines() if ln.strip().upper() not in TXN_KEYWORDS]
    return "\n".join(lines)


def build_mart(engine) -> dict:
    with engine.begin() as conn:
        for step in SQL_STEPS:
            logger.info("Running %s", step)
            conn.exec_driver_sql(_load_sql(step))

    with engine.connect() as conn:
        rows = conn.execute(
            text(f"SELECT count(*) FROM {MART}.{TABLE_ROUTE_CARD}")
        ).scalar()
        groups = conn.execute(
            text(f"SELECT count(*) FROM {CORE}.{TABLE_PRICE_BODY_GROUP}")
        ).scalar()
    logger.info("Mart rebuilt: %s rows in mart.%s, %s in core.%s",
                rows, TABLE_ROUTE_CARD, groups, TABLE_PRICE_BODY_GROUP)
    return {"mart_rows": rows, "body_groups": groups}


def main():
    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s %(levelname)-7s %(name)s: %(message)s")
    engine = create_engine(config.sqlalchemy_url)
    stats = build_mart(engine)
    print("=" * 60)
    print("Mart build summary (Question 2)")
    print(f"mart.{TABLE_ROUTE_CARD} rows        : {stats['mart_rows']}")
    print(f"core.{TABLE_PRICE_BODY_GROUP} rows  : {stats['body_groups']}")
    print("=" * 60)
    engine.dispose()


if __name__ == "__main__":
    main()
