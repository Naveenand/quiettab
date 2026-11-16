# QuietTab

![Build](https://github.com/Naveenand/quiettab/workflows/Build/badge.svg)

**Copilot-style autocomplete for JetBrains IDEs that stays quiet when it isn't sure.**
Gray text from a local model, Tab to accept. Your code never leaves your machine.

<!-- TODO: add demo GIF here: ![demo](docs/demo.gif) -->

Most autocomplete tools show a suggestion every time you pause. A wrong suggestion costs you a glance and a
decision, so a tool that is wrong half the time is noise. QuietTab only shows a suggestion when it is likely
you will accept it, and it learns, per project, how often that is.

## What it does

- **Inline gray-text completions** in IntelliJ-based IDEs (built and tested on IntelliJ IDEA 2026.2, Python files).
  <kbd>Tab</kbd> accepts, <kbd>Ctrl</kbd>+<kbd>→</kbd> accepts word by word, keep typing to ignore.
- **Local model:** Qwen2.5-Coder-1.5B (fill-in-the-middle) via llama.cpp. Nothing is sent to the cloud.
- **Stays quiet when unsure:** a calibrated confidence gate hides suggestions that are probably wrong.
- **Learns per project:** the self-tuning gate adjusts to your own accepts and rejects in each repo.
- **Secure by default:** secrets are kept away from the model and the logs, and risky code
  (for example `verify=False`, SQL built from strings) is never suggested.
- **Measurable:** every suggestion and what you did with it is logged locally, so every number below can be re-derived.

## How it works

```
You type ─► Plugin (Kotlin, IntelliJ)                      Server (Python, FastAPI)            Model (llama.cpp)
            1. Gate 0: skip bad moments                    5. Lock: token, Host, size checks
               (comments, secret files, code after cursor) 6. Hide secrets before the model ─► 7. Fill in the middle
            2. Wait up to 300 ms, cancel stale requests                                        + confidence per token
            3. Context: code around the cursor             8. Cleanup: cut at block end,
               + imports and signatures from other files      no repeated closing brackets
               (PSI "cheat sheet")                          9. Confidence gate + self-tuning
                                                              + security check on the output
            10. Gate 2: no new syntax errors  ◄────────────
            11. Gray text. Tab / reject is logged, and the gate learns from it.
```

**The confidence gate.** The model reports how sure it was about each token. A small logistic regression,
trained on 235 graded suggestions, turns that into `p_good`, the chance the suggestion is good.
Only suggestions above a bar are shown (multi-line suggestions get a stricter bar).

**Self-tuning silence** (`server/tuner.py`). The offline gate ranks suggestions well on new code, but its cutoff
doesn't transfer: shown suggestions were good 60% of the time on the training repos and 16% on unseen 2025 code.
So for each project, QuietTab learns a small correction (2-3 numbers) that turns `p_good` into
`q`, "the chance you press Tab", from your own accepts and rejects:

- Show a suggestion only if `q >= 0.30` (`QT_TAU`). With a reward of +0.75 per accept and -0.25 per reject,
  showing pays off above 25%.
- Day one, it behaves exactly like the offline gate. It refits every 10 outcomes, moves slowly
  (the offline gate counts as 10 votes), and weights recent outcomes more (half-life 150).
- 5% of suggestions just under the bar are shown anyway (`explore=true`), so it can also learn when it is too quiet.
- `GET /calibration?repo=<id>` shows the learned numbers, tuned vs offline show rate, and predicted vs actual acceptance.

## Quick start

You need: a GPU (tested on an NVIDIA RTX 5070 Ti, 16 GB; Apple Silicon should work with `brew install llama.cpp`, not yet tested),
[llama.cpp](https://github.com/ggml-org/llama.cpp) (check `llama-server --version`: b11393 or newer),
Python 3.11+, and an IntelliJ-based IDE 2026.2+.

> Windows + WSL: the model and server run in WSL, the IDE runs on Windows. They share one token file,
> so start the server with `QT_TOKEN_FILE` pointing at your Windows home (step 2). On macOS/Linux nothing extra is needed.

**1. Model** (terminal 1)
```bash
mkdir -p ~/.quiettab
[ -f ~/.quiettab/llama_key ] || python3 -c "import secrets;print(secrets.token_urlsafe(32))" > ~/.quiettab/llama_key
llama-server --fim-qwen-1.5b-default --host 127.0.0.1 --port 8012 --api-key "$(cat ~/.quiettab/llama_key)"
```
The first run downloads the model (about 1.6 GB). On an 8 GB Mac, add `-c 8192`.

**2. Server** (terminal 2)
```bash
git clone https://github.com/Naveenand/quiettab.git && cd quiettab
python3 -m venv ~/quiettab-env && source ~/quiettab-env/bin/activate
pip install -r server/requirements.txt
cd server
# Windows + WSL only:
# export QT_TOKEN_FILE="$(wslpath "$(cmd.exe /c 'echo %USERPROFILE%' 2>/dev/null | tr -d '\r')")/.quiettab/token"
uvicorn app:app --host 127.0.0.1 --port 8000
```
On first start the server creates the shared token in `~/.quiettab/token` (or `QT_TOKEN_FILE`).

**3. Plugin**
- Easiest: open the latest green [Build run](https://github.com/Naveenand/quiettab/actions), download the
  `plugin-distribution` artifact, unzip it, then in the IDE: <kbd>Settings</kbd> > <kbd>Plugins</kbd> > <kbd>⚙</kbd> >
  <kbd>Install Plugin from Disk...</kbd> and pick the plugin zip.
- From source: open the repo in IntelliJ IDEA (JDK 21) and run the **Run Plugin** configuration.
  A sandbox IDE opens with QuietTab installed.

**4. Try it.** Open a Python file and type `def add(a, b):`, Enter, `return `. Gray text `a + b` appears; press <kbd>Tab</kbd>.

**Check that it's working**
```bash
curl -s -o /dev/null -w "%{http_code}\n" -X POST localhost:8000/complete     # 401 = the lock works
cd server && pip install pytest && python -m pytest -q                       # all tests pass
tail -F server/logs/events.jsonl                                             # live events
```
No gray text? In the IDE: <kbd>Help</kbd> > <kbd>Show Log in Explorer/Finder</kbd>, open `idea.log`, search "QuietTab".
`no token at ...` means the token path differs between IDE and server (see the WSL note above).

## Settings

| Env var (server) | Default | What it does |
|---|---|---|
| `QT_TAU` | `0.30` | Minimum chance of acceptance to show. Higher = quieter. |
| `QT_EXPLORE` | `0.05` | Share of just-under-the-bar suggestions shown as a test. |
| `QT_TUNER` | `1` | `0` = use the offline gate only (no per-project learning). |
| `QT_SECURITY_POLICY` | `server/security_policy.json` | Per-team rules: `block`, `warn`, or `off` for each rule id. See `security_policy.example.json`. |
| `QT_TOKEN_FILE` | `~/.quiettab/token` | Shared secret between plugin and server. |
| `QT_DEBUG` | off | `1` = also save full prompts to `logs/prompts.jsonl` (debugging only). |

## Results

All numbers are reproducible with the scripts in `eval/` (see "Reproduce" below).

**Completion quality** (Qwen2.5-Coder-1.5B Q8_0, local RTX 5070 Ti)

| test set | points | exact match | valid code | server latency p50 / p90 |
|---|---|---|---|---|
| Held-out Python repos (+cleanup +context) | 250 | 25.2% | 97.2% | 59 / 270 ms |
| [Real-FIM-Eval](https://huggingface.co/datasets/gonglinyuan/real_fim_eval) (new code from 2025 commits) | 300 | 1.7% | 77.7% | 172 / 273 ms |

End-to-end (keystroke to gray text, measured in the IDE): p90 about 450 ms, under the 500 ms target.

**The confidence gate** (235 graded suggestions, each repo scored by a model that never saw it)

| | shown | good among shown |
|---|---|---|
| Show everything | 100% | 36% |
| Confidence gate (bar 0.40) | 43% | 60% |

- Multi-line suggestions got their own bar (0.44): good among shown went from 42% to 61%.
- On unseen 2025 code the same gate raised good-among-shown from 7% to 16%: the ranking transfers, the cutoff doesn't.
  That's why the self-tuning gate exists.

**Self-tuning gate** (simulation, `eval/simulate_tuner.py`: 20 runs x 2,000 suggestions; score per 100 suggestions, +0.75 accept / -0.25 reject)

| situation | offline gate | self-tuning | best possible |
|---|---|---|---|
| Unfamiliar code | -3.6 (shows 39%) | 0.0 (shows 4%) | +0.3 |
| Familiar code | 17.4 | 17.5 (finds 96% of good ones vs 83%) | 17.9 |
| Two repos, switching | 7.4 (one shared bar: 7.3) | 9.0 | 9.4 |
| Code changes halfway | -3.6 | -0.8 | +0.3 |

<!-- TODO (Phase 8): real-use numbers: acceptance rate, chars per accept, show rate, e2e p50/p90, /calibration per repo -->

**Security gate** (`server/secguard.py`): on 3.49 M lines of real Python it blocked 125 lines with 10 false alarms
(about 1 per 350k lines), about 6x quieter than Bandit (medium/high), and caught 77% of Bandit's findings
in the categories it covers.

**Speed work**
- Stale requests are really aborted: in a fast-typing test, cancelled requests went from 3 to 20.
- Prompt-cache-friendly window: prompt tokens re-read per request, p50 442 -> 5; prompt time p50 22 -> 11 ms.

## Security

- Model and server listen on `127.0.0.1` only. llama-server needs an API key.
- Every server call needs a token (`X-QuietTab-Token`). Requests with a foreign `Host` (DNS rebinding) or a browser `Origin` are refused.
  Body sizes are capped.
- Before sending code, the plugin checks it is talking to the real server (HMAC challenge on `/health`), so a program squatting on port 8000 gets nothing.
- Secret files (`.env`, keys, credentials) are never read. Secrets inside normal files are replaced with `REDACTED` before the model and in logs.
  While you type a secret (`API_KEY = "`), the model isn't called.
- Suggestions with secrets or risky patterns are refused with a rule id
  (`tls_verify_off`, `sql_string_build`, `yaml_unsafe_load`, `jwt_no_verify`, ...). Teams can set each rule to `block`, `warn` or `off`.
- Logs rotate (`events.jsonl` -> `events.1-3.jsonl`) instead of growing forever.

## What didn't work (and limits)

- A 5-feature gate was no better than confidence alone, so the gate uses one feature.
- Cross-file context: only 32 of 250 eval points had a cheat sheet. It made valid code 100% on those, but exact match didn't move.
- Real-FIM exact match is low (2%): guessing code someone decided to add is much harder than filling a gap in existing code.
- The self-tuning gate is measured in simulation. Real-use numbers are next. It adapts only partly after a big change in the code.
- Confidence is computed on the raw model output, including parts cleanup removes.
- Uses IntelliJ's inline-completion API, which is partly internal (the plugin verifier reports it as compatible with 2026.2 and 2026.3).
- Auto-inserted closing brackets can make the gray text flicker. Apostrophes in comments can look like strings to the cleanup.
- Only Python is tested.

## Project layout

```
src/main/kotlin/.../QuietTabProvider.kt   plugin: gates 0 and 2, context (PSI), cancel, accept tracking
server/app.py                             /complete, /log, /stats, /calibration
server/cleanup.py                         output cleanup
server/guard.py  server/secguard.py       lock + security gate
server/tuner.py                           self-tuning silence
server/gate.json                          offline confidence gate
eval/                                     dataset builder, eval runner, gate training, tuner simulation
```

## Reproduce the eval

```bash
pip install -r eval/requirements.txt && cd eval
python make_dataset.py                        # 250 fill-in points from held-out repos in eval/repos/
python run_eval.py --name baseline            # needs the model + server running
python summarize.py results/baseline.jsonl
python train_gate.py --features avg_logprob --target-precision 0.6   # writes server/gate.json
python import_realfim.py --n 300 && python run_eval.py --points data/realfim.jsonl --name realfim
python simulate_tuner.py                      # self-tuning gate simulation (~30 s)
```

## Next steps

- **Next-edit prediction:** use recent edits to predict the next change, not just the next characters.
- **Own the prompt:** call llama.cpp's `/completion` with our own FIM template (real file name, stable cache).
- **Any engine:** a backend interface for vLLM, Ollama or any OpenAI-compatible FIM server, each with its own calibrated gate.
- **Learned Gate 0** and a nightly per-user retrain of the gate from `events.jsonl`.
- **AST-aware FIM fine-tuning** and a settings page in the IDE.

Plugin based on the [IntelliJ Platform Plugin Template](https://github.com/JetBrains/intellij-platform-plugin-template).
