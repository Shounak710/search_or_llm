import hashlib
from collections import Counter
from datetime import date, datetime, timedelta, timezone

from .db import db_connection
from .geo_service import is_local_ip, lookup_country

_USER_HASH_SALT = "nemka-aggregate-stats-v1"


def user_hash_from_ip(ip: str) -> str:
    digest = hashlib.sha256(f"{_USER_HASH_SALT}:{ip}".encode()).hexdigest()
    return digest[:16]


def destination_from_result(result: dict) -> str:
    if result.get("source") == "stackoverflow":
        return "stackoverflow"
    return result.get("route", "search")


def log_request_stat(
    *,
    ip: str,
    country_hint: str | None,
    endpoint: str,
    result: dict,
    latency_ms: float,
    query_logged: bool,
) -> None:
    if country_hint:
        country = country_hint
    elif is_local_ip(ip) or ip == "unknown":
        country = "local"
    else:
        country = lookup_country(ip)

    now = datetime.now(timezone.utc)

    with db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO request_stats (
                    timestamp, date, user_hash, endpoint, destination,
                    route, source, latency_ms, country, query_logged
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    now,
                    now.date(),
                    user_hash_from_ip(ip),
                    endpoint,
                    destination_from_result(result),
                    result["route"],
                    result["source"],
                    round(latency_ms, 2),
                    country,
                    query_logged,
                ),
            )


def summarize_stats(days: int = 30) -> dict:
    cutoff = date.today() - timedelta(days=max(days - 1, 0))
    empty = {
        "total_requests": 0,
        "unique_users": 0,
        "avg_latency_ms": 0.0,
        "destination_pct": {},
        "requests_by_day": [],
        "requests_by_country": {},
    }

    with db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT
                    COUNT(*) AS total_requests,
                    COUNT(DISTINCT user_hash) AS unique_users,
                    COALESCE(AVG(latency_ms), 0) AS avg_latency_ms
                FROM request_stats
                WHERE date >= %s
                """,
                (cutoff,),
            )
            summary = cur.fetchone()
            if not summary or summary[0] == 0:
                return empty

            total_requests, unique_users, avg_latency_ms = summary

            cur.execute(
                """
                SELECT destination, COUNT(*) AS count
                FROM request_stats
                WHERE date >= %s
                GROUP BY destination
                """,
                (cutoff,),
            )
            destinations = Counter({row[0]: row[1] for row in cur.fetchall()})

            cur.execute(
                """
                SELECT date, COUNT(*) AS count
                FROM request_stats
                WHERE date >= %s
                GROUP BY date
                ORDER BY date
                """,
                (cutoff,),
            )
            requests_by_day = [
                {"date": row[0].isoformat(), "requests": row[1]}
                for row in cur.fetchall()
            ]

            cur.execute(
                """
                SELECT country, COUNT(*) AS count
                FROM request_stats
                WHERE date >= %s
                GROUP BY country
                ORDER BY count DESC
                """,
                (cutoff,),
            )
            requests_by_country = {row[0]: row[1] for row in cur.fetchall()}

    destination_pct = {
        key: round(count / total_requests * 100, 2)
        for key, count in destinations.items()
    }

    return {
        "total_requests": total_requests,
        "unique_users": unique_users,
        "avg_latency_ms": round(float(avg_latency_ms), 2),
        "destination_pct": destination_pct,
        "requests_by_day": requests_by_day,
        "requests_by_country": requests_by_country,
    }
