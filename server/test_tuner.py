"""Self-tuning silence tests. Run:  cd server && python -m pytest test_tuner.py -q"""
import json
import os
import random
import tempfile
from pathlib import Path

from tuner import Tuner

THR_LINE, THR_BLOCK = 0.40, 0.44


def new(**kw):
    return Tuner(THR_LINE, THR_BLOCK, rng=random.Random(0), **kw)


def feed(t, repo, p, outcome, n, start=0, is_block=False):
    for i in range(start, start + n):
        sid = f"{repo}-{i}"
        t.observe({"event": "shown", "sid": sid, "repo": repo, "p_good": p, "is_block": is_block})
        t.observe({"event": outcome, "sid": sid, "repo": repo, "p_good": p, "is_block": is_block})


def test_day_one_matches_frozen_gate_exactly():
    t = new(explore=0.0)
    for k in range(1, 100):
        p = k / 100
        assert t.decide("r", p, False)["show"] == (p >= THR_LINE)
        assert t.decide("r", p, True)["show"] == (p >= THR_BLOCK)


def test_learns_to_go_quiet_when_everything_is_rejected():
    t = new(explore=0.0)
    assert t.decide("noisy", 0.45, False)["show"]
    feed(t, "noisy", 0.45, "rejected", 200)
    assert not t.decide("noisy", 0.45, False)["show"]


def test_learns_to_speak_up_from_explored_accepts():
    t = new(explore=1.0)                          # always explore in the band, to make the test fast
    d = t.decide("good", 0.35, False)
    assert d["show"] and d["explore"]             # below the frozen threshold, shown as exploration
    feed(t, "good", 0.35, "accepted", 200)
    d = t.decide("good", 0.35, False)
    assert d["show"] and not d["explore"]         # now shown for real


def test_repos_learn_separately_but_share_a_prior():
    t = new(explore=0.0)
    feed(t, "a", 0.45, "rejected", 200)
    feed(t, "b", 0.45, "accepted", 200)
    assert not t.decide("a", 0.45, False)["show"]
    assert t.decide("b", 0.45, False)["show"]
    assert 0 < t.q("brand-new", 0.45, False) < 1   # unseen repo uses the user-level fit


def test_followed_overrides_rejected():
    t = new()
    t.observe({"event": "rejected", "sid": "x", "repo": "r", "p_good": 0.5})
    t.observe({"event": "followed", "sid": "x", "repo": "r", "p_good": 0.5})
    assert t.repos["r"].labels["x"][2] == 1.0


def test_events_without_sid_or_p_are_ignored():
    t = new()
    for e in ({"event": "accepted"}, {"event": "accepted", "sid": "s"}, {"event": "accepted", "p_good": "x", "sid": "s"}):
        t.observe(e)
    assert all(len(r.labels) == 0 for r in t.repos.values())


def test_rebuilds_same_state_from_log_file():
    live = new(explore=0.0)
    feed(live, "r", 0.45, "rejected", 120)
    log = Path(tempfile.mkdtemp()) / "events.jsonl"
    with log.open("w") as f:
        for i in range(120):
            for ev in ("shown", "rejected"):
                f.write(json.dumps({"event": ev, "sid": f"r-{i}", "repo": "r", "p_good": 0.45}) + "\n")
        f.write("not json\n")
    restored = new(explore=0.0)
    restored.load([log])
    assert abs(restored.q("r", 0.45, False) - live.q("r", 0.45, False)) < 0.02


def test_report_compares_tuned_and_frozen():
    t = new(explore=0.0)
    for i in range(300):
        p = 0.2 + 0.4 * (i % 10) / 10
        t.observe({"event": "shown" if p >= THR_LINE else "gated", "sid": f"s{i}", "repo": "r", "p_good": p})
        if p >= THR_LINE:
            t.observe({"event": "rejected", "sid": f"s{i}", "repo": "r", "p_good": p})
    rep = t.report("r")
    assert rep["labels"] > 0 and rep["frozen_gate"]["show_rate"] > rep["tuned"]["show_rate"]
    assert rep["calibration"]["ece"] is not None and rep["calibration"]["bins"]


# ---------------------------------------------------------------- through the real server ----
def test_server_end_to_end():
    tmp = Path(tempfile.mkdtemp())
    os.environ["QT_TOKEN_FILE"] = str(tmp / "token")
    import httpx
    from fastapi.testclient import TestClient

    import app as server
    server.TUNER = Tuner(THR_LINE, THR_BLOCK, explore=0.0, rng=random.Random(0))
    server.LOG_PATH = tmp / "events.jsonl"

    def fake_llama(request):                       # a confident-ish suggestion: p_good ~0.5
        return httpx.Response(200, json={"content": "a + b", "completion_probabilities": [{"logprob": -0.05}] * 3})
    server.client = httpx.AsyncClient(transport=httpx.MockTransport(fake_llama))
    http = TestClient(server.app, base_url="http://127.0.0.1:8000")
    h = {"X-QuietTab-Token": server.TOKEN, "Content-Type": "application/json"}
    body = {"prefix": "def add(a, b):\n    return ", "suffix": "\n", "repo": "abc123"}

    r = http.post("/complete", json=body, headers=h).json()
    assert r["show"] and r["q"] >= r["tau"]
    for i in range(300):                           # the developer rejects everything in this repo
        for ev in ("shown", "rejected"):
            http.post("/log", json={"event": ev, "sid": f"s{i}", "repo": "abc123", "p_good": r["p_good"]}, headers=h)
    r2 = http.post("/complete", json=body, headers=h).json()
    assert not r2["show"] and r2["q"] < r2["tau"]
    other = http.post("/complete", json={**body, "repo": "other"}, headers=h).json()
    assert other["q"] > r2["q"]                    # another repo is only partly affected (shared prior)
    rep = http.get("/calibration", params={"repo": "abc123"}, headers=h).json()
    assert rep["labels"] == 300 and rep["accept_rate_of_labeled"] == 0.0
    assert http.post("/complete", json={**body, "repo": "../etc"}, headers=h).status_code == 422


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
            print("ok", name)
