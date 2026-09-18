#!/usr/bin/env bash
# server/smoke-test.sh: sanity-checks every API route on a running server, then runs the unit tests.
# Owned by B (Backend).
#
#   terminal 1:  uvicorn server.main:app --port 8000
#   terminal 2:  bash server/smoke-test.sh          (BASE=http://host:port to aim elsewhere)
#
# Point it at a scratch server, not the one you will demo on: it resets the session and adds two
# rows to the stranger-QA log.
set -u
BASE="${BASE:-http://127.0.0.1:8000}"
PY="${PYTHON:-$(command -v python || command -v python3)}"
BODY="$(mktemp)"
trap 'rm -f "$BODY"' EXIT
pass=0; fail=0

ok()  { pass=$((pass + 1)); echo "  ok    $1"; }
bad() { fail=$((fail + 1)); echo "  FAIL  $1"; }

# req <name> <want-status> <METHOD> <path> [json-body]
req() {
  local code
  if [ -n "${5:-}" ]; then
    code=$(curl -s -o "$BODY" -w '%{http_code}' -X "$3" -H 'Content-Type: application/json' -d "$5" "$BASE$4")
  else
    code=$(curl -s -o "$BODY" -w '%{http_code}' -X "$3" "$BASE$4")
  fi
  if [ "$code" = "$2" ]; then ok "$1"; else bad "$1 (HTTP $code, wanted $2): $(head -c 160 "$BODY")"; fi
}
# has <name> <text expected in the last response>
has() { if grep -q -- "$2" "$BODY"; then ok "$1"; else bad "$1: no '$2' in $(head -c 160 "$BODY")"; fi; }

echo "Rich-HER smoke test against $BASE"
curl -s -o /dev/null --retry 10 --retry-connrefused --retry-delay 1 "$BASE/api/state" || { echo "server not reachable"; exit 1; }

echo "session & replay"
req "state (fresh)"                200 GET  /api/state;                                   has "  not onboarded" '"onboarded":false'
req "reset"                        200 POST /api/reset
req "advance before onboarding"    409 POST /api/advance '{"n":1}';                       has "  says why" 'NOT_ONBOARDED'
req "onboarding (new, AAPL)"       200 POST /api/onboarding '{"experience":"new","symbol":"AAPL"}'; has "  tier 1" '"tier":"beginner"'
req "onboarding twice"             409 POST /api/onboarding '{"experience":"new"}'
req "onboarding bad body"          422 POST /api/onboarding '{"experience":"wizard"}';    has "  validation shape" '"error":"VALIDATION"'

echo "market data"
req "quote (today)"                200 GET  /api/quote;                                   has "  168.00" '"price":168.0'
req "quote (a past bar)"           200 GET  "/api/quote?symbol=AAPL&as_of=10"
req "quote (the future)"           400 GET  "/api/quote?as_of=60";                        has "  no peeking" 'FUTURE_BAR'
req "quote (unknown symbol)"       404 GET  "/api/quote?symbol=ZZZ"

echo "trading & tier gating"
req "limit order at Tier 1"        403 POST /api/orders '{"symbol":"AAPL","side":"BUY","qty":1,"type":"LIMIT","limit_price":150,"as_of":40}'; has "  locked" 'TIER_LOCKED'
req "stale cursor"                 409 POST /api/orders '{"symbol":"AAPL","side":"BUY","qty":1,"as_of":3}'
req "buy 10 AAPL"                  200 POST /api/orders '{"symbol":"AAPL","side":"BUY","qty":10,"as_of":40}'; has "  filled at 168.00" '"price":168.0'
req "too many shares"              400 POST /api/orders '{"symbol":"AAPL","side":"BUY","qty":1000}'; has "  insufficient funds" 'INSUFFICIENT_FUNDS'
req "portfolio"                    200 GET  /api/portfolio;                               has "  cash 8320" '"cash":8320.0'
req "cancel a missing order"       404 DELETE /api/orders/99

echo "teaching"
req "tiers"                        200 GET  /api/tiers;                                   has "  three tiers" '"advanced"'
req "quick check (wrong)"          200 POST /api/comprehension '{"check_id":"downside","choice":0}'; has "  marked wrong" '"correct":false'
req "quick check (right)"          200 POST /api/comprehension '{"check_id":"downside","choice":2}'; has "  unlocks Tier 2" '"unlocked_tier":"intermediate"'

echo "the walk into the dip"
req "fast-forward stops at prompt" 200 POST /api/advance '{"n":30}';                      has "  prompt fired" 'SAFETY_NET_PROMPT'
req "advance while prompt pends"   409 POST /api/advance '{"n":1}';                       has "  blocked" 'PROMPT_PENDING'
req "accept the safety net"        200 POST /api/safety-net '{"symbol":"AAPL","decision":"accept"}'; has "  stop 151.20" '"stop_price":151.2'
req "fast-forward to the stop"     200 POST /api/advance '{"n":30}';                       has "  net sold" '"reason":"SAFETY_NET"'
req "qa log"                       200 GET  /api/qa-log;                                  has "  pitch line" 'first-time users'

echo "stubs & static"
req "news (stub)"                  200 GET  "/api/news?symbol=AAPL";                      has "  stub" '"stub":true'
req "fundamentals (stub)"          200 GET  "/api/fundamentals?symbol=AAPL";              has "  stub" '"stub":true'
req "web app at /"                 200 GET  /;                                            has "  html" '<title>Rich-HER'
if curl -sI "$BASE/app.js" | grep -qi 'content-type:.*javascript'; then ok "app.js served as JavaScript"; else bad "app.js not served as JavaScript"; fi
if curl -s -D - -o /dev/null -H 'Origin: http://127.0.0.1:5500' "$BASE/api/state" | grep -qi 'access-control-allow-origin'; then ok "CORS open for a separate static server"; else bad "CORS header missing"; fi
req "reset (leave it clean)"       200 POST /api/reset

echo
if "$PY" -c "import pytest" 2>/dev/null; then
  echo "unit tests ($PY -m pytest)"
  "$PY" -m pytest -q server/tests 2>&1 | tail -3 && ok "pytest" || bad "pytest"
else
  echo "(pytest not installed: skipping unit tests. pip install -r server/requirements.txt)"
fi

echo
echo "$pass passed, $fail failed"
[ "$fail" -eq 0 ]
