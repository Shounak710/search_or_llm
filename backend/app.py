from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from .classification_service import classify
from .query_log import log_classification, log_feedback

app = FastAPI(title="Query Router", version="1.0.0")


class ClassifyRequest(BaseModel):
    query: str = Field(..., min_length=1)


class ClassifyResponse(BaseModel):
    query: str
    route: str
    source: str
    confidence: float | None = None
    reason: str | None = None


class FeedbackRequest(BaseModel):
    query: str = Field(..., min_length=1)
    predicted_route: str
    chosen_route: str
    useful_route: str
    manual_override: bool = False
    classified_at: str | None = None


class FeedbackResponse(BaseModel):
    status: str = "ok"


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/classify", response_model=ClassifyResponse)
def classify_query(body: ClassifyRequest):
    query = body.query.strip()
    if not query:
        raise HTTPException(status_code=400, detail="Query cannot be empty")

    result = classify(query)
    log_classification(query, result)

    return ClassifyResponse(
        query=query,
        route=result["route"],
        source=result["source"],
        confidence=result.get("confidence"),
        reason=result.get("reason"),
    )


@app.post("/feedback", response_model=FeedbackResponse)
def submit_feedback(body: FeedbackRequest):
    if body.useful_route not in {"search", "llm", "both", "neither"}:
        raise HTTPException(status_code=400, detail="Invalid useful_route")

    log_feedback(body.model_dump())
    return FeedbackResponse()
