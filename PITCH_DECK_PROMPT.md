# Prompt: GopherGPT deck for Brandon Young (OpenAI)

Paste everything between the lines into Claude. All facts below are verified against the
repo — nothing is estimated.

---

## THE PROMPT

You are helping me build a slide deck. I'm an undergrad at the University of Minnesota
and the technical lead on a student-built project called GopherGPT. I'm sending this deck
to **Brandon Young, a Sales Engineering leader at OpenAI**, who has offered to look at the
project and possibly help with advice, API credits, or connections. A mutual contact has
already introduced us.

My real goal is twofold: get GopherGPT support, and build a genuine professional
relationship. So the deck has to make him think *"this team built something real and
knows where it's going,"* not just *"cool campus chatbot."*

### Who I'm writing for

Brandon leads Sales Engineering at OpenAI — he helps organizations deploy AI
successfully, and he sees polished demos constantly. What lands with this audience:

- **A real product with real users in sight.** Not a tech demo — something students will
  actually open every day.
- **Evidence over adjectives.** Measured numbers where we have them, honest "in progress"
  where we don't. No "revolutionary," no "seamless," no invented user counts.
- **A vision with a credible path.** He needs to see both what exists today and what this
  becomes — and believe the team can get there.
- **Engineering maturity as a supporting note**, not the headline. The eval harness and
  model bake-off are proof points that we build carefully. They support the story; they
  are not the story. One slide each, maximum.

### The story of the deck — read this before writing anything

The deck tells the story of a **product becoming a platform**:

1. Every UMN student faces the same maze — course data, grade histories, professor
   quality, section times, study spaces, research opportunities, all scattered across
   systems that don't talk to each other.
2. A team of students built one assistant that sits on top of all of it and answers in
   plain language, grounded in live data.
3. It already does a lot — eight distinct capabilities today, from grade charts to
   study-space finding to a full department explorer.
4. And the architecture is deliberately open-ended: it's a tool-using agent, so every new
   campus system we connect becomes a new thing students can just *ask for*. Clubs and
   student orgs, dining, events, registration itself. The current tools are the first
   eight, not the final eight.
5. The long vision: every large university has this exact problem. GopherGPT is the
   pattern — UMN is the first campus, not the only one.

Engineering rigor (evals, the model bake-off, honest bottlenecks) appears late in the
deck as *evidence that the vision is in capable hands* — not as the centerpiece.

### Verified facts — use these, do not invent others

**What it is**
GopherGPT is an AI assistant for UMN students. It answers questions about courses,
professors, grades, sections, study spaces, and campus research by pulling live data from
real sources before answering — GopherGrades (`umn.lol`), UMN's live course catalog,
UMN's room booking system, and domain-restricted web search across `umn.edu`.

**What students can do with it TODAY — give this real room in the deck, it's the product**
- **Ask anything about a course.** "How hard is CSCI 1933?" returns the actual grade
  distribution as a chart, drawn from years of real GopherGrades data — not a vague
  paragraph.
- **Professor cards.** Full profile for any professor — rating, courses taught, grading
  tendency — or two professors **side by side**: "compare professor Myers and Dovolis."
- **Course comparison.** Two courses side by side with grade charts and an AI
  recommendation on which to take.
- **Live sections & open-ended scheduling.** Real section data from UMN's catalog —
  times, instructors, rooms, open/closed with seat counts. Handles both "what sections of
  CSCI 1933 are open this fall?" and genuinely open-ended asks like "find a lib-ed that
  fits around my classes," where the agent chains multiple tools on its own.
- **Department Explorer.** Browse an entire department — every course with grade charts
  and ratings in one view. (117 courses for a single department, live.)
- **Study space finder.** Campus buildings by need — quiet, group work, late-night, tech,
  St. Paul campus — with Google Maps links and LibCal reservation links to actually book
  a room.
- **UMN Research Finder.** Domain-restricted search across `umn.edu` with AI summaries —
  find labs and research opportunities that match your interests.
- **Personalization.** A student profile — major, year, level, completed and planned
  coursework — feeds every answer. Recommendations skip prereqs you've already taken;
  "tell me about the courses I plan to take" just works. Conversations persist across
  sessions.

The point to land: this is not a chatbot with one trick. It's **one interface over the
whole campus experience**, and every answer is grounded in live institutional data with
rich visual cards, not generated text.

**Team and timeline**
- 9 contributors, 124 commits, first commit September 2025 — roughly 11 months of work.
- Student-led and student-built, no faculty engineering support.
- I'm technical lead: architecture, the evaluation system, and running the team.
- Real distributed collaboration — top contributor has 70 commits, I have 31, seven
  others contributed beyond that.
- ~4,100 lines of Python, ~3,200 lines of JavaScript.

**Architecture — one clean slide**
- ReAct agent on LangGraph orchestrating **8 registered tools**: four GopherGrades tools
  (search, class, professor, department), live UMN class sections, room booking, web
  search, and a RAG course-search retriever (built, not yet live).
- FastAPI backend, React frontend rendering rich data cards. Docker Compose, ChromaDB.
- **Pluggable LLM factory** — the same agent runs on local Ollama, OpenAI, or self-hosted
  vLLM via config alone.
- The architectural point that sets up the vision slide: **capabilities are tools.**
  Adding a new campus system doesn't mean building a new app — it means registering a new
  tool, and the agent learns to use it. That's why the roadmap below is credible.

**What's next — near-term roadmap (all real, in progress or scoped)**
- Concurrency fixes and caching to take worst-case latency from ~40s to seconds.
- RAG retrieval over campus documents going live (built and wired; a startup race
  condition currently blocks it — diagnosed, fix scoped).
