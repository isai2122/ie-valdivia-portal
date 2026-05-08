"""
MetanoSRGAN Elite v5.5 — Backend regression suite
Coverage: auth, health, v55 info, admin CRUD, carbon credits, compliance,
exports, api keys, webhooks, audit chain, analytics, websocket, v5.4 endpoints
"""
import os
import json
import time
import pytest
import requests

BASE_URL = os.environ.get(
    "REACT_APP_BACKEND_URL",
    "https://wingman-29b255c3-66da-47d4-b4ef-fc21ee142b5a.preview.emergentagent.com",
).rstrip("/")

ADMIN_EMAIL = "ortizisacc18@gmail.com"
ADMIN_USER = "ortizisacc18"
ADMIN_PASS = "212228IsaiJosias@"


# ───────────── Fixtures ─────────────
@pytest.fixture(scope="session")
def api():
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    return s


@pytest.fixture(scope="session")
def admin_token(api):
    r = api.post(
        f"{BASE_URL}/api/auth/login",
        json={"username": ADMIN_EMAIL, "password": ADMIN_PASS},
        timeout=30,
    )
    assert r.status_code == 200, f"Login failed: {r.status_code} {r.text}"
    return r.json()["access_token"]


@pytest.fixture(scope="session")
def admin_client(api, admin_token):
    s = requests.Session()
    s.headers.update(
        {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {admin_token}",
        }
    )
    return s


# ───────────── 1. Auth ─────────────
class TestAuth:
    def test_login_with_email(self, api):
        r = api.post(
            f"{BASE_URL}/api/auth/login",
            json={"username": ADMIN_EMAIL, "password": ADMIN_PASS},
            timeout=30,
        )
        assert r.status_code == 200
        d = r.json()
        assert "access_token" in d and len(d["access_token"]) > 20
        assert "refresh_token" in d and len(d["refresh_token"]) > 20
        assert d["user"]["role"] == "admin"
        assert d["user"]["username"] == ADMIN_USER

    def test_login_with_username(self, api):
        r = api.post(
            f"{BASE_URL}/api/auth/login",
            json={"username": ADMIN_USER, "password": ADMIN_PASS},
            timeout=30,
        )
        assert r.status_code == 200
        d = r.json()
        assert "access_token" in d
        assert d["user"]["username"] == ADMIN_USER

    def test_login_invalid_password(self, api):
        r = api.post(
            f"{BASE_URL}/api/auth/login",
            json={"username": ADMIN_USER, "password": "wrong"},
            timeout=30,
        )
        assert r.status_code in (401, 403, 400)


# ───────────── 2. Health & Info ─────────────
class TestHealthInfo:
    def test_health(self, api):
        r = api.get(f"{BASE_URL}/api/health", timeout=15)
        assert r.status_code == 200
        d = r.json()
        assert d["version"] == "5.5.0"
        assert d["database"] == "supabase"

    def test_v55_info(self, api):
        r = api.get(f"{BASE_URL}/api/v55/info", timeout=15)
        assert r.status_code == 200
        d = r.json()
        # Should advertise the 9 new capabilities
        text = json.dumps(d).lower()
        for kw in [
            "carbon",
            "compliance",
            "export",
            "key",
            "webhook",
            "audit",
            "comparativas",  # historical analytics key
            "websocket",
            "admin",
        ]:
            assert kw in text, f"Missing capability keyword: {kw}"


# ───────────── 3. Admin protection ─────────────
class TestAdminProtection:
    @pytest.mark.parametrize(
        "method,endpoint",
        [
            ("GET", "/api/admin/stats"),
            ("GET", "/api/admin/users"),
            ("POST", "/api/admin/users"),
            ("GET", "/api/admin/audit-log"),
        ],
    )
    def test_unauth_blocked(self, api, method, endpoint):
        r = api.request(method, f"{BASE_URL}{endpoint}", json={}, timeout=15)
        assert r.status_code in (401, 403), f"{endpoint} returned {r.status_code}"


