import json
import math
import os
import time
from pathlib import Path
from pydantic import BaseModel, Field
import httpx
from fastapi import FastAPI
from pydantic import BaseModel

from cleanup import clean

LOG_PATH = Path(__file__).parent / "logs" / "events.jsonl"
LOG_PATH.parent.mkdir(exist_ok=True)

DEBUG = os.getenv("QT_DEBUG") == "1"
PROMPT_LOG = LOG_PATH.parent / "prompts.jsonl"

LLAMA_URL = "http://localhost:8012/infill"

# NEW (Step 7): load the confidence gate trained by eval/train_gate.py
GATE_PATH = Path(__file__).parent / "gate.json"
GATE = json.loads(GATE_PATH.read_text()) if GATE_PATH.exists() else None

app = FastAPI()
client = httpx.AsyncClient(timeout=2.0)


class CompleteRequest(BaseModel):
    prefix: str = Field(max_length=8000)
    suffix: str = Field(max_length=4000)
    max_tokens: int = Field(64, ge=1, le=128)
    extra: list[dict] = Field(default_factory=list, max_length=8)


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
async def complete(req: CompleteRequest):
    start = time.perf_counter()
    current_line = req.prefix.rsplit("\n", 1)[-1]      # text before the cursor on this line
    single_line = current_line.strip() != ""            # typing mid-line?
    stop = ["\n"] if single_line else ["\n\n", "\ndef ", "\nclass "]
    max_tokens = 32 if single_line else req.max_tokens
    extra = [{**e, "text": e.get("text", "").rstrip("\n") + "\n"} for e in req.extra]

    # 1. Ask the model (only llama.cpp settings go here)
    r = await client.post(LLAMA_URL, json={
        "input_prefix": req.prefix,
        "input_suffix": req.suffix,
        "n_predict": max_tokens,
        "temperature": 0,        # same input -> same suggestion
        "n_probs": 1,            # also return confidence per token
        "cache_prompt": True,    # reuse work from the last request
        "stop": stop,
        "input_extra": extra,    # cheat sheet: signatures from other files
    })
    data = r.json()
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
    text = clean(data["content"], req.prefix, req.suffix, single_line)
    p = p_good(avg, mn, text, single_line, bool(req.extra))

    thr = None
    if GATE:
        thr = GATE["threshold"] if single_line else GATE.get("block_threshold", GATE["threshold"])

    # 4. Reply to the plugin
    return {
        "text": text,
        "raw_text": data["content"],
        "single_line": single_line,
        "avg_logprob": avg,
        "min_logprob": mn,
        "latency_ms": round((time.perf_counter() - start) * 1000),
        "p_good": p,                                       # NEW: how likely it's good
        "show": p is None or p >= thr,       # NEW: the gate's decision
    }


@app.post("/log")
async def log_event(event: dict):
    if LOG_PATH.exists() and LOG_PATH.stat().st_size > 50_000_000:   # 50 MB cap
        return {"ok": False, "reason": "log full"}
    with LOG_PATH.open("a") as f:
        f.write(json.dumps(event) + "\n")
    return {"ok": True}