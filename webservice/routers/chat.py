import datetime
import json
import os
import re
import asyncio

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from webservice.agent import ChatAgent
from webservice.dependencies import get_agent
from webservice.guardrails import run_guardrails
from webservice.personalization import build_personalized_prompt
from webservice.profile_store import get_profile
from webservice.routers.research import run_research_query, ResearchRequest
from autonomy.tools.gophergrades_api import fetch_class, fetch_search, fetch_prof
from autonomy.tools.umn_courses_tool import fetch_sections_async

# This defines where we are storing the conversation history into.
# Will be using as a memory cache, to continue dialogue with agent.
DATA_DIR = os.getenv("DATA_DIR", "/app/data")  # where the file will be stored
os.makedirs(
    DATA_DIR, exist_ok=True
)  # makes directory if doesn't exist, nothing if does exist
CONVERSATION_FILE = os.path.join(
    DATA_DIR, "conversations.json"
)  # full path of where JSON file is stored


router = APIRouter()

SCHEDULING_KEYWORDS = {
    "schedule", "section", "sections", "conflict", "fits", "fit",
    "sign up", "register", "enroll", "when does", "what time",
    "what sections", "lib ed", "lib-ed", "open sections", "taking"
}

GRADE_KEYWORDS = {
    "grade", "grades", "gpa", "distribution", "how hard", "difficult",
    "easy", "grading", "pass rate", "a rate", "grade breakdown",
    "how tough", "grade in", "grades in", "historically",
}

def _is_scheduling_request(message: str) -> bool:
    lower = message.lower()
    return any(kw in lower for kw in SCHEDULING_KEYWORDS)

def _is_grade_query(message: str) -> bool:
    lower = message.lower()
    return any(kw in lower for kw in GRADE_KEYWORDS)

def _extract_term(message: str) -> str:
    lower = message.lower()
    m = re.search(r'(fall|spring|summer)\s+(20\d{2})', lower)
    if m:
        return f"{m.group(1)} {m.group(2)}"
    today = datetime.date.today()
    month = today.month
    year = today.year
    if "this fall" in lower or "fall semester" in lower:
        return f"fall {year}"
    if "next fall" in lower:
        return f"fall {year + 1}"
    if "this spring" in lower or "spring semester" in lower:
        return f"spring {year}"
    if "next spring" in lower:
        return f"spring {year + 1}"
    if month <= 5:
        return f"spring {year}"
    if month <= 8:
        return f"fall {year}"
    return f"spring {year + 1}"

async def _fetch_one(code: str, term: str) -> dict | None:
    m = re.match(r'^([A-Z]+)(\d+[A-Z]?)', code)
    if not m:
        return None
    subject = m.group(1)
    catalog_number = m.group(2)
    try:
        sections = await fetch_sections_async(subject, catalog_number, term)
        if isinstance(sections, list) and len(sections) > 0:
            return {"code": code, "term": term, "sections": sections}
    except Exception:
        pass
    return None

async def _fetch_schedule_data(course_codes: list, term: str) -> list:
    results = await asyncio.gather(*[_fetch_one(code, term) for code in course_codes[:4]])
    return [r for r in results if r is not None]


class ChatRequest(BaseModel):
    message: str

    # ensures loading the correct history and not all
    conversation_id: int | None = (
        None  # makes it optional, provide stability to frontend, since no history may exist
    )
    user_id: str | None = None  # optional — used to load profile context


class ConversationRequest(BaseModel):
    id: int
    title: str
    messages: list


