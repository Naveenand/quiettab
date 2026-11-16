import asyncio
from collections import deque
import json
import math
import os
import time
from pathlib import Path


import httpx
from fastapi import FastAPI, Request, Response
from pydantic import BaseModel, ConfigDict, Field

from cleanup import clean
from guard import Guard, load_or_create_token, proof
from secguard import check_suggestion, redact, redact_event, secret_near_cursor
from tuner import Tuner

LOG_PATH = Path(__file__).parent / "logs" / "events.jsonl"
LOG_PATH.parent.mkdir(exist_ok=True)
DEBUG = os.getenv("QT_DEBUG") == "1"
PROMPT_LOG = LOG_PATH.parent / "prompts.jsonl"
LOG_MAX_BYTES, LOG_KEEP = 50_000_000, 3     # events.jsonl -> events.1.jsonl ... events.3.jsonl

LLAMA_URL = os.getenv("QT_LLAMA_URL", "http://127.0.0.1:8012/infill")
# llama-server started with --api-key: put the same key in this file (see HOW_TO_RUN.md)
_key_file = Path(os.getenv("QT_LLAMA_KEY_FILE", Path.home() / ".quiettab" / "llama_key"))
LLAMA_HEADERS = {"Authorization": f"Bearer {_key_file.read_text().strip()}"} if _key_file.exists() else {}

# NEW (Step 7): load the confidence gate trained by eval/train_gate.py
GATE_PATH = Path(__file__).parent / "gate.json"
GATE = json.loads(GATE_PATH.read_text()) if GATE_PATH.exists() else None

# Self-tuning silence (tuner.py): starts equal to the frozen gate, then learns per repo from accept/reject.
# QT_TUNER=0 turns it off (frozen gate only). QT_TAU = minimum chance of acceptance to show (higher = quieter).
TUNER = None
if GATE and os.getenv("QT_TUNER", "1") != "0":
    TUNER = Tuner(GATE["threshold"], GATE.get("block_threshold", GATE["threshold"]),
                  tau=float(os.getenv("QT_TAU", "0.30")), explore=float(os.getenv("QT_EXPLORE", "0.05")))
    TUNER.load([LOG_PATH.with_name(f"events.{i}.jsonl") for i in range(LOG_KEEP, 0, -1)] + [LOG_PATH])

TOKEN = load_or_create_token()
app = FastAPI()
app.add_middleware(Guard, token=TOKEN)      # host check, no browsers, token, body size (see guard.py)
client = httpx.AsyncClient(timeout=1.0)     # same 1 s budget as the plugin

# Fix 11: count suggestions we stopped early, and model failures

# Fix 11: count suggestions we stopped early, and model failures
STATS = {"cancelled": 0, "llama_errors": 0}
# Fix 12: llama.cpp timings of recent model calls: (prompt tokens read fresh, prompt ms, generate ms, tokens reused from cache)
RECENT = deque(maxlen=200)


async def ask_llama(request: Request, payload: dict):
    """Call llama-server, but stop it if the plugin hangs up first (= the user typed again)."""
    async def call():
        r = await client.post(LLAMA_URL, json=payload, headers=LLAMA_HEADERS)
        r.raise_for_status()
        return r.json()

    async def hung_up():
        while not await request.is_disconnected():
            await asyncio.sleep(0.02)

    llama, gone = asyncio.create_task(call()), asyncio.create_task(hung_up())
    done, _ = await asyncio.wait({llama, gone}, return_when=asyncio.FIRST_COMPLETED)
    if llama not in done:            # plugin gave up -> cancel = close connection -> llama stops too
        llama.cancel()
        STATS["cancelled"] += 1
        return None
    gone.cancel()
    try:
        return llama.result()
    except Exception as e:           # llama down / timeout / bad reply: say why instead of a bare 500
        STATS["llama_errors"] += 1
        print(f"[quiettab] llama error: {type(e).__name__}: {e}", flush=True)
        return None

@app.get("/health")
async def health(nonce: str = ""):
    """Open without a token. The plugin checks `proof` to be sure it's talking to the real server."""
    return {"ok": True, "proof": proof(TOKEN, nonce)}

