# -*- coding: utf-8 -*-
"""Command-line entry point for the ETL pipeline (Question 1).

Usage:
    python -m etl.main [--start-date YYYY-MM-DD] [--end-date YYYY-MM-DD]

Re-running for the same window is strictly idempotent (UPSERT / ON CONFLICT).
"""
import argparse
import logging

from sqlalchemy import create_engine

from etl.config import config
from etl.pipeline import run_pipeline


def main():
    parser = argparse.ArgumentParser(description="Run the Smart Logistics ETL (Question 1)")
    parser.add_argument("--start-date", help="Inclusive lower bound on loading_date")
    parser.add_argument("--end-date", help="Inclusive upper bound on loading_date")
    parser.add_argument("--with-mart", action="store_true",
                        help="After ETL, rebuild the analytical marts (Question 2)")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)-7s %(name)s: %(message)s",
    )

    run_pipeline(args.start_date, args.end_date)

    if args.with_mart:
        from etl.mart import build_mart
        engine = create_engine(config.sqlalchemy_url)
        build_mart(engine)
        engine.dispose()


if __name__ == "__main__":
    main()
