import re

# LLM intent — checked first so broad search patterns cannot override them.
_LLM_CREATION = re.compile(
    r"\b(write|create|design|generate|build|draft|implement|compose|make)\b"
)
_LLM_REASONING = re.compile(
    r"\b("
    r"why|how does|how do|explain|compare|pros and cons|should i|"
    r"teach me|debug|fix|recommend|summarize|evaluate|plan an|itinerary|"
    r"explained"
    r")\b"
)

# High-confidence search intent.
_NAVIGATION = re.compile(
    r"\b(near me|address|location|directions|closest|google maps?)\b"
)
_FACTUAL_LOOKUP = re.compile(
    r"\b("
    r"share price|stock price|weather in|weather today|temperature in|"
    r"petrol price|diesel price|bitcoin price|ethereum price|"
    r"what time is|current time|today'?s date|population of|"
    r"distance from|distance to|"
    r"news today|latest news|breaking news"
    r")\b"
)

_LLM_PREFIXES = re.compile(
    r"^(explain|teach|debug|fix|write|create|design|build|implement|recommend|summarize|evaluate)\b"
)


def apply_heuristics(query: str):
    q = query.lower().strip()
    if not q:
        return None

    words = q.split()

    if _LLM_CREATION.search(q):
        return {"route": "llm", "source": "heuristic", "reason": "creation"}

    if _LLM_REASONING.search(q):
        return {"route": "llm", "source": "heuristic", "reason": "reasoning"}

    if _NAVIGATION.search(q):
        return {"route": "search", "source": "heuristic", "reason": "navigation"}

    if _FACTUAL_LOOKUP.search(q):
        return {"route": "search", "source": "heuristic", "reason": "factual_lookup"}

    # Single-token lookups (e.g. "infosys", "sentosa") — skip LLM-style prefixes.
    if len(words) == 1 and not _LLM_PREFIXES.search(q):
        return {"route": "search", "source": "heuristic", "reason": "short_query"}

    return None
