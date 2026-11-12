"""Turn Real-FIM-Eval (Add split) into QuietTab eval points.

Real-FIM-Eval (Gong et al. 2025, arXiv 2506.00204): real GitHub commits from Jan-Feb 2025.
In the Add split, the code a developer ADDED to an existing file is the "middle" to predict.

Fields used:  prompt -> prefix,  canonical_solution -> middle,  suffix -> suffix,
              lang, repo, path, timestamp

What this script does:
  1. keeps Python, Add split, committed in 2025 (newer than the model's training data)
  2. keeps short additions (<= --max-lines lines) - QuietTab's use case, not whole new functions
  3. moves the first line's indentation into the prefix (the IDE has already auto-indented)
  4. keeps only examples where prefix + middle + suffix parses, so "valid code %" means something
  5. caps examples per repo so a few big repos can't dominate, then samples --n points
  6. writes the same format as make_dataset.py (extra = [] : no other files in this dataset)

Usage:  python import_realfim.py --n 300 --out data/realfim.jsonl
"""
import argparse
import ast
import json
import random
from collections import defaultdict
from pathlib import Path


def to_point(ex, max_lines):
    """One dataset row -> one point dict, or None if it doesn't fit QuietTab's use case."""
    prefix, middle, suffix = ex["prompt"], ex["canonical_solution"], ex["suffix"]
    stripped = middle.rstrip("\n")
    suffix = middle[len(stripped):] + suffix              # keep the newline(s) between middle and suffix
    middle = stripped
    lines = middle.split("\n")
    if not middle.strip() or len(lines) > max_lines:
        return None
    # move leading indentation of the first line into the prefix (cursor sits after auto-indent)
    indent = len(lines[0]) - len(lines[0].lstrip())
    if not prefix.endswith("\n") and prefix:            # middle starts mid-line: leave as is
        indent = 0
    prefix, middle = prefix + middle[:indent], middle[indent:]
    try:
        ast.parse(prefix + middle + suffix)               # real code must parse -> valid % is meaningful
    except (SyntaxError, ValueError):
        return None
    return {
        "repo": ex["repo"], "path": ex["path"],
        "kind": "line" if len(lines) == 1 else "block",
        "prefix": prefix, "middle": middle, "suffix": suffix,
        "extra": [],
    }


def load_add_rows():
    from datasets import load_dataset, get_dataset_config_names
    name = "gonglinyuan/real_fim_eval"
    configs = get_dataset_config_names(name)
    add_cfg = next((c for c in configs if "add" in c.lower()), None)
    ds = load_dataset(name, add_cfg) if add_cfg else load_dataset(name)
    splits = [s for s in ds if "add" in s.lower()] or list(ds)   # 'add' split, else whatever there is
    print(f"configs: {configs}  -> using config={add_cfg!r}, splits={splits}")
    for s in splits:
        yield from ds[s]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=300)
    ap.add_argument("--max-lines", type=int, default=8)
    ap.add_argument("--per-repo", type=int, default=15)
    ap.add_argument("--since", default="2025-01-01")
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--out", default="data/realfim.jsonl")
    args = ap.parse_args()
    rng = random.Random(args.seed)

    seen, by_repo, stats = set(), defaultdict(list), defaultdict(int)
    for ex in load_add_rows():
        stats["rows"] += 1
        if str(ex.get("lang", "")).lower() != "python":
            continue
        stats["python"] += 1
        if str(ex.get("timestamp", "")) < args.since:
            continue
        p = to_point(ex, args.max_lines)
        if p is None:
            continue
        key = (p["repo"], p["path"], p["middle"])
        if key in seen:
            continue
        seen.add(key)
        by_repo[p["repo"]].append(p)

    pool = []
    for repo, pts in sorted(by_repo.items()):
        rng.shuffle(pts)
        pool += pts[:args.per_repo]
    rng.shuffle(pool)
    chosen = pool[:args.n]
    for i, p in enumerate(chosen):
        p["id"] = i

    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    with open(args.out, "w") as f:
        for p in chosen:
            f.write(json.dumps(p) + "\n")
    n_line = sum(p["kind"] == "line" for p in chosen)
    print(f"rows read: {stats['rows']}, python: {stats['python']}, usable: {sum(map(len, by_repo.values()))} "
          f"from {len(by_repo)} repos")
    print(f"wrote {len(chosen)} points ({n_line} one-line, {len(chosen) - n_line} multi-line) -> {args.out}")


if __name__ == "__main__":
    main()
