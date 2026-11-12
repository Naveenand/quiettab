"""Step 7: learn WHEN TO STAY QUIET.

Reads the eval results from Step 6 and trains a tiny model (logistic regression) that
answers one question for every suggestion:  "how likely is this suggestion to be good?"
It only uses numbers the server already has at suggestion time:
  avg_logprob, min_logprob  (model confidence), suggestion length, line/block mode, cheat sheet yes/no

Then it:
  1. scores it fairly (out-of-fold: each repo is predicted by a model that never saw that repo)
  2. draws the accuracy-rejection curve  -> results/arc.png
  3. picks the threshold that keeps precision >= --target-precision while showing as much as possible
  4. saves the gate to server/gate.json (the server uses it to decide show / hide)

Usage:  python train_gate.py --results results/baseline.jsonl --points data/points.jsonl
"""
import argparse
import json
import math
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import GroupKFold, KFold

FEATURES = ["avg_logprob", "min_logprob", "log_len", "single_line", "has_extra"]


def to_features(row):
    return [row["avg_logprob"], row["min_logprob"], math.log1p(len(row["pred"])),
            1.0 if row["kind"] == "line" else 0.0, 1.0 if row["has_extra"] else 0.0]


def curve(scores, labels):
    """Show the most confident suggestions first. For each 'show rate', what % of shown ones are good?"""
    order = np.argsort(-scores)
    hits = labels[order]
    k = np.arange(1, len(hits) + 1)
    return k / len(hits), np.cumsum(hits) / k          # show rate, precision of shown


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--results", default="results/baseline.jsonl")
    ap.add_argument("--points", default="data/points.jsonl")
    ap.add_argument("--variant", default="+context", help="which setup to learn the gate for (the one you ship)")
    ap.add_argument("--good-chrf", type=float, default=70, help="a suggestion counts as GOOD if exact match, or valid code with chrF >= this")
    ap.add_argument("--target-precision", type=float, default=0.70)
    ap.add_argument("--out", default="../server/gate.json")
    ap.add_argument("--features", default=",".join(FEATURES), help="comma list, e.g. avg_logprob")
    args = ap.parse_args()

    repo_of = {p["id"]: p["repo"] for p in map(json.loads, open(args.points))}
    rows = [r for r in map(json.loads, open(args.results))
            if r["variant"] == args.variant and r["pred"].strip() and r["avg_logprob"] is not None]

    X_all = np.array([to_features(r) for r in rows])
    chosen = args.features.split(",")
    X = X_all[:, [FEATURES.index(f) for f in chosen]]
    y = np.array([1 if (r["em"] or (r["valid"] and r["chrf"] >= args.good_chrf)) else 0 for r in rows])
    groups = np.array([repo_of.get(r["id"], "?") for r in rows])
    print(f"{len(rows)} suggestions, {y.mean():.0%} of them are GOOD (= precision if we show everything)")

    # 1. fair scores: each repo is predicted by a model trained on the OTHER repos
    n_repos = len(set(groups))
    splitter = GroupKFold(n_splits=min(5, n_repos)) if n_repos >= 2 else KFold(5, shuffle=True, random_state=0)
    p_oof = np.zeros(len(y))
    for train, test in splitter.split(X, y, groups):
        model = LogisticRegression(max_iter=1000).fit(X[train], y[train])
        p_oof[test] = model.predict_proba(X[test])[:, 1]

        # With ONE feature the gate is just "a cutoff on that number": the ranking can't overfit,
    # so score it with the final model (fold-by-fold models put probabilities on different scales).
    final = LogisticRegression(max_iter=1000).fit(X, y)
    scores = final.predict_proba(X)[:, 1] if X.shape[1] == 1 else p_oof

    # 2. accuracy-rejection curves: learned gate vs raw confidence vs no gate
    cov_g, prec_g = curve(scores, y)
    cov_a, prec_a = curve(X_all[:, 0], y)                # avg_logprob alone
    auarc_g, auarc_a = prec_g.mean(), prec_a.mean()

    # 3. threshold: highest show rate that still reaches the target precision
    order = np.argsort(-scores)
    ok = np.where(prec_g >= args.target_precision)[0]
    if len(ok):
        k = ok.max()
        threshold = float(scores[order][k])
        show_rate, precision = float(cov_g[k]), float(prec_g[k])
    else:
        threshold, show_rate, precision = 1.0, 0.0, float("nan")
        print(f"!! no threshold reaches {args.target_precision:.0%} precision - try a lower --target-precision")
    plt.plot(cov_g, prec_g, label=f"learned gate (AUARC {auarc_g:.2f})")
    plt.plot(cov_a, prec_a, label=f"avg_logprob only (AUARC {auarc_a:.2f})", linestyle="--")
    plt.axhline(y.mean(), color="gray", linestyle=":", label=f"no gate ({y.mean():.0%})")
    if show_rate > 0:
        plt.scatter([show_rate], [precision], color="red", zorder=5, label=f"chosen: show {show_rate:.0%}, precision {precision:.0%}")
    plt.xlabel("show rate (fraction of suggestions shown)")
    plt.ylabel("precision of shown (% good)")
    plt.title("QuietTab: accuracy-rejection curve")
    plt.legend(fontsize=8); plt.grid(alpha=0.3); plt.tight_layout()
    Path("results").mkdir(exist_ok=True)
    plt.savefig("results/arc.png", dpi=150)

    # 4. final gate trained on everything, saved for the server
    gate = {"features": chosen, "coef": final.coef_[0].round(4).tolist(),
            "intercept": round(float(final.intercept_[0]), 4), "threshold": round(threshold, 4),
            "target_precision": args.target_precision, "good_definition": f"exact match OR (valid AND chrF >= {args.good_chrf})",
            "trained_on": len(y)}
    Path(args.out).write_text(json.dumps(gate, indent=2))

    summary = "\n".join([
        f"## Confidence gate ({args.variant}, {len(y)} suggestions)", "",
        "| | show rate | precision of shown | AUARC |", "|---|---|---|---|",
        f"| no gate (show everything) | 100% | {y.mean():.0%} | - |",
        f"| avg_logprob only | - | - | {auarc_a:.2f} |",
        f"| learned gate (threshold {threshold:.2f}) | {show_rate:.0%} | {precision:.0%} | {auarc_g:.2f} |",
        "", "Weights (bigger = pushes toward 'show'): " +
        ", ".join(f"{f} {w:+.2f}" for f, w in zip(FEATURES, gate["coef"])),
    ])
    Path("results/gate-summary.md").write_text(summary + "\n")
    print(summary)
    print(f"\nsaved {args.out} and results/arc.png")


if __name__ == "__main__":
    main()
