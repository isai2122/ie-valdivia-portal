#!/usr/bin/env bash
# Smoke Fase 1 — cubre criterios 1..12 del prompt.
set -euo pipefail

BASE="${API_BASE:-http://localhost:8001}"
pass() { printf "  \033[32m✓\033[0m %s\n" "$1"; }
fail() { printf "  \033[31m✗\033[0m %s\n" "$1"; exit 1; }

# ---- helpers ----
hdr_status() { curl -s -o /tmp/r.json -w "%{http_code}" "$@"; }
json()       { python3 -c "import sys,json;d=json.load(open('/tmp/r.json'));$1"; }

# login helper
login_as() {
  local email="$1"; local pass="$2"
  curl -s -X POST "$BASE/api/auth/login" \
    -H "Content-Type: application/json" \
    -d "{\"email\":\"$email\",\"password\":\"$pass\"}" \
    | python3 -c "import sys,json;print(json.load(sys.stdin)['access_token'])"
}

echo "=== Fase 0 baseline ==="
[ "$(hdr_status "$BASE/api/health")" = "200" ] && pass "health"      || fail "health"
TOKEN_ADMIN=$(login_as "admin@metanosrgan.co" "Admin123!")
[ -n "$TOKEN_ADMIN" ] && pass "login admin"                          || fail "login admin"
TOKEN_ANALYST=$(login_as "analista@metanosrgan.co" "Analista123!")
TOKEN_VIEWER=$(login_as "visor@metanosrgan.co" "Visor123!")

A="-H 'Authorization: Bearer $TOKEN_ADMIN'"

echo
echo "=== 1. /api/docs lista endpoints ==="
[ "$(hdr_status "$BASE/api/docs")" = "200" ] && pass "docs" || fail "docs"

echo
echo "=== 2. stations — requiere auth ==="
[ "$(hdr_status "$BASE/api/stations")" = "401" ] && pass "stations unauth 401" || fail "stations unauth"
[ "$(hdr_status -H "Authorization: Bearer $TOKEN_ADMIN" "$BASE/api/stations")" = "200" ] && pass "stations authed" || fail "stations authed"
n=$(json "print(len(d))"); [ "$n" = "5" ] && pass "stations=5" || fail "stations count $n"
# verifica campos nuevos
json "assert 'capacity_mmscfd' in d[0] and 'installation_year' in d[0] and 'risk_level' in d[0]" && pass "stations nuevos campos"

echo
echo "=== 3. wells ≥ 25 ==="
hdr_status -H "Authorization: Bearer $TOKEN_VIEWER" "$BASE/api/wells?limit=500" >/dev/null
n=$(json "print(len(d))"); [ "$n" -ge 25 ] && pass "wells=$n" || fail "wells only $n"

echo
echo "=== 4. pipelines ≥ 6 y LineString válidos ==="
hdr_status -H "Authorization: Bearer $TOKEN_VIEWER" "$BASE/api/pipelines" >/dev/null
n=$(json "print(len(d))"); [ "$n" -ge 6 ] && pass "pipelines=$n" || fail "pipelines=$n"
json "assert all(isinstance(p['coordinates'],list) and len(p['coordinates'])>=2 and all(len(c)==2 for c in p['coordinates']) for p in d)" && pass "linestrings ok"

echo
echo "=== 5. detections ≥ 60 con X-Total-Count y plume_geojson ≥ 80% ==="
total=$(curl -s -o /tmp/r.json -D /tmp/h.txt -H "Authorization: Bearer $TOKEN_VIEWER" "$BASE/api/detections?limit=10" -w "%{http_code}")
[ "$total" = "200" ] && pass "detections 200" || fail "detections $total"
xtc=$(grep -i '^x-total-count' /tmp/h.txt | tr -d '\r\n' | awk '{print $2}')
[ "${xtc:-0}" -ge 60 ] && pass "X-Total-Count=$xtc" || fail "X-Total-Count=$xtc"
# Bajamos 200 y medimos proporción con plume
curl -s -H "Authorization: Bearer $TOKEN_VIEWER" "$BASE/api/detections?limit=200" -o /tmp/r.json
json "items=d; n=len(items); p=sum(1 for x in items if x.get('plume_geojson')); print(f'PLUME={p}/{n}'); assert p/n >= 0.8, (p,n)"
pass "plume_geojson cover ≥ 80%"

echo
echo "=== 6. detections severity=critical ==="
hdr_status -H "Authorization: Bearer $TOKEN_VIEWER" "$BASE/api/detections?severity=critical&limit=200" >/dev/null
json "assert all(x['severity']=='critical' for x in d), set(x['severity'] for x in d)" && pass "all critical"

