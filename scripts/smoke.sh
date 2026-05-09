#!/usr/bin/env bash
# Smoke test mínimo de la API (Fase 0). Usa el backend local via :8001
# porque es más rápido; la URL externa también funciona (REACT_APP_BACKEND_URL).
set -euo pipefail

BASE="${API_BASE:-http://localhost:8001}"

pass() { printf "  \033[32m✓\033[0m %s\n" "$1"; }
fail() { printf "  \033[31m✗\033[0m %s\n" "$1"; exit 1; }

echo "▶ /api/health"
code=$(curl -s -o /tmp/smoke.json -w "%{http_code}" "$BASE/api/health")
[ "$code" = "200" ] || fail "health returned $code"
grep -q '"status":"ok"' /tmp/smoke.json || fail "health body unexpected"
pass "health ok"

echo "▶ /api/auth/login (admin)"
code=$(curl -s -o /tmp/smoke.json -w "%{http_code}" -X POST "$BASE/api/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@metanosrgan.co","password":"Admin123!"}')
[ "$code" = "200" ] || fail "login admin returned $code"
TOKEN=$(python3 -c "import sys,json;print(json.load(open('/tmp/smoke.json'))['access_token'])")
[ -n "$TOKEN" ] || fail "no token"
pass "login admin ok"

echo "▶ /api/auth/login (wrong password)"
code=$(curl -s -o /dev/null -w "%{http_code}" -X POST "$BASE/api/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@metanosrgan.co","password":"wrong"}')
[ "$code" = "401" ] || fail "wrong login returned $code (expected 401)"
pass "wrong login rejected"

echo "▶ /api/auth/me"
code=$(curl -s -o /tmp/smoke.json -w "%{http_code}" "$BASE/api/auth/me" \
  -H "Authorization: Bearer $TOKEN")
[ "$code" = "200" ] || fail "me returned $code"
grep -q '"role":"admin"' /tmp/smoke.json || fail "me body wrong role"
pass "me ok"

echo "▶ /api/auth/me (no token)"
code=$(curl -s -o /dev/null -w "%{http_code}" "$BASE/api/auth/me")
[ "$code" = "401" ] || fail "me without token returned $code"
pass "me rejects unauth"

echo "▶ /api/stations (con token)"
code=$(curl -s -o /tmp/smoke.json -w "%{http_code}" "$BASE/api/stations" \
  -H "Authorization: Bearer $TOKEN")
[ "$code" = "200" ] || fail "stations returned $code"
count=$(python3 -c "import sys,json;print(len(json.load(open('/tmp/smoke.json'))))")
[ "$count" = "5" ] || fail "expected 5 stations, got $count"
pass "stations returned 5 items"

echo
echo "All smoke tests passed ✅"
