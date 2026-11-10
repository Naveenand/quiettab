import math
import time

import httpx
from fastapi import FastAPI
from pydantic import BaseModel

LLAMA_URL = "http://localhost:8012/infill"

app = FastAPI()
client = httpx.AsyncClient(timeout=2.0)


class CompleteRequest(BaseModel):
    prefix: str          # code before the cursor
    suffix: str          # code after the cursor
    max_tokens: int = 64


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
    r = await client.post(LLAMA_URL, json={
        "input_prefix": req.prefix,
        "input_suffix": req.suffix,
        "n_predict": max_tokens,
        "temperature": 0,        # same input -> same suggestion
        "n_probs": 1,            # also return confidence per token
        "cache_prompt": True,
        "stop": stop,  # stop at a blank line or a new function/class # reuse work from the last request
    })
    data = r.json()
    logprobs = [token_logprob(t) for t in data.get("completion_probabilities", [])]
    return {
        "text": data["content"],
        "avg_logprob": sum(logprobs) / len(logprobs) if logprobs else None,
        "min_logprob": min(logprobs) if logprobs else None,
        "latency_ms": round((time.perf_counter() - start) * 1000),
    }