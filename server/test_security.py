"""Attack the server the way a web page, another program, or a bad request would.
Run:  cd server && python -m pytest test_security.py -q     (needs: pip install pytest)
No llama-server needed: a fake one records exactly what would reach the model."""
import json
import os
import tempfile
from pathlib import Path

TMP = Path(tempfile.mkdtemp())
os.environ["QT_TOKEN_FILE"] = str(TMP / "token")           # never touch your real token in tests
os.environ["QT_LLAMA_KEY_FILE"] = str(TMP / "no_llama_key")

import httpx                                                 # noqa: E402
from fastapi.testclient import TestClient                   # noqa: E402

import app as server                                         # noqa: E402
from guard import proof                                      # noqa: E402

SEEN = []                                                    # what the "model" received


def fake_llama(request: httpx.Request) -> httpx.Response:
    SEEN.append(json.loads(request.content))
    return httpx.Response(200, json={"content": "a + b", "completion_probabilities": [{"logprob": -0.05}]})


server.client = httpx.AsyncClient(transport=httpx.MockTransport(fake_llama))
server.LOG_PATH = TMP / "logs" / "events.jsonl"
server.LOG_PATH.parent.mkdir(exist_ok=True)
TOKEN = server.TOKEN
GOOD = {"X-QuietTab-Token": TOKEN, "Content-Type": "application/json"}
BODY = {"prefix": "def add(a, b):\n    return ", "suffix": "\n"}
http = TestClient(server.app, base_url="http://127.0.0.1:8000")


def post(path, body=BODY, headers=GOOD, **kw):
    SEEN.clear()
    data = body if isinstance(body, (bytes, str)) else json.dumps(body)
    return http.post(path, content=data, headers=headers, **kw)


def test_plugin_request_works():
    r = post("/complete")
    assert r.status_code == 200 and r.json()["text"] == "a + b"
    assert len(SEEN) == 1


def test_no_token_is_refused():
    assert post("/complete", headers={"Content-Type": "application/json"}).status_code == 401
    assert post("/stats/reset", headers={}).status_code == 401
    assert http.get("/stats").status_code == 401
    assert SEEN == []


def test_wrong_token_is_refused():
    assert post("/complete", headers={**GOOD, "X-QuietTab-Token": "guess"}).status_code == 401


def test_dns_rebinding_host_is_refused():
    assert post("/complete", headers={**GOOD, "Host": "attacker.test"}).status_code == 400
    assert post("/complete", headers={**GOOD, "Host": "attacker.test:8000"}).status_code == 400
    assert post("/complete", headers={**GOOD, "Host": "localhost:8000"}).status_code == 200


def test_browser_origin_is_refused_even_with_token():
    assert post("/complete", headers={**GOOD, "Origin": "https://evil.example"}).status_code == 403
    assert post("/log", {"event": "x"}, headers={**GOOD, "Origin": "null"}).status_code == 403
    assert SEEN == []


def test_huge_extra_item_never_reaches_model():
    big = {**BODY, "extra": [{"filename": "x.py", "text": "A" * 5_000_000}]}
    assert post("/complete", big).status_code == 413          # stopped at the door, before JSON parsing
    assert SEEN == []


def test_extra_item_limits_and_unknown_keys():
    assert post("/complete", {**BODY, "extra": [{"filename": "x.py", "text": "A" * 4001}]}).status_code == 422
    assert post("/complete", {**BODY, "extra": [{"filename": "x.py", "text": "ok", "evil_key": 1}]}).status_code == 422
    r = post("/complete", {**BODY, "extra": [{"filename": "x.py", "text": "def f(): ..."}]})
    assert r.status_code == 200
    assert SEEN[0]["input_extra"] == [{"filename": "x.py", "text": "def f(): ...\n"}]   # only these 2 keys


def test_chunked_body_without_length_is_capped():
    def gen():
        for _ in range(400):
            yield b"A" * 1024                                  # 400 KB, no content-length header
    SEEN.clear()
    r = http.post("/complete", content=gen(), headers=GOOD)
    assert r.status_code == 413 and SEEN == []


def test_log_event_size_capped_and_logging_never_stops():
    assert post("/log", {"junk": "B" * 100_000}).status_code == 413
    old_max = server.LOG_MAX_BYTES
    server.LOG_MAX_BYTES = 2_000
    try:
        for i in range(150):
            assert post("/log", {"event": "shown", "i": i, "pad": "x" * 50}).json() == {"ok": True}
        files = sorted(p.name for p in server.LOG_PATH.parent.glob("events*.jsonl"))
        assert files == ["events.1.jsonl", "events.2.jsonl", "events.3.jsonl", "events.jsonl"]
        assert all(p.stat().st_size <= 2_000 for p in server.LOG_PATH.parent.glob("events*.jsonl"))
    finally:
        server.LOG_MAX_BYTES = old_max


def test_wrong_types_give_422_not_500():
    assert post("/complete", {"prefix": 5, "suffix": [], "extra": "x"}).status_code == 422
    assert post("/complete", b"{not json").status_code == 422


def test_health_proves_identity_without_token():
    r = http.get("/health", params={"nonce": "abc123"})
    assert r.status_code == 200 and r.json()["proof"] == proof(TOKEN, "abc123")
    assert r.json()["proof"] != proof("some-other-token", "abc123")


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
            print("ok", name)
