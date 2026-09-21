#!/usr/bin/env bash
#
# demo_check.sh — pre-flight check for a GopherGPT demo.
#
# Run this before demoing. It:
#   1. Confirms the backend + frontend are up and prints the agent model.
#   2. Verifies each tool/card path returns the right thing.
#
# Usage:  bash scripts/demo_check.sh
#
set -u

API="${API:-http://localhost:8000}"
FRONTEND="${FRONTEND:-http://localhost:3000}"

green() { printf "\033[32m%s\033[0m\n" "$1"; }
red()   { printf "\033[31m%s\033[0m\n" "$1"; }
bold()  { printf "\033[1m%s\033[0m\n" "$1"; }

ask() {
  # ask "<label>" '<json body>' "<substring that must appear in response|content>"
  local label="$1" body="$2" expect="$3"
  local out
  out=$(curl -s --max-time 240 -X POST "$API/chat" \
        -H "Content-Type: application/json" -d "$body")
  if echo "$out" | grep -q "$expect"; then
    green "  ✓ $label"
  else
    red   "  ✗ $label  (did not find: $expect)"
    echo "     $out" | head -c 240; echo
  fi
}

bold "1. Services"
curl -s --max-time 3 "$API/"        >/dev/null && green "  ✓ backend  $API" || { red "  ✗ backend down — run: docker compose up -d"; exit 1; }
curl -s --max-time 3 "$FRONTEND"    >/dev/null && green "  ✓ frontend $FRONTEND" || red "  ✗ frontend down"
MODEL=$(docker exec gophergpt-webservice printenv LLM_MODEL 2>/dev/null)
PROVIDER=$(docker exec gophergpt-webservice printenv LLM_PROVIDER 2>/dev/null)
green "  · agent model: ${PROVIDER:-?}/${MODEL:-?}"

bold "2. Deterministic card paths (model-independent, fast)"
ask "Grades card"      '{"message":"how hard is CSCI 1933?"}'                     '"type":"grades"'
ask "Compare card"     '{"message":"compare CSCI 1933 and CSCI 2021"}'           '"type":"compare"'
ask "Sections card"    '{"message":"what sections of CSCI 1933 are open this fall?"}' '"type":"schedule"'
ask "Research card"    '{"message":"research opportunities in biology"}'          '"type":"research"'
ask "Professor card"   '{"message":"tell me about professor Chad Myers"}'         '"type":"prof_compare"'
ask "Prof compare card" '{"message":"compare professor Myers and professor Dovolis"}' '"type":"prof_compare"'

bold "3. Agent tool paths (LLM-driven)"
ask "Professor lookup"  '{"message":"tell me about professor Chad Myers"}'     'Chad Myers'
ask "Room booking"      '{"message":"how do I get to Keller Hall and can I book a room there?"}' 'campusmaps.umn.edu'
ask "Study spaces"      '{"message":"where are good places to study on campus?"}' 'Walter'
ask "General web search" '{"message":"what is the U Card at UMN?"}'            'U Card'
ask "RAG course_search" '{"message":"what are the prerequisites for CSCI 1933?"}' '1133'

bold "Done. Open $FRONTEND and demo."
