import math
import time

import httpx
from fastapi import FastAPI
from pydantic import BaseModel
from cleanup import clean
import json
from pathlib import Path

LOG_PATH = Path(__file__).parent / "logs" / "events.jsonl"
LOG_PATH.parent.mkdir(exist_ok=True)

LLAMA_URL = "http://localhost:8012/infill"

app = FastAPI()
client = httpx.AsyncClient(timeout=2.0)


class CompleteRequest(BaseModel):
    prefix: str          # code before the cursor
    suffix: str          # code after the cursor
    max_tokens: int = 64
    extra: list[dict] = []   # [{"filename": "...", "text": "..."}] from the plugin


def token_logprob(t: dict) -> float:
    # llama.cpp versions differ: some return "logprob", older ones return "probs"
    if "logprob" in t:
        return t["logprob"]
    return math.log(max(t["probs"][0]["prob"], 1e-9))


@app.post("/complete")
async def complete(req: CompleteRequest):
    start = time.perf_counter()
    current_line = req.prefix.rsplit("\n", 1)[-1]      # text before the cursor on this line
    single_line = current_line.strip() != ""            # typing mid-line?
    stop = ["\n"] if single_line else ["\n\n", "\ndef ", "\nclass "]
    max_tokens = 32 if single_line else req.max_tokens


    # 1. Ask the model (only llama.cpp settings go here)
    r = await client.post(LLAMA_URL, json={
        "input_prefix": req.prefix,
        "input_suffix": req.suffix,
        "n_predict": max_tokens,
        "temperature": 0,        # same input -> same suggestion
        "n_probs": 1,            # also return confidence per token
        "cache_prompt": True,    # reuse work from the last request
        "stop": stop,
        "input_extra": req.extra,   # cheat sheet: signatures from other files
    })
    data = r.json()

    # 2. Confidence from per-token logprobs
    logprobs = [token_logprob(t) for t in data.get("completion_probabilities", [])]

    # 3. Reply to the plugin (cleaned text + raw text for debugging)
    return {
        "text": clean(data["content"], req.prefix, req.suffix, single_line),
        "raw_text": data["content"],
        "single_line": single_line,
        "avg_logprob": sum(logprobs) / len(logprobs) if logprobs else None,
        "min_logprob": min(logprobs) if logprobs else None,
        "latency_ms": round((time.perf_counter() - start) * 1000),
    }
@app.post("/log")
async def log_event(event: dict):
    with LOG_PATH.open("a") as f:
        f.write(json.dumps(event) + "\n")
    return {"ok": True}