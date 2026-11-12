## 1  tokens=464  prefix_cut=False  extra_dropped=0/3

**Model output:**
```python
Agent(settings=settings, kb=kb, services=services)
```

**What the model saw:**
```
<|repo_name|>myproject
<|file_sep|>agent.py
def make_llms(settings: Settings):<|file_sep|>retrieval.py
class WebSearcher:
    def __init__(self, tool):
    def from_settings(cls, settings: Settings) -> "WebSearcher":
    def search(self, query: str) -> list[Document]:<|file_sep|>workflow.py
class Services:<|file_sep|>filename
<|fim_prefix|>er), vectorstore


def build_components(settings: Settings) -> Components:
    missing = settings.missing_keys()
    if missing:
        raise RuntimeError(f"Missing API keys: {', '.join(missing)}. Set them in .env or the environment.")
    from sentence_transformers import CrossEncoder  # heavy import, only when really starting

    kb, vectorstore = build_knowledge_base(settings)
    retriever = HybridRetriever(
        vectorstore=vectorstore,
        bm25_index=BM25Index([]),  # filled from the chunk store by refresh_if_stale below
        reranker=CrossEncoder(settings.rerank_model),
        settings=settings,
    )
    kb.retriever = retriever
    kb.refresh_if_stale()  # records the store version the index was built from
    if kb.store.count() == 0 and settings.auto_ingest:
        # Hosts with a wiped disk on restart (e.g. Hugging Face Spaces): rebuild the local chunk store.
        # Chunks already in Pinecone are skipped, so this is quick and costs nothing extra.
        logger.info("Knowledge base is empty; AUTO_INGEST is on, ingesting the default sources.")
        kb.ingest_defaults()
    if kb.store.count() == 0:
        logger.warning("Knowledge base is empty. Run `python cli.py ingest` or upload a document.")

    llm_fast, llm_strong = make_llms(settings)
    web = WebSearcher.from_settings(settings) if settings.enable_web else None
    services = Services(settings=settings, llm_fast=llm_fast, llm_strong=llm_strong, retriever=retriever, web=web)
    agent = <|fim_suffix|>
    return Components(settings=settings, agent=agent, kb=kb, audit=AuditLog(settings.audit_db_path))
<|fim_middle|>
```

## 2  tokens=405  prefix_cut=False  extra_dropped=0/1

**Model output:**
```python
for check in CHART_CHECKS:
            problems.extend(check(xml))
    return problems
```

**What the model saw:**
```
<|repo_name|>myproject
<|file_sep|>__init__.py
def part_text(data: bytes) -> str:<|file_sep|>filename
<|fim_prefix|>nonical) >= AXID_MINIMUM[kind]:
            hint = f"Fix: point them at the axes this part declares ({', '.join(canonical)})"
        else:
            hint = ("Fix: the part declares several axes of a kind -- declare the "
                    "secondary axes the series expects, or drop them")
        detail = (f"of which {', '.join(dead)} name no declared axis"
                  if dead else f"only {len(ids)} of which this part declares")
        problems.append(
            f"{part}: <c:{kind}> references axId {', '.join(ids)}, {detail}, "
            f"leaving fewer than two live axes; PowerPoint discards the chart. {hint}"
        )
    return problems


def _ext_lst_spans(text: str) -> list[tuple[int, int]]:
    spans: list[tuple[int, int]] = []
    depth = 0
    start = 0
    for match in re.finditer(r"<(/?)c:extLst\b[^>]*?(/?)>", text):
        closing, self_closing = match.group(1), match.group(2)
        if self_closing:
            continue
        if closing:
            depth -= 1
            if depth == 0:
                spans.append((start, match.end()))
        else:
            if depth == 0:
                start = match.start()
            depth += 1
    return spans


CHART_CHECKS = (_check_stacked_label_positions, _check_chart_axis_references)


def find_chart_problems(files: Mapping[str, bytes]) -> list[str]:
    problems: list[str] = []
    for part in sorted(n for n in files if _CHART_PART_RE.fullmatch(n)):
        xml = part_text(files[part])
        <|fim_suffix|>
    return problems
<|fim_middle|>
```

## 3  tokens=675  prefix_cut=False  extra_dropped=0/1

**Model output:**
```python
False}
```

**What the model saw:**
```
<|repo_name|>myproject
<|file_sep|>base.py
class ProviderProfile:
    def fetch_account_usage( self, *, base_url: str | None = None, api_key: str | None = None ) -> AccountUsageSnapshot | None:
    def resolve_aux_model(self, *, vision: bool = False) -> str:
    def get_hostname(self) -> str:
    def prepare_messages(self, messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    def build_extra_body( self, *, session_id: str | None = None, **context: Any ) -> dict[str, Any]:
    def default_reasoning_config(self, model: str | None = None) -> dict | None:
    def build_api_kwargs_extras( self, *, reasoning_config: dict | None = None, **context: Any, ) -> tuple[dict[str, Any], dict[str, Any]]:
    def build_client_kwargs_extras(self, **context: Any) -> dict[str, Any]:
    def default_vision_model(self) -> str | None:
    def get_model_context_length(self, model: str) -> int | None:
    def get_usage_cost(self, model: str, usage: Any) -> Any | None:
    def get_max_tokens(self, model: str | None) -> int | None:
    def support<|file_sep|>filename
<|fim_prefix|>"""Tencent TokenHub provider profile (OpenAI-compatible, tokenhub.tencentmaas.com).

Request quirk: top-level ``reasoning_effort``, clamped to TokenHub's low/medium/high and omitted
when thinking is off; a main-loop turn with no configured effort sends ``high``.

Endpoint, ``TOKENHUB_API_KEY``, aliases and the static Hy model list stay in
``hermes_cli/auth.py`` / ``hermes_cli/models_catalog_static.py``. ``base_url`` is left empty so
model listing keeps today's paths: first-time setup probes ``{base}/models`` through the generic
fallback and the ``/model`` picker serves the curated list. The doctor probe stays off.
"""

from typing import Any

from agent.reasoning_effort import requested_effort, tokenhub_effort
from providers import register_provider
from providers.base import ProviderProfile


class TokenHubProfile(ProviderProfile):
    """TokenHub: top-level ``reasoning_effort``; main-loop turns default to ``high``."""

    def default_reasoning_config(self, model: str | None = None) -> dict | None:
        """Unset effort on a main-loop turn: ``high`` (TokenHub's own default is weaker).
        Auxiliary calls never take this default, so an unset aux call sends no effort."""
        return {"enabled": <|fim_suffix|>

    def build_api_kwargs_extras(
        self, *, reasoning_config: dict | None = None, **context: Any,
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        # No config (an auxiliary call with no effort configured): send nothing. Main-loop turns
        # reach here with ``default_reasoning_config`` filled in.
        if not reasoning_config or not isinstance(reasoning_config, dict) or reasoning_config.get("enabled") is False:
            return {}, {}
        return {}, {"reasoning_effort"<|fim_middle|>
```

## 4  tokens=532  prefix_cut=False  extra_dropped=0/1

**Model output:**
```python
request.rel_url.path
```

**What the model saw:**
```
<|repo_name|>myproject
<|file_sep|>base.py
class UpstreamAdapter(ABC):
    def name(self) -> str:
    def display_name(self) -> str:
    def allowed_paths(self) -> frozenset[str]:
    def is_authenticated(self) -> bool:
    def get_credential(self) -> UpstreamCredential:
    def get_retry_credential( self, *, failed_credential: UpstreamCredential, status_code: int ) -> Optional[UpstreamCredential]:
    def describe(self) -> str:<|file_sep|>filename
<|fim_prefix|>
    the single loop and every other in-flight streaming completion.
    """
    _require_aiohttp()
    # The bind address is fixed for the app's lifetime, so derive the Host policy once.
    bound = _canonical_host(bound_host.strip("[]"))
    wildcard = _is_wildcard(bound)
    allowed_hosts = _LOOPBACK_HOSTS | {bound}

    @web.middleware
    async def local_only(request: web.Request, handler):
        refusal = _local_request_error(
            request.headers.get("Host", ""),
            request.headers.get("Origin"),
            request.headers.get("Sec-Fetch-Site"),
            wildcard=wildcard,
            allowed_hosts=allowed_hosts,
        )
        if refusal:
            return _json_error(
                403,
                "Request refused: browser requests and foreign Host names are not accepted by this proxy.",
                code=refusal,
            )
        return await handler(request)

    app = web.Application(client_max_size=MAX_REQUEST_BYTES, middlewares=[local_only])
    # AppKey: forward-compat with aiohttp versions that strip bare-string keys.
    app[web.AppKey("adapter", UpstreamAdapter)] = adapter

    async def handle_health(request: web.Request) -> web.Response:
        authenticated = await asyncio.to_thread(adapter.is_authenticated)
        return web.json_response({"status": "ok", "upstream": adapter.display_name, "authenticated": authenticated})

    async def handle_proxy(request: web.Request) -> web.StreamResponse:
        rel_path = <|fim_suffix|>
        if rel_path not in adapter.allowed_paths:
            allowed = ", ".join(sorted(adapter.allowed_paths))
            return _json_error(
                404, f"Path /v1{rel_path} is not forwarded by this proxy. Allowed: {allowed}", code="path_not_allowed"
            )
        try:
            cred = await asyncio.to_thread(adapter.get_credential)
        except Exception as exc:
            logger.warning("proxy: credential resolution failed: %s", exc)
            return _json_error(40<|fim_middle|>
```

