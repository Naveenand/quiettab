import builtins, json, keyword, re
from collections import Counter
from pathlib import Path

HERE = Path(__file__).parent
RUN = HERE / "results" / "newline_fix.jsonl"
LOG = HERE.parent / "server" / "logs" / "prompts.jsonl"
OUT = HERE / "results" / "cheatsheet_check.md"

SKIP = set(keyword.kwlist) | set(dir(builtins)) | {"self", "cls"}
for t in (str, list, dict, set, tuple, int, float, bytes):
    SKIP |= set(dir(t))          # common methods like .append, .strip
def names(s):
    s = re.sub(r"<\|\w+\|>", " ", s)                 # drop special tokens
    return set(re.findall(r"[A-Za-z_]\w*", s)) - SKIP

def split(prompt):                                   # cut the prompt into its 3 parts
    sheet, _, rest = prompt.partition("<|file_sep|>filename\n")
    prefix, _, rest = rest.partition("<|fim_suffix|>")
    return sheet, prefix, rest.split("<|fim_middle|>")[0]

results = [json.loads(l) for l in RUN.open()]
results = [r for r in results if r["has_extra"] and "context" in r["variant"]]
prompts = [p for p in map(json.loads, LOG.open()) if p["extra"]]
assert len(results) == len(prompts), f"{len(results)} results vs {len(prompts)} prompts"

cats, used_ok, lines, all_missing = Counter(), 0, [], Counter()
for r, p in zip(results, prompts):
    if r["pred"].strip()[:20] not in p["raw_text"]:
        print(f"warning: id {r['id']} may be matched to the wrong prompt")
    sheet, prefix, suffix = split(p["prompt"])
    needed = names(r["middle"]) - names(prefix) - names(suffix)   # names not in the file
    missing = needed - names(sheet)
    all_missing.update(missing)
    if not needed:
        cat = "A: answer needs no outside names"
    elif missing:
        cat = "C: cheat sheet MISSING the name (retrieval miss)"
    else:
        cat = "B: cheat sheet HAD the name"
        used_ok += needed <= names(r["pred"])
    cats[cat] += 1
    lines.append(f"## id {r['id']} - {cat}\n- needed: {sorted(needed)}  missing: {sorted(missing)}\n"
                 f"- correct: `{r['middle'].strip()[:120]}`\n- model:   `{r['pred'].strip()[:120]}`\n")

for cat, n in sorted(cats.items()):
    print(f"{n:3d}  {cat}")
print(f"     in B, model used the needed name(s): {used_ok}/{cats['B: cheat sheet HAD the name']}")
OUT.write_text("\n".join(lines))
print("wrote", OUT)
print("most common missing names:", all_missing.most_common(15))