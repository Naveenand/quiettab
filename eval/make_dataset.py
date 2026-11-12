"""Build an eval set of completion points from Python repos.

For every repo folder in eval/repos/, pick random spots inside functions and hide
some code. The model's job is to fill it back in.

  kind="line":  cursor in the middle of a line, hide the rest of that line
  kind="block": cursor at the start of a statement, hide the whole statement (1-6 lines)

Also builds the "cheat sheet" (extra context) the same way the plugin does:
names used near the cursor -> signatures of where they are defined in OTHER files.

Usage:  python make_dataset.py --repos repos --out data/points.jsonl --n 250
"""
import argparse
import ast
import json
import random
import re
from pathlib import Path

PREFIX_CHARS, SUFFIX_CHARS = 1500, 500   # same window as the plugin
MAX_PER_FILE = 4
MAX_PER_REPO = 120   # so one huge repo can't dominate the exam

# ---------- cheat sheet: follow this file's IMPORTS (like the plugin's PSI resolve) ----------

def header(src_lines, node):
    """First line(s) of a def/class, up to the ':' that starts its body."""
    first, last = node.lineno - 1, (node.body[0].lineno - 2) if node.body else node.lineno - 1
    text = " ".join(l.strip() for l in src_lines[first:max(first, last) + 1])
    return re.sub(r"\s+", " ", text)[:300]


def module_name(rel: str) -> str:
    """'pkg/sub/mod.py' -> 'pkg.sub.mod'   'pkg/__init__.py' -> 'pkg'"""
    parts = Path(rel).with_suffix("").parts
    return ".".join(parts[:-1] if parts[-1] == "__init__" else parts)


def build_index(repo: Path):
    """module name -> (file name, {top-level name: signature}). Test files are skipped."""
    index = {}
    for f in repo.rglob("*.py"):
        if "test" in f.name.lower():
            continue
        try:
            src = f.read_text(encoding="utf-8")
            tree = ast.parse(src)
        except Exception:
            continue
        lines = src.splitlines()
        defs = {}
        for node in tree.body:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                defs[node.name] = header(lines, node)
            elif isinstance(node, ast.ClassDef):
                members = [n for n in node.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]
                sig = "\n".join([header(lines, node)] + ["    " + header(lines, m) for m in members[:15]])
                defs[node.name] = sig[:1000]
        index[module_name(str(f.relative_to(repo)))] = (f.name, defs)
    return index


def find_module(index, dotted: str):
    """Exact match, else a key ending in '.dotted' (handles src/ layouts)."""
    if dotted in index:
        return dotted
    hits = [k for k in index if k.endswith("." + dotted)]
    return hits[0] if len(hits) == 1 else None


def file_imports(index, rel: str, tree):
    """What this file imports from OTHER repo files.
    names:   local name -> (module, name)   e.g. circle_area -> ('pkg.geo', 'circle_area')
    modules: local name -> module           e.g. geo -> 'pkg.geo'   (for geo.circle_area)"""
    names, modules = {}, {}
    here = module_name(rel).split(".")
    pkg = here if Path(rel).name == "__init__.py" else here[:-1]
    for node in tree.body:
        if isinstance(node, ast.ImportFrom):
            base = pkg[:max(0, len(pkg) - (node.level - 1))] if node.level else []
            dotted = ".".join(base + (node.module.split(".") if node.module else []))
            mod = find_module(index, dotted) if dotted else None
            for a in node.names:
                local = a.asname or a.name
                sub = find_module(index, f"{dotted}.{a.name}" if dotted else a.name)
                if sub:                                    # from pkg import geo  -> a module
                    modules[local] = sub
                elif mod and a.name in index[mod][1]:      # from pkg.geo import circle_area
                    names[local] = (mod, a.name)
        elif isinstance(node, ast.Import):
            for a in node.names:
                mod = find_module(index, a.name)
                if mod:                                    # import pkg.geo as geo
                    modules[a.asname or a.name] = mod
    return names, modules


def cheat_sheet(index, rel, prefix, tree):
    """Imported names used in the last 400 chars before the cursor -> their signatures (max 5)."""
    names, modules = file_imports(index, rel, tree)
    window = prefix[-400:]
    extra, seen = [], set()

    def add(mod, name):
        key = (mod, name)
        if key not in seen and len(extra) < 5 and name in index[mod][1]:
            seen.add(key)
            extra.append({"filename": index[mod][0], "text": index[mod][1][name]})

    for name in re.findall(r"[A-Za-z_][A-Za-z0-9_]*", window):
        if name in names:
            add(*names[name])
    for alias, attr in re.findall(r"\b([A-Za-z_]\w*)\.([A-Za-z_]\w*)", window):
        if alias in modules:
            add(modules[alias], attr)
    return extra


