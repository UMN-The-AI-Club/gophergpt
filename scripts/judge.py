#!/usr/bin/env python3
"""
Judge: score eval_runner.py results against a rubric using GPT-4o.
"""

import argparse # parses cmd line flags such as --run, --model, etc
import json
import glob # find latest run file
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from pydantic import BaseModel, Field
from langchain_openai import ChatOpenAI # Used to define schema to force LLM to respond in a certain way/shape
from langchain_core.messages import SystemMessage, HumanMessage 

# Creating the schema
class JudgeScore(BaseModel):
    correctness: int = Field(
        ge=1, le=5,
        description="Are the facts stated (course name, numbers, prof names) accurate?"
    )
    groundedness: int = Field(
        ge=1, le=5,
        description=(
            "Does every specific claim look traceable to real data rather than invented? "
            "Penalize confident-sounding numbers/names with no basis."
        ),
    )
    tool_use: int = Field(
        ge=1, le=5,
        description="Did the response draw on the right data source for this question?",
    )
    completeness: int = Field(
        ge=1, le=5,
        description="Does the response fully answer what was actually asked?"
    )
    style: int = Field(
        ge=1, le=5,
        description="Concise, no filler, no leaked tool/internal names, matches assistant tone.",
    )
    verdict: str = Field(description="Overall judgment: 'pass' or 'fail'")
    rationale: str = Field(description="1-3 sentences citing specific issues, if any")


# Turning schema into structured llm call
def build_judge_llm(model: str) -> ChatOpenAI:
    # .env uses OPENAI_KEY (not LangChain's default OPENAI_API_KEY), same as
    # autonomy/llm/openai_llm.py
    llm = ChatOpenAI(model=model, api_key=os.getenv("OPENAI_KEY"), temperature=0)
    return llm.with_structured_output(JudgeScore)

# System Prompt
JUDGE_SYSTEM_PROMPT = """You are grading a University of Minnesota course-assistant chatbot's response.

You will be given: the user's question, the assistant's response, which data-source \
tools were expected vs. actually used, and a "ground truth hint" (a verified fact \
about the real answer, when available).

This app answers some questions with a rich CARD (a chart or table) rather than prose. \
On those, the response text is a short lead-in and the substance lives in the \
structured payload. Judge the response text AND the card payload together as one \
answer. A brief lead-in above a card that fully answers the question is CORRECT and \
COMPLETE — do not penalize it for being short, and do not expect the text to restate \
numbers the chart already shows.

When a card payload is provided it is genuine tool output, so use it as the source of \
truth for groundedness: any number or name in the response text must be consistent \
with it. When no payload is provided you do not have the raw tool output — in that \
case judge groundedness by whether claims are specific-but-plausible and consistent \
with the ground truth hint (when given), rather than re-deriving the source data. \
Either way, penalize claims that look fabricated: invented statistics, professor names \
grounded in nothing, times/dates stated with false confidence.

A tool trace, when provided, is genuine retrieved data — treat it as source of truth \
alongside any card payload. A claim in the response text is grounded if it matches \
EITHER the card payload OR the tool trace. If both are absent, the assistant answered \
without looking anything up: score groundedness and tool_use low unless the question \
genuinely needed no lookup.

For tool_use, judge whether the answer actually rests on real retrieved data for this \
kind of question. "Tools actually used: unknown/none recorded" means the harness did \
not capture the tool list — it is NOT evidence that no tool ran, so do not penalize \
for it; infer from whether the answer (including any card payload) contains real \
grounded data.

Score each rubric dimension from 1 (bad) to 5 (excellent). Give an overall pass/fail \
verdict — fail if the response contains a hallucinated fact, misses the actual \
question, or leaks internal tool names. Keep your rationale short and specific."""

# Building per-case user message
def format_case_prompt(result: dict, golden_case: dict | None, profile_notes: str | None) -> str:
    lines = [
        f"Question: {result['question']}",
        f"Intent: {result.get('intent')}",
    ]
    if profile_notes:
        lines.append(f"User profile context: {profile_notes}")

    lines.append(f"Expected tool(s): {result.get('expected_tools') or 'none specified'}")
    lines.append(f"Tools actually used: {result.get('tools_used') or 'unknown/none recorded'}")

    if result.get("expected_content_types"):
        lines.append(f"Expected content types: {result['expected_content_types']}")
    lines.append(f"Content types returned: {result.get('content_types')}")

    if golden_case and golden_case.get("notes"):
        lines.append(f"Ground truth hint: {golden_case['notes']}")

    checks = result.get("checks", {})
    if checks.get("missing_groups") or checks.get("forbidden_found"):
        lines.append(
            "Note: automated checks already flagged issues — "
            f"missing required terms: {checks.get('missing_groups')}, "
            f"forbidden terms found: {checks.get('forbidden_found')}"
        )

    lines.append(f"\nAssistant's full response text:\n{result.get('checked_text', '')}")

    # Card paths answer via a structured payload rendered as a chart/table in the UI.
    # It is real tool output, so it is the ground truth for groundedness on these cases.
    payload = result.get("content_payload")
    if payload:
        lines.append(
            "\nStructured data shown to the user in a card (this IS real tool output — "
            "treat it as the source of truth; may be truncated):\n" + payload
        )
    # The agent's actual tool calls. Distinct from the card payload: cards come from
    # direct fetches, this is what the LLM agent itself retrieved.
    trace = result.get("tool_outputs")
    if trace:
        lines.append(
            "\nTool calls the assistant made and what they returned (real retrieved "
            "data - also source of truth for groundedness; may be truncated):\n" + trace
        )
    return "\n".join(lines)