def _generate_follow_ups(message: str, course_codes: list, response_type: str = "general") -> list:
    """Generate contextual follow-up chip suggestions based on request content."""
    primary = course_codes[0] if course_codes else None
    lower = message.lower()

    if response_type == "schedule" and primary:
        return [
            f"Who teaches {primary} with the best ratings?",
            f"What are the prerequisites for {primary}?",
            "Find a conflict-free schedule",
        ]

    if response_type == "grades" and primary:
        return [
            f"Who teaches {primary} with the best grades?",
            f"What sections of {primary} are open this fall?",
            f"Compare {primary} to a similar course",
        ]

    if primary:
        if any(kw in lower for kw in ("who teaches", "professor", "instructor", "prof")):
            return [
                f"What are the grade distributions in {primary}?",
                f"What sections of {primary} are open this fall?",
                f"What are the prerequisites for {primary}?",
            ]
        return [
            f"What sections of {primary} are open this fall?",
            f"Who teaches {primary} with the best grades?",
            f"What are the prerequisites for {primary}?",
        ]

    if any(kw in lower for kw in ("professor", "prof", "instructor")):
        return [
            "What courses does this professor teach?",
            "How do grades compare across instructors?",
            "When does this professor teach next semester?",
        ]

    return [
        "What courses should I take next semester?",
        "Who are the highest-rated professors in CS?",
        "How do I find courses that fit my schedule?",
    ]


# --- Professor lookup / comparison -------------------------------------------

# "professor(s)", "prof(s)", "prof.", "instructor(s)", "dr", "dr." — the intent trigger
_PROF_TRIGGER = re.compile(r'\b(?:professors?|profs?|instructors?|dr)\b\.?\s+', re.IGNORECASE)
# A redundant trigger word leading an individual name segment (stripped per-segment)
_PROF_LEAD = re.compile(r'^\s*(?:professors?|profs?|instructors?|dr)\b\.?\s+', re.IGNORECASE)

# Words that may sit next to a name but are not part of it
_PROF_STOP = {
    "ratings", "rating", "grades", "grade", "reviews", "review", "profile",
    "info", "information", "and", "vs", "versus", "teach", "teaches", "teaching",
    "please", "the", "a", "an", "for", "in", "with", "at", "umn", "score", "scores",
    "his", "her", "their", "office", "hours", "class", "classes", "course", "courses",
}


def _extract_prof_names(text):
    """
    Pull one or more professor names out of a message.

    Handles all common phrasings once a trigger word ("professor"/"prof"/etc.)
    appears anywhere: single lookups ("tell me about professor Chad Myers"),
    and comparisons where the trigger is written once OR twice
    ("compare professor Myers and Dovolis", "professors Myers vs Dovolis",
    "professor Chad Myers vs professor Dan Dovolis"). Lowercase input and
    trailing words like "ratings"/"grades" are tolerated. Returns Title-cased
    names in order. Bogus segments are harmless — _fetch_prof_data drops any
    name that doesn't resolve to a real professor.
    """
    m = _PROF_TRIGGER.search(text)
    if not m:
        return []

    # Everything from the first trigger onward is the candidate name region.
    region = text[m.start():]
    # Split into per-professor segments on connectors: and / vs / versus / , / & / /
    segments = re.split(r"\b(?:and|vs|versus)\b|[,&/]", region, flags=re.IGNORECASE)

    names = []
    for seg in segments:
        seg = _PROF_LEAD.sub("", seg)               # drop a leading "professor"/"prof"
        seg = re.split(r"[\?\.;:]|'s", seg)[0]       # cut trailing punctuation / possessive
        tokens = re.findall(r"[A-Za-z'\-]+", seg)
        while tokens and tokens[0].lower() in _PROF_STOP:
            tokens.pop(0)
        while tokens and tokens[-1].lower() in _PROF_STOP:
            tokens.pop()
        name = " ".join(tokens[:3]).strip()
        if name and name.lower() not in _PROF_STOP:
            title = name.title()
            if title not in names:
                names.append(title)
    return names


def _fetch_prof_data(name):
    """
    Deterministically resolve a professor name to full GopherGrades data.

    Runs the same search -> prof chain the agent would, so the professor card
    fires 100% of the time regardless of the model. Returns
    {"name", "code", "data"} or None if the professor can't be found.
    """
    try:
        result = fetch_search(name)
        profs = (result.get("data") or {}).get("professors") or []

        # Fallback: a wrong/missing first name ("Dan Dovolis") finds nothing —
        # retry on the surname alone ("Dovolis") before giving up.
        if not profs:
            parts = name.split()
            if len(parts) > 1:
                retry = fetch_search(parts[-1])
                profs = (retry.get("data") or {}).get("professors") or []
        if not profs:
            return None

        best = profs[0]
        code = best.get("id")
        if code is None:
            return None
        prof_raw = fetch_prof(str(code))
        data = prof_raw.get("data")
        if not data:
            return None
        return {"name": best.get("name") or name, "code": str(code), "data": data}
    except Exception:
        return None