- Automated evaluation in CI on every code change.
- Authentication + per-user data, unlocking real personalization at scale.
- Then: multi-user deployment and public launch to a campus of 50,000 students.

**Where it goes — the vision slide(s). Make this expansive but grounded.**
Frame the future in two rings:

*Ring 1 — more of campus, same pattern (each of these is "register a tool," not "build
an app"):*
- **Clubs & student orgs** — "what clubs match my interests and meet Tuesdays?"
- **Events & campus life** — what's happening this weekend, free food, career fairs.
- **Dining & facilities** — hours, menus, what's open right now.
- **Advising support** — degree-progress-aware answers: "what requirements do I have
  left, and which courses satisfy them with the best professors?"
- **Registration itself** — from "find me a schedule" all the way to helping you actually
  sign up for classes, once auth exists.

The framing sentence: *today students ask GopherGPT about campus; the goal is that
students can ask GopherGPT to do things on campus.* Answers → actions.

*Ring 2 — beyond UMN:*
Every large university has identical pain — fragmented systems, terrible discoverability,
students navigating bureaucracy instead of learning. Grade-data sites like GopherGrades
have equivalents at many schools; course catalogs and room systems are near-universal.
GopherGPT is a **repeatable pattern for grounded campus agents**, and UMN is deployment
one. Don't oversell this — one confident slide, no fake market-size numbers.

**Proof we build carefully — ONE slide, late in the deck**
Two quick proof points, side by side:

*We measure model choice:* we ran the agent on local Qwen 2.5 7B (failed multi-step tool
chains), then 14B (open-ended agentic queries took 120-400 seconds and timed out), then
GPT-4o — the same queries in ~6 seconds. We chose OpenAI on measured merit through our
own pluggable-model setup, and below a capability threshold the agent doesn't get slower,
it stops working.

*We measure quality:* we built our own eval harness — a 36-case golden set across 7
intent categories, deterministic assertions plus a GPT-4o judge scoring correctness,
groundedness, tool use, completeness, and style. Between our Aug 1 baseline and Aug 13
run: judge pass rate 53% → **75%**, and tool-use score (does the answer rest on real
retrieved data?) **2.81 → 4.06** out of 5. Every run versioned; 32 stored runs.

**Honest current limits — a few lines on the roadmap slide, not a dedicated slide**
No auth yet (so no public launch), RAG built but not live, concurrency work in progress,
evals still run manually. Present these as the near-term roadmap items they are — a team
that names its own gaps — without dwelling.

### Deck spec

12 slides, 16:9. Self-contained HTML I can present in a browser and export to PDF.
Arrow-key navigation, one idea per slide, large readable type. University of Minnesota
maroon `#7A0019` and gold `#FFCC33` as accents on a clean light background. Headlines and
evidence on slides; talking points in speaker notes written in my voice — a confident
undergrad who did the work and isn't overselling.

Suggested arc (adjust if you see a better flow, but keep the product-first balance):

1. **Title.** GopherGPT — one assistant for the whole campus. Name, role, one line.
2. **The problem.** First-person and specific: picking next semester's classes means
   juggling grade histories, professor reviews, live section times, and prereqs across
   four systems that don't talk. Every UMN student knows this feeling.
3. **The answer.** One screen: ask in plain language, get a grounded answer with real
   data cards. Position it as one interface over the whole campus experience.
4-5. **What it does today.** Two slides for the capability tour — courses & grades &
   professor comparisons on one; scheduling, Department Explorer, study spaces, research
   finder, personalization on the other. Visual, card-like, concrete example queries.
6. **How it works.** Architecture: agent + 8 tools + live data sources. End on the key
   sentence: new capability = new tool, and that's the whole growth model.
7. **Built by students.** Team, timeline, scale. 9 contributors, 11 months, ~7,300 lines.
8. **What's next.** Near-term roadmap including the honest gaps, framed as scoped work.
9. **Answers → actions.** Ring 1 vision: clubs, events, dining, advising, registration.
   The open-ended framing — students ask it to *do* things, not just know things.
10. **Beyond UMN.** Ring 2: the repeatable pattern, one confident slide.
11. **We build carefully.** The combined proof slide: model bake-off + eval numbers.
12. **The ask.**

### The ask slide

Specific, modest, ranked so he can pick:
1. **Advice** — 30 minutes on agent architecture and evaluation from someone who deploys
   this professionally. Listed first on purpose: it's the easiest yes and it starts a
   relationship rather than a transaction.
2. **API credits** — to run evals automatically on every change and to load-test for
   campus-scale launch. Token cost is currently why our evals are manual.
3. **Connections** — anyone at OpenAI working on agents or education deployments.

Do not ask for a job or internship anywhere in the deck. That happens through the
relationship, not the slide.

### Rules

- Every number comes from the facts above. Invent nothing — no user counts, no adoption
  stats, no testimonials, no market sizes. Every figure must survive a follow-up question.
- Future capabilities (clubs, dining, registration, other campuses) must always read as
  vision, never as things that exist. Keep the today/tomorrow line crisp — with this
  audience, blurring it once costs all credibility.
- Do not claim RAG works. Built and wired, not yet operational.
- No hype vocabulary: cut "revolutionary," "cutting-edge," "seamless," "game-changing."
- Show me the slide-by-slide outline with headlines before building the full HTML, so I
  can adjust the story first.

---

## Follow-ups worth asking Claude after the deck exists

```
Give me the 60-second verbal version of this deck for a live call.
```

```
What are the 5 hardest questions a Sales Engineering leader at OpenAI would ask
about this project, and how should I answer each one honestly?
```

```
Draft a LinkedIn connection note under 300 characters — specific, no flattery,
references the mutual intro, makes the deck easy to say yes to.
```
