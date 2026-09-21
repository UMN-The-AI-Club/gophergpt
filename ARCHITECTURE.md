# GopherGPT — Architecture (for review)

> Written for an experienced engineer joining as an advisor. Assumes you know
> LLM agents, FastAPI, and React. The goal is to give you enough to critique the
> design and tell us where we're wrong. Candid about tradeoffs and tech debt —
> the "where we want your input" section at the end is the point.

---

## 1. What it is

An AI assistant for UMN students: courses, professors, grade distributions, live
class sections, study spaces, and general campus questions. It answers by calling
real data sources (GopherGrades, UMN's course catalog, room booking, web search)
rather than from model memory.

- **Backend:** FastAPI, Python 3.11. Agent orchestration via LangGraph.
- **LLM:** pluggable (local Ollama / OpenAI / self-hosted vLLM) behind one factory.
- **Frontend:** React 18. Answers render as rich data cards, not just text.
- **Infra:** Docker Compose (backend, frontend, ChromaDB). Persistence is JSON files.

Deployment today is local/demo. There is no auth, no multi-tenant story, and
persistence is flat files — see §8.

---

## 2. The one design decision to understand first

**We run a hybrid: deterministic "card" paths *and* a ReAct agent.** Every chat
message hits `/chat` (`webservice/routers/chat.py`) which decides:

1. **Deterministic paths** — common intents (grade lookup, course compare,
   professor lookup/compare, live sections, research, "my planned courses") are
   detected by keyword/regex, fetch their data directly, and return a structured
   **card** the frontend renders. No LLM tool-selection involved.
2. **ReAct agent fallback** — anything else goes to the LangGraph agent, which
   picks and chains tools until it can answer in prose.

**Why we did this:** the deterministic paths are fast (~0.5s), reliable, and
produce rich visual cards (charts, side-by-side comparisons). They don't depend
on the model choosing the right tool. The agent handles the long tail.

**The tension (want your take):** this is essentially hand-written routing in
front of an agent. It's brittle (keyword heuristics can misroute) and it means
"adding a feature" often means adding a branch in `chat.py` rather than a tool.
With a strong enough model, we could arguably delete most of it and let the agent
do everything — at the cost of latency and visual cards. Is the hybrid a
pragmatic win or a smell? See §9.

---

## 3. Request lifecycle

```
frontend  ──POST /chat {message, conversation_id?, user_id?}──▶  chat.py
                                                                   │
   load profile (if user_id) + history (if conversation_id)        │
                                                                   ▼
   ┌── keyword/regex intent match? ──┐
   │                                 │
   yes → deterministic path          no → ReAct agent
   fetch_* (full data) → card        (system prompt + history + message)
   return {response, content[], follow_ups}   → tools loop → prose
                                     return {response, content:[], follow_ups}
```

- `content[]` is an array of card objects (`grades`, `compare`, `prof_compare`,
  `schedule`, `research`) the frontend maps to components (`RichContent.js`).
- `follow_ups` are suggested next questions rendered as chips.
- Profile context (major/level/year/notes) is injected into the agent prompt only
  on the fallback path.

---

## 4. The agent

- **Framework:** LangGraph `StateGraph`, a textbook ReAct loop
  (`autonomy/agent/react_agent.py`): `chat_node` (LLM) ↔ `tool_node`, conditional
  edge on whether the last message has tool calls. `recursion_limit=15`
  (`base_agent.py`) — no graceful degradation when hit.
- **Tools** (`autonomy/tools/`): `gophergrades_search/class/prof/dept`,
  `umn_class_sections`, `umn_room_booking`, `tavily_search`.
- **System prompt:** `webservice/prompts/system.md` (~2,000 tokens), loaded at
  startup with a `{today}` substitution. It carries tool-routing guidance,
  procedures for scheduling and professor lookup, a canned study-spaces list, and
  style rules.
- **Single global agent instance** created at app startup
  (`dependencies.gopher_assistant`). It's stateless per call (history is passed
  in), so concurrent requests share the compiled graph but not conversation state.

### The fetch / summarize split (important)

Every data tool has two layers:

- **`fetch_*(...)`** → **full** structured data. Used by the deterministic cards
  and the `/umn/*` routes.
- **`@tool` wrapper** → **compact text summary**. What the agent reads.

This exists because tool outputs are huge and, in a ReAct loop, every tool result
stays in context and is re-read on every subsequent step. Measured reductions:

| Tool | Raw | Summary |
|------|-----|---------|
| `gophergrades_class` | 8,218 B | 395 B |
| `gophergrades_prof` | 8,401 B | 121 B |
| `gophergrades_dept` | 110,092 B | 768 B |
| `umn_class_sections` | 3,096 B | 866 B |

So when editing a tool: change the summarizer for what the *agent* sees, change
`fetch_*` for what the *cards* see. They're intentionally decoupled.

---

## 5. LLM backend & deployment tiers

`autonomy/llm/factory.py` selects the model from `LLM_PROVIDER`. All three speak
the OpenAI API, so the wrapper (`OpenAILLM`, a thin `ChatOpenAI`) is shared and
switching is env-only.

| Provider | Intended role | Notes |
|----------|---------------|-------|
| `ollama` | local / dev | qwen2.5 7b/14b; free, private, **slow** |
| `openai` | benchmark / current demo | `gpt-4o` now; `gpt-4o-mini` default |
| `vllm` | production (self-host, e.g. AWS GPU) | not yet stood up |

**What we learned the hard way:** on local `qwen2.5:14b`, a single tool round is
~7.5s warm and *grows* as context accumulates. Open-ended multi-step queries
(e.g. "find a lib-ed that fits my schedule" → sections for 3 courses + reasoning +
candidate lookups) hit 120–400s and timed out. The 7b was worse — it also leaked
internal tool names and hallucinated tool args. We moved the demo to `gpt-4o`
(~6s for the same query). The tool-output trimming in §4 was the other lever.