## 5  tokens=142  prefix_cut=False  extra_dropped=0/1

**Model output:**
```python
FirecrawlWebSearchProvider())
```

**What the model saw:**
```
<|repo_name|>myproject
<|file_sep|>provider.py
class FirecrawlWebSearchProvider(BaseWebSearchProvider):
    def is_available(self) -> bool:
    def search(self, query: str, limit: int = 5) -> dict[str, Any]:
    async def extract(self, urls: list[str], **kwargs: Any) -> list[dict[str, Any]]:
    def get_setup_schema(self) -> dict[str, Any]:<|file_sep|>filename
<|fim_prefix|>"""Firecrawl web search + extract plugin — bundled, auto-loaded."""
from __future__ import annotations
from plugins.web.firecrawl.provider import FirecrawlWebSearchProvider


def register(ctx) -> None:
    ctx.register_web_search_provider(<|fim_suffix|>
<|fim_middle|>
```

## 6  tokens=622  prefix_cut=False  extra_dropped=0/5

**Model output:**
```python
file.filename.rsplit(".", 1)[-1].lower()
```

**What the model saw:**
```
<|repo_name|>myproject
<|file_sep|>deps.py
def require_admin( x_admin_key: str = Header(default="", description="Admin key for ingestion and audit endpoints"), settings: Settings = Depends(get_app_settings), ) -> None:<|file_sep|>bootstrap.py
class Components:<|file_sep|>deps.py
def get_components(request: Request) -> Components:<|file_sep|>config.py
class Settings(BaseSettings):
    def _env_name(cls, v: str) -> str:
    def chunk_db_path(self) -> Path:
    def audit_db_path(self) -> Path:
    def checkpoint_db_path(self) -> Path:
    def is_production(self) -> bool:
    def missing_keys( self, needed: tuple[str, ...] = ("openai_api_key", "pinecone_api_key", "tavily_api_key") ) -> list[str]:
    def check_production_safety(self) -> None:<|file_sep|>deps.py
def get_app_settings(request: Request) -> Settings:<|file_sep|>filename
<|fim_prefix|>request_id_var.set(request_id)
        except Exception as exc:
            request_id_var.set(request_id)
            logger.exception("Streaming chat failed")
            components.audit.record(
                question=question, request_id=request_id, thread_id=thread_id, error=type(exc).__name__
            )
            yield sse("error", {"detail": "The agent failed to answer. Please try again.", "request_id": request_id})

    return StreamingResponse(
        events(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},  # no proxy buffering
    )


# ---------------------------------------------------------------------------
# Knowledge base
# ---------------------------------------------------------------------------


@router.get("/sources", response_model=list[SourceInfo], tags=["knowledge base"])
def list_sources(components: Components = Depends(get_components)):
    """Documents currently in the knowledge base."""
    return components.kb.store.sources()


@router.post(
    "/ingest/file", response_model=IngestResponse, tags=["knowledge base"], dependencies=[Depends(require_admin)]
)
def ingest_file(
    file: UploadFile = File(...),
    components: Components = Depends(get_components),
    settings: Settings = Depends(get_app_settings),
):
    """Upload a PDF, DOCX, Markdown, TXT or HTML file. Re-uploading the same file name replaces it."""
    name = safe_filename(file.filename or "")
    suffix = <|fim_suffix|>
    if suffix not in SUPPORTED_EXTENSIONS:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, f"Unsupported file type. Use: {', '.join(sorted(SUPPORTED_EXTENSIONS))}"
        )

    max_bytes = settings.max_upload_mb * 1024 * 1024
    data = file.file.read(max_bytes + 1)  # read at most one byte past the limit
    if len(data) > max_bytes:
        raise HTTPException(status.HTTP_413_CONTENT_TOO_LARGE, f"File is larger than {settings.max_upload_mb} MB")
    if not data:
      <|fim_middle|>
```

## 7  tokens=557  prefix_cut=False  extra_dropped=0/1

**Model output:**
```python
_data_dir() / name
```

**What the model saw:**
```
<|repo_name|>myproject
<|file_sep|>hermes_constants.py
def get_hermes_home() -> Path:<|file_sep|>filename
<|fim_prefix|>ifestyle", "calendar", metric="weekend_sessions", tiers=[25, 75, 200, 600, 1500]),
    _ach("night_shift_operator", "Night Shift Operator", "Run sessions during gremlin hours repeatedly.", "Lifestyle", "moon", metric="night_sessions", tiers=[25, 75, 200, 600, 1500]),
    _ach("cache_hit_appreciator", "Cache Hit Appreciator", "Notice or benefit from prompt/cache behavior.", "Lifestyle", "cache", metric="cache_events", tiers=[100, 300, 1000, 3000, 8000], secret=True),

]

# ---- Durable state files ----

SNAPSHOT_FILE = "scan_snapshot.json"
CHECKPOINT_FILE = "scan_checkpoint.json"
# Checkpoint schema 2: per-session stats read the compaction-archived display history, not just
# the active window. Version 1 caches were computed active-only and are rescanned once.
_CHECKPOINT_SCHEMA_VERSION = 2


def _data_dir() -> Path:
    """Durable data root (``<hermes home>/plugin-data/hermes-achievements/``). State used to
    live in the install tree and died on ``hermes plugins remove``/``update``; legacy files
    migrate on first read (see ``_data_file``)."""
    try:
        from plugins.plugin_storage import plugin_data_dir
        return plugin_data_dir("hermes-achievements")
    except Exception:
        # Standalone dashboard import (no plugins package on sys.path): same layout, computed locally.
        root = get_hermes_home() / "plugin-data" / "hermes-achievements"
        root.mkdir(parents=True, exist_ok=True)
        return root


def _data_file(name: str) -> Path:
    path = <|fim_suffix|>
    if not path.exists():
        legacy = get_hermes_home() / "plugins" / "hermes-achievements" / name
        if legacy.exists():
            try:
                # Two statements so the read (utf-8-sig, tolerates a BOM)
                # and the write (utf-8, never emits one) stay distinct.
                legacy_text = legacy.read_text(encoding="utf-8-sig")
                path.write_text(legacy_text, encoding="utf-8")
            except Exception:
                pass
    return path


def<|fim_middle|>
```

## 8  tokens=501  prefix_cut=False  extra_dropped=0/2

**Model output:**
```python
state["services"]
```

**What the model saw:**
```
<|repo_name|>myproject
<|file_sep|>prompts.py
def format_history(messages: list[AnyMessage], limit: int = 6) -> str:<|file_sep|>state.py
class AgentState(TypedDict, total=False):<|file_sep|>filename
<|fim_prefix|>graph
        logger.warning("%s call failed, using default: %s", schema.__name__, exc)
        return default


# Defence in depth: the LLM router also flags private data, but this regex does not
# depend on the model noticing. If either check fires, the question never goes to the web.
PRIVATE_DATA_RE = re.compile(
    r"[\w.+-]+@[\w-]+\.[\w.]+"  # email address
    r"|\b(?:account|acct|customer|employee|patient|invoice|order|ssn|id)\s*(?:#|no\.?|number)?\s*:?\s*\d{3,}"
    r"|(?<!\w)\+?(?:\d[\s().-]?){9,}\d(?!\w)"  # phone-number-like (10+ digits)
    r"|\b(?:password|api[_ ]?key|secret|token)\b\s*[:=]",
    re.IGNORECASE,
)


def looks_private(text: str) -> bool:
    return bool(PRIVATE_DATA_RE.search(text))


# ============================================================================
# Nodes
# ============================================================================


def trace(state: AgentState, message: str) -> list[str]:
    logger.info(message)
    return state.get("trace", []) + [message]


def _history(state: AgentState, services: Services) -> str:
    # messages[-1] is the current question; history is everything before it
    return format_history(state.get("messages", [])[:-1], services.settings.max_history_messages)


# ---------------------------------------------------------------------------
# Routing
# ---------------------------------------------------------------------------


def route_question(state: AgentState, runtime: Runtime[Services]):
    s = <|fim_suffix|>
    # Fail safe: if the router breaks, assume private data so nothing leaks to the web.
    fallback = RouteDecision(route="retrieve", standalone_question=state["question"], contains_private_data=True)
    decision = structured_call(
        s.llm_fast,
        RouteDecision,
        ROUTER_PROMPT.format(
            kb_description=s.settings.kb_description, history=_history(state, s), question=state["question"]
        ),
        default=fallback,
    )
    standalone = decision.standalone_que<|fim_middle|>
```

## 9  tokens=403  prefix_cut=False  extra_dropped=0/1

**Model output:**
```python
# Write final HTML report (with auto-refresh)
    if args.live:
        live_report_path.write_text(generate_html(output, auto_refresh=True, skill_name=name))
        print(f"\nReport: {live_report_path}", file=sys.stderr)
```

