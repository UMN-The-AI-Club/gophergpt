# GopherGPT

An AI assistant for University of Minnesota students. Ask it about courses, professors, grade distributions, class sections, study spaces, or what's on campus, and it pulls real data from GopherGrades, UMN's live course catalog, UMN's room booking system, and the broader web before answering.

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
          │  Tools: GopherGrades (umn.lol) · UMN class sections · room booking ·   │
          │         Tavily web search                                             │
          └──────────────────────────────────────────────────────────────────────┘
                                               │
                                  ┌────────────▼─────────────┐
                                  │  LLM (pluggable via env)  │
                                  │  ollama · openai · vllm   │
                                  └───────────────────────────┘

  Persistence: conversations.json + profiles.json   |   RAG: ChromaDB index (autonomy/rag)
```

### Two request paths

The `/chat` endpoint routes each message one of two ways:

1. **Deterministic cards** — common intents (grade lookup, course/professor comparison, live sections, research, "my planned courses") are detected by keyword in `webservice/routers/chat.py`, fetch their data directly, and return a **rich card** the frontend renders (`RichContent.js`). No LLM tool-selection, so they're fast and reliable regardless of model.
2. **ReAct agent** — anything open-ended goes to the LangGraph agent, which chooses and chains tools until it can answer.

### Tools & the fetch/summarize split

Every tool has two layers so the same data source serves both paths without bloating the agent's context:

- **`fetch_*(...)`** returns the **full** structured data — used by the deterministic cards and the `/umn/*` routes.
- **`@tool` wrapper** returns a **compact text summary** — what the agent reads (e.g. `gophergrades_class` full JSON ≈ 8 KB → summary ≈ 400 B).

| Tool | Purpose |
|------|---------|
| `gophergrades_search` | Free-text search across courses, profs, departments (returns IDs) |
| `gophergrades_class` | One course — grade distribution, SRT, instructors |
| `gophergrades_prof` | One professor — rating, courses, grade tendency |
| `gophergrades_dept` | Department overview (highest-enrollment courses) |
| `umn_class_sections` | Live sections for a course+term (times, instructor, open/closed) |
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

## Stack

- **Backend:** FastAPI, LangChain, LangGraph, provider-agnostic LLM (Ollama / OpenAI / vLLM), Tavily, ChromaDB (RAG index), Poetry
- **Frontend:** React 18, Recharts + custom SVG card components, Tailwind CSS, Lucide icons
- **Infra:** Docker Compose (backend, frontend, chromadb), JSON file persistence

## Quickstart

### With Docker (recommended)

```bash
cp .env.example .env
# add OPENAI_KEY and TAVILY_API_KEY, and set LLM_PROVIDER/LLM_MODEL (see above)

docker compose up --build
```

Frontend at [http://localhost:3000](http://localhost:3000), backend at [http://localhost:8000](http://localhost:8000), ChromaDB at `:8001`.

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
│   │                            #   umn_rooms_tool, web_search_tool
│   └── rag/                     # ChromaDB indexer, chunker, embedder, retriever
├── webservice/                  # FastAPI app
│   ├── app.py                   # app wiring, lifespan, /debug
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
├── scripts/
│   ├── demo_check.sh            # pre-flight: services + every tool/card path
│   └── test_research.py
├── DEMO.md                      # demo runbook + prompt script
├── CHANGES.md                   # branch changelog
├── docker-compose.yml
└── pyproject.toml
```

## Demo & verification

```bash
bash scripts/demo_check.sh       # confirms services are up + every tool/card path works
python scripts/test_research.py  # research pipeline smoke test
```

See `DEMO.md` for a guided demo script (one prompt per capability) and `CHANGES.md` for what changed on this branch.

## Contributors

Built collaboratively. Branch contributors include Ahshaam, Adil, Jamie, Nick, Akihito, and Jesse.

## License

No license file included yet. Contact the contributors before reuse.
