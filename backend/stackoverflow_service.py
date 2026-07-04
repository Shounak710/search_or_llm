import json
import re
import urllib.error
import urllib.parse
import urllib.request

STACKEXCHANGE_API = "https://api.stackexchange.com/2.3/search/advanced"
USER_AGENT = "search-v-llm-router/1.0"
MIN_SCORE = 3

_CODE_QUERY = re.compile(
    r"\b("
    r"python|javascript|typescript|java|c\+\+|c#|rust|golang|go lang|ruby|php|sql|"
    r"error|exception|traceback|stack trace|syntaxerror|typeerror|nameerror|"
    r"referenceerror|valueerror|keyerror|attributeerror|indentationerror|"
    r"importerror|modulenotfounderror|runtimeerror|nullpointer|segfault|"
    r"function|variable|class|method|import|compile|debug|regex|api|"
    r"react|vue|angular|node\.?js|django|flask|fastapi|spring|kubernetes|docker|"
    r"git|npm|pip|gradle|compiler|algorithm|leetcode|stackoverflow|"
    r"undefined is not|null is not|cannot read propert"
    r")\b",
    re.IGNORECASE,
)

_CODE_SYNTAX = re.compile(
    r"(```|`def |`function |`class |=>|\(\)\s*\{|#include|console\.log|"
    r"System\.out|public static void|fn main|use std::)",
    re.IGNORECASE,
)


def is_code_query(query: str) -> bool:
    return bool(_CODE_QUERY.search(query) or _CODE_SYNTAX.search(query))


def _search_stackoverflow(query: str, accepted_only: bool) -> list[dict]:
    params = {
        "order": "desc",
        "sort": "relevance",
        "q": query,
        "site": "stackoverflow",
        "pagesize": "5",
        "answers": "1",
    }
    if accepted_only:
        params["accepted"] = "True"

    url = f"{STACKEXCHANGE_API}?{urllib.parse.urlencode(params)}"
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})

    with urllib.request.urlopen(request, timeout=5) as response:
        payload = json.loads(response.read())

    return payload.get("items", [])


def _pick_best_match(items: list[dict]) -> dict | None:
    for item in items:
        if not item.get("is_answered"):
            continue

        score = item.get("score", 0)
        has_accepted = item.get("accepted_answer_id") is not None

        if has_accepted or score >= MIN_SCORE:
            return {
                "url": item["link"],
                "title": item.get("title", ""),
                "score": score,
                "accepted": has_accepted,
            }

    return None


def find_acceptable_answer(query: str) -> dict | None:
    try:
        accepted_matches = _search_stackoverflow(query, accepted_only=True)
        match = _pick_best_match(accepted_matches)
        if match:
            return match

        answered_matches = _search_stackoverflow(query, accepted_only=False)
        return _pick_best_match(answered_matches)
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, KeyError):
        return None
