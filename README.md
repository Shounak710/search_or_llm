# Nemka

Route each query to **web search** or an **LLM** automatically, instead of choosing yourself every time. A FastAPI backend classifies queries, a browser extension provides a popup UI, and a setup page helps you register Nemka as your default search engine.

## How it works

1. You submit a query (address bar, setup page, or extension popup).
2. The backend classifies it using **heuristics**, a **scikit-learn model**, and optional **Stack Overflow** lookup for code questions.
3. You are redirected to:
   - **Search** — Google, DuckDuckGo, or Bing
   - **Stack Overflow** — when a strong existing answer is found
   - **LLM** — ChatGPT or Claude (query copied to clipboard on handoff)

```
Query → Heuristics → (if no match) ML model → (if code query) Stack Overflow API → Redirect
```

## Features

- **Smart routing** — factual lookups tend toward search; reasoning, creation, and code review toward LLM
- **Stack Overflow shortcut** — code queries with a good accepted/high-scoring answer go straight to that thread
- **Browser extension** — classify, override manually, and give delayed feedback on whether search or LLM was more useful
- **Default search engine** — copy a generated URL from the setup page and set it as your browser default
- **Query history** — local browser history with optional ratings (when query logging is enabled)
- **Privacy controls** — opt out of query text logging; anonymous aggregate stats still collected
- **Usage analytics** — per-request stats (route mix, latency, country, unique users) without storing query text

## Project structure

```
├── backend/                 # FastAPI app
│   ├── app.py               # Routes and redirect logic
│   ├── classification_service.py
│   ├── heuristic_service.py
│   ├── stackoverflow_service.py
│   ├── routing_urls.py
│   ├── query_log.py         # Query + feedback logs
│   ├── stats_log.py         # Anonymous aggregate stats
│   ├── geo_service.py       # Country detection
│   └── static/              # Setup page assets
├── extension/               # Chrome/Firefox extension (Manifest V3)
├── model_training/          # Dataset, notebooks, trained model
│   ├── dataset.example.csv  # Format reference (committed)
│   ├── dataset.csv          # Private — not in git; copy from example locally
│   ├── query_router.pkl     # Trained classifier (committed; safe to deploy)
│   ├── training.ipynb
│   └── model.ipynb
└── requirements.txt
```

## Quick start

### Backend

```bash
pip install -r requirements.txt
uvicorn backend.app:app --reload --port 5000
```

Open [http://127.0.0.1:5000](http://127.0.0.1:5000) for the setup page.

### Browser extension

1. Open `chrome://extensions` (or Firefox equivalent).
2. Enable **Developer mode**.
3. Click **Load unpacked** and select the `extension/` folder.
4. Ensure the backend is running at `http://127.0.0.1:5000`.

Reload the extension after changing `manifest.json` or permissions.

### Default search engine

On the setup page:

1. Choose your search engine and LLM destination.
2. Copy the generated search URL (it contains `q=%s` — do not URL-encode the `%s`).
3. Add it as a custom search engine named **Nemka** (shortcut: `nemka`) and set it as default.

Example URL shape:

```
http://127.0.0.1:5000/search?q=%s&se=google&llm=openai
```

Add `&log=0` to disable query logging while still collecting anonymous stats.

## API

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/` | Setup page |
| `GET` | `/search?q=…` | Classify and redirect (main entry point for default search engine) |
| `POST` | `/classify` | Classify only (used by extension) |
| `POST` | `/feedback` | Submit routing feedback |
| `POST` | `/api/log-preference` | Rate a logged query from setup history |
| `GET` | `/api/stats/summary?days=30` | Private usage analytics (`X-Stats-Key` required; 404 if unset) |
| `GET` | `/health` | Health check |

### Classify response

```json
{
  "query": "explain quicksort vs mergesort",
  "route": "llm",
  "source": "model",
  "confidence": 0.82,
  "redirect_url": null
}
```

When Stack Overflow matches, `source` is `"stackoverflow"` and `redirect_url` points to the question.

## Logging and privacy

Log files and training data are **not committed to git** and are **not served over HTTP**.

| Log file | Contents | In git | Opt-out |
|----------|----------|--------|---------|
| `backend/logs/queries.jsonl` | Full query text + classification | No | Yes (`log=0` or checkbox on setup page) |
| `backend/logs/feedback.jsonl` | User feedback on routing quality | No | N/A |
| `backend/logs/stats.jsonl` | Anonymous stats per request | No | Always on |
| `model_training/dataset.csv` | Training labels | No | N/A |
| `model_training/query_router.pkl` | Trained classifier | Yes | N/A |

**Stats entries** include timestamp, hashed user ID, route destination (`search` / `llm` / `stackoverflow`), latency, country, and whether the query was logged. No query text is stored in stats.

Set `STATS_API_KEY` in your environment (see `.env.example`). The stats endpoint returns **404** when the key is not configured, and **403** without a valid `X-Stats-Key` header. Log files are never served over HTTP.

Query history on the setup page is stored in **localStorage** in your browser, not on the server.

## Model training

Training data is private. Copy the format from `model_training/dataset.example.csv` to `model_training/dataset.csv` and add your labeled rows locally (this file stays out of git). To retrain:

1. Open `model_training/training.ipynb`.
2. Train and export `query_router.pkl`.
3. Restart the backend to load the new model, then commit `query_router.pkl` if you want it deployed via git.

The classifier uses TF-IDF + logistic regression with a search bias at inference time (uncertain or close calls favor search).

## Configuration

Search engine and LLM options are encoded in the `/search` URL parameters:

| Param | Values |
|-------|--------|
| `se` | `google`, `duckduckgo`, `bing` |
| `llm` | `openai`, `claude` |
| `log` | `1` (default) or `0` to skip query logging |

Preferences on the setup page are saved to `localStorage` under `nemka_setup_preferences`.

## Requirements

- Python 3.10+
- scikit-learn (compatible with the pickled model version)
- A modern Chromium or Firefox browser for the extension