echo
echo "=== 7. wind ahora → grid 100 ==="
NOW=$(python3 -c "from datetime import datetime,timezone; print(datetime.now(timezone.utc).isoformat().replace('+00:00','Z'))")
hdr_status -H "Authorization: Bearer $TOKEN_VIEWER" "$BASE/api/wind?at=$NOW" >/dev/null
g=$(json "print(len(d['grid']))"); [ "$g" = "100" ] && pass "wind grid=100" || fail "wind grid=$g"

echo
echo "=== 8. alerts?acknowledged=false ≥ 1 ==="
hdr_status -H "Authorization: Bearer $TOKEN_VIEWER" "$BASE/api/alerts?acknowledged=false&limit=200" >/dev/null
n=$(json "print(len(d))"); [ "$n" -ge 1 ] && pass "alerts unack=$n" || fail "alerts unack=$n"

echo
echo "=== 9. POST ack con analyst ==="
# pick un alert unack
hdr_status -H "Authorization: Bearer $TOKEN_VIEWER" "$BASE/api/alerts?acknowledged=false&limit=1" >/dev/null
AID=$(json "print(d[0]['id'])")
code=$(curl -s -o /tmp/r.json -w "%{http_code}" -X POST \
  -H "Authorization: Bearer $TOKEN_ANALYST" "$BASE/api/alerts/$AID/ack")
[ "$code" = "200" ] && pass "ack 200" || fail "ack $code"
curl -s -H "Authorization: Bearer $TOKEN_VIEWER" "$BASE/api/alerts/$AID" -o /tmp/r.json
json "assert d['acknowledged'] is True and d['acknowledged_by']" && pass "ack persistido"

echo
echo "=== 10. inference/jobs: POST file, polling hasta done ==="
echo "dummy-netcdf-content" > /tmp/dummy.nc
code=$(curl -s -o /tmp/r.json -w "%{http_code}" -X POST \
  -H "Authorization: Bearer $TOKEN_ANALYST" \
  -F "file=@/tmp/dummy.nc" "$BASE/api/inference/jobs")
[ "$code" = "200" ] && pass "inference job queued" || fail "inference $code"
json "assert d['runner']=='demo-synthetic' and 'warning' in d and d['status']=='queued'" && pass "runner=demo-synthetic + warning"
JID=$(json "print(d['job_id'])")
# poll hasta ~12s
for i in $(seq 1 8); do
  sleep 2
  hdr_status -H "Authorization: Bearer $TOKEN_ANALYST" "$BASE/api/inference/jobs/$JID" >/dev/null
  st=$(json "print(d['status'])")
  [ "$st" = "done" ] && break
done
[ "$st" = "done" ] && pass "job done" || fail "job status=$st"
json "ids=d['output_detection_ids']; assert 1<=len(ids)<=3, ids" && pass "1-3 detections"

echo
echo "=== 11. WS conecta, sin token close 1008, con token mensaje <100s ==="
python3 - "$BASE" "$TOKEN_VIEWER" <<'PY'
import asyncio, json, sys, time, urllib.parse
import websockets

base = sys.argv[1]
ws_base = base.replace("http://","ws://").replace("https://","wss://")
tok = sys.argv[2]

async def main():
    # sin token
    try:
        async with websockets.connect(f"{ws_base}/api/ws/alerts") as ws:
            await ws.recv()
            print("FAIL: ws without token should close")
            sys.exit(1)
    except Exception as e:
        print("  ✓ ws without token closed:", type(e).__name__)

    # con token — esperar alert.created en <100s
    url = f"{ws_base}/api/ws/alerts?token={urllib.parse.quote(tok)}"
    async with websockets.connect(url, ping_interval=None) as ws:
        welcome = json.loads(await ws.recv())
        assert welcome.get("type") == "welcome", welcome
        print("  ✓ welcome:", welcome.get("user"))
        t0 = time.time()
        got_alert = False
        while time.time() - t0 < 100:
            try:
                msg = await asyncio.wait_for(ws.recv(), timeout=100 - (time.time()-t0))
            except asyncio.TimeoutError:
                break
            data = json.loads(msg)
            if data.get("type") == "alert.created":
                print(f"  ✓ received alert.created at t+{int(time.time()-t0)}s sev={data['alert']['severity']}")
                got_alert = True
                break
        assert got_alert, "no alert received in 100s"
asyncio.run(main())
PY
pass "WS test passed"

echo
echo "=== 12. stats/overview ==="
hdr_status -H "Authorization: Bearer $TOKEN_VIEWER" "$BASE/api/stats/overview" >/dev/null
json "expected={'total_detections','detections_last_24h','active_alerts','critical_alerts','stations_count','avg_ppb_last_7d','detections_by_severity','detections_timeseries_30d'}; missing=expected - set(d.keys()); assert not missing, missing" && pass "overview fields"
json "assert len(d['detections_timeseries_30d'])==30" && pass "timeseries 30"

echo
echo "All smoke tests passed ✅"
