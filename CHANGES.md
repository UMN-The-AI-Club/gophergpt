# Changes — `frontend-changes` branch

Demo-hardening pass on GopherGPT: made every tool/agent path fire reliably and
fast, fixed several crashes and data-flow bugs, and cut tool-call latency.
Grouped by theme below; file list and run/revert notes at the bottom.

_Last updated: 2026-07-01_

---

## 1. Agent model

Moved the agent off the local model to **OpenAI gpt-4o** for the demo.

- **Why:** local `qwen2.5:7b` failed multi-step tool chains (e.g. professor
  lookup), leaked internal tool names, and dropped required links. `14b` fixed
  correctness but per-step latency (~7.5s/tool round, compounding as context
  grows) made open-ended agentic queries (e.g. "find a lib-ed that fits my
  schedule") take 120–400s and time out. gpt-4o does the same query in ~6s.
- **Where:** `.env` (`LLM_PROVIDER=openai`, `LLM_MODEL=gpt-4o`). Provider
  changes are read at container start, so they need
  `docker compose up -d --force-recreate backend` (no rebuild).
- **Revert to local:** `.env.bak` is a gitignored snapshot of the original
  config (`qwen2.5:7b`, plus the API keys) taken at the start of the session.
  For the better local experience, set `LLM_PROVIDER=ollama` +
  `LLM_MODEL=qwen2.5:14b-instruct-q4_K_M`, then force-recreate the backend.

---

## 2. Professor cards (`prof_compare`)

The frontend already had a polished `prof_compare` card, but **no backend path
ever produced it** — professor questions fell through to the agent as plain
text. Added a deterministic path.

- Detects a professor name after "professor / prof / instructor / dr", runs the
  `gophergrades_search → gophergrades_prof` chain itself, and returns a
  `prof_compare` card for **1 or 2** professors, with an AI one-line takeaway.
- Handles many phrasings: `professor Myers and Dovolis`, `professors Myers and
  Dovolis`, `professor Chad Myers vs Dan Dovolis`.
- **Surname fallback:** a wrong/missing first name ("Dan Dovolis") retries on the
  last name alone ("Dovolis").
- **Where:** `webservice/routers/chat.py` (`_extract_prof_names`,
  `_fetch_prof_data`, routing block).

---

## 3. Profile personalization fixes

The agent kept saying "I don't have access to your profile." Two bugs:

1. **Frontend never sent `user_id`** with chat messages, so the backend never
   loaded the profile. → `frontend/src/App.js` now includes
   `user_id` in the `/chat` body.
2. **Academic Level was silently dropped on save** — the UI collected it but
   `ProfileRequest` had no `level` field, so pydantic discarded it. →
   `webservice/routers/profile.py` adds `level` and passes it through.

---

## 4. Black-screen crash fix

Asking e.g. "who teaches CSCI 4061" turned the whole screen black.

- **Cause:** the typewriter animation re-formats the *partial* message on every
  keystroke. A bullet mid-type like `- **Abhishek Chandra` (bold opened, not yet
  closed) hit an unguarded regex match (`bl[1]` on `null`), throwing during
  render and unmounting the whole React tree.
- **Fix:** `frontend/src/utils/messageFormatter.js` — guard the null match, plus
  a `try/catch` around the whole formatter that degrades to plain text so a
  formatting bug can never blank the app again.

---

## 5. "My courses" fast path + course-code suffix fix

"Tell me about the courses I plan to take" timed out (agent spiraled over 3
courses). Now handled deterministically.

- `webservice/routers/chat.py` (`_is_my_courses_query`) pulls the course codes
  from the profile notes and returns a live **sections card** (~0.6s, covers all
  courses since sections exist even when historical grades don't).
- **Course-code W/H suffix fix:** `extract_course_codes` was dropping the
  trailing letter (`CSCI 4511W` → `CSCI4511`, which has no data). It now keeps
  it, which also fixes direct queries like "how hard is CSCI 4511W" everywhere.
  `_fetch_schedule_data`'s subject/number split does too.

---

## 6. System prompt moved to a file

Extracted the ~2,000-token system prompt out of Python.

- **New:** `webservice/prompts/system.md` — the full prompt, with a `{today}`
  placeholder.
- `webservice/agent.py` `load_system_prompt()` reads it at startup and
  `.replace()`s the date. Also added an explicit **PROFESSOR LOOKUP** procedure
  to the prompt.
- **Edit the prompt there, not in `agent.py`.**

---

## 7. Tool-output trimming (biggest latency win)

Tools returned raw API JSON that stayed in context and was re-read on every
agent step. Split each tool into two layers:

- **`fetch_*(...)` → full data** — used by the visual cards, the `/umn/*`
  routes, the debug route, and the RAG indexer.
- **`@tool` wrapper → compact text summary** — what the agent reads.

Measured char reductions (÷4 ≈ tokens):

| Tool | Before | After |
|---|---|---|
| `gophergrades_class` | 8,218 | 395 |
| `gophergrades_prof` | 8,401 | 121 |
| `gophergrades_dept` | 110,092 | 768 |
| `umn_class_sections` | 3,096 | 866 |
| `gophergrades_search` | 238 | 84 |

- **Where:** `autonomy/tools/gophergrades_api.py` (`fetch_search/class/prof/dept`
  + `_summarize_*`), `autonomy/tools/umn_courses_tool.py` (`fetch_sections` +
  summary), `autonomy/tools/umn_rooms_tool.py` (agent-only → compact text),
  **new** `autonomy/tools/web_search_tool.py` (wraps Tavily, replaces the raw
  `TavilySearch`). Internal call sites repointed to `fetch_*` in
  `chat.py`, `courses.py`, `app.py`, `rag/indexer.py`.
- **Rule of thumb:** edit `_summarize_*` for what the *agent* sees; edit
  `fetch_*` for what the *cards* see — they're independent now.

---

## 8. Misc

- **Request timeout** raised 90s → 180s in `frontend/src/App.js` as a safety net
  for heavy agent queries.

---

## Demo materials (new)

- **`DEMO.md`** — 9-step demo script (one prompt per tool/card), trigger cheat
  sheet, and live-troubleshooting notes.
- **`scripts/demo_check.sh`** — pre-flight: confirms services are up, prints the
  agent model, and verifies every tool/card path returns the right thing.

---

## Files changed

**Backend**
- `webservice/agent.py` — load prompt from file; register wrapped `tavily_search`
- `webservice/prompts/system.md` *(new)* — the system prompt
- `webservice/routers/chat.py` — prof cards, "my courses" path, code-suffix fix, `fetch_*` wiring
- `webservice/routers/profile.py` — add `level` field
- `webservice/routers/courses.py` — `fetch_*` wiring
- `webservice/app.py` — `fetch_*` wiring
- `autonomy/tools/gophergrades_api.py` — split fetch/summarize
- `autonomy/tools/umn_courses_tool.py` — split fetch/summarize
- `autonomy/tools/umn_rooms_tool.py` — compact text output
- `autonomy/tools/web_search_tool.py` *(new)* — Tavily wrapper
- `autonomy/rag/indexer.py` — use `fetch_dept`

**Frontend**
- `frontend/src/App.js` — send `user_id`; 180s timeout
- `frontend/src/utils/messageFormatter.js` — crash guard + safety net

**Ops / docs**
- `.env` — model switch (`.env.bak` = gitignored backup of the original 7b config)
- `.gitignore` — ignore `.env.bak` / `*.bak` so the key-bearing backup isn't committed
- `DEMO.md`, `scripts/demo_check.sh` *(new)*

---

## Running it

```bash
docker compose up -d --build      # backend :8000, frontend :3000, chromadb :8001
bash scripts/demo_check.sh        # verify everything, then open http://localhost:3000
```

Backend code is baked into the image (`COPY . .`), so code/prompt changes need
`--build`; `.env` changes need `--force-recreate backend`.