@app.get("/stats")
async def stats():
    def pct(i, q):
        v = sorted(r[i] for r in RECENT if r[i] is not None)
        return round(v[min(len(v) - 1, int(q * len(v)))], 1) if v else None
    return {**STATS, "calls": len(RECENT),
            "prompt_tokens_p50": pct(0, 0.5), "prompt_tokens_p90": pct(0, 0.9),   # tokens llama had to READ (lower = better cache use)
            "prompt_ms_p50": pct(1, 0.5), "prompt_ms_p90": pct(1, 0.9),
            "gen_ms_p50": pct(2, 0.5), "gen_ms_p90": pct(2, 0.9),
            "cached_tokens_p50": pct(3, 0.5)}                                     # tokens reused from the last request


@app.post("/stats/reset")
async def stats_reset():
    RECENT.clear()
    STATS.update(cancelled=0, llama_errors=0)
    return {"ok": True}



class ExtraItem(BaseModel):
    """One cheat-sheet entry. Only these two fields ever reach llama.cpp."""
    model_config = ConfigDict(extra="forbid")
    filename: str = Field("", max_length=256)
    text: str = Field("", max_length=4000)


class CompleteRequest(BaseModel):
    prefix: str = Field(max_length=8000)
    suffix: str = Field(max_length=4000)
    max_tokens: int = Field(64, ge=1, le=128)
    extra: list[ExtraItem] = Field(default_factory=list, max_length=8)
    repo: str = Field("", max_length=64, pattern=r"^[A-Za-z0-9_\-]*$")   # hashed project id (self-tuning silence)



def token_logprob(t: dict) -> float:
    # llama.cpp versions differ: some return "logprob", older ones return "probs"
    if "logprob" in t:
        return t["logprob"]
    return math.log(max(t["probs"][0]["prob"], 1e-9))


# NEW (Step 7): probability that a suggestion is good, using whatever features the gate was trained on
def p_good(avg, mn, text, single_line, has_extra):
    if GATE is None or avg is None:
        return None
    feats = {"avg_logprob": avg, "min_logprob": mn, "log_len": math.log1p(len(text)),
             "single_line": float(single_line), "has_extra": float(has_extra)}
    z = GATE["intercept"] + sum(w * feats[f] for f, w in zip(GATE["features"], GATE["coef"]))
    return 1 / (1 + math.exp(-z))