# ---------- completion points ----------

def line_points(src, tree):
    """One-line statements inside function bodies -> hide the rest of the line."""
    starts = [0]
    for line in src.splitlines(keepends=True):
        starts.append(starts[-1] + len(line))
    for fn in ast.walk(tree):
        if not isinstance(fn, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        for st in fn.body:
            if st.lineno != st.end_lineno or isinstance(st, (ast.Pass, ast.Expr)) and isinstance(getattr(st, "value", None), ast.Constant):
                continue
            line = src[starts[st.lineno - 1]:starts[st.lineno]].rstrip("\n")
            code_start = len(line) - len(line.lstrip())
            body = line[code_start:]
            if len(body) < 12:
                continue
            # cut after "= " or after the first "(", else in the middle at a space
            m = re.search(r"=\s|\(", body)
            cut = m.end() if m and m.end() < len(body) - 3 else body.rfind(" ", 0, len(body) // 2) + 1
            if cut <= 0:
                continue
            pos = starts[st.lineno - 1] + code_start + cut
            end = starts[st.lineno - 1] + len(line)
            yield "line", pos, end


def block_points(src, tree):
    """Compound statements (if/for/while/with/try) of 2-6 lines -> hide the whole statement."""
    starts = [0]
    for line in src.splitlines(keepends=True):
        starts.append(starts[-1] + len(line))
    for node in ast.walk(tree):
        if isinstance(node, (ast.If, ast.For, ast.While, ast.With, ast.Try)) and 2 <= node.end_lineno - node.lineno + 1 <= 6:
            line = src[starts[node.lineno - 1]:starts[node.lineno]]
            pos = starts[node.lineno - 1] + len(line) - len(line.lstrip())
            end = starts[node.end_lineno] - 1 if node.end_lineno < len(starts) - 1 else len(src)
            yield "block", pos, end


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repos", default="repos")
    ap.add_argument("--out", default="data/points.jsonl")
    ap.add_argument("--n", type=int, default=250)
    ap.add_argument("--seed", type=int, default=0)
    args = ap.parse_args()
    rng = random.Random(args.seed)

    candidates = []
    for repo in sorted(p for p in Path(args.repos).iterdir() if p.is_dir()):
        index = build_index(repo)
        repo_cands = []
        for f in sorted(repo.rglob("*.py")):
            if "test" in f.name.lower():
                continue
            try:
                src = f.read_text(encoding="utf-8")
                tree = ast.parse(src)
            except Exception:
                continue
            pts = list(line_points(src, tree)) + list(block_points(src, tree))
            rng.shuffle(pts)
            for kind, pos, end in pts[:MAX_PER_FILE]:
                rel = str(f.relative_to(repo))
                prefix, middle, suffix = src[:pos], src[pos:end], src[end:]
                repo_cands.append({
                    "repo": repo.name, "path": rel, "kind": kind,
                    "prefix": prefix, "middle": middle, "suffix": suffix,
                    "extra": cheat_sheet(index, rel, prefix, tree),
                })
        rng.shuffle(repo_cands)
        candidates += repo_cands[:MAX_PER_REPO]

        # balance: ~60% line, ~40% block

    # balance: ~60% line, ~40% block
    lines = [c for c in candidates if c["kind"] == "line"]
    blocks = [c for c in candidates if c["kind"] == "block"]
    rng.shuffle(lines); rng.shuffle(blocks)
    n_block = min(len(blocks), int(args.n * 0.4))
    chosen = blocks[:n_block] + lines[:args.n - n_block]
    rng.shuffle(chosen)   # mix line and block points (so --limit gives a fair sample)
    for i, c in enumerate(chosen):
        c["id"] = i

    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    with open(args.out, "w") as f:
        for c in chosen:
            f.write(json.dumps(c) + "\n")
    print(f"wrote {len(chosen)} points ({len(chosen) - n_block} line, {n_block} block) "
          f"from {len({c['repo'] for c in chosen})} repos -> {args.out}")
    print(f"points with a cheat sheet: {sum(1 for c in chosen if c['extra'])}")


if __name__ == "__main__":
    main()