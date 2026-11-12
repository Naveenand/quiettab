"""Fix 10: test the FROZEN gate (server/gate.json) on results it was NOT tuned on.

No retraining: we only apply the same rule the server uses
  p_good = sigmoid(intercept + coef * features)
  show if p_good >= threshold        (block_threshold if the suggestion has a newline)
and report how often it speaks and how often it's right, with a 95% bootstrap range.

    python check_gate.py results/realfim.jsonl
    python check_gate.py results/baseline.jsonl     # the data it was tuned on (for comparison)
"""
import argparse, json, math, random
from pathlib import Path

ap = argparse.ArgumentParser()
ap.add_argument("results")
ap.add_argument("--gate", default="../server/gate.json")
ap.add_argument("--good-chrf", type=float, default=70)
ap.add_argument("--boot", type=int, default=2000)
args = ap.parse_args()

gate = json.loads(Path(args.gate).read_text())
rows = [json.loads(l) for l in open(args.results)]
rows = [r for r in rows if r.get("variant") == "+context" and r.get("pred")
        and all(r.get(f) is not None for f in gate["features"])]

def p_good(r):
    z = gate["intercept"] + sum(c * r[f] for c, f in zip(gate["coef"], gate["features"]))
    return 1 / (1 + math.exp(-z))

def shown(r):  # exactly the server's rule
    thr = gate.get("block_threshold", gate["threshold"]) if "\n" in r["pred"] else gate["threshold"]
    return p_good(r) >= thr

def good(r):
    return bool(r["em"] or (r["valid"] and r["chrf"] >= args.good_chrf))

def summary(rs):
    s = [r for r in rs if shown(r)]
    base = sum(map(good, rs)) / len(rs)
    show = len(s) / len(rs)
    prec = sum(map(good, s)) / len(s) if s else float("nan")
    return base, show, prec

def ci(rs, i):  # 95% bootstrap range for summary()[i]
    random.seed(0)
    vals = sorted(v for v in (summary(random.choices(rs, k=len(rs)))[i] for _ in range(args.boot)) if v == v)
    return vals[int(0.025 * len(vals))], vals[int(0.975 * len(vals)) - 1]

print(f"## Frozen gate on {args.results}  (threshold {gate['threshold']}, block {gate.get('block_threshold', '-')})\n")
print("| | n | good if we show everything | show rate | precision of shown (95% range) |")
print("|---|---|---|---|---|")
for name, rs in [("all", rows),
                 ("one-line suggestions", [r for r in rows if "\n" not in r["pred"]]),
                 ("multi-line suggestions", [r for r in rows if "\n" in r["pred"]])]:
    if len(rs) < 5:
        continue
    base, show, prec = summary(rs)
    lo, hi = ci(rs, 2)
    print(f"| {name} | {len(rs)} | {base:.0%} | {show:.0%} | **{prec:.0%}** ({lo:.0%}-{hi:.0%}) |")