**What the model saw:**
```
<|repo_name|>myproject
<|file_sep|>generate_report.py
def generate_html(data: dict, auto_refresh: bool = False, skill_name: str = "") -> str:<|file_sep|>filename
<|fim_prefix|>t_path.write_text("<html><body><h1>Starting optimization loop...</h1><meta http-equiv='refresh' content='5'></body></html>")
        webbrowser.open(str(live_report_path))
    else:
        live_report_path = None

    # Determine output directory (create before run_loop so logs can be written)
    if args.results_dir:
        timestamp = time.strftime("%Y-%m-%d_%H%M%S")
        results_dir = Path(args.results_dir) / timestamp
        results_dir.mkdir(parents=True, exist_ok=True)
    else:
        results_dir = None

    log_dir = results_dir / "logs" if results_dir else None

    output = run_loop(
        eval_set=eval_set,
        skill_path=skill_path,
        description_override=args.description,
        num_workers=args.num_workers,
        timeout=args.timeout,
        max_iterations=args.max_iterations,
        runs_per_query=args.runs_per_query,
        trigger_threshold=args.trigger_threshold,
        holdout=args.holdout,
        model=args.model,
        verbose=args.verbose,
        live_report_path=live_report_path,
        log_dir=log_dir,
    )

    # Save JSON output
    json_output = json.dumps(output, indent=2)
    print(json_output)
    if results_dir:
        (results_dir / "results.json").write_text(json_output)

    # Write final HTML report (without auto-refresh)
    if live_report_path:
        live_report_path.write_text(generate_html(output, auto_refresh=False, skill_name=name))
        print(f"\nReport: {live_report_path}", file=sys.stderr)

    <|fim_suffix|>

    if results_dir:
        print(f"Results saved to: {results_dir}", file=sys.stderr)


if __name__ == "__main__":
    main()
<|fim_middle|>
```

## 10  tokens=534  prefix_cut=False  extra_dropped=0/1

**Model output:**
```python
process_activity(proc)
```

**What the model saw:**
```
<|repo_name|>myproject
<|file_sep|>i18n.py
def t(key: str, lang: str | None = None, **format_kwargs: Any) -> str:<|file_sep|>filename
<|fim_prefix|>ted_at)) if exited_at else 0,
            "detail": _last_output_line(proc.output_buffer),
        })
    rows.sort(key=lambda r: (r["status"] != "running", -r["elapsed"] if r["status"] == "running" else r["since_exit"]))
    return rows


_GLYPH = {"running": "⚙", "done": "✔", "failed": "✘", "killed": "✘", "lost": "?"}
# Finished-status id → catalog key of the exit verdict (looked up at paint time).
_VERDICT_KEYS = {"done": "cli.dock.exit_code", "failed": "cli.dock.exit_code",
                 "killed": "cli.dock.verdict_killed", "lost": "cli.dock.verdict_lost"}


def process_activity(row: dict) -> str:
    """The trailing ``· …`` part of a dock line: elapsed + latest output while running, the exit
    verdict + age once finished."""
    if row["status"] == "running":
        return f"{row['elapsed']}s · " + (
            t("cli.dock.last_output", detail=row["detail"]) if row["detail"] else t("cli.dock.starting"))
    verdict = _VERDICT_KEYS[row["status"]]
    verdict = t(verdict, code=row["exit_code"])
    return t("cli.dock.verdict_ago", verdict=verdict, seconds=row["since_exit"])


def process_glyph(row: dict) -> str:
    return _GLYPH.get(row["status"], "?")


def process_tail(process_id: str) -> str:
    from hermes_cli.gateway_tools import process_registry as _registry
    process_registry = _registry()  # the gateway session's processes (rewired CLI)

    proc = process_registry.get(process_id)
    if proc is None:
        return t("cli.dock.process_gone")
    text = <|fim_suffix|>
    text = "".join(c for c in text if c.isprintable() or c in "\n\t")
    return text or t("cli.dock.no_output")


def kill(process_id: str) -> dict:
    from hermes_cli.gateway_tools import process_registry as _registry
    process_registry = _registry()  # the gateway session's processes (rewired CLI)

    return process_registry.kill_process(process_id)
<|fim_middle|>
```

## 11  tokens=394  prefix_cut=False  extra_dropped=0/1

**Model output:**
```python
langchain_core.llms import OpenAI as ChatOpenAI
```

**What the model saw:**
```
<|repo_name|>myproject
<|file_sep|>config.py
class Settings(BaseSettings):
    def _env_name(cls, v: str) -> str:
    def chunk_db_path(self) -> Path:
    def audit_db_path(self) -> Path:
    def checkpoint_db_path(self) -> Path:
    def is_production(self) -> bool:
    def missing_keys( self, needed: tuple[str, ...] = ("openai_api_key", "pinecone_api_key", "tavily_api_key") ) -> list[str]:
    def check_production_safety(self) -> None:<|file_sep|>filename
<|fim_prefix|>"""The agent's public interface: build the LLMs and conversation store, and answer questions."""

import logging
import sqlite3
import time
from pathlib import Path

from langchain_core.messages import HumanMessage

from app.core.config import Settings
from app.rag.state import AgentState
from app.rag.workflow import Services, build_graph

logger = logging.getLogger(__name__)


def make_llms(settings: Settings):
    """Return (llm_fast, llm_strong).

    Uses OpenAI's Responses API: on current models, structured outputs and tool calling work
    there with reasoning switched on. No temperature is set (reasoning models only accept the
    default). The strong model falls back to the fast model if it fails.
    """
    from <|fim_suffix|>

    def chat(model: str, effort: str, retries: int) -> ChatOpenAI:
        return ChatOpenAI(
            model=model,
            api_key=settings.openai_api_key,
            use_responses_api=True,
            reasoning={"effort": effort},
            max_retries=retries,
            timeout=settings.llm_timeout_s,
        )

    llm_fast = chat(settings.fast_model, settings.fast_reasoning_effort, retries=3)
    llm_strong = chat(settings.strong_model, settings.strong_reasoning_effort, retri<|fim_middle|>
```

## 12  tokens=514  prefix_cut=False  extra_dropped=0/1

**Model output:**
```python
choices.append(t("gateway.exec_approval.text_choice_shorten", prefix=prefix))
    if not smart_denied:
        choices.append(t("gateway.exec_approval.text_choice_shorten_session", prefix=prefix))
    if not smart_denied:
        choices.append(t("gateway.exec_approval.text_choice_shorten_deny", prefix
```

**What the model saw:**
```
<|repo_name|>myproject
<|file_sep|>i18n.py
def t(key: str, lang: str | None = None, **format_kwargs: Any) -> str:<|file_sep|>filename
<|fim_prefix|> bool = False) -> tuple[str, bool]:
    """``(prompt, deny_only)``: instructions and deadline ahead of the command, so a cut can only
    shorten the command; when the whole prompt does not fit, a shortened command and Deny alone.
    LINE has no ``MAX_MESSAGE_LENGTH``, so its 4096 default is used: conservative, never cut."""
    from gateway.platforms.base import fit_prefix
    from gateway.platforms.base_exec_approval import (
        approval_timeout_seconds, code_fence, ea_header_text, fit_fenced, ea_reason_label_text, format_approval_deadline_line)
    limit = adapter.max_message_length_for_chat(chat_id)
    measure = adapter.message_len_fn_for_chat(chat_id)
    heading = t("gateway.exec_approval.smart_deny_heading") if smart_denied else f"⚠️ **{ea_header_text()}**"

    def prompt(choices: list[str], notice: str, shown: str, fence: str) -> str:
        instructions = (t("gateway.exec_approval.text_choice_joiner").join(choices[:-1])
                        + t("gateway.exec_approval.text_choice_last", choice=choices[-1])) if choices[1:] else f"{choices[0]}.\n"
        return (f"{heading}\n\n{instructions}{notice}{format_approval_deadline_line(approval_timeout_seconds())}"
                f"\n\n{ea_reason_label_text()}: {description}\n{fence}\n{shown}\n{fence}")

    choices = [t("gateway.exec_approval.text_choice_once", prefix=prefix)]
    if not smart_denied and allow_session:
        choices.append(t("gateway.exec_approval.text_choice_session", prefix=prefix))
        <|fim_suffix|>
    choices.append(t("gateway.exec_approval.text_choice_deny", prefix=prefix))
    full = prompt(choices, "", command, code_fence(command))
    if measure(full) <= limit:
        return full, False
    deny = [t("gateway.exec_approval.text_choice_deny", prefix=prefix)]
    # The whole command fits beside Deny alone but not beside every choice: say so, not "shortened".
    whole = prompt(deny, t("gateway.exec_approval.text_prompt_deny_only") + "\n", command, code_fence(command))
    if measure(w<|fim_middle|>
```

## 13  tokens=448  prefix_cut=False  extra_dropped=0/1

**Model output:**
```python
Web(settings)
```