# Phrases that mean "the courses in my profile" (codes come from the profile,
# not the message). Used to answer instantly instead of sending a vague
# multi-course prompt through the agent's ReAct loop (which is slow on a local
# model and tends to make redundant/hallucinated tool calls).
_MY_COURSES_SELF = (
    "my ", "i plan", "i'm taking", "im taking", "i am taking", "i will take",
    "i will be taking", "planning to take", "plan to take", "i put", "i signed up",
    "i registered", "i'm enrolled", "im enrolled", "profile", "signed up for",
)


def _is_my_courses_query(message: str, has_codes: bool) -> bool:
    if has_codes:
        return False
    lower = message.lower()
    mentions_courses = any(w in lower for w in ("course", "class", "classes", "schedule"))
    mentions_self = any(w in lower for w in _MY_COURSES_SELF)
    return mentions_courses and mentions_self


def extract_course_codes(text):
    """
    Extract normalized UMN course codes (e.g. CSCI4041) from a message.

    Args:
        text: string entered by user

    Returns:
        a list of course codes found within text (e.g. ["CSCI4041","STAT3021"])

    Keeps a trailing section letter when present (e.g. "CSCI 4511W" -> "CSCI4511W",
    "MATH 1271H" -> "MATH1271H"), which is significant for GopherGrades lookups.
    """
    pattern = r"\b([A-Z]{2,6})\s*(\d{4}[A-Z]?)\b"
    seen = []
    for m in re.finditer(pattern, text.upper()):
        code = f"{m.group(1)}{m.group(2)}"
        if code not in seen:
            seen.append(code)
    return seen


def is_research_followup(message, history):
    """
    Returns True if this looks like a follow-up to a prior research query.

    Args:
        message: user entered message
        history: the conversation history between user and agent

    Returns:
        True if the message is a research follow-up, False otherwise
    """
    if not re.match(
        r"^(what|how)\s+about|^and\b|^what if", message.strip(), re.IGNORECASE
    ):
        return False
    recent = history[-6:] if len(history) > 6 else history
    return any(re.search(r"rea?sea?rch", msg["content"].lower()) for msg in recent)


def build_research_query(current_message, history):
    """
    Construct a full research query from a follow-up message using prior context.

    Args:
        current_message: the current message in conversation
        history: the conversation history between user and agent

    Returns:
        a constructed research query string, or the original message if no context found
    """
    for msg in reversed(history):
        if msg["role"] == "user" and re.search(r"rea?sea?rch", msg["content"].lower()):
            # Extract the new subject from the follow-up (e.g. "what about for biology" → "biology")
            m = re.search(
                r"(?:for|about|in)\s+([\w\s]+?)(?:\?|$)", current_message, re.IGNORECASE
            )
            if m:
                subject = m.group(1).strip()
                return (
                    f"research opportunities for {subject} at University of Minnesota"
                )
            break
    return current_message


def _enrich_research_query(raw_query: str, profile: dict) -> str:
    """
    Make a research query more specific using profile context and UMN-specific terms.

    Args:
        raw_query: the unmodified query provided from user
        profile: filters provided from user profile

    Returns:
        a more specific query string enriched with profile context and UMN terms
    """
    query = raw_query.strip()

    # Add major from profile if not already in the query
    major = (profile.get("major") or "").strip()
    if major and major.lower() not in query.lower():
        query = f"{query} {major}"

    # Add specificity terms if the query is generic
    generic_terms = ["research", "research opportunities", "research opportunity"]
    if query.lower() in generic_terms or re.match(
        r"^research\s*(opportunities?|programs?)?\s*$", query.lower()
    ):
        query = f"undergraduate research opportunities programs apply University of Minnesota"
        if major:
            query += f" {major}"
    elif re.search(r"research", query, re.IGNORECASE):
        # Already has research in it — ensure UMN context and add specificity
        if (
            "university of minnesota" not in query.lower()
            and "umn" not in query.lower()
        ):
            query += " University of Minnesota"
        if not any(
            t in query.lower()
            for t in ["apply", "program", "lab", "undergraduate", "faculty"]
        ):
            query += " undergraduate program apply"

    return query


