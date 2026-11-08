# -*- coding: utf-8 -*-
"""Configuration loaded from environment variables (see .env / .env.example)."""
import os

from dotenv import load_dotenv

# .env must not override already-set environment variables (e.g. -e flags in Docker).
load_dotenv(override=False)


class Config:
    DB_HOST = os.getenv("DB_HOST", "localhost")
    DB_PORT = os.getenv("DB_PORT", "5434")
    DB_NAME = os.getenv("DB_NAME", "postgres")
    DB_USER = os.getenv("DB_USER", "postgres")
    DB_PASSWORD = os.getenv("DB_PASSWORD", "root")
    DB_SCHEMA = os.getenv("DB_SCHEMA", "TEST_V3")
    AS_OF_DATE = os.getenv("AS_OF_DATE", "2026-10-26")

    @property
    def sqlalchemy_url(self) -> str:
        return (
            f"postgresql+psycopg2://{self.DB_USER}:{self.DB_PASSWORD}"
            f"@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
        )

    @property
    def schema_quoted(self) -> str:
        """Schema name as a quoted identifier (handles mixed-case like TEST_V3)."""
        return '"' + self.DB_SCHEMA.replace('"', '""') + '"'


config = Config()
