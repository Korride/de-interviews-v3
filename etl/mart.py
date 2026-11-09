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

from etl.config import config

logger = logging.getLogger("etl.mart")

SQL_DIR = Path(__file__).resolve().parent.parent / "sql"
CORE = config.core
MART = config.mart

_TXN_KEYWORDS = {"BEGIN;", "COMMIT;", "ROLLBACK;", "BEGIN", "COMMIT"}


def _load_sql(name: str) -> str:
    sql = (SQL_DIR / name).read_text(encoding="utf-8")
    lines = [ln for ln in sql.splitlines() if ln.strip().upper() not in _TXN_KEYWORDS]
    return "\n".join(lines)


def build_mart(engine) -> dict:
    steps = ["body_groups.sql", "build_mart.sql"]
    with engine.begin() as conn:
        for step in steps:
            logger.info("Running %s", step)
            conn.exec_driver_sql(_load_sql(step))

    with engine.connect() as conn:
        rows = conn.execute(
            text(f"SELECT count(*) FROM {MART}.route_card")
        ).scalar()
        groups = conn.execute(
            text(f"SELECT count(*) FROM {CORE}.price_body_group")
        ).scalar()
    logger.info("Mart rebuilt: %s rows in mart.route_card, %s in core.price_body_group", rows, groups)
    return {"mart_rows": rows, "body_groups": groups}


def main():
    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s %(levelname)-7s %(name)s: %(message)s")
    engine = create_engine(config.sqlalchemy_url)
    stats = build_mart(engine)
    print("=" * 60)
    print("Mart build summary (Question 2)")
    print(f"mart.route_card rows        : {stats['mart_rows']}")
    print(f"core.price_body_group rows  : {stats['body_groups']}")
    print("=" * 60)
    engine.dispose()


if __name__ == "__main__":
    main()