def summarize_research_text(text, limit=200):
    """
    Truncates and cleans text to a specified character limit.

    Args:
        text: string provided to be cleaned
        limit: character limit, defaults to 200

    Returns:
        the cleaned and truncated string.
    """

    if not text:
        return ""

    cleaned = re.sub(r"\s+", " ", str(text)).strip()
    cleaned = re.sub(r"(#{1,6}\s*)+", "", cleaned)

    if len(cleaned) <= limit:
        return cleaned

    shortened = cleaned[:limit].rsplit(" ", 1)[0].strip()
    return f"{shortened}..."


# responsible for loading/retrieving chat messages
@router.post("/chat")
async def chat_endpoint(request: ChatRequest, agent: ChatAgent = Depends(get_agent)):
    """
    Handles incoming chat requests, routing to research, course comparison, or general agent response.

    Args:
        request: ChatRequest containing the user message, conversation_id, and user_id

    Returns:
        a dict with response string and content list for the frontend to render
    """

    message = request.message.lower()
    tools_used = []

    # Load profile context if user_id provided
    profile_context = ""
    if request.user_id:
        profile = get_profile(request.user_id)
        profile_context = build_personalized_prompt(profile)

    # Loads the conversation history from file "app/data"
    history = []
    if request.conversation_id is not None and os.path.exists(CONVERSATION_FILE):
        with open(CONVERSATION_FILE, "r") as file:
            conversations = json.load(file)
        match = next(
            (c for c in conversations if c["id"] == request.conversation_id), None
        )
        if match:
            history = [
                {
                    "role": "user" if msg["isUser"] else "assistant",
                    "content": msg["text"],
                }
                for msg in match["messages"]
            ]

    course_codes = extract_course_codes(request.message)

    # "Tell me about the courses I plan to take" / "my classes" — pull the codes
    # from the profile and return a grade-overview card directly. This avoids the
    # slow, error-prone multi-course ReAct loop on a local model.
    if request.user_id and _is_my_courses_query(request.message, bool(course_codes)):
        notes = (get_profile(request.user_id).get("personalization_notes") or "")
        profile_codes = extract_course_codes(notes)
        if profile_codes:
            term = _extract_term(notes)
            schedule_data = await _fetch_schedule_data(profile_codes, term)
            if schedule_data:
                codes_str = ", ".join(c["code"] for c in schedule_data)
                tools_used.append("umn_class_sections")
                return {
                    "response": f"Here are the live {term.title()} sections for the courses in your profile — {codes_str}.",
                    "content": [{"type": "schedule", "courses": schedule_data}],
                    "follow_ups": [
                        "Do any of these conflict in my schedule?",
                        f"Who teaches {schedule_data[0]['code']} with the best grades?",
                        f"How hard is {schedule_data[0]['code']}?",
                    ],
                    "tools_used": tools_used,
                }

    if re.search(r"rea?sea?rch", message) or is_research_followup(message, history):
        raw_query = (
            request.message
            if re.search(r"rea?sea?rch", message)
            else build_research_query(message, history)
        )
        query = _enrich_research_query(
            raw_query, get_profile(request.user_id) if request.user_id else {}
        )
        research_data = run_research_query(ResearchRequest(query=query, max_results=10))
        tools_used.append("tavily_search")

        # Deduplicate by domain, but allow up to 2 results per domain for rich sources
        domain_counts: dict = {}
        unique_results = []
        for r in research_data.results:
            domain = re.sub(r"^https?://([^/]+).*", r"\1", r.url)
            count = domain_counts.get(domain, 0)
            if count < 2:
                domain_counts[domain] = count + 1
                unique_results.append(r)

        summary_text = summarize_research_text(research_data.summary, limit=200)

        # Build topic-specific follow-ups for research responses
        topic_words = re.sub(r'(research|opportunities?|programs?|university of minnesota|umn)', '', raw_query, flags=re.IGNORECASE).strip()
        topic = topic_words[:40] if topic_words else "this field"
        research_follow_ups = [
            f"What are the application requirements?",
            f"Which labs accept undergraduates in {topic}?",
            f"How do I contact faculty researchers?",
        ]

        return {
            "response": "Here's a research snapshot with the strongest matches I found.",
            "content": [
                {
                    "type": "research",
                    "summary": summary_text,
                    "results": [
                        {
                            "title": summarize_research_text(result.title, limit=90),
                            "url": result.url,
                            "snippet": summarize_research_text(
                                result.snippet, limit=160
                            ),
                        }
                        for result in unique_results
                    ][:6],
                }
            ],
            "follow_ups": research_follow_ups,
            "tools_used": tools_used,
        }

    # Professor lookup / comparison: resolve GopherGrades data ourselves and
    # return a visual prof card (search -> prof chain, model-independent).
    # Only fires when an actual professor name is present in the message.
    prof_names = _extract_prof_names(request.message)
    if prof_names:
        profs = []
        for name in prof_names[:2]:
            prof_data = _fetch_prof_data(name)
            if prof_data:
                profs.append(prof_data)

        if profs:
            guided_message = (
                request.message
                + "\n\n[System: RateMyProfessors scores, courses taught, grade distributions "
                "and teaching ratings for these professors are already shown visually in a card. "
                "Write 2-3 sentences max giving a high-level, qualitative takeaway or recommendation. "
                "Do NOT list any numbers, grades, or ratings — those are already in the card.]"
            )
            try:
                summary, trace = await agent.invoke_with_trace(guided_message, history=history)
            except Exception:
                summary, trace = "", []
                tools_used.extend(t['name'] for t in trace if t['name'] not in tools_used)

            if len(profs) >= 2:
                prof_follow_ups = [
                    f"Who has higher grades, {profs[0]['name']} or {profs[1]['name']}?",
                    f"What courses does {profs[0]['name']} teach?",
                    "Which professor should I take?",
                ]
            else:
                prof_follow_ups = [
                    f"What courses does {profs[0]['name']} teach?",
                    f"Compare {profs[0]['name']} with another professor",
                    f"How do {profs[0]['name']}'s grades compare to other instructors?",
                ]

            return {
                "response": "",
                "content": [{
                    "type": "prof_compare",
                    "profs": profs,
                    "summary": summary.strip() if isinstance(summary, str) else "",
                }],
                "follow_ups": prof_follow_ups,
            }

    # Detect course comparison requests
    is_compare_request = "compare" in message and len(course_codes) >= 1

    if is_compare_request:
        courses = []
        for code in course_codes[:2]:
            try:
                class_result = fetch_class(code)
                if class_result.get("data"):
                    courses.append({"code": code, "data": class_result["data"]})
                    if "gophergrades_class" not in tools_used:
                        tools_used.append("gophergrades_class")
            except Exception:
                pass

        if courses:
            guided_message = (
                request.message
                + "\n\n[System: Grade distributions and SRT ratings will be shown visually. "
                "Write 2-3 sentences max giving a high-level insight or recommendation. "
                "Do NOT mention any numbers, grades, or ratings — those are already in the charts.]"
            )
            ai_summary, trace = await agent.invoke_with_trace(guided_message, history=history)
            tools_used.extend(t['name'] for t in trace if t['name'] not in tools_used)
            codes = course_codes[:2]
            compare_follow_ups = [
                f"Who teaches {codes[0]} with the highest grades?" if codes else "Who gives the best grades?",
                f"What are the prerequisites for {codes[0]}?" if codes else "What are the prerequisites?",
                f"Which course is better for my major?",
            ]
            return {
                "response": "",
                "content": [
                    {"type": "compare", "courses": courses, "summary": ai_summary}
                ],
                "follow_ups": compare_follow_ups,
                "tools_used": tools_used,
                "tool_outputs": trace, 
            }

    # Grade distribution: fetch from GopherGrades and return a visual card
    # Only trigger when there's a clear grade-related keyword AND a course code,
    # and only when it's not already handled as a compare request.
    if _is_grade_query(request.message) and course_codes and not is_compare_request:
        grade_courses = []
        for code in course_codes[:2]:
            try:
                class_result = fetch_class(code)
                if class_result.get("data"):
                    grade_courses.append({"code": code, "data": class_result["data"]})
                    if "gophergrades_class" not in tools_used:
                        tools_used.append("gophergrades_class")
                
            except Exception:
                pass
        if grade_courses:
            code_list = ", ".join(c["code"] for c in grade_courses)
            return {
                "response": f"Here are the historical grade distributions for {code_list}.",
                "content": [{"type": "grades", "courses": grade_courses}],
                "follow_ups": _generate_follow_ups(request.message, course_codes, "grades"),
                "tools_used": tools_used,
            }

    # Scheduling: resolve section data BEFORE calling the agent so we can return early
    # (avoids the agent writing out sections as prose text alongside the card)
    if _is_scheduling_request(request.message) and len(course_codes) >= 1:
        term = _extract_term(request.message)
        schedule_data = await _fetch_schedule_data(course_codes, term)
        if schedule_data:
            codes_str = ", ".join(c["code"] for c in schedule_data)
            tools_used.append("umn_class_sections")
            return {
                "response": f"Here are the live sections for {codes_str} — {term.title()}.",
                "content": [{"type": "schedule", "courses": schedule_data}],
                "follow_ups": _generate_follow_ups(request.message, course_codes, "schedule"),
                "tools_used": tools_used,
            }

    full_message = f"{profile_context}\n\nUser message:\n{request.message}" if profile_context else request.message
    raw_response, trace = await agent.invoke_with_trace(full_message, history=history)
    raw_response = run_guardrails(response=raw_response, message=full_message)
    tools_used.extend(t["name"] for t in trace if t["name"] not in tools_used)

    return {
        "response": raw_response.strip(),
        "content": [],
        "follow_ups": _generate_follow_ups(request.message, course_codes),
        "tools_used": tools_used,
        "tool_outputs": trace,
    }


