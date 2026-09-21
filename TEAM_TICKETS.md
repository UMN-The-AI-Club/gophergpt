
## 0. Team-wide context post (send first, pin it)

> We got outside feedback on the architecture from a senior engineer. Summary + what it
> changes for us:
>
> **The good news:** our 36-case golden set is a solid primitive, not a crutch. 27/36
> judge-pass on a LangGraph ReAct agent with live API grounding is a real result for a
> student team. We keep it.
>
> **The order matters.** We are NOT touching Terraform/ECS/cloud spend yet. Infra doesn't
> fix a broken agent loop. Triage order is:
> 1. **Stability** — Chroma race condition, RAG index that never builds
> 2. **Performance** — the 40.7s latency tail (this is the big one)
> 3. **Eval automation** — CI on every PR to `dev`
> 4. **Auth/scoping** — hard blocker before anyone outside the team touches this
>
> **Funding angle:** when we pitch the university, we lead with the *evaluation harness*,
> not the chatbot. "75% pass on a rigorous 7-intent eval matrix, we need $X to test
> concurrency" gets grants. A cool demo doesn't.
>
> Tickets in thread 👇

---

## 1. 🔴 Chroma race condition + the RAG index that never builds — @DevA

> **Two separate bugs stacked on each other. RAG has never worked in production.**
>
> Bug 1: `docker-compose.yml` has `depends_on: - chromadb` with no condition, so backend
> starts before Chroma's HTTP server is listening. The one-time auto-index in
> `webservice/app.py`'s lifespan handler dies with
> `WARNING: ChromaDB connection failed` and never retries.
>
> Bug 2 (independent): `autonomy/rag/indexer.py` → `run_indexing()` points at
> `autonomy/rag/data/courses.csv`, which **does not exist in the repo**. Only
> `sample_courses.csv` is there, and the line using it is commented out. So indexing would
> fail even with a healthy connection.
>
> Net effect: 0 collections in Chroma, `umn_docs` was never created, and every
> `course_search` call returns "No course information found." The `course_search` tool had
> **zero hits** across our entire last eval run.
>
> Done when: `docker compose up` from cold → Chroma has a populated `umn_docs` collection,
> and a `course_search` golden case passes.

**Claude prompt:**
```
Fix the ChromaDB startup race and the broken RAG indexing path in this repo.

1. In docker-compose.yml, add a healthcheck to the chromadb service that polls its
   HTTP heartbeat endpoint, and change the backend's depends_on to use
   condition: service_healthy.
2. In autonomy/rag/indexer.py, run_indexing() references
   autonomy/rag/data/courses.csv which doesn't exist. Decide with me whether to point
   it at sample_courses.csv or generate courses.csv, then make indexing actually run.
3. Make the lifespan indexer in webservice/app.py fail loudly (not a swallowed
   WARNING) and be safely re-runnable so it doesn't duplicate documents.

Then verify for real: bring the stack up cold, query the Chroma API directly, and show
me that the umn_docs collection exists and has documents in it. Don't just read the code.
```

---

## 2. 🔴 The 40.7s latency tail — sync HTTP inside async endpoints — @DevA

