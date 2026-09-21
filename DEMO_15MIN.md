# GopherGPT — 15-Minute Stakeholder Demo

For a short meeting with someone from the University. This is a **pitch with a
live demo inside it**, not a feature tour. The story: *students already ask these
questions — we answer them from real UMN data, and we can prove it works.*

Time budget: **2 min setup · 8 min live demo · 3 min how-it-works · 2 min the ask.**
If you're running long, cut from section 3, never from section 2.

---

## Before they arrive (5 min ahead, terminal in the repo)

```bash
docker compose up -d
bash scripts/demo_check.sh
```

All 11 lines must be green ✓. Then open **http://localhost:3000**, start a
**New Chat**, and leave it on screen. Close everything else — the terminal too.

Type each demo prompt once *before* the meeting. First-of-the-day section
lookups take ~2s (6h cache); everything else is instant after one warm-up.

---

## 1. Open (2 min) — say this, don't show yet

> "GopherGPT is an assistant for UMN students built by UMN students. The
> difference from asking ChatGPT is that it doesn't guess — every answer is
> pulled live from UMN sources: GopherGrades, the live class schedule, the
> full course catalog, room booking. And we measure whether it's right.
> Let me show you what a sophomore planning next semester actually does with it."

---

## 2. Live demo (8 min) — six prompts, one story

Type these in order. **Bold** = what to point at. Keep moving; don't wait for
them to read every card.

| # | Type this | Say while it renders |
|---|-----------|----------------------|
| 1 | `How hard is CSCI 1933?` | "This is the **real grade distribution** — every section, every semester, from GopherGrades. Not a paragraph. A student sees the A-rate and average GPA in two seconds." |
| 2 | `What are the prerequisites for CSCI 3081W?` | "Now the **course catalog**. We indexed every UMN Twin Cities course — 25,000 of them — from the University's own catalog system, and it answers from that, not from memory. That's why it gets the prereqs exactly right." |
| 3 | `What sections of CSCI 1933 are open this fall?` | "**Live section data** — times, instructor, room, open or closed, seat caps. Straight from the schedule system, right now." |
| 4 | `Tell me about Professor Chad Myers` | "**Professor profile** — RateMyProfessors score, every course they teach, their aggregated grade tendency. Students triangulate this across three sites today; here it's one card." |
| 5 | `Compare professor Myers and professor Dovolis` | "Side by side, with a one-line recommendation. This is the question every student actually asks — 'which section should I take?' — and nothing on campus answers it." |
| 6 | Click a **gold follow-up chip** under the last card | "It anticipates the next question. Zero typing." |

**Stop there.** Six prompts is enough. If they ask "can it do X" — try it live
only if X is on the safe list below; otherwise say "that's on the roadmap" and
move on.

**Safe to improvise:** any `how hard is <COURSE>`, `compare <A> and <B>`,
`prerequisites for <COURSE>` (any subject now, not just CSCI), `what sections
of <COURSE> are open this fall`, `where can I study on campus`, `how do I get
to <BUILDING>`.

**Do not attempt live:** comparing 3+ professors (slow path), anything about
"my grades" / personal records (no auth yet), history from two browsers,
scheduling across 4+ courses at once.

---

## 3. How it works (3 min) — one breath each

> **"It's an agent, not a chatbot."** A LangGraph ReAct agent on GPT-4o picks
> and chains tools — GopherGrades, the live schedule API, our catalog index,
> room booking, web search. The common questions skip the model entirely and
> hit deterministic card paths, so they're fast and can't hallucinate.

> **"The catalog is a real vector index."** Every course description is
> embedded into Postgres with pgvector. It rebuilds itself from the live
> Coursedog API on startup, so it's never stale and needs no hand-maintained
> data files.

> **"We measure it."** We have a 41-case evaluation set across 8 question
> types — grades, scheduling, professors, rooms, catalog, multi-step,
> personalized, and adversarial. Every case has expected tools and expected
> facts. Our last judged run was 27 of 36 passing a GPT-4o rubric — 75% — and
> the failures are categorized, not mysterious: 7 of 9 were "right data,
> generic wording," which is a prompt fix, not an architecture problem.

That last point is the one to land. A working demo is table stakes; **a team
that can tell you exactly where it fails and why** is what's rare.

---

## 4. The ask (2 min)

Pick the one that matches who you're talking to:

- **If they can grant access/data:** "The catalog and grades data we use are
  public scrapes. With official read access to the class schedule and catalog
  APIs, we remove our biggest fragility overnight."
- **If they can grant money/compute:** "We're running on one laptop and a
  personal OpenAI key. To test with real students we need to run a
  concurrency test — 50 simultaneous users — which means hosting and an API
  budget. We have the eval harness to prove it holds up before anyone's grade
  planning depends on it."
- **If they can grant reach:** "We want 30 CS students using it for spring
  registration, with the eval harness measuring every failure. Can you help
  us find them?"

Then stop talking and let them respond.

---

## If something breaks live

- **"Sorry, I encountered an error"** → say "let me retry that" and resend.
  If it repeats, switch to a prompt from the safe list — all six demo prompts
  are cached and will work.
- **A card doesn't render, just text** → you dropped the course code or the
  trigger word. `how hard is CSCI 1933` works; `is 1933 hard` doesn't.
- **Everything is dead** → in the terminal: `docker compose restart backend`,
  ~10 seconds. The catalog index survives restarts. Cover with section 3
  talking points while it comes back.
- **Wi-Fi drops** → grades and section data for the six demo prompts are
  served from cache and will still work. The catalog answer (prompt 2) and the
  professor recommendation need the model, so skip to prompt 3 and 4.

---

## Numbers to have in your head

| | |
|--|--|
| Courses indexed | ~25,700 fetched, 15,581 indexed (with descriptions), 344 subjects |
| Eval set | 41 cases, 8 intents, tool + fact assertions per case |
| Last judged pass rate | 27/36 (75%) on a GPT-4o rubric |
| Typical response | 1–4s cards, 4–10s agent answers |
| Data sources | GopherGrades (umn.lol) · courses.umn.edu · Coursedog catalog · LibCal/25Live · Tavily |
| Team | 7 UMN students, ~140 commits |