**What the model saw:**
```
<|repo_name|>myproject
<|file_sep|>agent.py
def make_llms(settings: Settings):<|file_sep|>filename
<|fim_prefix|>ings)
    store = ChunkStore(settings.chunk_db_path)
    vector_index = VectorIndex(vectorstore, index, settings.pinecone_namespace)
    return KnowledgeBase(settings, store, vector_index, retriever), vectorstore


def build_components(settings: Settings) -> Components:
    missing = settings.missing_keys()
    if missing:
        raise RuntimeError(f"Missing API keys: {', '.join(missing)}. Set them in .env or the environment.")
    from sentence_transformers import CrossEncoder  # heavy import, only when really starting

    kb, vectorstore = build_knowledge_base(settings)
    retriever = HybridRetriever(
        vectorstore=vectorstore,
        bm25_index=BM25Index([]),  # filled from the chunk store by refresh_if_stale below
        reranker=CrossEncoder(settings.rerank_model),
        settings=settings,
    )
    kb.retriever = retriever
    kb.refresh_if_stale()  # records the store version the index was built from
    if kb.store.count() == 0 and settings.auto_ingest:
        # Hosts with a wiped disk on restart (e.g. Hugging Face Spaces): rebuild the local chunk store.
        # Chunks already in Pinecone are skipped, so this is quick and costs nothing extra.
        logger.info("Knowledge base is empty; AUTO_INGEST is on, ingesting the default sources.")
        kb.ingest_defaults()
    if kb.store.count() == 0:
        logger.warning("Knowledge base is empty. Run `python cli.py ingest` or upload a document.")

    llm_fast, llm_strong = make_llms(settings)
    web = <|fim_suffix|>
    services = Services(settings=settings, llm_fast=llm_fast, llm_strong=llm_strong, retriever=retriever, web=web)
    agent = RAGAgent(services, checkpointer=make_checkpointer(settings))
    return Components(settings=settings, agent=agent, kb=kb, audit=AuditLog(settings.audit_db_path))
<|fim_middle|>
```

## 14  tokens=482  prefix_cut=False  extra_dropped=0/2

**Model output:**
```python
raise PublicVisibilityError(f"Committed {key}; public visibility verification failed")
        self.store.put(key, body, etag)
```

**What the model saw:**
```
<|repo_name|>myproject
<|file_sep|>release_channels.py
def canonical_json(value: object) -> bytes:<|file_sep|>release_channels.py
class ChannelError(ValueError):<|file_sep|>filename
<|fim_prefix|>f"HermesChannel{token}"
    return {"token": token, "displayName": f"Hermes {name}",
            "appId": f"ai.hermes.channel.h{token}", "appNamePascal": pascal,
            "artifactNamePascal": pascal, "cliName": f"hermes-{name}",
            "windowsExecutableName": pascal, "msixAppIdWithOrg": f"NousResearch.{pascal}"}


class ChannelPublisher:
    def __init__(self, store: R2ChannelStore, repository: str, public_base: str,
                 authorize, verify_build=None):
        self.store = store
        self.repository = validate_repository(repository)
        self.public_base = validate_public_base(public_base)
        self.reader = ChannelReader(self.public_base, self.repository)
        self.authorize = authorize
        self.verify_build = verify_build


    def _read(self, name: str) -> tuple[dict, str] | None:
        value = self.store.get(channel_key(name))
        if value is None:
            return None
        body, etag = value
        return validate_record(decode_json(body), name=name, repository=self.repository), etag

    def _write(self, key: str, value: dict, etag: str | None = None) -> None:
        body = canonical_json(value)
        self.store.put(key, body, etag)
        try:
            visible = self.reader.read_bytes(key)
        except ChannelError as exc:
            raise PublicVisibilityError(f"Committed {key}; public visibility verification failed") from exc
        if visible != body:
            current = self.store.get(key)
            <|fim_suffix|>
            raise PublicVisibilityError(f"Committed {key}; public visibility verification failed")

    def _preview(self, action: str, record: dict) -> None:
        if record["policy"] != "preview":
            raise ChannelError("Protected release policy requires its existing release gate")
        if record["state"] != "active":
            raise ChannelError("Retired channel is permanently closed to publication")
        self.authorize(action, record)

    def _stable_identity(self) -> dic<|fim_middle|>
```

## 15  tokens=471  prefix_cut=False  extra_dropped=0/1

**Model output:**
```python
len(pos)
```

**What the model saw:**
```
<|repo_name|>myproject
<|file_sep|>generate_report.py
def generate_html(data: dict, auto_refresh: bool = False, skill_name: str = "") -> str:<|file_sep|>filename
<|fim_prefix|>     "train_total": train_summary["total"],
            "train_results": train_results["results"],
            "test_passed": test_summary["passed"] if test_summary else None,
            "test_failed": test_summary["failed"] if test_summary else None,
            "test_total": test_summary["total"] if test_summary else None,
            "test_results": test_results["results"] if test_results else None,
            # For backward compat with report generator
            "passed": train_summary["passed"],
            "failed": train_summary["failed"],
            "total": train_summary["total"],
            "results": train_results["results"],
        })

        # Write live report if path provided
        if live_report_path:
            partial_output = {
                "original_description": original_description,
                "best_description": current_description,
                "best_score": "in progress",
                "iterations_run": len(history),
                "holdout": holdout,
                "train_size": len(train_set),
                "test_size": len(test_set),
                "history": history,
            }
            live_report_path.write_text(generate_html(partial_output, auto_refresh=True, skill_name=name))

        if verbose:
            def print_eval_stats(label, results, elapsed):
                pos = [r for r in results if r["should_trigger"]]
                neg = [r for r in results if not r["should_trigger"]]
                tp = <|fim_suffix|>
                pos_runs = sum(r["runs"] for r in pos)
                fn = pos_runs - tp
                fp = sum(r["triggers"] for r in neg)
                neg_runs = sum(r["runs"] for r in neg)
                tn = neg_runs - fp
                total = tp + tn + fp + fn
                precision = tp / (tp + fp) if (tp + fp) > 0 else 1.0
                recall = tp / (tp + fn) if (tp + fn) > 0 else 1.0
                accuracy = (tp + tn) / total if total > 0 else 0.0
                print(<|fim_middle|>
```

## 16  tokens=356  prefix_cut=False  extra_dropped=0/1

**Model output:**
```python
self._enqueue_tool_line(line)
```

**What the model saw:**
```
<|repo_name|>myproject
<|file_sep|>stream_events.py
class ToolCallChunk:<|file_sep|>filename
<|fim_prefix|>al[str] = None  # "new"-mode dedup

    def dispatch(self, event: StreamEvent) -> None:
        """Route a single event.  Never raises into the agent's worker thread."""
        try:
            self._dispatch(event)
        except Exception:  # presentation must never break the agent loop
            logger.debug("stream-event dispatch error", exc_info=True)

    def _dispatch(self, event: StreamEvent) -> None:
        # ToolCallFinished: no chrome on completion (only "started" is rendered);
        # completion only drives onboarding hints (LongToolHint).
        if isinstance(event, (MessageChunk, MessageStop, Commentary)):
            if self.sink is not None:
                self.adapter.render_message_event(event, self.sink)
        elif isinstance(event, ToolCallChunk):
            self._dispatch_tool_call(event)
        elif isinstance(event, LongToolHint) and self._on_long_tool is not None:
            self._on_long_tool(event)
        elif isinstance(event, GatewayNotice) and self._on_notice is not None:
            self._on_notice(event)

    def _dispatch_tool_call(self, event: ToolCallChunk) -> None:
        if self.tool_mode == "off" or self._enqueue_tool_line is None:
            return
        if self.tool_mode == "new" and event.tool_name == self._last_tool:
            return
        self._last_tool = event.tool_name
        line = self.adapter.format_tool_event(
            event, mode=self.tool_mode, preview_max_len=self.preview_max_len,
        )
        <|fim_suffix|>


__all__ = ["GatewayEventDispatcher"]
<|fim_middle|>
```

## 17  tokens=541  prefix_cut=False  extra_dropped=0/1

**Model output:**
```python
if is_release_age_failure(listed.stdout):
        raise RuntimeError(f"pnpm list --recursive --depth -1 --json failed with {listed.stderr}")
    for project in json.loads(listed.stdout):
        relative = Path(project["path"]).resolve().relative_to(root.resolve())
        (scratch / relative).mkdir(parent
```

**What the model saw:**
```
<|repo_name|>myproject
<|file_sep|>filesystem.py
def native(path: str | os.PathLike[str]) -> str:<|file_sep|>filename
<|fim_prefix|>iolations). The same update with
saving allowed and no terminal to prompt on lists them as ERR_PNPM_NO_MATURE_MATCHING_VERSION; it
may write the manifests, so it runs on a scratch copy of the workspace's resolution inputs.
"""
from __future__ import annotations

import json
from pathlib import Path
import re
import shutil
import subprocess
import tempfile

from pm.filesystem import native

REQUIRES_SAVE = "ERR_PNPM_STRICT_MIN_RELEASE_AGE_REQUIRES_SAVE"
NO_MATURE = "ERR_PNPM_NO_MATURE_MATCHING_VERSION"
_VIOLATION = re.compile(r"^\s+(\S+@\S+) was published at ", re.MULTILINE)
# What a lockfile-only resolution reads at the workspace root besides each project's package.json.
_ROOT_INPUTS = ("pnpm-workspace.yaml", "pnpm-lock.yaml", ".npmrc", ".pnpmfile.cjs", ".pnpmfile.mjs")


def is_release_age_failure(output: str) -> bool:
    return REQUIRES_SAVE in output or NO_MATURE in output


def _run(command: list[str], *, cwd: Path, env: dict[str, str], timeout: int) -> subprocess.CompletedProcess:
    # No terminal on stdin: pnpm fails with the list instead of prompting to write it.
    return subprocess.run(command, check=False, cwd=native(cwd), env=env, stdin=subprocess.DEVNULL, capture_output=True,
                          text=True, encoding="utf-8", errors="replace", timeout=timeout)


def _stage_inputs(pnpm: str, root: Path, scratch: Path, env: dict[str, str]) -> None:
    listed = _run([pnpm, "list", "--recursive", "--depth", "-1", "--json"], cwd=root, env=env, timeout=120)
    <|fim_suffix|>
    for project in json.loads(listed.stdout):
        relative = Path(project["path"]).resolve().relative_to(root.resolve())
        (scratch / relative).mkdir(parents=True, exist_ok=True)
        shutil.copy2(root / relative / "package.json", scratch / relative / "package.json")
    for name in _ROOT_INPUTS:
        if (root / name).is_file():
            shutil.copy2(root / name, scratch / name)


def immature_picks(pnpm: str, root: Path, env: dict[str, str], *, timeout: int = 3600) -> list[s<|fim_middle|>
```

