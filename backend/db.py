import os
from contextlib import contextmanager

import psycopg2
from psycopg2.pool import SimpleConnectionPool

_pool: SimpleConnectionPool | None = None

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS classifications (
    log_id UUID PRIMARY KEY,
    timestamp TIMESTAMPTZ NOT NULL,
    query TEXT NOT NULL,
    route TEXT NOT NULL,
    source TEXT NOT NULL,
    confidence DOUBLE PRECISION,
    reason TEXT,
    redirect_url TEXT,
    stackoverflow_title TEXT,
    stackoverflow_score INTEGER,
    stackoverflow_accepted BOOLEAN,
    useful_route TEXT,
    useful_route_at TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS request_stats (
    id BIGSERIAL PRIMARY KEY,
    timestamp TIMESTAMPTZ NOT NULL,
    date DATE NOT NULL,
    user_hash TEXT NOT NULL,
    endpoint TEXT NOT NULL,
    destination TEXT NOT NULL,
    route TEXT NOT NULL,
    source TEXT NOT NULL,
    latency_ms DOUBLE PRECISION NOT NULL,
    country TEXT NOT NULL,
    query_logged BOOLEAN NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_request_stats_date ON request_stats (date);
CREATE INDEX IF NOT EXISTS idx_request_stats_user_hash ON request_stats (user_hash);

CREATE TABLE IF NOT EXISTS feedback (
    id BIGSERIAL PRIMARY KEY,
    timestamp TIMESTAMPTZ NOT NULL,
    log_id UUID,
    query TEXT NOT NULL,
    predicted_route TEXT,
    chosen_route TEXT,
    useful_route TEXT NOT NULL,
    manual_override BOOLEAN NOT NULL DEFAULT FALSE,
    classified_at TIMESTAMPTZ,
    source TEXT
);

CREATE INDEX IF NOT EXISTS idx_feedback_log_id ON feedback (log_id);
"""


def get_database_url() -> str:
    url = os.getenv("DATABASE_URL", "").strip()
    if not url:
        raise RuntimeError(
            "DATABASE_URL is not set. Add a Postgres service on Railway or set it locally."
        )
    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql://", 1)
    return url


def init_db() -> None:
    global _pool
    if _pool is not None:
        return

    _pool = SimpleConnectionPool(1, 10, dsn=get_database_url())
    with db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(SCHEMA_SQL)


def close_db() -> None:
    global _pool
    if _pool is not None:
        _pool.closeall()
        _pool = None


@contextmanager
def db_connection():
    if _pool is None:
        raise RuntimeError("Database pool is not initialized")

    conn = _pool.getconn()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        _pool.putconn(conn)


def check_db_connection() -> bool:
    try:
        with db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1")
        return True
    except Exception:
        return False