**The intended end state** is side-by-side: local for dev, self-hosted vLLM
(open model, ~70B) on AWS for production economics, and a cloud API
(GPT / cheaper OpenAI-compatible providers like Groq, DeepSeek, Together) as
fallback/burst — with a router picking per query. Not built yet. This is a big
area we want advice on (§9).

---

## 6. Data sources & persistence

- **GopherGrades** (`umn.lol/api`) — grades, SRT, professor/dept data. Public JSON.
- **UMN course catalog** (`courses.umn.edu`) — live section data. We resolve the
  strm term code ourselves.
- **Room booking** — LibCal scrape (libraries) + 25Live links (other buildings).
- **Tavily** — domain-restricted web search (`umn.edu`, `reddit.com`).
- **RAG:** there's a full ChromaDB pipeline (`autonomy/rag/`: indexer, chunker,
  embedder, retriever) and a `rag_tools.py` — **but the retriever is not
  registered as an agent tool.** It's built and unused. Wiring it in is our
  leading idea for grounding/hallucination reduction.
- **Persistence:** `webservice/data/{conversations.json, profiles.json}`,
  read-modify-write on every save. No locking, no DB. Fine for a demo, not for
  concurrency (see §8).

---

## 7. Frontend (brief)

- React 18, single-page. `App.js` holds chat state, calls `/chat`, and runs a
  **typewriter** animation over the response.
- `RichContent.js` dispatches `content[]` items to card components (grade charts,
  compare panels, sections, prof compare, research results).
- Profile is stored under a `localStorage` `user_id`, sent with each `/chat` call
  and used to personalize.
- Recharts is a dependency; grade charts are custom SVG.

---

## 8. Known weaknesses / tech debt (a reviewer will spot these)

- **JSON-file persistence, no locking.** `/save` does read-modify-write on
  `conversations.json`. Concurrent writes will corrupt/clobber. Needs a real DB
  (SQLite at minimum, Postgres for prod).
- **No auth / identity.** `user_id` is a client-generated `localStorage` string.
  Anyone can read/write any profile by guessing an id.
- **`CORS allow_origins=["*"]`** and secrets in `.env`.
- **No streaming.** Backend returns the full answer, then the frontend types it
  out — perceived latency is worse than actual.
- **No observability.** No tracing, token/cost logging, or per-tool latency
  metrics. We're tuning by stopwatch and eyeballing.
- **No eval harness.** Every change (prompt, model, tool trim) has been validated
  by vibes. This is the biggest gap — see §9.
- **Routing is heuristic.** Intent detection in `chat.py` is keyword/regex; it can
  misfire (e.g. a course question phrased unusually falls through to the agent).
- **Agent robustness.** `recursion_limit=15` with no graceful landing; tool calls
  are sequential; no retry-with-correction on bad tool args.
- **Single global agent instance** shared across requests (stateless per call, so
  probably fine, but unverified under load).

---

## 9. Where we most want your advice

1. **Hybrid vs. full-agent.** Is the deterministic-cards-in-front-of-an-agent
   pattern the right long-term shape, or a crutch for weak/slow models that we
   should shed once on a strong model? How do teams usually draw that line?
2. **Evaluation & judges.** We want to stop tuning by vibes. Plan is: a golden
   set + a runner + deterministic guardrails + an LLM-as-judge (offline) scoring
   correctness/groundedness/tool-use. Is that the right first build? Where do
   online reflection judges actually earn their latency? How big/curated should
   the golden set be to be trustworthy?
3. **Model strategy / cost.** Self-host vLLM on AWS (which instance, which open
   model) vs. staying on OpenAI vs. cheaper OpenAI-compatible providers. How would
   you structure a router (per-intent? per-complexity? confidence-based?) and a
   fallback chain without over-engineering?
4. **Grounding.** We have an unused ChromaDB retriever. Is RAG-as-a-tool the right
   move for factual grounding here, or is tool-output + citations enough given the
   data is already structured?
5. **Reliability under real use.** Streaming, concurrency, persistence, retries,
   observability — if you had to pick the two that matter most before a real user
   launch, which and why?
6. **Adding tools safely.** Our stated rule is "no new tools until the agent
   performs well and evals gate them." Reasonable, or too conservative?

---

## 10. Roadmap (our current thinking)

1. **Measurement** — eval harness + judge + guardrails. Unblocks everything.
2. **Agent quality** — wire RAG grounding, trim/few-shot the prompt, prompt the
   agent for *insight* not data dumps; iterate against evals.
3. **Deployment** — stand up vLLM on AWS; add model routing + fallback; add
   cost/latency telemetry; benchmark every provider with the harness.
4. **Then** — new tools, each shipped with eval cases.

---

## Map of the code

| Concern | Where |
|---------|-------|
| Chat routing (hybrid decision) | `webservice/routers/chat.py` |
| Agent loop | `autonomy/agent/react_agent.py`, `base_agent.py` |
| Tools (split fetch/summarize) | `autonomy/tools/*` |
| LLM provider selection | `autonomy/llm/factory.py`, `openai_llm.py` |
| System prompt | `webservice/prompts/system.md` |
| Cards / other routes | `webservice/routers/{courses,profile,research}.py` |
| Personalization | `webservice/personalization.py`, `profile_store.py` |
| RAG (built, mostly unused) | `autonomy/rag/*` |
| Frontend rendering | `frontend/src/components/RichContent.js`, `App.js` |

See `README.md` for run instructions and `CHANGES.md` for recent branch history.