> **This is the highest-value fix on the board. Likely 40.7s → under 5s.**
>
> We are calling **synchronous `urlopen`** inside async FastAPI endpoints in three places:
> - `autonomy/tools/gophergrades_api.py:13`
> - `autonomy/tools/umn_courses_tool.py:13`
> - `autonomy/tools/umn_rooms_tool.py:131`
>
> Every one of those blocks the entire event loop. It's why we effectively cap at ~1
> concurrent user, and it's why the 50-concurrent load test later in the roadmap would
> fail on the spot.
>
> Second half: `_fetch_schedule_data` in `webservice/routers/chat.py:72` loops over up to
> 4 course codes and fetches them **one at a time, sequentially**. There is not a single
> `asyncio.gather` anywhere in the codebase — I grepped. That loop fully explains the
> 40.7s / 26s / 21.8s tail in our eval results.
>
> Fix: swap `urlopen` → `httpx.AsyncClient` (we already use httpx in
> `autonomy/rag/sources/base_scraper.py`, so it's a dependency we have), and fan the
> course fetches out with `asyncio.gather`.
>
> ⚠️ Watch out: these `fetch_*` helpers are called from BOTH the async chat router and
> sync LangChain `@tool` wrappers. Don't break the tool path — see the split pattern note
> in the prompt.
>
> Done when: re-run the golden set and the max latency in the results JSON is under 10s.

**Claude prompt:**
```
Convert our blocking HTTP layer to async and parallelize sequential fetches.

Context: autonomy/tools/gophergrades_api.py, umn_courses_tool.py, and umn_rooms_tool.py
all use synchronous urllib urlopen inside code paths reached from async FastAPI
endpoints. This blocks the event loop. We already depend on httpx.

Important constraint: each of these modules uses a split pattern — a raw fetch_* helper
returning full data (called by the card paths in webservice/routers/chat.py and the
/umn/* routes) and a @tool wrapper returning a compact summary for the LLM agent. The
LangChain tool wrappers are synchronous. Preserve both paths; don't break tool calling.

1. Migrate the fetch_* helpers to httpx.AsyncClient with async variants, keeping a sync
   entry point for the LangChain @tool wrappers.
2. In webservice/routers/chat.py, _fetch_schedule_data (line ~72) fetches up to 4 courses
   in a sequential for-loop. Rewrite it with asyncio.gather so they run in parallel, and
   keep the existing per-course exception isolation so one failure doesn't kill the rest.

Then run scripts/eval_runner.py against the golden set and show me before/after max and
average latency from the results JSON. Our current worst case is 40.7s.
```

---

## 3. 🟡 Redis cache for catalog + GopherGrades data — @DevA

> Follow-on to #2, do it after. Course catalog and grade distributions basically never
> change mid-semester and we re-fetch them on every single request.
>
> Add a Redis container to `docker-compose.yml`, cache catalog/GopherGrades responses on
> a 24h TTL, stale-while-revalidate so a cold key never blocks a user.
>
> This was already on our roadmap as a Phase 3 item — the outside feedback independently
> flagged it, so it's confirmed, not optional.

**Claude prompt:**
```
Add a Redis caching layer for our external API calls.

1. Add a redis service to docker-compose.yml with a healthcheck and a named volume.
2. Add a small async cache helper (get/set with TTL, JSON-serialized) in the webservice.
3. Wrap the fetch_* helpers in autonomy/tools/gophergrades_api.py and
   umn_courses_tool.py with a 24h TTL cache, keyed on the actual query params.
   Use stale-while-revalidate: serve the stale value and refresh in the background
   rather than blocking on a cold miss.
4. Cache misses must degrade gracefully — if Redis is down the app still works, just
   slower. Never let a cache failure surface as a user-facing error.

Show me a measured cache hit vs miss latency difference for the same query.
```

---

## 4. 🟡 Eval: stop paying the LLM to check things code can check — @DevB

> The feedback here was sharper than I expected, and **we're already half-done**, which is
> good news.
>
> `scripts/eval_runner.py:187-207` already does deterministic checks for `must_contain`,
> `must_not_contain`, and `content_types`, and computes `passed` from them. That part is
> correct — keep it.
>
> The gap: `expected_tools` and `tools_used` are collected in the result JSON and then
> handed to the **GPT-4o judge** to evaluate as a `tool_use` score. That's the mistake.
> "Did `gophergrades_class` fire for a grades question?" is a **set comparison**. We're
> paying tokens and eating LLM variance for something that's a 10-line assert.
>
> 31 of our 36 cases already have `expected_tools` populated, so the data is right there.
>
> Split it: code asserts tool selection, judge handles only tone/completeness/nuance.
>
> ⚠️ Also fix while you're in there: `tools_used.extend` at `chat.py:539` is inside an
> `except` block, so **successful** tool traces never get recorded. Our tool-use data is
> partly fiction right now — fix this first or the assertions will be measuring nothing.

**Claude prompt:**
```
Split our eval harness into deterministic assertions vs LLM judgments.

Current state: scripts/eval_runner.py already does deterministic must_contain /
must_not_contain / content_type checks and computes a `passed` flag. Good, keep that.
But expected_tools vs tools_used is only evaluated by the GPT-4o judge in
scripts/judge.py as a "tool_use" score. That should be a code assertion.

1. First fix a data bug: in webservice/routers/chat.py around line 539, a
   tools_used.extend(...) call sits inside an except block, so successful tool traces
   are never recorded. Verify this, then fix it so tools_used is accurate on the
   success path. Everything else depends on this being right.
2. In eval_runner.py, add a deterministic tool_check comparing expected_tools against
   tools_used (report exact match, missing, and unexpected tools separately) and fold
   it into the `passed` computation.
3. In judge.py, drop the tool_use dimension from the rubric and keep the judge focused
   on correctness, groundedness, completeness, and style — the things that genuinely
   need judgment.
4. Update the summary output to report deterministic pass rate and judge pass rate as
   two separate numbers.

Then run the full golden set and show me both numbers. Our last judged run
(run_20260813_212129) was 27/36 judge-pass.
```

---

## 5. 🟡 Grow the golden set to 100-150 cases — @DevB + anyone with 30 min

> 36 cases cannot cover a campus of 50,000 students. Current spread:
> grades 6 · scheduling 6 · prof 5 · rooms 5 · general 5 · multistep 5 · personalized 4.
>
> Target 100-150. Two things we're specifically missing:
> - **`course_search` / RAG coverage** — the tool is registered in `webservice/agent.py`
>   but got **zero hits** in the last run. It's wired and completely unvalidated.
> - **Adversarial cases.** e.g. *"What grade did I get in CSCI 1133?"* — we have no auth,
>   so the correct behavior is to say it can't access personal grades. Right now nobody
>   knows what it does. Also: prompt injection, nonexistent course codes, out-of-scope
>   questions, questions about professors who don't exist.
>
> **This is the highest-leverage thing a non-backend person can do.** Writing good
> adversarial cases needs product judgment, not Python. Anyone can grab a batch.

**Claude prompt:**
```
Expand evals/golden_set.json from 36 to ~120 cases.

Read the existing file first and match its schema exactly (id, intent, question,
user_id, expected_tools, expected_content_types, must_contain, must_not_contain, notes).
Current intent distribution: grades 6, scheduling 6, prof 5, rooms 5, general 5,
multistep 5, personalized 4.

Priorities:
1. course_search / RAG cases — this tool is registered in webservice/agent.py but had
   zero hits in our last eval run. It is wired and unvalidated. Read the indexer to see
   what's actually searchable before writing these.
2. An adversarial set. We have NO authentication, so anything asking for a specific
   student's personal record must be refused gracefully. Include: personal-data requests,
   nonexistent course codes, professors who don't exist, prompt injection attempts,
   and out-of-scope questions.
3. Even out the thin intents.

For each case, set must_contain to substrings a correct answer genuinely must have —
not phrasing we hope for. Fragile string matching makes the harness useless. Show me
the new cases for review before writing the file.
```

---

## 6. 🔴 CI — we have zero, and it's our biggest bottleneck — @DevB

> There is **no `.github/` directory in this repo at all.** No CI, nothing runs on a PR.
> The outside read was that this is our single biggest process bottleneck, and I agree.
>
> Every eval run right now is someone remembering to run it by hand. We have 32 result
> files in `evals/results/` and the last *judged* run is from Aug 13 — the smoke runs
> after that were never judged. That's exactly the failure mode.
>
> We do **not** need cloud infra for this. GitHub Actions free tier + a self-hosted runner
> on one of our machines is enough.
>
> Do it in two stages so it lands fast:
> - **Stage 1 (this week):** lint + unit tests on every PR to `dev`. No LLM calls, no API
>   keys, runs in under 2 min.
> - **Stage 2:** the deterministic slice of the eval harness (needs #4 done first, since
>   the deterministic checks are the part that can run without judge tokens).
>
> Done when: a PR to `dev` shows a green check without anyone running anything locally.

**Claude prompt:**
```
Set up GitHub Actions CI for this repo. There is currently no .github/ directory.

Stage 1 — a workflow that runs on every pull request to dev:
- Python lint and any existing tests under tests/
- Frontend build check for frontend/
- Must run without API keys or network access to external services, and finish fast.

Stage 2 — a separate workflow, manual dispatch for now:
- Runs scripts/eval_runner.py against the golden set
- Fails the build if the deterministic pass rate drops below a threshold I set
- Uploads the results JSON as a build artifact
- Do NOT run the GPT-4o judge in CI; that costs tokens per run. Deterministic only.

Read pyproject.toml and the dockerfiles first so the CI environment matches how we
actually build. Point out anything that will fail in CI but passes locally.
```

---

## 7. 🟠 DISCUSSION — the keyword router (needs a call, not a ticket)

> The feedback said: *"Kill the keyword router. If your deterministic keyword layer is
> shadowing your LLM routing, it defeats the purpose of using LangGraph."*
>
> **Directionally right, but I don't think we take it literally**, and here's why —
> whoever picks this up needs to know this before touching it.
>
> Our keyword layer (`SCHEDULING_KEYWORDS` / `GRADE_KEYWORDS`, `chat.py:30-48`, routing at
> `607` and `632`) isn't only a speed shortcut. It selects which **rich card** the frontend
> renders via `RichContent.js` — grades, compare, schedule, research, prof_compare. Rip out
> the keyword layer wholesale and we lose the cards, which are a big part of why the demo
> lands.
>
> The real problem is subtler: since we moved to gpt-4o the agent is fast enough that the
> card paths are **visual niceties, not speed crutches** — but they still intercept
> requests before the LLM ever gets to reason about them. A question like "how hard is
> CSCI 1933 compared to 2011" hits the keyword path and gets canned text.
>
> That matches our own eval data: **7 of 9 judge failures were "right card, canned text
> that doesn't answer the specific question."** It's a synthesis problem, not a retrieval
> problem. The router picks correctly and then we don't actually answer.
>
> So the question isn't "keywords or LLM." It's: **how do we keep card rendering while
> letting the LLM own the answer text?** My proposal — the agent decides the content type
> and returns a structured card payload as a tool result, instead of keywords deciding
> upstream. That keeps the cards and removes the shadowing.
>
> Bigger than a ticket. Let's talk on the next call before anyone starts.

---

## 8. 🔴 BLOCKER — no auth, and `/history` leaks across all users

> Not urgent for the demo, absolute blocker before anyone outside the team touches this.
>
> `/history`, `/save`, and `/history/clear` have **no user scoping whatsoever**. Every
> user shares one `conversations.json`, with no locking. Any user can read any other
> user's conversation history. If we hand this to real students as-is, that's a privacy
> incident, not a bug.
>
> Also on the list: `allow_origins=["*"]` with credentials enabled, and `/debug/prof`
> ships raw API dumps to anyone who asks.
>
> Sequencing: mock auth for dev now, real UMN OAuth2 before launch. Nobody outside the
> team gets a link until scoping is real.

**Claude prompt:**
```
Add user scoping and basic auth structure to the webservice.

Current problem: /history, /save, and /history/clear in the webservice have no user
scoping — all users share a single conversations.json with no locking, so any user can
read anyone else's conversations.

1. Scope conversation storage per user_id, with locking on concurrent writes. Note that
   Alembic and SQLAlchemy groundwork already exists in this repo — check whether moving
   off the JSON file to the DB is the cleaner fix here, and recommend one.
2. Add a mock auth dependency for dev that injects a user identity, structured so a real
   OAuth2 provider can replace it without touching the route handlers.
3. Lock down CORS — allow_origins is currently ["*"] with credentials enabled, which
   browsers reject anyway and is wrong regardless.
4. Put the /debug/prof endpoint behind a debug flag; it currently returns raw API dumps.

Do not implement real UMN OAuth yet. Structure for it, mock it for now, and tell me
what the real integration would need.
```