# Loading golden set + building the id/profile lookups
def load_golden_lookup(golden_path: Path):
    with open(golden_path) as f:
        golden = json.load(f)

    cases_by_id = {c["id"]: c for c in golden.get("cases", [])}
    profiles_by_user = {
        p["user_id"]: p.get("personalization_notes")
        for p in golden.get("profiles", [])
    }
    return cases_by_id, profiles_by_user

# Scoring loop
def judge_result(judge_llm, result: dict, cases_by_id: dict, profiles_by_user: dict) -> dict:
    if result.get("error"):
        return {"error": f"skipped - eval_runner reported: {result['error']}"}

    golden_case = cases_by_id.get(result["id"])
    profile_notes = profiles_by_user.get(result.get("user_id"))
    user_prompt = format_case_prompt(result, golden_case, profile_notes)

    try:
        score = judge_llm.invoke([
            SystemMessage(content=JUDGE_SYSTEM_PROMPT),
            HumanMessage(content=user_prompt),
        ])
        return score.model_dump()
    except Exception as e:
        return {"error": str(e)}

# Helper
def latest_run_file(out_dir="evals/results") -> Path | None:
    files = sorted(glob.glob(f"{out_dir}/run_*.json"))
    return Path(files[-1]) if files else None

# Summary Printer
def print_judge_summary(results):
    from collections import defaultdict

    by_intent = defaultdict(list)
    for r in results:
        j = r.get("judge") or {}
        if "error" in j:
            continue
        by_intent[r["intent"]].append(j)

    dims = ["correctness", "groundedness", "tool_use", "completeness", "style"]
    print("\n=== Judge Summary by Intent ===")
    header = f"{'Intent':<15}" + "".join(f"{d[:10]:<12}" for d in dims) + f"{'Pass Rate':<10}"
    print(header)
    print("-" * len(header))

    for intent in sorted(by_intent):
        scores = by_intent[intent]
        row = f"{intent:<15}"
        for d in dims:
            avg = sum(s[d] for s in scores) / len(scores)
            row += f"{avg:<12.2f}"
        pass_rate = sum(1 for s in scores if s["verdict"] == "pass") / len(scores)
        row += f"{pass_rate:<10.0%}"
        print(row)


def main():
    parser = argparse.ArgumentParser(description="Judge eval_runner.py results with GPT-4o")
    parser.add_argument("--run", help="Path to a run JSON (default: latest in evals/results/)")
    parser.add_argument("--golden", default="evals/golden_set.json")
    parser.add_argument("--model", default="gpt-4o")
    parser.add_argument("--filter", help="Only judge cases with this intent")
    parser.add_argument("--id", help="Only judge a single case ID")
    parser.add_argument("--out", help="Output path (default: <run>_judged.json)")
    args = parser.parse_args()

    load_dotenv()

    run_path = Path(args.run) if args.run else latest_run_file()
    if run_path is None or not run_path.exists():
        print(f"ERROR: no run file found (looked for {args.run or 'evals/results/run_*.json'})", file=sys.stderr)
        sys.exit(1)

    with open(run_path) as f:
        run_data = json.load(f)

    cases_by_id, profiles_by_user = load_golden_lookup(Path(args.golden))
    judge_llm = build_judge_llm(args.model)

    results = run_data["results"]
    if args.id:
        results = [r for r in results if r["id"] == args.id]
    elif args.filter:
        results = [r for r in results if r.get("intent") == args.filter]

    for i, result in enumerate(results, 1):
        print(f"[{i}/{len(results)}] judging {result['id']}...", file=sys.stderr)
        result["judge"] = judge_result(judge_llm, result, cases_by_id, profiles_by_user)

    out_path = Path(args.out) if args.out else run_path.with_name(run_path.stem + "_judged.json")
    with open(out_path, "w") as f:
        json.dump(run_data, f, indent=2)

    print(f"\nJudged results written to {out_path}")
    print_judge_summary(run_data["results"])

    failed = sum(1 for r in results if (r.get("judge") or {}).get("verdict") == "fail")
    if failed:
        sys.exit(1)


if __name__ == "__main__":
    main()


