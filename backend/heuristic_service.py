import re

# LLM intent — checked first so broad search patterns cannot override them.
_LLM_CREATION = re.compile(
    r"\b(write|create|design|generate|build|draft|implement|compose|make)\b"
)
_LLM_CODE_REVIEW = re.compile(
    r"\b("
    r"check if|is it correct|is this correct|does this look|am i doing this right|"
    r"review this|in this code|in my code|this code|my code|"
    r"what'?s wrong with this|did i do this right"
    r")\b",
    re.IGNORECASE,
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

_POPULAR_WEBSITES = re.compile(
    r"\b("
    r"reddit|youtube|twitter|instagram|facebook|github|gitlab|linkedin|"
    r"tiktok|twitch|discord|spotify|netflix|amazon|wikipedia|medium|"
    r"pinterest|craigslist|ebay|stackoverflow|stack overflow|"
    r"hacker news|hackernews|imdb|yelp|airbnb|snapchat|whatsapp|telegram|"
    r"substack|patreon|kickstarter|quora|mastodon|bluesky"
    r")\b",
    re.IGNORECASE,
)

# Building the platform itself (e.g. "how to build reddit"), not using it ("reddit login").
_WEBSITE_PLATFORM_BUILD = re.compile(
    r"\b(build|create|implement|design|develop|clone|replicate|architect)\b",
    re.IGNORECASE,
)
_WEBSITE_USAGE = re.compile(
    r"\b("
    r"account|login|log in|sign up|signup|post|comment|profile|subreddit|"
    r"upload|subscribe|follow|message|dm|notification|password|settings"
    r")\b",
    re.IGNORECASE,
)

_LLM_PREFIXES = re.compile(
    r"^(explain|teach|debug|fix|write|create|design|build|implement|recommend|summarize|evaluate)\b"
)


def is_code_review_query(query: str) -> bool:
    return bool(_LLM_CODE_REVIEW.search(query))


def is_website_platform_creation(query: str) -> bool:
    q = query.lower()
    if not _POPULAR_WEBSITES.search(q):
        return False
    if not _WEBSITE_PLATFORM_BUILD.search(q):
        return False
    return not _WEBSITE_USAGE.search(q)


def apply_heuristics(query: str):
    q = query.lower().strip()
    if not q:
        return None

    words = q.split()

    if _LLM_CREATION.search(q):
        return {"route": "llm", "source": "heuristic", "reason": "creation"}

    if _LLM_CODE_REVIEW.search(q):
        return {"route": "llm", "source": "heuristic", "reason": "code_review"}

    if _LLM_REASONING.search(q):
        return {"route": "llm", "source": "heuristic", "reason": "reasoning"}

    if _NAVIGATION.search(q):
        return {"route": "search", "source": "heuristic", "reason": "navigation"}

    if _FACTUAL_LOOKUP.search(q):
        return {"route": "search", "source": "heuristic", "reason": "factual_lookup"}

    if _POPULAR_WEBSITES.search(q):
        if is_website_platform_creation(q):
            return {"route": "llm", "source": "heuristic", "reason": "website_creation"}
        return {"route": "search", "source": "heuristic", "reason": "popular_website"}

    # Single-token lookups (e.g. "infosys", "sentosa") — skip LLM-style prefixes.
    if len(words) == 1 and not _LLM_PREFIXES.search(q):
        return {"route": "search", "source": "heuristic", "reason": "short_query"}

    return None
