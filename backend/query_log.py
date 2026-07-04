import json
from datetime import datetime, timezone
from pathlib import Path

LOG_DIR = Path(__file__).resolve().parent / "logs"
CLASSIFICATION_LOG_PATH = LOG_DIR / "queries.jsonl"
FEEDBACK_LOG_PATH = LOG_DIR / "feedback.jsonl"


def _append_jsonl(path: Path, entry: dict) -> None:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def log_classification(query: str, result: dict) -> None:
    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "query": query,
        "route": result["route"],
        "source": result["source"],
    }

    if "confidence" in result:
        entry["confidence"] = result["confidence"]
    if "reason" in result:
        entry["reason"] = result["reason"]

    _append_jsonl(CLASSIFICATION_LOG_PATH, entry)


def log_feedback(feedback: dict) -> None:
    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        **feedback,
    }
    _append_jsonl(FEEDBACK_LOG_PATH, entry)
