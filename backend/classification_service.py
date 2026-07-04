from pathlib import Path
import pickle

from .heuristic_service import apply_heuristics

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


def classify(query: str):
    heuristics = apply_heuristics(query)
    if heuristics:
        return heuristics

    route, confidence = _predict(query)

    return {"route": route, "source": "model", "confidence": confidence}
