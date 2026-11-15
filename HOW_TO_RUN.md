# How to run QuietTab

Three parts: the **model** (llama.cpp), the **server** (FastAPI, Python), and the **plugin** (Kotlin, IntelliJ).
Tested on Windows 11 + WSL2 Ubuntu, RTX 5070 Ti (16 GB), IntelliJ IDEA 2026.2.3, JDK 21, Python 3.14.

## 1. Model (WSL)
Build or install [llama.cpp](https://github.com/ggml-org/llama.cpp) with CUDA, then:
```bash
llama-server --fim-qwen-1.5b-default --port 8012
```
The first run downloads Qwen2.5-Coder-1.5B (Q8_0). It listens on 127.0.0.1:8012.

## 2. Server (WSL, second terminal)
```bash
python3 -m venv ~/quiettab-env
source ~/quiettab-env/bin/activate
pip install -r server/requirements.txt
cd server
uvicorn app:app --host 127.0.0.1 --port 8000
```
Check it:
```bash
curl -s localhost:8000/complete -H "Content-Type: application/json" \
  -d '{"prefix":"def add(a, b):\n    return ","suffix":"\n"}'
curl -s localhost:8000/stats
```
The first call returns `"text": "a + b"` with `p_good` and `show`.

Optional: start with `QT_DEBUG=1 uvicorn ...` to save every prompt to `server/logs/prompts.jsonl` (for debugging only).

## 3. Plugin (Windows, IntelliJ IDEA 2026.2)
1. Open the repo folder in IntelliJ IDEA (JDK 21).
2. Run the **Run Plugin** configuration (Gradle `runIde`). A sandbox IDE opens with QuietTab installed.
3. In the sandbox, open any Python file and type. Gray text appears when QuietTab is confident; **Tab** accepts.

Events (shown / accepted / rejected / gated / ...) are logged to `server/logs/events.jsonl`. Watch them live:
```bash
tail -F ---disable-inotify -s 1 server/logs/events.jsonl
```

## 4. Evaluation (optional, WSL)
```bash
pip install -r eval/requirements.txt
cd eval
python make_dataset.py                                 # build the 250-point eval set (see --help)
python run_eval.py --name baseline                     # needs the model + server running
python summarize.py results/baseline.jsonl             # EM, chrF, valid code, latency
python train_gate.py --features avg_logprob --target-precision 0.6   # writes server/gate.json
python block_gate.py results/baseline.jsonl --target 0.6             # adds block_threshold
python import_realfim.py --n 300                       # unseen 2025 code (Real-FIM-Eval)
python run_eval.py --points data/realfim.jsonl --name realfim
python check_gate.py results/realfim.jsonl             # frozen gate on unseen code
```
Restart uvicorn after changing `server/gate.json`.
