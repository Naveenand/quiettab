"""Run the eval set through the QuietTab server and score it.

For every point we ask the server twice (without / with the cheat sheet) and score 3 setups:
  raw        = model output before cleanup        (no cheat sheet)
  +cleanup   = after the Step 4 trims             (no cheat sheet)
  +context   = after trims, WITH the cheat sheet  (Step 5)

Metrics: exact match, chrF (0-100, character overlap), valid code (file still parses),
         latency p50/p90 (server-side model time).

Usage:  python run_eval.py --points data/points.jsonl --name baseline
"""
import argparse
import ast
import json
import statistics
import time
from pathlib import Path

import httpx
from sacrebleu.metrics import CHRF

PREFIX_CHARS, SUFFIX_CHARS = 1500, 500   # same window as the plugin
chrf = CHRF()


def norm(code: str) -> str:
    return "\n".join(l.rstrip() for l in code.strip().splitlines())


def is_valid(prefix: str, pred: str, suffix: str) -> bool:
    try:
        ast.parse(prefix + pred + suffix)
        return True
    except SyntaxError:
        return False


def pct(values, q):
    values = sorted(values)
    return values[min(len(values) - 1, int(q * len(values)))] if values else 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--points", default="data/points.jsonl")
    ap.add_argument("--server", default="http://localhost:8000")
    ap.add_argument("--name", default="run")
    ap.add_argument("--limit", type=int, default=0, help="only run the first N points (quick test)")
    args = ap.parse_args()

    points = [json.loads(l) for l in open(args.points)]
    if args.limit:
        points = points[:args.limit]
    out_dir = Path("results"); out_dir.mkdir(exist_ok=True)
    rows = []

    with httpx.Client(timeout=10) as client:
        for i, p in enumerate(points, 1):
            req = {"prefix": p["prefix"][-PREFIX_CHARS:], "suffix": p["suffix"][:SUFFIX_CHARS]}
            for use_extra in (False, True):
                body = dict(req, extra=p["extra"] if use_extra else [])
                t0 = time.perf_counter()
                res = client.post(f"{args.server}/complete", json=body).json()
                wall_ms = (time.perf_counter() - t0) * 1000
                variants = [("+context", res["text"])] if use_extra else [("raw", res["raw_text"]), ("+cleanup", res["text"])]
                for variant, pred in variants:
                    rows.append({
                        "id": p["id"], "kind": p["kind"], "variant": variant, "pred": pred, "middle": p["middle"],
                        "has_extra": bool(p["extra"]),
                        "em": norm(pred) == norm(p["middle"]),
                        "chrf": chrf.sentence_score(pred, [p["middle"]]).score,
                        "valid": is_valid(p["prefix"], pred, p["suffix"]),
                        "latency_ms": res["latency_ms"], "wall_ms": round(wall_ms),
                        "avg_logprob": res["avg_logprob"], "min_logprob": res["min_logprob"],
                    })
            if i % 25 == 0:
                print(f"  {i}/{len(points)} points done")

    with open(out_dir / f"{args.name}.jsonl", "w") as f:
        for r in rows:
            f.write(json.dumps(r) + "\n")

    # ---- summary table ----
    def summarize(sel):
        return (f"| {len(sel)} | {100 * sum(r['em'] for r in sel) / len(sel):.1f} "
                f"| {statistics.mean(r['chrf'] for r in sel):.1f} "
                f"| {100 * sum(r['valid'] for r in sel) / len(sel):.1f} "
                f"| {pct([r['latency_ms'] for r in sel], 0.5)} | {pct([r['latency_ms'] for r in sel], 0.9)} |")

    lines = [f"## Eval: {args.name} ({len(points)} points)", "",
             "| setup | kind | n | exact match % | chrF | valid code % | p50 ms | p90 ms |",
             "|---|---|---|---|---|---|---|---|"]
    for variant in ("raw", "+cleanup", "+context"):
        for kind in ("all", "line", "block"):
            sel = [r for r in rows if r["variant"] == variant and (kind == "all" or r["kind"] == kind)]
            if sel:
                lines.append(f"| {variant} | {kind} " + summarize(sel))
    # context only matters where a cheat sheet exists: compare on those points
    lines += ["", "Points that had a cheat sheet only:", "",
              "| setup | n | exact match % | chrF | valid code % | p50 ms | p90 ms |", "|---|---|---|---|---|---|---|"]
    for variant in ("+cleanup", "+context"):
        sel = [r for r in rows if r["variant"] == variant and r["has_extra"]]
        if sel:
            lines.append(f"| {variant} " + summarize(sel))

    table = "\n".join(lines)
    (out_dir / f"{args.name}-summary.md").write_text(table + "\n")
    print(table)


if __name__ == "__main__":
    main()