## 18  tokens=529  prefix_cut=False  extra_dropped=0/1

**Model output:**
```python
elif ext in _FAIL_CLOSED_INPROC_EXTS:
            return LintResult(skipped=True, message=f"Failed to read {path} for lint")
        else:
            return self._check_lint_shell(path, content)
```

**What the model saw:**
```
<|repo_name|>myproject
<|file_sep|>file_operations_common.py
class LintResult:
    def to_dict(self) -> dict:<|file_sep|>filename
<|fim_prefix|>int_yaml_inproc,
    '.yml': _lint_yaml_inproc,
    '.toml': _lint_toml_inproc,
}

# Extensions where write_file REFUSES on a parse failure. ``.py`` is excluded on
# purpose: test fixtures use ``*.py`` paths as a stand-in for arbitrary text, so
# Python keeps the non-blocking lint-delta report.
_FAIL_CLOSED_INPROC_EXTS = frozenset({'.json', '.yaml', '.yml', '.toml'})


class LintMixin:
    """Post-write syntax lint + LSP diagnostics. Requires ``_exec``,
    ``_has_command``, ``_escape_shell_arg``, ``_escape_native_tool_arg`` and
    ``env`` from the host class."""

    def _check_lint(self, path: str, content: Optional[str] = None) -> LintResult:
        """Syntax-check ``path``: in-process linter when one matches the
        extension (``content`` avoids a re-read), else the shell linter table."""
        ext = os.path.splitext(path)[1].lower()
        inproc = LINTERS_INPROC.get(ext)
        if inproc is not None:
            if content is None:
                read_result = self._exec(f"cat {self._escape_shell_arg(path)} 2>/dev/null")
                if read_result.exit_code != 0:
                    return LintResult(skipped=True, message=f"Failed to read {path} for lint")
                content = read_result.stdout
            ok, err = inproc(content)
            if err == "__SKIP__":
                return LintResult(skipped=True, message=f"No linter available for {ext} (missing dependency)")
            return LintResult(success=ok, output="" if ok else err)
        <|fim_suffix|>
        # Single-file tsc can't read tsconfig.json and floods phantom TS2307/TS2339
        # errors the delta filter misreports as "pre-existing"; let the LSP tier speak.
        if ext == '.ts' and self._has_ancestor_tsconfig(path):
            return LintResult(skipped=True, message=(
                "Project tsconfig.json detected — per-file tsc skipped "
                "(single-file tsc can't resolve project aliases/globals; "
                "use the LSP tier or `tsc -p tsconfig.json` fo<|fim_middle|>
```

## 19  tokens=499  prefix_cut=False  extra_dropped=0/1

**Model output:**
```python
if gateway:
        return gateway
    if request.cookies.get("sso_attempt"):
        return None
    return RedirectResponse(url="/login", status_code=302)
```

**What the model saw:**
```
<|repo_name|>myproject
<|file_sep|>webapp_sign_in.py
def cookie_gateway(request: Request) -> str:<|file_sep|>filename
<|fim_prefix|>irects; the SPA's
    401 handler navigates to ``login_url`` on ``unauthenticated`` / ``session_expired``."""
    next_param = _safe_next_target(request)
    prefix = prefix_from_request(request)
    login_url = f"{prefix}/login?next={next_param}" if next_param else f"{prefix}/login"
    if request.url.path.startswith("/api/"):
        expired = reason == "invalid_or_expired_session"
        # Same reason the client already receives. Never include the bearer.
        audit_log(AuditEvent.SESSION_REJECTED, reason=reason, path=request.url.path,
                  ip=_client_ip(request))
        return JSONResponse(
            {"error": "session_expired" if expired else "unauthenticated", "detail": "Unauthorized",
             "reason": reason, "login_url": login_url}, status_code=401)
    return RedirectResponse(url=login_url, status_code=302)


def _auto_sso_response(request: Request) -> Response | None:
    """302 straight to ``/auth/login`` on an unauthenticated HTML load, or ``None``.

    Only for a document load (not ``/api/*``) when exactly one interactive OAuth-style provider is
    registered (a password provider must render the form) and the one-shot loop-guard cookie is
    absent — a present marker means the portal had no session last time: clear it and fall back
    to ``/login`` rather than ping-pong. Convenience, not a security check.
    """
    if request.url.path.startswith("/api/"):
        return None
    gateway = webapp_sign_in.cookie_gateway(request)
    <|fim_suffix|>
    providers = list_interactive_providers()
    if len(providers) != 1 or getattr(providers[0], "supports_password", False):
        return None
    provider = providers[0]
    prefix = prefix_from_request(request)
    next_param = _safe_next_target(request)
    auth_login = f"{prefix}/auth/login?provider={quote(provider.name, safe='')}"
    if next_param:
        auth_login = f"{auth_login}&next={next_param}"
    resp = RedirectResponse(url=auth_login, status_code=302)
    set_sso_attempt_coo<|fim_middle|>
```

## 20  tokens=507  prefix_cut=False  extra_dropped=0/1

**Model output:**
```python
Pinecone
```

**What the model saw:**
```
<|repo_name|>myproject
<|file_sep|>config.py
class Settings(BaseSettings):
    def _env_name(cls, v: str) -> str:
    def chunk_db_path(self) -> Path:
    def audit_db_path(self) -> Path:
    def checkpoint_db_path(self) -> Path:
    def is_production(self) -> bool:
    def missing_keys( self, needed: tuple[str, ...] = ("openai_api_key", "pinecone_api_key", "tavily_api_key") ) -> list[str]:
    def check_production_safety(self) -> None:<|file_sep|>filename
<|fim_prefix|>"""Embeddings + Pinecone: connect to the index, upload new chunks, delete stale ones.

Unlike a "delete and recreate the index on mismatch" approach, this never deletes an index:
a wrong embedding size stops startup with a clear error instead of wiping your data.
"""

import logging
import time

from langchain_core.documents import Document

from app.core.config import Settings

logger = logging.getLogger(__name__)


def make_embeddings(settings: Settings):
    """bge-small-en-v1.5 runs locally (free). BGE expects an instruction in front of queries only."""
    from langchain_huggingface import HuggingFaceEmbeddings

    embeddings = HuggingFaceEmbeddings(
        model_name=settings.embed_model,
        encode_kwargs={"normalize_embeddings": True},
        query_encode_kwargs={"normalize_embeddings": True, "prompt": settings.bge_query_prompt},
    )
    dim = len(embeddings.embed_query("dimension check"))
    if dim != settings.embed_dim:
        raise RuntimeError(f"{settings.embed_model} returns {dim} dims but EMBED_DIM is {settings.embed_dim}.")
    return embeddings


def connect_vectorstore(settings: Settings, embeddings):
    """Create the serverless index if it doesn't exist; return (vectorstore, raw_index)."""
    from langchain_pinecone import PineconeVectorStore
    from pinecone import <|fim_suffix|>

    pc = Pinecone(api_key=settings.pinecone_api_key)
    name = settings.pinecone_index_name
    if pc.has_index(name):
        existing_dim = pc.describe_index(name).dimension
        if existing_dim != settings.embed_dim:
            raise RuntimeError(
                f"Pinecone index '{name}' has dimension {existing_dim}, but the embedding model needs "
                f"{settings.embed_dim}. Set PINECONE_INDEX_NAME to a new index name."
            )
    else:
        logger.info("Creatin<|fim_middle|>
```

## 21  tokens=500  prefix_cut=False  extra_dropped=0/1

**Model output:**
```python
if target.startswith("http://") or target.startswith("https://"):
            return self.ingest_url(target)
        if target.startswith("file://"):
            target = target[7:]
        if not Path(target).exists():
            raise FileNotFoundError(target)
        if target.endswith(".md"):
            return self.ingest
```

