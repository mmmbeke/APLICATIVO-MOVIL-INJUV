"""Tests de integración contra PostgreSQL real.

TEST_DATABASE_ADMIN_URL debe apuntar a un servidor Postgres de pruebas. Si existe la BD
`injuv_web_template` (esquema creado por la plataforma web) se clona; si no, se parte de una BD vacía.
Nunca apuntar a Neon de producción.
"""
import os
import uuid

import psycopg2
import pytest
from psycopg2 import sql

ADMIN_URL = os.environ.get("TEST_DATABASE_ADMIN_URL", "postgresql://postgres:postgres@localhost:5432/postgres")
TEMPLATE = os.environ.get("TEST_DATABASE_TEMPLATE", "injuv_web_template")
DB_NAME = f"injuv_test_{uuid.uuid4().hex[:8]}"
BASE = ADMIN_URL.rsplit("/", 1)[0]


def _admin_conn():
    conn = psycopg2.connect(ADMIN_URL)
    conn.autocommit = True
    return conn


_c = _admin_conn()
with _c.cursor() as _cur:
    _cur.execute("SELECT 1 FROM pg_database WHERE datname = %s", (TEMPLATE,))
    _has_template = _cur.fetchone() is not None
    if _has_template:
        _cur.execute(sql.SQL("CREATE DATABASE {} TEMPLATE {}").format(sql.Identifier(DB_NAME), sql.Identifier(TEMPLATE)))
    else:
        _cur.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(DB_NAME)))
_c.close()

os.environ["DATABASE_URL"] = f"{BASE}/{DB_NAME}"
os.environ["DB_SSLMODE"] = "disable"
os.environ["JWT_SECRET_KEY"] = "test-secret-key-con-largo-suficiente-para-hs256"
os.environ["CORS_ORIGINS"] = "*"

from fastapi.testclient import TestClient  # noqa: E402

from app.db.session import engine  # noqa: E402
from main import app  # noqa: E402
from scripts.init_db import main as init_db  # noqa: E402


@pytest.fixture(scope="session", autouse=True)
def database():
    init_db()
    init_db()  # idempotencia
    yield
    engine.dispose()
    c = _admin_conn()
    with c.cursor() as cur:
        cur.execute(sql.SQL("DROP DATABASE IF EXISTS {} WITH (FORCE)").format(sql.Identifier(DB_NAME)))
    c.close()


@pytest.fixture(scope="session")
def client():
    with TestClient(app) as c:
        yield c


@pytest.fixture(scope="session")
def has_web_schema():
    return _has_template

