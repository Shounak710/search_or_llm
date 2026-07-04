from pathlib import Path
import pickle

from .heuristic_service import apply_heuristics
from .stackoverflow_service import find_acceptable_answer, is_code_query

_MODEL_PATH = Path(__file__).resolve().parent.parent / "model_training" / "query_router.pkl"
_model = pickle.load(_MODEL_PATH.open("rb"))

# Prefer search when the model is uncertain or only slightly favors LLM.
_UNCERTAIN_THRESHOLD = 0.60
_SEARCH_BIAS_MARGIN = 0.12


def _predict(query: str):
    probs = _model.predict_proba([query])[0]
    prob_by_label = {
        label: float(prob) for label, prob in zip(_model.classes_, probs)
    }
    search_prob = prob_by_label["search"]
    llm_prob = prob_by_label["llm"]

    if max(probs) < _UNCERTAIN_THRESHOLD:
        return "search", search_prob

    if llm_prob > search_prob and (llm_prob - search_prob) < _SEARCH_BIAS_MARGIN:
        return "search", search_prob

    if search_prob >= llm_prob:
        return "search", search_prob

    return "llm", llm_prob


def _apply_stackoverflow_override(query: str, result: dict) -> dict:
    if not is_code_query(query):
        return result

    match = find_acceptable_answer(query)
    if not match:
        return result

    overridden = {
        "route": "search",
        "source": "stackoverflow",
        "redirect_url": match["url"],
        "reason": "stackoverflow_match",
        "stackoverflow_title": match["title"],
        "stackoverflow_score": match["score"],
        "stackoverflow_accepted": match["accepted"],
    }

    if "confidence" in result:
        overridden["confidence"] = result["confidence"]

    return overridden


def classify(query: str):
    heuristics = apply_heuristics(query)
    if heuristics:
        return _apply_stackoverflow_override(query, heuristics)

    route, confidence = _predict(query)
    result = {"route": route, "source": "model", "confidence": confidence}

    return _apply_stackoverflow_override(query, result)
