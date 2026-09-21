#!/usr/bin/env python3
"""
Eval runner: fire golden-set cases at /chat, log results with checks.
"""

import argparse
import json
import sys
import time
import subprocess
from pathlib import Path
from datetime import datetime
import requests

# Cap on the serialized card payload stored per result (chars).
MAX_PAYLOAD_CHARS = 8000


def main():
    parser = argparse.ArgumentParser(
        description="Run golden-set evals against a GopherGPT backend"
    )
    parser.add_argument(
        "--base-url", default="http://localhost:8000", help="Backend URL"
    )
    parser.add_argument(
        "--golden", default="evals/golden_set.json", help="Path to golden set"
    )
    parser.add_argument("--filter", help="Filter by intent (e.g., 'grades')")
    parser.add_argument("--id", help="Run single case by ID")
    parser.add_argument("--out-dir", default="evals/results", help="Output directory")
    parser.add_argument(
        "--timeout", type=int, default=120, help="Request timeout in seconds"
    )
    args = parser.parse_args()

    # Load golden set
    golden_path = Path(args.golden)
    if not golden_path.exists():
        print(f"ERROR: {golden_path} not found", file=sys.stderr)
        sys.exit(1)

    with open(golden_path) as f:
        golden_data = json.load(f)

    cases = golden_data.get("cases", [])
    profiles = golden_data.get("profiles", [])
    global_must_not = golden_data.get("global_must_not_contain", [])

    # Ping backend
    try:
        requests.get(f"{args.base_url}/history", timeout=5)
    except Exception as e:
        print(f"ERROR: Backend not reachable at {args.base_url}: {e}", file=sys.stderr)
        sys.exit(1)

    # Setup profiles
    for profile in profiles:
        try:
            requests.put(f"{args.base_url}/profile", json=profile, timeout=args.timeout)
        except Exception as e:
            print(
                f"WARNING: Failed to load profile {profile.get('user_id')}: {e}",
                file=sys.stderr,
            )

    # Filter cases
    if args.id:
        cases = [c for c in cases if c["id"] == args.id]
    elif args.filter:
        cases = [c for c in cases if c.get("intent") == args.filter]

    if not cases:
        print("No cases matched filter", file=sys.stderr)
        sys.exit(1)

    # Run cases
    results = []
    errors_count = 0
    failed_count = 0

    for case in cases:
        result = run_case(case, args.base_url, args.timeout, global_must_not)
        results.append(result)
        if result.get("error"):
            errors_count += 1
        elif not result["checks"]["passed"]:
            failed_count += 1

    # Get git SHA
    try:
        git_sha = (
            subprocess.check_output(["git", "rev-parse", "--short", "HEAD"])
            .decode()
            .strip()
        )
    except:
        git_sha = "unknown"

    # Write results
    run_id = datetime.now().strftime("run_%Y%m%d_%H%M%S")
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    output = {
        "run_id": run_id,
        "timestamp": datetime.now().isoformat(),
        "base_url": args.base_url,
        "git_sha": git_sha,
        "num_cases": len(results),
        "results": results,
    }

    out_file = out_dir / f"{run_id}.json"
    with open(out_file, "w") as f:
        json.dump(output, f, indent=2)

    print(f"\nResults written to {out_file}")
    print_summary(results)

    if errors_count > 0 or failed_count > 0:
        sys.exit(1)