# ───────────── 4. Admin CRUD ─────────────
class TestAdminCRUD:
    def test_admin_stats(self, admin_client):
        r = admin_client.get(f"{BASE_URL}/api/admin/stats", timeout=20)
        assert r.status_code == 200
        d = r.json()
        # Should have a user count somewhere
        text = json.dumps(d).lower()
        assert "user" in text or "total" in text

    def test_admin_users_list(self, admin_client):
        r = admin_client.get(f"{BASE_URL}/api/admin/users", timeout=20)
        assert r.status_code == 200
        d = r.json()
        assert isinstance(d, (list, dict))

    def test_admin_user_full_lifecycle(self, admin_client):
        uname = f"TEST_user_{int(time.time())}"
        # CREATE
        r = admin_client.post(
            f"{BASE_URL}/api/admin/users",
            json={
                "username": uname,
                "password": "TempPass123!",
                "email": f"{uname}@test.com",
                "role": "viewer",
                "full_name": "Test User",
            },
            timeout=20,
        )
        assert r.status_code in (200, 201), f"create failed {r.status_code} {r.text}"

        # UPDATE
        r2 = admin_client.put(
            f"{BASE_URL}/api/admin/users/{uname}",
            json={"full_name": "Updated User", "role": "viewer"},
            timeout=20,
        )
        assert r2.status_code in (200, 204), f"update {r2.status_code} {r2.text}"

        # RESET PASSWORD
        r3 = admin_client.post(
            f"{BASE_URL}/api/admin/users/{uname}/reset-password",
            json={"new_password": "NewPass456!"},
            timeout=20,
        )
        assert r3.status_code in (200, 204), f"reset {r3.status_code} {r3.text}"

        # TOGGLE
        r4 = admin_client.post(
            f"{BASE_URL}/api/admin/users/{uname}/toggle", timeout=20
        )
        assert r4.status_code in (200, 204), f"toggle {r4.status_code} {r4.text}"

        # DELETE
        r5 = admin_client.delete(f"{BASE_URL}/api/admin/users/{uname}", timeout=20)
        assert r5.status_code in (200, 204), f"delete {r5.status_code} {r5.text}"

    def test_admin_audit_log(self, admin_client):
        r = admin_client.get(f"{BASE_URL}/api/admin/audit-log", timeout=20)
        assert r.status_code == 200


# ───────────── 5. Carbon Credits ─────────────
class TestCarbon:
    def test_carbon_credits(self, admin_client):
        r = admin_client.get(f"{BASE_URL}/api/v55/carbon/credits", timeout=30)
        assert r.status_code == 200, r.text
        d = r.json()
        text = json.dumps(d).lower()
        # IPCC AR6 GWP 29.8 must be present
        assert "29.8" in text or "gwp" in text
        assert "total_co2e_ton_year" in text or "co2e" in text
        assert "creditos_verra_usd" in text or "verra" in text
        assert "creditos_gold_standard_usd" in text or "gold" in text
        assert "valor_eu_ets_usd" in text or "eu_ets" in text


# ───────────── 6. Compliance ─────────────
class TestCompliance:
    def test_normativas(self, admin_client):
        r = admin_client.get(f"{BASE_URL}/api/v55/compliance/normativas", timeout=20)
        assert r.status_code == 200
        text = json.dumps(r.json()).lower()
        for k in ["epa_ooooa_b", "eu_mrr", "co_rua_pi", "ogmp_2_0_gold", "wb_gmfr"]:
            assert k in text, f"missing normativa {k}"

    def test_summary(self, admin_client):
        r = admin_client.get(f"{BASE_URL}/api/v55/compliance/summary", timeout=20)
        assert r.status_code == 200

    def test_violations(self, admin_client):
        r = admin_client.get(f"{BASE_URL}/api/v55/compliance/violations", timeout=20)
        assert r.status_code == 200


# ───────────── 7. Exports ─────────────
class TestExports:
    def test_csv(self, admin_client):
        r = admin_client.get(f"{BASE_URL}/api/v55/export/csv", timeout=30)
        assert r.status_code == 200
        ct = r.headers.get("content-type", "").lower()
        assert "csv" in ct or "text" in ct

    def test_excel(self, admin_client):
        r = admin_client.get(f"{BASE_URL}/api/v55/export/excel", timeout=30)
        assert r.status_code == 200
        ct = r.headers.get("content-type", "").lower()
        assert "spreadsheet" in ct or "xlsx" in ct or "excel" in ct or "octet" in ct

    def test_pdf(self, admin_client):
        r = admin_client.get(f"{BASE_URL}/api/v55/export/pdf", timeout=30)
        assert r.status_code == 200
        ct = r.headers.get("content-type", "").lower()
        assert "pdf" in ct