@app.post("/complete")
async def complete(req: CompleteRequest, request: Request):
    start = time.perf_counter()
    current_line = req.prefix.rsplit("\n", 1)[-1]      # text before the cursor on this line
    single_line = current_line.strip() != ""            # typing mid-line?
    stop = ["\n"] if single_line else ["\n\n", "\ndef ", "\nclass "]
    max_tokens = 32 if single_line else req.max_tokens
    # 0. Security gate, input side: secrets never reach the model or the logs (secguard.py)
    if secret_near_cursor(req.prefix, req.suffix) is not None:
        return {"text": "", "raw_text": "", "show": False, "security": "secret_near_cursor",
                "single_line": single_line, "latency_ms": round((time.perf_counter() - start) * 1000)}
    prefix, found = redact(req.prefix)
    suffix, found_s = redact(req.suffix)
    extra = []
    for e in req.extra:
        e_text, found_e = redact(e.text)
        found += found_e
        extra.append({"filename": e.filename, "text": e_text.rstrip("\n") + "\n"})
    found += found_s

    # 1. Ask the model (only llama.cpp settings go here)
    data = await ask_llama(request, payload={
        "input_prefix": req.prefix,
        "input_suffix": req.suffix,
        "n_predict": max_tokens,
        "temperature": 0,        # same input -> same suggestion
        "n_probs": 1,            # also return confidence per token
        "cache_prompt": True,    # reuse work from the last request
        "stop": stop,
        "input_extra": extra,    # cheat sheet: signatures from other files
    })
    if data is None or not isinstance(data.get("content"), str):   # plugin hung up, or llama failed / odd reply
        return Response(status_code=503)
    t = data.get("timings") or {}
    RECENT.append((t.get("prompt_n"), t.get("prompt_ms"), t.get("predicted_ms"), t.get("cache_n", data.get("tokens_cached"))))

    if DEBUG:
        prompt = data.get("prompt") or ""
        with PROMPT_LOG.open("a") as f:
            f.write(json.dumps({
                "prompt": prompt,                                   # exactly what the model saw
                "tokens_evaluated": data.get("tokens_evaluated"),
                "truncated": data.get("truncated"),
                "extra": req.extra,
                "prefix_cut": req.prefix[:100] not in prompt,       # top of file lost?
                "extra_dropped": sum(e.get("text", "")[:100] not in prompt for e in req.extra),
                "raw_text": data["content"],
            }) + "\n")

    # 2. Confidence from per-token logprobs
    logprobs = [token_logprob(t) for t in data.get("completion_probabilities", [])]
    avg = sum(logprobs) / len(logprobs) if logprobs else None
    mn = min(logprobs) if logprobs else None

    # 3. Clean the text, then ask the gate (NEW, Step 7)
    text = clean(data["content"], prefix, suffix, single_line)
    p = p_good(avg, mn, text, single_line, bool(req.extra))

    is_block = "\n" in text            # the SUGGESTION has several lines
    thr = None

    if GATE:
        thr = GATE.get("block_threshold", GATE["threshold"]) if is_block else GATE["threshold"]

    # 3b. Security gate, output side: never suggest secrets or known-dangerous code
    above = "\n".join(prefix.split("\n")[-6:-1])          # a few lines above, to understand a match
    blocked, warnings = check_suggestion(text, current_line, context=above)
    raw_text = redact(data["content"])[0]
    if blocked:
        text, raw_text = "", ""        # don't even send it to the plugin

    # 3c. Show or stay quiet: the self-tuning gate if on, else the frozen gate
    if TUNER and p is not None and not blocked:
        decision = TUNER.decide(req.repo, p, is_block)
    else:
        decision = {"show": not blocked and ((p >= thr) if p is not None else GATE is None),   # no confidence -> quiet
                    "q": None, "tau": None, "explore": False}

        # 4. Reply to the plugin
    return {
        "q": decision["q"],                                # tuned chance YOU accept it (None = tuner off)
        "tau": decision["tau"],                            # show when q >= tau
        "explore": decision["explore"],                    # shown just below tau, so the gate keeps learning
        "text": text,
        "raw_text": raw_text,
        "security": blocked,                               # rule id that blocked it, or None
        "security_warnings": warnings,                     # shown, but flagged (policy = warn)
        "redacted": len(found),                            # secrets kept out of the model this call
        "single_line": single_line,
        "avg_logprob": avg,
        "min_logprob": mn,
        "latency_ms": round((time.perf_counter() - start) * 1000),
        "p_good": p,                                       # NEW: how likely it's good
        "show": decision["show"],
        "is_block": is_block,
    }


def rotate_logs():
    """events.jsonl full -> becomes events.1.jsonl (older ones shift up, the oldest is deleted)."""
    for i in range(LOG_KEEP, 0, -1):
        src = LOG_PATH if i == 1 else LOG_PATH.with_name(f"events.{i - 1}.jsonl")
        if src.exists():
            src.replace(LOG_PATH.with_name(f"events.{i}.jsonl"))


@app.post("/log")
async def log_event(event: dict):          # Guard already capped the body at 64 KB
    event = redact_event(event)                       # no secrets in events.jsonl
    line = json.dumps(event) + "\n"
    if LOG_PATH.exists() and LOG_PATH.stat().st_size + len(line) > LOG_MAX_BYTES:
        rotate_logs()                      # never stop logging: old events move aside instead
    with LOG_PATH.open("a") as f:
        f.write(line)
    if TUNER:
        TUNER.observe(event, refit=False)  # accept/reject outcomes teach the self-tuning gate
        if TUNER.due():                    # every 10 outcomes: refit in a worker thread, not on the request path
            await asyncio.to_thread(TUNER.refit_due)
    return {"ok": True}


@app.get("/calibration")
async def calibration(repo: str = ""):
    """Audit the silence for one repo: the fit, show rate and expected acceptance (tuned vs frozen gate),
    and a reliability table (predicted vs actual acceptance). Without ?repo= : the list of repos."""
    if TUNER is None:
        return {"tuner": "off"}
    if not repo:
        return {"repos": {name: len(r.labels) for name, r in TUNER.repos.items()}, "tau": TUNER.tau}
    return TUNER.report(repo)