def run_case(case, base_url, timeout, global_must_not):
    """Run a single case."""
    case_id = case["id"]
    question = case["question"]
    user_id = case.get("user_id")
    expected_tools = case.get("expected_tools", [])
    expected_content_types = case.get("expected_content_types", [])
    must_contain = case.get("must_contain", [])
    must_not_contain = case.get("must_not_contain", [])

    error = None
    response_text = ""
    content_types = []
    content_payload = None
    tool_outputs = None
    latency_ms = 0
    tools_used = None

    t0 = time.perf_counter()
    try:
        resp = requests.post(
            f"{base_url}/chat",
            json={"message": question, "user_id": user_id},
            timeout=timeout,
        )
        latency_ms = (time.perf_counter() - t0) * 1000

        if resp.status_code != 200:
            error = f"HTTP {resp.status_code}"
        else:
            data = resp.json()
            response_text = data.get("response", "")

            # Gather content types and checked_text from content
            if "content" in data:
                for item in data["content"]:
                    if "type" in item:
                        content_types.append(item["type"])
                    if "summary" in item:
                        response_text += " " + item.get("summary", "")

                # Card paths (grades/compare/schedule/research/prof_compare) put the
                # substance of the answer in the structured payload, not in `response`
                # or `summary`. Capture it so the judge can score what the user
                # actually sees. Truncated — a dept payload can run ~110KB.
                content_payload = json.dumps(data["content"])[:MAX_PAYLOAD_CHARS]

            # Extract tools_used if available
            if "tools_used" in data:
                tools_used = data["tools_used"]
            # The agent's tool calls and what they returned. Card paths answer
            # without the agent, so this is absent there — expected, not a failure.
            if "tool_outputs" in data:
                tool_outputs = json.dumps(data["tool_outputs"])[:MAX_PAYLOAD_CHARS]

    except requests.exceptions.Timeout:
        error = f"Timeout after {timeout}s"
        latency_ms = (time.perf_counter() - t0) * 1000
    except Exception as e:
        error = str(e)
        latency_ms = (time.perf_counter() - t0) * 1000

    # Run checks (case-insensitive substring)
    checked_text = response_text.lower()
    missing_groups = []
    forbidden_found = []
    content_type_ok = True

    for group in must_contain:
        if not any(alt.lower() in checked_text for alt in group):
            missing_groups.append(group)

    all_forbidden = global_must_not + must_not_contain
    for forbidden in all_forbidden:
        if forbidden.lower() in checked_text:
            forbidden_found.append(forbidden)

    if expected_content_types:
        content_type_ok = all(ct in content_types for ct in expected_content_types)

    passed = (
        not error and not missing_groups and not forbidden_found and content_type_ok
    )

    return {
        "id": case_id,
        "intent": case.get("intent"),
        "question": question,
        "user_id": user_id,
        "response": response_text[:500],  # Truncate for readability
        "tool_outputs": tool_outputs,
        "checked_text": response_text,
        "content_types": content_types,
        "content_payload": content_payload,
        "latency_ms": latency_ms,
        "error": error,
        "checks": {
            "missing_groups": missing_groups,
            "forbidden_found": forbidden_found,
            "content_type_ok": content_type_ok,
            "passed": passed,
        },
        "expected_tools": expected_tools,
        "tools_used": tools_used,
        "judge": None,
    }


def print_summary(results):
    """Print summary table."""
    from collections import defaultdict

    by_intent = defaultdict(
        lambda: {"passed": 0, "failed": 0, "error": 0, "latencies": []}
    )

    for r in results:
        intent = r["intent"]
        latencies = by_intent[intent]["latencies"]
        latencies.append(r["latency_ms"])

        if r["error"]:
            by_intent[intent]["error"] += 1
        elif r["checks"]["passed"]:
            by_intent[intent]["passed"] += 1
        else:
            by_intent[intent]["failed"] += 1

    print("\n=== Summary by Intent ===")
    print(
        f"{'Intent':<15} {'Cases':<8} {'Passed':<8} {'Failed':<8} {'Error':<8} {'Mean (ms)':<12} {'Max (ms)':<12}"
    )
    print("-" * 80)

    total_cases = total_passed = total_failed = total_error = 0
    total_latencies = []

    for intent in sorted(by_intent.keys()):
        stats = by_intent[intent]
        cases = stats["passed"] + stats["failed"] + stats["error"]
        mean_lat = (
            sum(stats["latencies"]) / len(stats["latencies"])
            if stats["latencies"]
            else 0
        )
        max_lat = max(stats["latencies"]) if stats["latencies"] else 0

        print(
            f"{intent:<15} {cases:<8} {stats['passed']:<8} {stats['failed']:<8} {stats['error']:<8} {mean_lat:<12.0f} {max_lat:<12.0f}"
        )

        total_cases += cases
        total_passed += stats["passed"]
        total_failed += stats["failed"]
        total_error += stats["error"]
        total_latencies.extend(stats["latencies"])

    print("-" * 80)
    mean_total = sum(total_latencies) / len(total_latencies) if total_latencies else 0
    max_total = max(total_latencies) if total_latencies else 0
    print(
        f"{'TOTAL':<15} {total_cases:<8} {total_passed:<8} {total_failed:<8} {total_error:<8} {mean_total:<12.0f} {max_total:<12.0f}"
    )


if __name__ == "__main__":
    main()