**What the model saw:**
```
<|repo_name|>myproject
<|file_sep|>ingestion.py
def load_file(path: Path, display_name: Optional[str] = None) -> tuple[str, str]:<|file_sep|>filename
<|fim_prefix|>le: str) -> IngestResult:
        chunks = chunk_markdown(md, source=source, title=title, settings=self.settings)
        if not chunks:
            raise IngestionError(f"{source} produced no chunks (too little text).")
        with self._lock:
            old_ids = self.store.ids_for_source(source)
            new_ids = {c.id for c in chunks}
            uploaded = self.vector_index.upsert(chunks)  # 1) vectors first: a failure here changes nothing
            stale = sorted(old_ids - new_ids)
            if stale:
                self.vector_index.delete(stale)  # 2) remove chunks that no longer exist
            self.store.replace_source(source, chunks)  # 3) local text store
            self._refresh_keyword_index()  # 4) keyword index sees the new text immediately
        result = IngestResult(source, title, len(chunks), uploaded, len(chunks) - uploaded, len(stale))
        logger.info("Ingested %s", result.as_dict())
        return result

    def ingest_url(self, url: str) -> IngestResult:
        md, title = load_url(url, allow_private=self.settings.allow_private_urls)
        return self.ingest(md, source=url, title=title)

    def ingest_file(self, path: Path, display_name: Optional[str] = None) -> IngestResult:
        md, title = load_file(path, display_name)
        return self.ingest(md, source=display_name or path.name, title=title)

    def ingest_target(self, target: str) -> IngestResult:
        """Ingest a URL (http/https) or a local file path."""
        <|fim_suffix|>
        return self.ingest_file(Path(target))

    def ingest_defaults(self) -> int:
        """Ingest default_targets(); returns how many failed (each failure is logged, not raised)."""
        failures = 0
        for target in default_targets(self.settings):
            try:
                self.ingest_target(target)
            except (IngestionError, FileNotFoundError) as exc:
                failures += 1
                logger.warning("Could not ingest %s: %s", target, exc)
        retur<|fim_middle|>
```

## 22  tokens=574  prefix_cut=False  extra_dropped=0/1

**Model output:**
```python
first = master
        theme = _resolve(rels_path, theme)
        owner[theme] = master
    return owner.items()
```

**What the model saw:**
```
<|repo_name|>myproject
<|file_sep|>__init__.py
def part_text(data: bytes) -> str:<|file_sep|>filename
<|fim_prefix|>get))


def _theme_rel(files: Mapping[str, bytes], master: str):
    rels_path = _rels_path(master)
    rels = files.get(rels_path)
    if rels is None:
        return None
    for element in _RELATIONSHIP_RE.findall(part_text(rels)):
        if f'Type="{THEME_REL_TYPE}"' not in element:
            continue
        target = re.search(r'\bTarget="([^"]+)"', element)
        if target is None:
            continue
        return rels_path, element, _resolve(rels_path, target.group(1))
    return None


def _masters(files: Mapping[str, bytes]) -> list[str]:
    return sorted((n for n in files if _MASTER_RE.match(n)), key=_sort_key)


_PRESENTATION = "ppt/presentation.xml"
_NOTES_MASTERS = "ppt/notesMasters/"
_IGNORABLE_RE = re.compile(r"<!--.*?-->|<\?.*?\?>", re.DOTALL)
_AFTER_SLDIDLST_RE = re.compile(
    r"<p:sldIdLst\b(?:[^>]*/>|[^>]*>.*?</p:sldIdLst\s*>)\s*(<[^>\s/]+)", re.DOTALL
)


def _notes_master_share_is_inert(files: Mapping[str, bytes]) -> bool:
    data = files.get(_PRESENTATION)
    if data is None:
        return False
    match = _AFTER_SLDIDLST_RE.search(_IGNORABLE_RE.sub("", part_text(data)))
    return match is not None and match.group(1) == "<p:notesMasterIdLst"


def _shares(files: Mapping[str, bytes]):
    owner: dict[str, str] = {}
    for master in _masters(files):
        found = _theme_rel(files, master)
        if found is None:
            continue
        rels_path, element, theme = found
        if theme not in files:
            continue  
        <|fim_suffix|>


def _is_inert(master: str, inert_notes: bool) -> bool:
    return inert_notes and master.startswith(_NOTES_MASTERS)


def find_shared_master_themes(files: Mapping[str, bytes]) -> list[str]:
    return [
        f"{master} shares {theme} with {first}"
        for master, _, _, theme, first in _shares(files)
    ]


def live_shared_master_themes(files: Mapping[str, bytes]) -> list[str]:
    inert_notes = _notes_master_share_is_inert(files)
    return [
        f"{master} shares {theme} with {fi<|fim_middle|>
```

## 23  tokens=700  prefix_cut=False  extra_dropped=0/2

**Model output:**
```python
store  # app.rag.vectorstore.ChunkStore (or a fake in tests)
```

**What the model saw:**
```
<|repo_name|>myproject
<|file_sep|>config.py
class Settings(BaseSettings):
    def _env_name(cls, v: str) -> str:
    def chunk_db_path(self) -> Path:
    def audit_db_path(self) -> Path:
    def checkpoint_db_path(self) -> Path:
    def is_production(self) -> bool:
    def missing_keys( self, needed: tuple[str, ...] = ("openai_api_key", "pinecone_api_key", "tavily_api_key") ) -> list[str]:
    def check_production_safety(self) -> None:<|file_sep|>retrieval.py
class HybridRetriever:
    def __init__(self, vectorstore, bm25_index: BM25Index, reranker, settings: Settings):
    def refresh_keyword_index(self, docs: list[Document]) -> None:
    def retrieve(self, queries: list[str]) -> list[Document]:
    def rerank(self, query: str, docs: list[Document]) -> list[Document]:<|file_sep|>filename
<|fim_prefix|>ntent, metadata FROM chunks ORDER BY source, id").fetchall()
        return [Document(id=r[0], page_content=r[1], metadata=json.loads(r[2])) for r in rows]

    def sources(self) -> list[dict]:
        with self._connect() as con:
            rows = con.execute(
                "SELECT source, json_extract(MIN(metadata), '$.title'), COUNT(*), MAX(created_at) "
                "FROM chunks GROUP BY source ORDER BY MAX(created_at) DESC"
            ).fetchall()
        return [{"source": r[0], "title": r[1], "chunks": r[2], "updated_at": r[3]} for r in rows]

    def version(self) -> tuple:
        """Changes whenever chunks are added or removed (by this process or another one)."""
        with self._connect() as con:
            return tuple(con.execute("SELECT COUNT(*), MAX(created_at), TOTAL(LENGTH(id)) FROM chunks").fetchone())

    def count(self) -> int:
        with self._connect() as con:
            return con.execute("SELECT COUNT(*) FROM chunks").fetchone()[0]


@dataclass
class IngestResult:
    source: str
    title: str
    chunks: int  # chunks in the new version
    uploaded: int  # newly embedded and uploaded
    unchanged: int  # already in Pinecone, skipped
    removed: int  # stale chunks deleted from Pinecone

    def as_dict(self) -> dict:
        return asdict(self)


class KnowledgeBase:
    def __init__(self, settings: Settings, store: ChunkStore, vector_index, retriever: Optional[HybridRetriever]):
        self.settings = settings
        self.store = <|fim_suffix|>
        self.vector_index = vector_index  # app.rag.vectorstore.VectorIndex (or a fake in tests)
        self.retriever = retriever
        self._lock = threading.Lock()  # one ingestion at a time keeps the three stores consistent
        self._index_version: tuple | None = None

    def ingest(self, md: str, source: str, title: str) -> IngestResult:
        chunks = chunk_markdown(md, source=source, title=title, settings=self.settings)
        if not chunks:
            raise IngestionError(f"<|fim_middle|>
```

## 24  tokens=491  prefix_cut=False  extra_dropped=0/1

**Model output:**
```python
saved['target']
```

**What the model saw:**
```
<|repo_name|>myproject
<|file_sep|>hermes_state_runtime.py
class RuntimeStoreError(ValueError):
    def __init__(self, reason: str, *, field: str | None = None, detail: str | None = None):<|file_sep|>filename
<|fim_prefix|>eak
            through = later['id']
    return through


def _child_policy(policy, child, prepared):
    """The parent's frozen policy, except editor MCP servers: the gateway prepared the child's own
    selection under the child's own scope (gateway/session_local_mcp.py ``prepare_branch_editor``).
    Copying the parent's would share its scope, borrowed credentials and live connections.
    A branch starts at Default (``ask``), as main's ACP ``fork_session`` did."""
    if 'edit_approval_policy' in policy:
        policy = {**policy, 'edit_approval_policy': 'ask'}
    if prepared is None:
        if policy.get('editor_mcp_json'):
            raise RuntimeStoreError('runtime_coordination_required')
        return policy
    # Prepared against the parent's selection and the child id this commit derives; anything else moved.
    if child != prepared['child'] or policy.get('editor_mcp_json') != prepared['parent_editor_mcp_json']:
        raise RuntimeStoreError('revision_conflict')
    return {**policy, 'editor_mcp_json': prepared['editor_mcp_json'], 'toolsets': prepared['toolsets'],
            'config_secret_ref': prepared['config_secret_ref']}


def branch_in_transaction(db, conn, session_id, payload, prepared=None):
    row = conn.execute('SELECT value FROM state_meta WHERE key=?',
                       (POLICY_PREFIX + session_id,)).fetchone()
    if row is None:
        raise RuntimeStoreError('runtime_coordination_required')
    saved = json.loads(row[0])
    target = <|fim_suffix|>
    require_idle(db, conn, list({session_id, target}))
    # Late: the routing entry/key are gateway types (the gateway imports this store at module level).
    from gateway.session import SessionEntry, SessionSource
    from gateway.config import Platform
    from hermes_state_keys import local_identity, profile_from_session_key
    request_id = prepared['request_id'] if prepared else 'branch:' + uuid.uuid4().hex
    child = local_identity(saved['profile_id'], saved['principal_id'], request_id<|fim_middle|>
```