# ───────────── 8. API Keys ─────────────
class TestApiKeys:
    created_id = None

    def test_keys_lifecycle(self, admin_client):
        # LIST
        r = admin_client.get(f"{BASE_URL}/api/v55/keys", timeout=20)
        assert r.status_code == 200

        # CREATE
        r2 = admin_client.post(
            f"{BASE_URL}/api/v55/keys",
            json={"name": "TEST_key", "scopes": ["read:detections"]},
            timeout=20,
        )
        assert r2.status_code in (200, 201), r2.text
        d = r2.json()
        key_id = (
            d.get("id")
            or d.get("key_id")
            or d.get("api_key", {}).get("id")
            or d.get("data", {}).get("id")
        )
        # Try alt: list & pick last
        if not key_id:
            lst = admin_client.get(f"{BASE_URL}/api/v55/keys", timeout=20).json()
            items = lst if isinstance(lst, list) else lst.get("keys") or lst.get("data") or []
            if items:
                key_id = items[-1].get("id") or items[-1].get("key_id")

        # DELETE
        if key_id:
            r3 = admin_client.delete(f"{BASE_URL}/api/v55/keys/{key_id}", timeout=20)
            assert r3.status_code in (200, 204, 404)


# ───────────── 9. Webhooks ─────────────
class TestWebhooks:
    def test_webhook_lifecycle(self, admin_client):
        r = admin_client.get(f"{BASE_URL}/api/v55/webhooks", timeout=20)
        assert r.status_code == 200

        r2 = admin_client.post(
            f"{BASE_URL}/api/v55/webhooks",
            json={
                "url": "https://example.com/hook",
                "events": ["detection.created"],
                "name": "TEST_hook",
            },
            timeout=20,
        )
        assert r2.status_code in (200, 201), r2.text
        d = r2.json()
        wid = d.get("id") or d.get("webhook_id") or d.get("data", {}).get("id")
        if not wid:
            lst = admin_client.get(f"{BASE_URL}/api/v55/webhooks", timeout=20).json()
            items = (
                lst if isinstance(lst, list) else lst.get("webhooks") or lst.get("data") or []
            )
            if items:
                wid = items[-1].get("id") or items[-1].get("webhook_id")
        if wid:
            r3 = admin_client.delete(f"{BASE_URL}/api/v55/webhooks/{wid}", timeout=20)
            assert r3.status_code in (200, 204, 404)


# ───────────── 10. Audit chain ─────────────
class TestAuditChain:
    def test_chain_integrity(self, admin_client):
        r = admin_client.get(f"{BASE_URL}/api/v55/audit/chain", timeout=30)
        assert r.status_code == 200
        d = r.json()
        v = d.get("verificacion") or d.get("verification") or {}
        # Must report integro=true
        integro = v.get("integro", v.get("integrity", v.get("valid")))
        assert integro is True, f"chain not integro: {v}"


# ───────────── 11. Analytics ─────────────
class TestAnalytics:
    def test_by_period_month(self, admin_client):
        r = admin_client.get(
            f"{BASE_URL}/api/v55/analytics/by-period?kind=month", timeout=20
        )
        assert r.status_code == 200

    def test_by_asset(self, admin_client):
        r = admin_client.get(f"{BASE_URL}/api/v55/analytics/by-asset", timeout=20)
        assert r.status_code == 200


# ───────────── 12. WebSocket heartbeat ─────────────
class TestWebSocket:
    def test_ws_heartbeat(self):
        try:
            from websockets.sync.client import connect
        except Exception:
            pytest.skip("websockets lib not installed")
        ws_url = BASE_URL.replace("https://", "wss://").replace("http://", "ws://") + "/api/ws/live"
        try:
            with connect(ws_url, open_timeout=10, close_timeout=5) as ws:
                msg = ws.recv(timeout=15)
                d = json.loads(msg)
                assert d.get("type") == "heartbeat" or "heartbeat" in json.dumps(d).lower()
        except Exception as e:
            pytest.fail(f"WS connection failed: {e}")


# ───────────── 13. v5.4 Existing endpoints ─────────────
class TestV54Endpoints:
    @pytest.mark.parametrize(
        "endpoint",
        [
            "/api/status",
            "/api/detections",
            "/api/detections/map",
            "/api/detections/latest",
            "/api/dashboard/summary",
            "/api/tickets",
            "/api/ml/status",
            "/api/ml/predictions",
            "/api/tropomi/status",
            "/api/supabase/status",
        ],
    )
    def test_v54_endpoint(self, api, endpoint):
        r = api.get(f"{BASE_URL}{endpoint}", timeout=30)
        assert r.status_code == 200, f"{endpoint} -> {r.status_code} {r.text[:200]}"
