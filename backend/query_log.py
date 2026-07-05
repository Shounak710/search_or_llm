import uuid
from datetime import datetime, timezone

from .db import db_connection


def log_classification(query: str, result: dict) -> str:
    log_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc)

    with db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO classifications (
                    log_id, timestamp, query, route, source,
                    confidence, reason, redirect_url,
                    stackoverflow_title, stackoverflow_score, stackoverflow_accepted
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    log_id,
                    now,
                    query,
                    result["route"],
                    result["source"],
                    result.get("confidence"),
                    result.get("reason"),
                    result.get("redirect_url"),
                    result.get("stackoverflow_title"),
                    result.get("stackoverflow_score"),
                    result.get("stackoverflow_accepted"),
                ),
            )

    return log_id


def update_log_preference(log_id: str, useful_route: str) -> bool:
    now = datetime.now(timezone.utc)

    with db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE classifications
                SET useful_route = %s, useful_route_at = %s
                WHERE log_id = %s
                """,
                (useful_route, now, log_id),
            )
            return cur.rowcount > 0


def log_feedback(feedback: dict) -> None:
    now = datetime.now(timezone.utc)
    classified_at = feedback.get("classified_at")
    if isinstance(classified_at, str) and classified_at:
        classified_at = datetime.fromisoformat(classified_at.replace("Z", "+00:00"))
    elif not classified_at:
        classified_at = None

    with db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO feedback (
                    timestamp, log_id, query, predicted_route, chosen_route,
                    useful_route, manual_override, classified_at, source
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    now,
                    feedback.get("log_id"),
                    feedback["query"],
                    feedback.get("predicted_route"),
                    feedback.get("chosen_route"),
                    feedback["useful_route"],
                    bool(feedback.get("manual_override", False)),
                    classified_at,
                    feedback.get("source"),
                ),
            )