## 25  tokens=461  prefix_cut=False  extra_dropped=0/1

**Model output:**
```python
"rewrite_web", rewrite_web)
```

**What the model saw:**
```
<|repo_name|>myproject
<|file_sep|>state.py
class AgentState(TypedDict, total=False):<|file_sep|>filename
<|fim_prefix|>"]:
    return "generate" if state.get("evidence") else "insufficient"


def after_check(state: AgentState, runtime: Runtime[Services]) -> Literal["generate", "web_search", "finalize"]:
    check = state["check"]
    if not check["grounded"] and state["generation_attempts"] < runtime.context.settings.max_generation_attempts:
        return "generate"  # retry with the checker's feedback
    if check["grounded"] and not check["answers_question"] and state["web_allowed"] and not state.get("web_searched"):
        return "web_search"  # grounded but incomplete → get more evidence once
    return "finalize"


# ============================================================================
# Build the graph
# ============================================================================


def build_graph(checkpointer=None):
    """Compile the agent graph.

    * context_schema=Services: nodes get LLMs/retriever/web via `runtime.context`.
    * RetryPolicy: automatic retries on transient network errors.
    * checkpointer: stores state per thread_id → conversation memory.
      Swap InMemorySaver for a Postgres/Redis saver in production.
    """
    network_retry = RetryPolicy(max_attempts=3, initial_interval=1.0)

    g = StateGraph(AgentState, context_schema=Services)
    g.add_node("route_question", route_question)
    g.add_node("retrieve_kb", retrieve_kb, retry_policy=network_retry)
    g.add_node("grade_kb", grade_kb)
    g.add_node("rewrite_query", rewrite_query)
    g.add_node(<|fim_suffix|>
    g.add_node("grade_web", grade_web)
    g.add_node("generate", generate, retry_policy=network_retry)
    g.add_node("check_answer", check_answer)
    g.add_node("direct_answer", direct_answer, retry_policy=network_retry)
    g.add_node("insufficient", insufficient)
    g.add_node("finalize", finalize)

    g.add_edge(START, "route_question")
    g.add_conditional_edges("route_question", after_route)
    g.add_edge("retrieve_kb", "grade_kb")
    g.add_conditional_edges("grade_kb", after_grade<|fim_middle|>
```

## 26  tokens=812  prefix_cut=False  extra_dropped=0/5

**Model output:**
```python
[]
```

**What the model saw:**
```
<|repo_name|>myproject
<|file_sep|>vectorstore.py
def make_embeddings(settings: Settings):<|file_sep|>vectorstore.py
def connect_vectorstore(settings: Settings, embeddings):<|file_sep|>knowledge_base.py
class ChunkStore:
    def __init__(self, path: Path):
    def _connect(self):
    def ids_for_source(self, source: str) -> set[str]:
    def replace_source(self, source: str, chunks: list[Document]) -> None:
    def delete_source(self, source: str) -> list[str]:
    def all_documents(self) -> list[Document]:
    def sources(self) -> list[dict]:
    def version(self) -> tuple:
    def count(self) -> int:<|file_sep|>vectorstore.py
class VectorIndex:
    def __init__(self, vectorstore, index, namespace: str, batch_size: int = 100):
    def existing_ids(self, ids: list[str]) -> set[str]:
    def upsert(self, chunks: list[Document]) -> int:
    def delete(self, ids: list[str]) -> int:<|file_sep|>knowledge_base.py
class KnowledgeBase:
    def __init__(self, settings: Settings, store: ChunkStore, vector_index, retriever: Optional[HybridRetriever]):
    def ingest(self, md: str, source: str, title: str) -> IngestResult:
    def ingest_url(self, url: str) -> IngestResult:
    def ingest_file(self, path: Path, display_name: Optional[str] = None) -> IngestResult:
    def ingest_target(self, target: str) -> IngestResult:
    def ingest_defaults(self) -> int:
    def delete_source(self, source: str) -> int:
    def refresh_if_stale(self) -> bool:
    def _refresh_keyword_index(self) -> None:<|file_sep|>filename
<|fim_prefix|>"""Composition root: build every component once, in one place.

The API (at startup) and the CLI both call `build_components`. Tests skip it and build the
same objects from fakes, so nothing here needs to change for testing.
"""

import logging
from dataclasses import dataclass

from app.core.config import Settings
from app.rag.agent import RAGAgent, make_checkpointer, make_llms
from app.rag.retrieval import BM25Index, HybridRetriever, WebSearcher
from app.rag.vectorstore import VectorIndex, connect_vectorstore, make_embeddings
from app.rag.workflow import Services
from app.services.audit import AuditLog
from app.services.knowledge_base import ChunkStore, KnowledgeBase

logger = logging.getLogger(__name__)


@dataclass
class Components:
    settings: Settings
    agent: RAGAgent
    kb: KnowledgeBase
    audit: AuditLog


def build_knowledge_base(settings: Settings, retriever=None) -> tuple[KnowledgeBase, object]:
    """Embeddings + Pinecone + chunk store. Returns (kb, vectorstore)."""
    embeddings = make_embeddings(settings)
    vectorstore, index = connect_vectorstore(settings, embeddings)
    store = ChunkStore(settings.chunk_db_path)
    vector_index = VectorIndex(vectorstore, index, settings.pinecone_namespace)
    return KnowledgeBase(settings, store, vector_index, retriever), vectorstore


def build_components(settings: Settings) -> Components:
    missing = <|fim_suffix|>
    if missing:
        raise RuntimeError(f"Missing API keys: {', '.join(missing)}. Set them in .env or the environment.")
    from sentence_transformers import CrossEncoder  # heavy import, only when really starting

    kb, vectorstore = build_knowledge_base(settings)
    retriever = HybridRetriever(
        vectorstore=vectorstore,
        bm25_index=BM25Index([]),  # filled from the chunk store by refresh_if_stale below
        reranker=CrossEncoder(settings.rerank_model),
        settings<|fim_middle|>
```

## 27  tokens=550  prefix_cut=False  extra_dropped=0/2

**Model output:**
```python
next_check_in(limit=runtime.DEFAULT_IDLE_STOP_MINUTES * 60, idle=runtime._get_idle())
```

**What the model saw:**
```
<|repo_name|>myproject
<|file_sep|>runtime.py
def _create_time(pid: int) -> Optional[float]:<|file_sep|>runtime.py
def stop_if_idle(launcher: Optional[tuple[int, float]] = None) -> bool:<|file_sep|>filename
<|fim_prefix|>ping import Optional

from tools.bot_desktop import runtime

logger = logging.getLogger(__name__)

_MIN_DELAY_S = 30.0  # the gateway watcher's cadence; a window shorter than that is checked at its own length


def next_check_in(limit: float, idle: Optional[float]) -> int:
    """Whole seconds until the screen could next be due: when the window runs out at the current idle age,
    or a full window later while something (a human holding it) keeps it past that. With the auto-stop off
    (``limit <= 0``) the setting is re-read every default window."""
    if limit <= 0:
        return runtime.DEFAULT_IDLE_STOP_MINUTES * 60
    idle = idle or 0.0
    return math.ceil(max(min(_MIN_DELAY_S, limit), limit - idle if idle < limit else limit))


def _own_launcher(argv: list[str]) -> Optional[tuple[int, float]]:
    """``(pid, create_time)`` of the launcher that ran this check (its pid is the one argument), so the
    check stops only that screen and never a replacement started while it waited on ``start.lock``. A
    launcher already gone gets an identity nothing matches."""
    pid_s = argv[0] if argv else ""
    if not pid_s.isdigit():
        return None
    born = runtime._create_time(int(pid_s))
    return int(pid_s), born if born is not None else -1.0


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s idle-watch %(message)s")  # stderr = launcher.log
    if runtime.stop_if_idle(launcher=_own_launcher(sys.argv[1:])):
        return
    delay = <|fim_suffix|>
    logger.info("screen kept; next idle check in %ds", delay)
    print(delay)


if __name__ == "__main__":
    # stop() kills the launcher's process group, which this check was started in; in a session of its own it
    # survives that kill to finish the stop (SIGKILL stragglers, drop the runtime files), then exits. A process
    # that already leads its group (run by hand from a shell) cannot setsid and is not in the launcher's group.
    if os.getpgrp() != os.getpid():  # windows-footgun: ok<|fim_middle|>
```

## 28  tokens=516  prefix_cut=False  extra_dropped=0/2

**Model output:**
```python
fields
```

