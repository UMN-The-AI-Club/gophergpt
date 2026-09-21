# GopherGPT — Demo Script

A 5–7 minute walkthrough that exercises **every tool** the assistant has. Each
prompt below is chosen to reliably trigger one specific capability. Type them
into the chat at http://localhost:3000.

> Persona for the story: *a UMN sophomore CS major planning next semester.*

---

## 0. Before the demo (do this ~2 min ahead)

```bash
# from the repo root
docker compose up -d           # backend :8000, frontend :3000, chromadb :8001
bash scripts/demo_check.sh     # health check + warms the 14b model
```

`demo_check.sh` must print all ✓.

**Model:** the demo runs on **OpenAI gpt-4o** (`LLM_PROVIDER=openai`,
`LLM_MODEL=gpt-4o` in `.env`). Responses are ~3–6s across the board, including
open-ended multi-step queries (e.g. "find a lib-ed that fits my schedule"),
which is why no model warm-up is needed. Earlier local models (qwen2.5 7b/14b)
were swapped out because per-step latency made agentic queries time out.
To go fully local/offline again, restore `.env.bak` (or set
`LLM_PROVIDER=ollama`, `LLM_MODEL=qwen2.5:14b-instruct-q4_K_M`) and run
`docker compose up -d --force-recreate backend` — expect much slower agent
answers.

---

## 1. The demo flow

Run these in order — it tells a coherent "planning my semester" story while
touching all 9 paths. **Bold** = what to point at on screen.

| # | Type this | Triggers | Point out |
|---|-----------|----------|-----------|
| 1 | `How hard is CSCI 1933?` | **Grades card** | Full grade-distribution chart + SRT teaching ratings, pulled live from GopherGrades. |
| 2 | `Compare CSCI 1933 and CSCI 2021` | **Compare card** | Two courses side-by-side; the AI writes a one-line recommendation above the charts. |
| 3 | `What sections of CSCI 1933 are open this fall?` | **Sections card** | **Live** section data — times, instructor, room, open/closed + seat caps, straight from courses.umn.edu. |
| 4 | `Tell me about Professor Chad Myers` | **Professor card** | Full profile card — RateMyProfessors score (linked), every course he teaches as chips, aggregated grade distribution, and teaching (SRT) ratings. The backend runs the search→prof chain itself. |
| 5 | `Compare professor Myers and professor Dovolis` | **Professor compare card** | Two professors side-by-side — RMP scores, courses, grade charts — with a one-line AI recommendation on top. |
| 6 | `Research opportunities in biology` | **Research card** | Web research snapshot — deduped sources, clickable, summarized. Powered by Tavily. |
| 7 | `How do I get to Keller Hall and can I book a room there?` | **Room booking** (agent) | Google Maps + UMN campus-map links **and** the correct booking system (25Live for Keller, LibCal for libraries). |
| 8 | `Where are good places to study on campus?` | **Study-spaces guide** (agent) | Curated, grouped list (quiet / group / late-night / tech / St. Paul) with map + reservation links — no generic web dump. |
| 9 | `What is the U Card and how do I get one?` | **General web search** (agent) | Falls back to live UMN web search for anything the structured tools don't cover. |

### Bonus flourish — follow-up chips
After **any** card, gold-bordered **follow-up chips** appear under the message.
Click one (e.g. *"Who teaches CSCI1933 with the best grades?"*) — it sends
instantly. Great for showing the assistant anticipates the next question
without you typing.

---

## 2. One-liner per tool (cheat sheet)

Memorize these — each is the shortest reliable trigger:

- **Grades** → `how hard is <COURSE>?`  (needs a grade word + a course code)
- **Compare** → `compare <COURSE A> and <COURSE B>`  (the word "compare" + a code)
- **Sections** → `what sections of <COURSE> are open this fall?`
- **Professor** → `tell me about professor <NAME>`  (the word "professor"/"prof" + a name)
- **Professor compare** → `compare professor <NAME A> and professor <NAME B>`
- **Research** → `research opportunities in <FIELD>`  (the word "research")
- **Room / directions** → `how do I get to <BUILDING> and book a room?`
- **Study spaces** → `where can I study on campus?`  (no building named)
- **General** → any UMN question the above don't cover

Course codes must look like `CSCI 1933` / `MATH1271`. Grade and schedule cards
**require a course code** in the message.

---

## 3. If something misfires live

- **A card doesn't appear** → you probably left out the course code, or the
  keyword. E.g. "is 1933 hard" won't trigger; "how hard is **CSCI 1933**" will.
- **First response is slow (~40s)** → the model went cold. Re-run
  `scripts/demo_check.sh` to re-warm, or just send one throwaway prompt first.
- **Professor card doesn't fire** → you need the word "professor"/"prof" **and**
  a name, e.g. "professor Myers". Just a course ("who teaches CSCI 1933") goes to
  the agent as text instead. The card data is deterministic (search→prof), so if
  the professor exists in GopherGrades it will always render.
- **Backend restarted?** → the model is cold again; warm it before continuing.

---

## 4. What's under the hood (talking points)

- **9 paths, two styles.** Grades / Compare / Sections / Research / Professor
  (single + compare) are *deterministic* — the backend calls the data source
  itself and renders a rich card, so they never depend on the model guessing.
  Room / Study / General are *agent-driven* — the model picks and chains tools
  via a ReAct loop.
- **Live data, not memorized.** Sections come from courses.umn.edu; grades &
  professor stats from GopherGrades (umn.lol); research & general Q&A from Tavily
  web search scoped to umn.edu + reddit.
- **UMN-branded UI** — maroon + gold design system, custom cards for every data
  type instead of walls of text.
