# -*- coding: utf-8 -*-
"""Configuration loaded from environment variables (see .env / .env.example)."""
import os

from dotenv import load_dotenv

# .env must not override already-set environment variables (e.g. -e flags in Docker).
load_dotenv(override=False)


def _quoted(name: str) -> str:
    """Schema name as a safe SQL identifier (handles any case)."""
    return '"' + name.replace('"', '""') + '"'


class Config:
    DB_HOST = os.getenv("DB_HOST", "localhost")
    DB_PORT = os.getenv("DB_PORT", "5434")
    DB_NAME = os.getenv("DB_NAME", "postgres")
    DB_USER = os.getenv("DB_USER", "postgres")
    DB_PASSWORD = os.getenv("DB_PASSWORD", "root")

    # raw -> core -> mart layers
    RAW_SCHEMA = os.getenv("DB_RAW_SCHEMA", "raw")
    CORE_SCHEMA = os.getenv("DB_CORE_SCHEMA", "core")
    MART_SCHEMA = os.getenv("DB_MART_SCHEMA", "mart")

    AS_OF_DATE = os.getenv("AS_OF_DATE", "2026-10-26")

    @property
    def sqlalchemy_url(self) -> str:
        return (
            f"postgresql+psycopg2://{self.DB_USER}:{self.DB_PASSWORD}"
            f"@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
        )

    @property
    def raw(self) -> str:
        return _quoted(self.RAW_SCHEMA)

    @property
    def core(self) -> str:
        return _quoted(self.CORE_SCHEMA)

    @property
    def mart(self) -> str:
        return _quoted(self.MART_SCHEMA)


config = Config()
