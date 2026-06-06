from pathlib import Path
import pickle

from .heuristic_service import apply_heuristics

_MODEL_PATH = Path(__file__).resolve().parent.parent / "model_training" / "query_router.pkl"
_model = pickle.load(_MODEL_PATH.open("rb"))


def classify(query: str):
    heuristics = apply_heuristics(query)
    if heuristics:
        return heuristics

    prediction = _model.predict([query])[0]
    confidence = float(_model.predict_proba([query]).max())

    return {"route": prediction, "source": "model", "confidence": confidence}