# Implementing History Permanent Storage


# receives a conversation object from frontend, and store it
@router.post("/save")
def save_endpoint(request: ConversationRequest):
    """
    Saves or updates a conversation in the JSON store.

    Args:
        request: ConversationRequest containing id, title, and messages

    Returns:
        a dict with ok status
    """

    # checks if json already exist, before saving.
    if os.path.exists(CONVERSATION_FILE):
        # exist, so read file
        with open(CONVERSATION_FILE, "r") as file:
            content = file.read().strip()
            conversations = json.loads(content) if content else []
    else:
        # doesn't exist, so make list to store temporarily
        conversations = []

    # find index of the existing conversation in list, if exist.
    match_index = next(
        (i for i, c in enumerate(conversations) if c["id"] == request.id), None
    )

    # if conversation exist, overwrite it with updated version.
    if match_index is not None:
        # found index, loading message
        conversations[match_index] = {
            "id": request.id,
            "title": request.title,
            "messages": request.messages,
        }
    else:
        # adds conversations components
        conversations.append(
            {"id": request.id, "title": request.title, "messages": request.messages}
        )

    # open file to write, creates if doesn't exist
    with open(CONVERSATION_FILE, "w") as file:
        json.dump(conversations, file, indent=2)

    # Good Return
    return {"ok": True}


# clears all saved conversations
@router.delete("/history/clear")
def clear_history_endpoint():
    """
    Deletes all saved conversations from the JSON store.

    Returns:
        a dict with ok status
    """

    if os.path.exists(CONVERSATION_FILE):
        os.remove(CONVERSATION_FILE)
    return {"ok": True}


# returns all saved conversations to the frontend
@router.get("/history")
def history_endpoint():
    """
    Returns all saved conversations from the JSON store in reverse chronological order.

    Returns:
        a dict with ok status and list of conversations
    """

    # checks if file exist
    if os.path.exists(CONVERSATION_FILE):
        # opens and read file
        with open(CONVERSATION_FILE, "r") as file:
            # load file into parsed format
            conversations = json.load(file)

            # return file
            return {"ok": True, "conversations": list(reversed(conversations))}
    else:
        # file doesn't exist, return empty list
        return {"ok": True, "conversations": []}
