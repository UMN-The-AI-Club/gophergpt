# GopherGPT

An AI assistant for University of Minnesota students. Ask it about courses, professors, grade distributions, class sections, study spaces, or what's on campus, and it pulls real data from GopherGrades, UMN's live course catalog, a vector index of every UMN course description, UMN's room booking system, and the broader web before answering.

Built on a ReAct agent (LangGraph) with a **pluggable LLM backend** (local Ollama, OpenAI, or self-hosted vLLM), a FastAPI backend, and a React frontend that renders answers as rich data cards.

![Python](https://img.shields.io/badge/python-3.11-blue.svg)
![FastAPI](https://img.shields.io/badge/FastAPI-0.118-009688.svg)
![React](https://img.shields.io/badge/React-18-61dafb.svg)
![Docker](https://img.shields.io/badge/Docker-ready-2496ed.svg)

## What it does

- **Course lookup & grade insight.** Grade distributions, SRT ratings, and instructor lists from GopherGrades (`umn.lol`), rendered as charts. Ask "how hard is CSCI 1933?" and get the distribution, not a paragraph.
- **Professor cards.** Full profile for one professor (rating, courses, grade tendency), or two professors **side by side** — "compare professor Myers and Dovolis".
- **Course comparison.** Two courses side by side with grade charts and an AI recommendation.
- **Live sections & scheduling.** Real section data from UMN's course catalog — times, instructor, room, open/closed with seat caps. Handles "what sections of CSCI 1933 are open this fall?" and open-ended scheduling ("find a lib-ed that fits with my classes").
- **Course catalog search (RAG).** Descriptions, prerequisites, credits, and offered terms for every UMN Twin Cities course — indexed from the live Coursedog catalog into Postgres + pgvector at startup. "What are the prerequisites for CSCI 3081W?" is answered from the catalog, not from the model's memory.
- **Department Explorer.** Browse a full department's courses with grade charts and ratings.
- **Study space finder.** Buildings by category (quiet, group, late-night, tech, St. Paul) with Google Maps + campus map links and LibCal reservation links.
- **UMN Research Finder.** Domain-restricted web search across `umn.edu` with LLM-generated summaries.
- **Chat with memory.** Conversations persist across sessions — save, reload, clear.
- **Personalization.** Profile-aware responses — major, level, year, and completed/planned coursework feed the prompt so recommendations skip prereqs you've taken. "Tell me about the courses I plan to take" reads codes straight from your profile.

## Architecture

```
┌─────────────────┐        ┌────────────────────────────────────┐
│  React frontend │ ─HTTP─▶ │  FastAPI backend (port 8000)       │
│  (port 3000)    │        │  /chat · /umn/* · /research · ...   │
└─────────────────┘        └──────────────────┬─────────────────┘
                                               │  intent routing (chat.py)
                        ┌──────────────────────┴───────────────────────┐
                        ▼                                               ▼
          ┌───────────────────────────┐                  ┌──────────────────────────┐
          │  Deterministic cards       │                  │  ReAct agent (LangGraph)  │
          │  (no LLM tool-choice):     │                  │  picks + chains tools     │
          │  grades · compare ·        │                  │  for open-ended questions │
          │  sections · prof_compare · │                  └────────────┬─────────────┘
          │  research · my-courses     │                               │
          └────────────┬──────────────┘                               │
             full data  │                                              │  compact summaries
             (fetch_*)  ▼                                              ▼  (@tool)
          ┌──────────────────────────────────────────────────────────────────────┐
          │  Tools: GopherGrades (umn.lol) · UMN class sections · course_search    │
          │         (pgvector RAG) · room booking · Tavily web search              │
          └──────────────────────────────────────────────────────────────────────┘
                          │                    │                     │
                 ┌────────▼────────┐  ┌────────▼─────────┐  ┌────────▼──────────┐
                 │ Redis           │  │ Postgres+pgvector │  │ LLM (env-selected) │
                 │ API response    │  │ course catalog    │  │ ollama · openai ·  │
                 │ cache (30d/6h)  │  │ embeddings        │  │ vllm               │
                 └─────────────────┘  └───────────────────┘  └────────────────────┘

  Persistence: conversations.json + profiles.json (JSON files; DB migration in progress)
```

### Two request paths

The `/chat` endpoint routes each message one of two ways:

1. **Deterministic cards** — common intents (grade lookup, course/professor comparison, live sections, research, "my planned courses") are detected by keyword in `webservice/routers/chat.py`, fetch their data directly, and return a **rich card** the frontend renders (`RichContent.js`). No LLM tool-selection, so they're fast and reliable regardless of model.
2. **ReAct agent** — anything open-ended goes to the LangGraph agent, which chooses and chains tools until it can answer.

### Tools & the fetch/summarize split

Every tool has two layers so the same data source serves both paths without bloating the agent's context:

- **`fetch_*(...)`** / **`fetch_*_async(...)`** return the **full** structured data — used by the deterministic cards and the `/umn/*` routes. External HTTP goes through `httpx.AsyncClient` so a slow upstream never blocks the event loop; schedule lookups for multiple courses fan out in parallel with `asyncio.gather`.
- **`@tool` wrapper** returns a **compact text summary** — what the agent reads (e.g. `gophergrades_class` full JSON ≈ 8 KB → summary ≈ 400 B).

GopherGrades and section responses are cached in **Redis** (30 days for grade data, 6 hours for live sections). The cache fails open — if Redis is down, requests still work, just uncached.

| Tool | Purpose |
|------|---------|
| `gophergrades_search` | Free-text search across courses, profs, departments (returns IDs) |
| `gophergrades_class` | One course — grade distribution, SRT, instructors |
| `gophergrades_prof` | One professor — rating, courses, grade tendency |
| `gophergrades_dept` | Department overview (highest-enrollment courses) |
| `umn_class_sections` | Live sections for a course+term (times, instructor, open/closed) |
| `course_search` | Catalog RAG — descriptions, prereqs, credits, offered terms (exact-code lookup when a code is present, semantic search otherwise; falls back to web search on weak matches) |
| `umn_room_booking` | Room/study-space lookup with directions + booking links |
| `tavily_search` | General UMN web search for anything else |

The system prompt lives in `webservice/prompts/system.md` (loaded at startup, `{today}` filled in) — edit it there, not in code.

## Model configuration

The LLM is selected at runtime via `LLM_PROVIDER` (see `autonomy/llm/factory.py`). All three providers speak the OpenAI API, so switching is an env change — no code.

| `LLM_PROVIDER` | Intended use | Key env |
|----------------|--------------|---------|
| `ollama` | Local / offline dev | `LLM_MODEL`, `LLM_BASE_URL` (default `http://localhost:11434/v1`) |
| `openai` | Cloud / benchmark | `LLM_MODEL` (default `gpt-4o-mini`), `OPENAI_KEY` |
| `vllm` | Self-hosted production (e.g. GPU on AWS) | `LLM_MODEL`, `LLM_BASE_URL` (required) |

Note: `.env` changes are read at container start, so apply them with `docker compose up -d --force-recreate backend`. Code/prompt changes need `--build` (the image uses `COPY . .`).

## Course catalog index (RAG)

`course_search` answers from a vector index of the UMN Twin Cities course catalog, stored in **Postgres with the pgvector extension** (`autonomy/rag/vector_store.py` — one `embeddings` table, cosine-distance search via `<=>`).

On startup the backend checks whether catalog chunks are present and, if not, indexes in the background without blocking requests:

1. **Live Coursedog API** (default) — `autonomy/rag/sources/coursedog_api.py` discovers the current catalog ID from the public catalog page and pages through every course (~25k records, ~15.5k with descriptions). The raw payload is cached at `autonomy/rag/data/courses_api.json` for 24h.
2. **CSV export** — `autonomy/rag/data/courses.csv` (gitignored) if the API is unreachable or `CATALOG_SOURCE=csv`.
3. **Sample CSV** — the committed `sample_courses.csv` (138 CSCI courses) as a last resort, with a loud warning.

Knobs (all optional, passed through `docker-compose.yml`):

| Env | Effect |
|-----|--------|
| `FORCE_REINDEX=1` | Re-index on this boot even if the store looks populated |
| `CATALOG_SOURCE=csv` | Skip the API and index from the CSV |
| `CATALOG_MAX_AGE_HOURS` | API cache lifetime (default 24) |

Manual re-index: `poetry run python scripts/run_indexing.py`. Inspect the store: `docker exec gophergpt-postgres psql -U gophergpt -d gophergpt -c "SELECT count(*) FROM embeddings;"`.

## Stack

- **Backend:** FastAPI, LangChain, LangGraph, provider-agnostic LLM (Ollama / OpenAI / vLLM), httpx, Tavily, Poetry
- **Data:** Postgres 16 + pgvector (course catalog embeddings), Redis 7 (external API cache), JSON files (conversations, profiles — DB migration in progress via SQLAlchemy/Alembic)
- **Frontend:** React 18, Recharts + custom SVG card components, Tailwind CSS, Lucide icons
- **Infra:** Docker Compose (backend, frontend, nginx, postgres, redis)

## Quickstart

### With Docker (recommended)

```bash
cp .env.example .env
# add OPENAI_KEY and TAVILY_API_KEY, and set LLM_PROVIDER/LLM_MODEL (see above)

docker compose up --build
```

Frontend at [http://localhost:3000](http://localhost:3000), backend at [http://localhost:8000](http://localhost:8000), nginx at `:80`/`:443`, Postgres at `:5432`, Redis at `:6379`.

First boot indexes the full course catalog in the background (a few minutes; embedding is rate-limited by OpenAI). The app serves requests immediately — `course_search` just returns nothing until indexing finishes. Watch progress with `docker compose logs -f backend`. Subsequent boots skip indexing when the store is already populated.

The research endpoint falls back to a mock response if `TAVILY_API_KEY` is missing, so you can run a partial demo without it.

### Without Docker

Backend:

```bash
poetry install
poetry run uvicorn webservice.app:app --reload
```

Frontend:

```bash
cd frontend
npm install
npm start
```

## API

All endpoints accept and return JSON. `/chat` responses include a `content` array of card objects (`grades`, `compare`, `prof_compare`, `schedule`, `research`) plus `follow_ups`.

| Method | Path | Description |
|--------|------|-------------|
| `GET`  | `/` | Health check |
| `POST` | `/chat` | Main chat. Body: `{ message, conversation_id?, user_id? }` |
| `POST` | `/research` | UMN-scoped research. Body: `{ query, max_results }` |
| `POST` | `/umn/course` | Course lookup by code or name |
| `POST` | `/umn/prof` | Professor lookup |
| `POST` | `/umn/dept` | Department breakdown (Department Explorer) |
| `POST` | `/umn/sections` | Live sections. Body: `{ subject, catalog_number, term }` |
| `GET`  | `/profile?user_id=...` | Get a user profile |
| `PUT`  | `/profile` | Update a profile (`user_id, major, level, year, personalization_notes`) |
| `GET`  | `/history` | List saved conversations |
| `POST` | `/save` | Save a conversation |
| `DELETE` | `/history/clear` | Clear all history |

Example:

```bash
curl -X POST http://localhost:8000/chat \
  -H 'Content-Type: application/json' \
  -d '{"message": "compare professor Myers and Dovolis", "user_id": "demo"}'
```

## Environment

Keys:

- `OPENAI_KEY` — required when `LLM_PROVIDER=openai` (otherwise unused)
- `TAVILY_API_KEY` — research endpoint and general web search (falls back to a mock if unset)

Model:

- `LLM_PROVIDER` — `ollama` | `openai` | `vllm` (see [Model configuration](#model-configuration))
- `LLM_MODEL`, `LLM_BASE_URL`, `LLM_TEMPERATURE`

Data services (defaults match `docker-compose.yml`; only change for non-Docker runs):

- `POSTGRES_HOST`, `POSTGRES_PORT`, `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB`
- `REDIS_HOST`, `REDIS_PORT`
- `FORCE_REINDEX`, `CATALOG_SOURCE`, `CATALOG_MAX_AGE_HOURS` — see [Course catalog index](#course-catalog-index-rag)

Frontend / optional:

- `REACT_APP_API_BASE` — backend URL the frontend calls (default `http://localhost:8000`)
- `GOPHERGRADES_API_BASE` — defaults to `https://umn.lol/api`, override for local dev

## Project layout

```
gophergpt/
├── autonomy/                    # agent, tools, RAG
│   ├── agent/                   # base_agent, react_agent, simple_agent
│   ├── llm/                     # provider factory + OpenAI-compatible wrapper
│   ├── tools/                   # gophergrades_api, umn_courses_tool,
│   │                            #   umn_rooms_tool, rag_tools (course_search)
│   └── rag/                     # indexer, chunker, embedder, retriever,
│       ├── vector_store.py      #   pgvector store (embeddings table)
│       └── sources/             #   coursedog_api (live catalog), csv_catalog
├── webservice/                  # FastAPI app
│   ├── app.py                   # app wiring, lifespan (DB init + catalog indexing), /debug
│   ├── guardrails.py            # response post-processing (tool-name leak filter)
│   ├── agent.py                 # ChatAgent (loads prompts/system.md)
│   ├── prompts/system.md        # agent system prompt
│   ├── routers/                 # chat, courses, profile, research
│   ├── personalization.py       # profile → prompt
│   ├── profile_store.py         # JSON-backed profiles
│   └── data/                    # conversations.json, profiles.json
├── frontend/                    # React app
│   ├── src/pages/               # ChatPage, DepartmentExplorer, Research,
│   │                            #   ProfileSettings, CourseCompare, ScheduleBuilder
│   ├── src/components/          # ChatWindow, Sidebar, Message, RichContent, compare/*
│   └── src/utils/               # messageFormatter, loadingLabel
├── evals/
│   └── golden_set.json          # 41-case eval set (grades, scheduling, prof, rooms,
│                                #   general, multistep, personalized, RAG, adversarial)
├── scripts/
│   ├── demo_check.sh            # pre-flight: services + every tool/card path
│   ├── eval_runner.py           # runs the golden set against /chat, deterministic checks
│   ├── judge.py                 # GPT-4o rubric judge over eval results
│   ├── run_indexing.py          # manual catalog re-index
│   └── test_research.py
├── tests/                       # pytest (integration test needs a local Ollama)
├── DEMO.md                      # demo runbook + prompt script
├── ARCHITECTURE.md
├── CHANGES.md                   # branch changelog
├── docker-compose.yml
└── pyproject.toml
```

## Demo & verification

```bash
bash scripts/demo_check.sh       # confirms services are up + every tool/card path works
python scripts/test_research.py  # research pipeline smoke test
```

### Evaluation harness

`evals/golden_set.json` holds 41 cases across 9 intents, each with the question, expected tools, expected card types, and `must_contain` / `must_not_contain` substrings.

```bash
python scripts/eval_runner.py    # runs every case against the live /chat, writes evals/results/run_<ts>.json
python scripts/judge.py          # scores a results file with a GPT-4o rubric (correctness, groundedness, completeness, style)
```

Deterministic checks (substrings, card types, tool selection) need no LLM tokens and are the intended CI gate; the judge is for qualitative regressions.

See `DEMO.md` for a guided demo script (one prompt per capability) and `CHANGES.md` for what changed on this branch.

## Contributors

Built collaboratively by UMN students. Contributors include Ahshaam, Jesse, Akihito, Maanas, Adil, Jamie, and Nick.

## License

No license file included yet. Contact the contributors before reuse.
