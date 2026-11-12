import json
from pathlib import Path

log = Path(__file__).parent.parent / "server" / "logs" / "prompts.jsonl"
out = Path(__file__).parent / "results" / "inspect.md"

rows = [json.loads(l) for l in log.open()]
rows = [r for r in rows if r["extra"]]          # only calls that had a cheat sheet

print(f"{len(rows)} prompts with a cheat sheet")
print(f"  prefix cut (top of file not seen): {sum(r['prefix_cut'] for r in rows)}")
print(f"  cheat sheet partly dropped:        {sum(r['extra_dropped'] > 0 for r in rows)}")

with out.open("w") as f:
    for i, r in enumerate(rows, 1):
        f.write(f"## {i}  tokens={r['tokens_evaluated']}  prefix_cut={r['prefix_cut']}  "
                f"extra_dropped={r['extra_dropped']}/{len(r['extra'])}\n\n")
        f.write("**Model output:**\n```python\n" + r["raw_text"] + "\n```\n\n")
        f.write("**What the model saw:**\n```\n" + (r["prompt"] or "(none)") + "\n```\n\n")
print("wrote", out)