**What the model saw:**
```
<|repo_name|>myproject
<|file_sep|>skills_tool_setup.py
def _build_setup_note( readiness_status: SkillReadinessStatus, missing: list[str], setup_help: str | None = None) -> str | None:<|file_sep|>skills_tool_setup.py
def _is_remote_env_backend(backend: str) -> bool:<|file_sep|>filename
<|fim_prefix|>rt register_credential_files
            missing_cred_files = register_credential_files(required_cred_files_raw)
            setup_needed = setup_needed or bool(missing_cred_files)
        except Exception:
            logger.debug("Could not register credential files for skill %s", skill_name, exc_info=True)
    status = SkillReadinessStatus.SETUP_NEEDED if setup_needed else SkillReadinessStatus.AVAILABLE
    fields = {
        "required_environment_variables": required_env_vars, "required_commands": [],
        "missing_required_environment_variables": remaining,
        "missing_credential_files": missing_cred_files, "missing_required_commands": [],
        "setup_needed": setup_needed, "setup_skipped": capture_result["setup_skipped"],
        "readiness_status": status.value}
    extras: dict = {}
    if setup_help := next((e["help"] for e in required_env_vars if e.get("help")), None):
        extras["setup_help"] = setup_help
    if capture_result["gateway_setup_hint"]:
        extras["gateway_setup_hint"] = capture_result["gateway_setup_hint"]
    missing_items = [f"env ${n}" for n in remaining] + [f"file {p}" for p in missing_cred_files]
    if setup_needed and (setup_note := _build_setup_note(status, missing_items, setup_help)):
        if _is_remote_env_backend(backend):
            setup_note = f"{setup_note} {backend.upper()}-backed skills need these requirements available inside the remote environment as well."
        extras["setup_note"] = setup_note
    return <|fim_suffix|>


def _owning_search_dir(skill_md: Path, all_dirs) -> Optional[Path]:
    """Most specific search dir containing *skill_md*, compared lexically: a symlinked entry
    belongs to the root that exposes it, not to the root its target lives in."""
    owners = [Path(d) for d in all_dirs if skill_md.is_relative_to(d)]
    return max(owners, key=lambda d: len(d.parts), default=None)


def locate_skill(name: str, local_category_name: Optional[str], roots):
    """Unique on-disk skill for *name* over `<|fim_middle|>
```

## 29  tokens=341  prefix_cut=False  extra_dropped=0/1

**Model output:**
```python
["claude", "-p"]
```

**What the model saw:**
```
<|repo_name|>myproject
<|file_sep|>utils.py
def parse_skill_md(skill_path: Path) -> tuple[str, str, str]:<|file_sep|>filename
<|fim_prefix|>#!/usr/bin/env python3
"""Improve a skill description based on eval results.

Takes eval results (from run_eval.py) and generates an improved description
by calling `claude -p` as a subprocess (same auth pattern as run_eval.py —
uses the session's Claude Code auth, no separate ANTHROPIC_API_KEY needed).
"""

import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path

from scripts.utils import parse_skill_md


def _call_claude(prompt: str, model: str | None, timeout: int = 300) -> str:
    """Run `claude -p` with the prompt on stdin and return the text response.

    Prompt goes over stdin (not argv) because it embeds the full SKILL.md
    body and can easily exceed comfortable argv length.
    """
    cmd = <|fim_suffix|>
    if model:
        cmd.extend(["--model", model])

    # Remove CLAUDECODE env var to allow nesting claude -p inside a
    # Claude Code session. The guard is for interactive terminal conflicts;
    # programmatic subprocess usage is safe. Same pattern as run_eval.py.
    env = {k: v for k, v in os.environ.items() if k != "CLAUDECODE"}

    result = subprocess.run(
        cmd,
        input=prompt,
        capture_output=True,
        text=True,
        env=env,
        timeout=timeout,
   <|fim_middle|>
```

## 30  tokens=536  prefix_cut=False  extra_dropped=0/1

**Model output:**
```python
argparse.ArgumentParser()
```

**What the model saw:**
```
<|repo_name|>myproject
<|file_sep|>config.py
def get_settings() -> Settings:<|file_sep|>filename
<|fim_prefix|>ces…")
    agent = _build_agent()
    thread_id = uuid.uuid4().hex
    print("Ready. Ask a question (/new for a new conversation, /quit to exit).\n")
    while True:
        try:
            question = input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if question == "/quit":
            break
        if question == "/new":
            thread_id = uuid.uuid4().hex
            print("Started a new conversation.\n")
            continue
        if not question:
            continue
        result = agent.ask(question, thread_id=thread_id, on_step=lambda node, line: print(f"  [{node}] {line}"))
        print(f"\nAssistant ({result['source_used']}, {result['latency_s']}s):\n{result['answer']}")
        for c in result.get("citations", []):
            section = f" › {c['section']}" if c["section"] else ""
            print(f"  [{c['id']}] ({c['type']}) {c['title']}{section}  {c['url']}")
        print()
    return 0


def cmd_eval() -> int:
    from app.services.evaluation import run_eval

    rows = run_eval(_build_agent())
    return 0 if all(r["source_ok"] and not r["web_leak"] for r in rows) else 1


def cmd_sources() -> int:
    from app.services.knowledge_base import ChunkStore

    store = ChunkStore(get_settings().chunk_db_path)
    for s in store.sources():
        print(f"{s['chunks']:>5} chunks  {s['title']}  ({s['source']})")
    print(f"Total: {store.count()} chunks")
    return 0


def main(argv=None) -> int:
    parser = <|fim_suffix|>
    sub = parser.add_subparsers(dest="command", required=True)
    p_ingest = sub.add_parser("ingest", help="add documents to the knowledge base")
    p_ingest.add_argument("targets", nargs="*", help="files or URLs (default: SOURCE_URLS + data/sample_kb)")
    sub.add_parser("chat", help="chat in the terminal")
    sub.add_parser("eval", help="run the evaluation set")
    sub.add_parser("sources", help="list documents in the knowledge base")
    args = parser.parse_args(argv)

    settings = ge<|fim_middle|>
```

## 31  tokens=496  prefix_cut=False  extra_dropped=0/1

**Model output:**
```python
if x_access_code == settings.access_code:
        return
    if request.client and request.client.host in settings.rate_limit_ips:
        rate_limiter.check(request.client.host, settings.rate_limit_per_minute)
    if request.client and request.client.host in settings.rate_limit_ips:
        rate_limiter.check(request.client.host,
```

**What the model saw:**
```
<|repo_name|>myproject
<|file_sep|>config.py
class Settings(BaseSettings):
    def _env_name(cls, v: str) -> str:
    def chunk_db_path(self) -> Path:
    def audit_db_path(self) -> Path:
    def checkpoint_db_path(self) -> Path:
    def is_production(self) -> bool:
    def missing_keys( self, needed: tuple[str, ...] = ("openai_api_key", "pinecone_api_key", "tavily_api_key") ) -> list[str]:
    def check_production_safety(self) -> None:<|file_sep|>filename
<|fim_prefix|>_REQUESTS,
                    detail="Too many questions; please wait a moment.",
                    headers={"Retry-After": str(retry)},
                )
            hits.append(now)


class DailyQuota:
    """Counts questions per UTC day for the whole app: a hard ceiling on LLM spend for a public demo.

    Kept in memory, so it restarts at 0 with the process. The provider's monthly budget limit
    (e.g. OpenAI usage limits) is the backstop that survives restarts.
    """

    def __init__(self) -> None:
        self._day = ""
        self._count = 0
        self._lock = threading.Lock()

    def check(self, limit: int) -> None:
        if limit <= 0:
            return
        today = datetime.now(timezone.utc).date().isoformat()
        with self._lock:
            if today != self._day:
                self._day, self._count = today, 0
            if self._count >= limit:
                raise HTTPException(
                    status.HTTP_429_TOO_MANY_REQUESTS,
                    detail="The demo has reached its daily question limit. Please try again tomorrow.",
                )
            self._count += 1


rate_limiter = RateLimiter()
daily_quota = DailyQuota()


def limit_chat(
    request: Request,
    x_access_code: str = Header(default="", description="Demo access code, when ACCESS_CODE is set"),
    settings: Settings = Depends(get_app_settings),
) -> None:
    """Gate for every question, cheapest check first: access code, per-IP rate, daily total."""
    <|fim_suffix|>
    client = request.client.host if request.client else "unknown"
    rate_limiter.check(client, settings.rate_limit_per_minute)
    daily_quota.check(settings.daily_question_limit)
<|fim_middle|>
```

## 32  tokens=303  prefix_cut=False  extra_dropped=0/1

**Model output:**
```python
{}
```

**What the model saw:**
```
<|repo_name|>myproject
<|file_sep|>method_ctx.py
def bind_module(module_globals: dict, server, *, skip=()) -> None:<|file_sep|>filename
<|fim_prefix|>"""Per-server rows of an installed portable plugin for ``plugins.manage list`` (``methods_tools._plugin_rows``).

Bodies are rebound onto server.py's globals (method_ctx.bind_module) and reference them bare.
"""

from __future__ import annotations

from pathlib import Path

from .method_ctx import bind_module


def _plugin_server_rows(
    plugin_dir: Path | None, key: str, *, portable: bool,
    catalog_titles: dict[str, str] | None = None,
) -> list[dict]:
    if not portable or plugin_dir is None:
        return []
    package = _tools_mod("hermes_cli.agent_plugins").load_agent_plugin(plugin_dir, plugin_dir)
    namespace = <|fim_suffix|>
    declared = namespace.get("servers", {})
    if not isinstance(declared, dict):
        return []
    server_name_for = _tools_mod("hermes_cli.plugins_manifest").portable_mcp_server_name
    liveness = _tools_mod("tools.mcp_liveness")
    core = _tools_mod("tools.mcp_tool_common")._core
    resolve_key = _tools_mod("tools.mcp_tool_scope")._resolve_server_key
    # The server sentence's app name: the curated catalog title when the package is a catalog
    # install, else the manifest name, el<|fim_middle|>
```

