"""Re-score an eval run the QuietTab way: staying quiet is NOT a wrong answer.

  shown %          how often QuietTab speaks (pred is not empty)
  EM / chrF / valid (shown)   quality only on the suggestions it actually shows
  EM (all)         exact matches per 100 attempts (quiet counts as a miss)

Usage:  python summarize.py results/baseline.jsonl
"""
import json
import statistics
import sys
from collections import defaultdict


def row(rs):
    shown = [r for r in rs if r["pred"].strip()]
    pct = lambda xs, f: 100 * sum(1 for x in xs if f(x)) / len(xs) if xs else 0.0
    return (
        len(rs),
        pct(rs, lambda r: r["pred"].strip()),
        pct(shown, lambda r: r["em"]),
        statistics.mean(r["chrf"] for r in shown) if shown else 0.0,
        pct(shown, lambda r: r["valid"]),
        pct(rs, lambda r: r["em"]),
    )


def table(title, groups):
    print(f"\n{title}\n")
    print("| setup | kind | n | shown % | EM (shown) | chrF (shown) | valid (shown) | EM (all) |")
    print("|---|---|---|---|---|---|---|---|")
    for (variant, kind), rs in groups:
        n, sh, em, chrf, valid, em_all = row(rs)
        print(f"| {variant} | {kind} | {n} | {sh:.1f} | {em:.1f} | {chrf:.1f} | {valid:.1f} | {em_all:.1f} |")


def main(path):
    rows = [json.loads(l) for l in open(path)]
    variants = list(dict.fromkeys(r["variant"] for r in rows))   # keep file order
    by = defaultdict(list)
    for r in rows:
        by[(r["variant"], "all")].append(r)
        by[(r["variant"], r["kind"])].append(r)
    table("## All points", [((v, k), by[(v, k)]) for v in variants for k in ("all", "line", "block") if by[(v, k)]])

    ctx = [r for r in rows if r.get("has_extra")]
    if ctx:
        g = defaultdict(list)
        for r in ctx:
            g[(r["variant"], "all")].append(r)
        table(f"## Points with a cheat sheet only (n={len(ctx) // len(variants)})",
              [((v, "all"), g[(v, "all")]) for v in variants if g[(v, "all")]])


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "results/baseline.jsonl")
