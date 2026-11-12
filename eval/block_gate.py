"""Fix 5: a stricter bar for multi-line blocks.

Uses the gate you already trained (server/gate.json) and finds a SEPARATE
threshold for block suggestions, so wordy/wrong blocks stay quiet while
one-line suggestions keep the normal threshold.

Run AFTER train_gate.py (train_gate.py rewrites gate.json and drops this value):
    python block_gate.py results/<same file train_gate.py uses>.jsonl --target 0.6
"""
import argparse, json, math
from pathlib import Path

ap = argparse.ArgumentParser()
ap.add_argument("results")
ap.add_argument("--target", type=float, default=0.6, help="precision wanted for blocks")
ap.add_argument("--gate", default="../server/gate.json")
ap.add_argument("--good-chrf", type=float, default=70)
args = ap.parse_args()

gate = json.loads(Path(args.gate).read_text())
rows = [json.loads(l) for l in open(args.results)]
rows = [r for r in rows if r.get("variant") == "+context" and r.get("pred")
        and all(r.get(f) is not None for f in gate["features"])]

def p_good(r):  # same formula the server uses
    z = gate["intercept"] + sum(c * r[f] for c, f in zip(gate["coef"], gate["features"]))
    return 1 / (1 + math.exp(-z))

def good(r):    # same "good" definition as train_gate.py
    return bool(r["em"] or (r["valid"] and r["chrf"] >= args.good_chrf))

def at(rs, thr):  # show rate and precision if we only show p_good >= thr
    shown = [r for r in rs if p_good(r) >= thr]
    prec = sum(good(r) for r in shown) / len(shown) if shown else float("nan")
    return len(shown) / len(rs), prec

print(f"| kind | n | good (no gate) | shown @ {gate['threshold']:.2f} | precision @ {gate['threshold']:.2f} |")
print("|---|---|---|---|---|")
for kind in ["line", "block"]:
    rs = [r for r in rows if r["kind"] == kind]
    if not rs:
        continue
    show, prec = at(rs, gate["threshold"])
    print(f"| {kind} | {len(rs)} | {sum(map(good, rs)) / len(rs):.0%} | {show:.0%} | {prec:.0%} |")

# block threshold: the LOWEST cutoff (= shows the most) that still reaches the target precision
blocks = sorted([r for r in rows if r["kind"] == "block"], key=p_good, reverse=True)
best, hits = None, 0
for i, r in enumerate(blocks, 1):
    hits += good(r)
    if hits / i >= args.target:
        best = p_good(r)
if best is None:
    best = 1.01   # no cutoff reaches the target -> never show blocks
    print(f"\n!! no block threshold reaches {args.target:.0%} precision -> blocks are always hidden")

best = max(best, gate["threshold"])   # blocks are never easier than lines
show, prec = at(blocks, best)
print(f"\nblock_threshold = {best:.2f}  ->  blocks shown {show:.0%}, precision {prec:.0%}")

gate["block_threshold"] = round(best, 4)
Path(args.gate).write_text(json.dumps(gate, indent=2))
print(f"saved block_threshold into {args.gate}  (restart uvicorn to use it)")
