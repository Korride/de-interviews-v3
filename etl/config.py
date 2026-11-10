# -*- coding: utf-8 -*-
"""Configuration loaded from environment variables (see .env / .env.example).

Значения по умолчанию берутся из `constants.py`.
"""
import os

from dotenv import load_dotenv

from constants import (
    AS_OF_DATE as DEFAULT_AS_OF_DATE,
    DEFAULT_CORE_SCHEMA,
    DEFAULT_DB_HOST,
    DEFAULT_DB_NAME,
    DEFAULT_DB_PASSWORD,
    DEFAULT_DB_PORT,
    DEFAULT_DB_USER,
    DEFAULT_MART_SCHEMA,
    DEFAULT_RAW_SCHEMA,
)

# .env must not override already-set environment variables (e.g. -e flags in Docker).
load_dotenv(override=False)


def _quoted(name: str) -> str:
    """Schema name as a safe SQL identifier (handles any case)."""
    return '"' + name.replace('"', '""') + '"'


class Config:
    DB_HOST = os.getenv("DB_HOST", DEFAULT_DB_HOST)
    DB_PORT = os.getenv("DB_PORT", DEFAULT_DB_PORT)
    DB_NAME = os.getenv("DB_NAME", DEFAULT_DB_NAME)
    DB_USER = os.getenv("DB_USER", DEFAULT_DB_USER)
    DB_PASSWORD = os.getenv("DB_PASSWORD", DEFAULT_DB_PASSWORD)

    # raw -> core -> mart layers
    RAW_SCHEMA = os.getenv("DB_RAW_SCHEMA", DEFAULT_RAW_SCHEMA)
    CORE_SCHEMA = os.getenv("DB_CORE_SCHEMA", DEFAULT_CORE_SCHEMA)
    MART_SCHEMA = os.getenv("DB_MART_SCHEMA", DEFAULT_MART_SCHEMA)

    AS_OF_DATE = os.getenv("AS_OF_DATE", DEFAULT_AS_OF_DATE)

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
