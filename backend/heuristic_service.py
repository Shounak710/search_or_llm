import re


def apply_heuristics(query: str):
    q = query.lower().strip()
    words = q.split()

    # ---------------------------
    # 1. NAVIGATIONAL / LOCAL → SEARCH
    # ---------------------------
    if re.search(r"\b(near me|address|location|directions|map|closest)\b", q):
        return {"route": "search", "source": "heuristic", "reason": "navigation"}

    # ---------------------------
    # 2. FACTUAL / LOOKUP → SEARCH
    # ---------------------------
    factual_patterns = [
        r"\b(price|cost|weather|temperature|time|date|population|distance)\b",
        r"\b(rate|score|result|news|update)\b",
    ]

    if any(re.search(p, q) for p in factual_patterns):
        return {"route": "search", "source": "heuristic", "reason": "factual_lookup"}

    # ---------------------------
    # 3. VERY SHORT QUERY → SEARCH
    # ---------------------------
    if len(words) <= 2:
        return {"route": "search", "source": "heuristic", "reason": "short_query"}

    # ---------------------------
    # 4. GENERATIVE / CREATION → LLM
    # ---------------------------
    generative_patterns = [r"\b(write|create|design|generate|build|draft)\b"]

    if any(re.search(p, q) for p in generative_patterns):
        return {"route": "llm", "source": "heuristic", "reason": "creation"}

    # ---------------------------
    # 5. EXPLANATION / REASONING → LLM
    # ---------------------------
    reasoning_patterns = [
        r"\b(why|how does|how do|explain|compare|pros and cons|should i)\b"
    ]

    if any(re.search(p, q) for p in reasoning_patterns):
        return {"route": "llm", "source": "heuristic", "reason": "reasoning"}

    # ---------------------------
    # 6. EXACT ERROR (still useful globally)
    # ---------------------------
    if re.search(r"\b(error|exception|failed|not found)\b", q):
        return {"route": "search", "source": "heuristic", "reason": "known_issue"}

    return None
