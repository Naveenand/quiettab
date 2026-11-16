"""Does self-tuning silence work? A simulation tied to your measured numbers.

Why a simulation: real accept/reject data only exists once people use QuietTab. This replays the
exact Tuner the server runs (server/tuner.py) against simulated users whose acceptance behaviour is
known, so we can check it learns the right threshold, how fast, and what it costs.

Set-up (from your own results):
  * p_good comes from the real gate.json formula; avg_logprob is drawn so the frozen gate shows ~43%
    (your gate-summary.md).
  * "unfamiliar" repo: frozen gate's shown suggestions are accepted 16% of the time (your Real-FIM number).
  * "familiar" repo: shown ones are accepted 70% of the time, but many good ones are hidden.
  * "drift": familiar for the first half, unfamiliar after (a new codebase / new model).
  * "two repos": the same developer switches between a familiar and an unfamiliar repo, suggestion by
    suggestion. "one-size" = the same tuner without per-repo fits (all outcomes pooled together).
Policies compared on the same suggestions: frozen gate, tuned, and an oracle that knows the true
acceptance chance (the best any threshold policy can do).
Score = Cursor's reward: +0.75 per accepted, -0.25 per rejected shown suggestion, 0 when quiet.

Usage: python simulate_tuner.py [--seeds 20] [--n 2000] [--out results/tuner-sim.md]
"""
import argparse
import json
import math
import random
import statistics
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "server"))
from tuner import Tuner, logit, sigmoid  # noqa: E402

GATE = json.loads((Path(__file__).resolve().parent.parent / "server" / "gate.json").read_text())
THR_LINE, THR_BLOCK = GATE["threshold"], GATE.get("block_threshold", GATE["threshold"])


def p_good(rng):
    avg_logprob = -rng.expovariate(1 / 0.40)
    return sigmoid(GATE["intercept"] + GATE["coef"][0] * avg_logprob)


def true_accept(p, blk, beta, slope=4.0):
    return sigmoid(slope * logit(p) + beta - 0.3 * blk)


def solve_beta(target, rng_seed=0):
    """Pick beta so the frozen gate's shown suggestions are accepted `target` of the time."""
    rng = random.Random(rng_seed)
    sample = [(p_good(rng), rng.random() < 0.6) for _ in range(20000)]
    shown = [(p, b) for p, b in sample if p >= (THR_BLOCK if b else THR_LINE)]
    lo, hi = -8.0, 8.0
    for _ in range(50):
        mid = (lo + hi) / 2
        rate = sum(true_accept(p, b, mid) for p, b in shown) / len(shown)
        lo, hi = (mid, hi) if rate < target else (lo, mid)
    return (lo + hi) / 2


def make_tuner(seed, strength, half_life):
    return Tuner(THR_LINE, THR_BLOCK, tau=0.30, explore=0.05, strength_user=strength, strength_repo=strength,
                 half_life=half_life, rng=random.Random(seed + 1))


def step(tuner, repo, sid, p, blk, accepted):
    d = tuner.decide(repo, p, blk)
    tuner.observe({"event": "shown" if d["show"] else "gated", "sid": sid, "repo": repo, "p_good": p,
                   "is_block": blk, "explore": d["explore"]})
    if d["show"]:
        tuner.observe({"event": "accepted" if accepted else "rejected", "sid": sid, "repo": repo,
                       "p_good": p, "is_block": blk})
    return d["show"]


def run(scenario, betas, seed, n, strength, half_life=150.0):
    rng = random.Random(seed)
    tuner, single = make_tuner(seed, strength, half_life), make_tuner(seed, strength, half_life)
    out = {k: [] for k in ("frozen", "one-size", "tuned", "oracle")}
    for i in range(n):
        if scenario == "two repos":
            repo = rng.choice(("familiar", "unfamiliar"))
            beta = betas[0] if repo == "familiar" else betas[1]
        else:
            repo = "repo"
            beta = betas[0] if (scenario != "drift" or i < n // 2) else betas[1]
        p, blk = p_good(rng), rng.random() < 0.6
        t = true_accept(p, blk, beta)
        accepted = rng.random() < t                      # same user reaction for every policy
        shown_tuned = step(tuner, repo, f"s{i}", p, blk, accepted)
        shown_single = step(single, "", f"s{i}", p, blk, accepted) if scenario == "two repos" else None
        for name, shown in (("frozen", p >= (THR_BLOCK if blk else THR_LINE)), ("tuned", shown_tuned),
                            ("one-size", shown_single), ("oracle", t >= 0.30)):
            if shown is not None:
                out[name].append((shown, accepted, t))
    return out


def metrics(rows):
    shown = [r for r in rows if r[0]]
    good_total = sum(r[2] for r in rows)
    return {"show": len(shown) / len(rows),
            "precision": sum(r[1] for r in shown) / len(shown) if shown else float("nan"),
            "score": sum((0.75 if r[1] else -0.25) for r in shown) / len(rows) * 100,   # per 100 candidates
            "found": sum(r[2] for r in shown) / good_total}                            # share of good ones shown


def mean_ci(vals):
    vals = [v for v in vals if not math.isnan(v)]
    if not vals:
        return float("nan"), float("nan")
    m = statistics.mean(vals)
    s = statistics.stdev(vals) / math.sqrt(len(vals)) if len(vals) > 1 else 0
    return m, 1.96 * s


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds", type=int, default=20)
    ap.add_argument("--n", type=int, default=2000)
    ap.add_argument("--strength", type=float, default=10.0)
    ap.add_argument("--half-life", type=float, default=150.0)
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    b_unfam, b_fam = solve_beta(0.16), solve_beta(0.70)
    scenarios = {"unfamiliar": (b_unfam, b_unfam), "familiar": (b_fam, b_fam), "drift": (b_fam, b_unfam),
                 "two repos": (b_fam, b_unfam)}
    lines = [f"## Self-tuning silence: simulation ({args.seeds} seeds x {args.n} suggestions, strength {args.strength:g}, half-life {args.half_life:g}, tau 0.30, explore 5%)",
             "", "Mean over seeds, +- 95% CI. Window = which suggestions are scored "
             "(early = first 300, late = last 500; for drift: last 500 = after the change).", "",
             "| scenario | window | policy | shown % | accepted % of shown | score /100 | good ones shown % |",
             "|---|---|---|---|---|---|---|"]
    for sc, betas in scenarios.items():
        runs = [run(sc, betas, s, args.n, args.strength, args.half_life) for s in range(args.seeds)]
        for wname, sl in (("early", slice(0, 300)), ("late", slice(args.n - 500, args.n))):
            for pol in ("frozen", "one-size", "tuned", "oracle"):
                if not runs[0][pol]:
                    continue
                ms = [metrics(r[pol][sl]) for r in runs]
                cell = lambda k, pct=True: "{:.1f} ± {:.1f}".format(*[v * (100 if pct else 1) for v in mean_ci([m[k] for m in ms])])  # noqa: E731
                lines.append(f"| {sc} | {wname} | {pol} | {cell('show')} | {cell('precision')} | {cell('score', False)} | {cell('found')} |")
    text = "\n".join(lines)
    print(text)
    if args.out:
        Path(args.out).write_text(text + "\n")


if __name__ == "__main__":
    main()
