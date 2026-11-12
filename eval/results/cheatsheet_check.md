## id 11 - C: cheat sheet MISSING the name (retrieval miss)
- needed: ['RAGAgent', 'checkpointer', 'make_checkpointer']  missing: ['RAGAgent', 'checkpointer', 'make_checkpointer']
- correct: `RAGAgent(services, checkpointer=make_checkpointer(settings))`
- model:   `Agent(settings=settings, kb=kb, services=services)`

## id 20 - C: cheat sheet MISSING the name (retrieval miss)
- needed: ['check']  missing: ['check']
- correct: `for check in CHART_CHECKS:
            problems.extend(check(part, xml))`
- model:   `for check in CHART_CHECKS:
            problems.extend(check(xml))`

## id 26 - A: answer needs no outside names
- needed: []  missing: []
- correct: `True, "effort": "high"}`
- model:   `False}`

## id 32 - C: cheat sheet MISSING the name (retrieval miss)
- needed: ['match_info', 'tail']  missing: ['match_info', 'tail']
- correct: `"/" + request.match_info.get("tail", "").lstrip("/")`
- model:   `request.rel_url.path`

## id 37 - A: answer needs no outside names
- needed: []  missing: []
- correct: `FirecrawlWebSearchProvider())`
- model:   `FirecrawlWebSearchProvider())`

## id 39 - B: cheat sheet HAD the name
- needed: ['Path']  missing: []
- correct: `Path(name).suffix.lower()`
- model:   `file.filename.rsplit(".", 1)[-1].lower()`

## id 43 - A: answer needs no outside names
- needed: []  missing: []
- correct: `_data_dir() / name`
- model:   `_data_dir() / name`

## id 47 - C: cheat sheet MISSING the name (retrieval miss)
- needed: ['context']  missing: ['context']
- correct: `runtime.context`
- model:   `state["services"]`

## id 51 - A: answer needs no outside names
- needed: []  missing: []
- correct: `if results_dir and live_report_path:
        (results_dir / "report.html").write_text(generate_html(output, auto_refresh`
- model:   `# Write final HTML report (with auto-refresh)
    if args.live_report:
        live_report_path.write_text(generate_html`

## id 77 - A: answer needs no outside names
- needed: []  missing: []
- correct: `(proc.output_buffer or "")[-32768:]`
- model:   `process_activity(proc)`

## id 88 - C: cheat sheet MISSING the name (retrieval miss)
- needed: ['langchain_openai']  missing: ['langchain_openai']
- correct: `langchain_openai import ChatOpenAI`
- model:   `langchain_core.llms import OpenAI as ChatOpenAI`

## id 91 - C: cheat sheet MISSING the name (retrieval miss)
- needed: ['allow_permanent', 'text_choice_always']  missing: ['allow_permanent', 'text_choice_always']
- correct: `if allow_permanent:
            choices.append(t("gateway.exec_approval.text_choice_always", prefix=prefix))`
- model:   `if allow_session:
            choices.append(t("gateway.exec_approval.text_choice_session_deny", prefix=prefix))`

## id 116 - C: cheat sheet MISSING the name (retrieval miss)
- needed: ['WebSearcher', 'enable_web', 'from_settings']  missing: ['WebSearcher', 'enable_web', 'from_settings']
- correct: `WebSearcher.from_settings(settings) if settings.enable_web else None`
- model:   `Web(settings)`

## id 119 - C: cheat sheet MISSING the name (retrieval miss)
- needed: ['A', 'Allocation', 'CAS', 'CDN', 'ChannelConflict', 'a', 'before', 'changed', 'gap', 'head', 'leaving', 'may', 'must', 'qualify', 're', 'readback', 'response', 'retirement', 'retry', 'stale', 'subsequent', 'superseded', 'the']  missing: ['A', 'Allocation', 'CAS', 'CDN', 'ChannelConflict', 'a', 'before', 'changed', 'gap', 'head', 'leaving', 'may', 'must', 'qualify', 're', 'readback', 'response', 'retirement', 'retry', 'stale', 'subsequent', 'superseded', 'the']
- correct: `if current is not None and current[0] != body:
                # A real subsequent CAS is not a stale CDN response. Allo`
- model:   ``

## id 121 - A: answer needs no outside names
- needed: []  missing: []
- correct: `sum(r["triggers"] for r in pos)`
- model:   `len(pos) - sum(r["triggers"] for r in pos)`

## id 128 - C: cheat sheet MISSING the name (retrieval miss)
- needed: ['chose', 'eat', 'this', 'to']  missing: ['chose', 'eat', 'this', 'to']
- correct: `if line:  # None/"" == adapter chose to eat this event
            self._enqueue_tool_line(line)`
- model:   `self._enqueue_tool_line(line)`

## id 130 - C: cheat sheet MISSING the name (retrieval miss)
- needed: ['returncode', 'stderr']  missing: ['returncode', 'stderr']
- correct: `if listed.returncode != 0:
        raise RuntimeError(listed.stdout + listed.stderr)`
- model:   `if is_release_age_failure(listed.stdout):
        raise RuntimeError(f"pnpm list --recursive --depth -1 --json failed wi`

## id 134 - C: cheat sheet MISSING the name (retrieval miss)
- needed: ['LINTERS', 'files']  missing: ['LINTERS', 'files']
- correct: `if ext not in LINTERS:
            return LintResult(skipped=True, message=f"No linter for {ext} files")`
- model:   `elif ext in _FAIL_CLOSED_INPROC_EXTS:
            return LintResult(skipped=True, message=f"Failed to read {path} for li`

## id 137 - C: cheat sheet MISSING the name (retrieval miss)
- needed: ['_unauth_response', 'clear_sso_attempt_cookie', 'no_cookie', 'read_sso_attempt_cookie']  missing: ['_unauth_response', 'clear_sso_attempt_cookie', 'no_cookie', 'read_sso_attempt_cookie']
- correct: `if read_sso_attempt_cookie(request, gateway):
        resp = _unauth_response(request, reason="no_cookie")
        clear`
- model:   `if gateway:
        return gateway`

## id 141 - C: cheat sheet MISSING the name (retrieval miss)
- needed: ['ServerlessSpec']  missing: ['ServerlessSpec']
- correct: `Pinecone, ServerlessSpec`
- model:   `Pinecone`

## id 144 - A: answer needs no outside names
- needed: []  missing: []
- correct: `if target.startswith(("http://", "https://")):
            return self.ingest_url(target)`
- model:   `if target.startswith("http://") or target.startswith("https://"):
            return self.ingest_url(target)
        eli`

## id 147 - A: answer needs no outside names
- needed: []  missing: []
- correct: `if theme in owner:
            yield master, rels_path, element, theme, owner[theme]
        else:
            owner[the`
- model:   `first = master
        theme = _resolve(rels_path, theme)
        owner[theme] = master`

## id 154 - A: answer needs no outside names
- needed: []  missing: []
- correct: `store`
- model:   `store  # app.rag.vectorstore.ChunkStore (or a fake in tests)`

## id 163 - C: cheat sheet MISSING the name (retrieval miss)
- needed: ['validate_local_lineage']  missing: ['validate_local_lineage']
- correct: `validate_local_lineage(conn, saved)`
- model:   `saved['target']`

## id 167 - A: answer needs no outside names
- needed: []  missing: []
- correct: `"web_search", web_search, retry_policy=network_retry)`
- model:   `"rewrite_web", rewrite_web)`

## id 169 - C: cheat sheet MISSING the name (retrieval miss)
- needed: ['missing_keys']  missing: ['missing_keys']
- correct: `settings.missing_keys()`
- model:   `[]`

## id 177 - C: cheat sheet MISSING the name (retrieval miss)
- needed: ['idle_seconds', 'idle_stop_seconds']  missing: ['idle_seconds', 'idle_stop_seconds']
- correct: `next_check_in(runtime.idle_stop_seconds(), runtime.idle_seconds())`
- model:   `next_check_in(runtime.DEFAULT_IDLE_STOP_MINUTES, runtime._get_idle())`

## id 195 - A: answer needs no outside names
- needed: []  missing: []
- correct: `fields, extras`
- model:   `fields`

## id 216 - C: cheat sheet MISSING the name (retrieval miss)
- needed: ['output']  missing: ['output']
- correct: `["claude", "-p", "--output-format", "text"]`
- model:   `["claude", "-p"]`

## id 219 - C: cheat sheet MISSING the name (retrieval miss)
- needed: ['Agentic', 'ArgumentParser', 'Copilot', 'Knowledge', 'RAG', 'argparse', 'description', 'tools']  missing: ['Agentic', 'ArgumentParser', 'Copilot', 'Knowledge', 'RAG', 'argparse', 'description', 'tools']
- correct: `argparse.ArgumentParser(description="Agentic RAG Knowledge Copilot tools")`
- model:   `argparse.ArgumentParser()`

## id 229 - C: cheat sheet MISSING the name (retrieval miss)
- needed: ['A', 'HTTP_401_UNAUTHORIZED', '_same_secret', 'access_code', 'ask', 'needed', 'to', 'valid']  missing: ['A', 'HTTP_401_UNAUTHORIZED', '_same_secret', 'access_code', 'ask', 'to', 'valid']
- correct: `if settings.access_code and not _same_secret(x_access_code, settings.access_code):
        raise HTTPException(status.HT`
- model:   `if x_access_code == settings.access_code:
        return`

## id 243 - C: cheat sheet MISSING the name (retrieval miss)
- needed: ['com', 'extensions', 'hermes', 'nousresearch']  missing: ['com', 'extensions', 'hermes', 'nousresearch']
- correct: `package.manifest.get("extensions", {}).get("com.nousresearch.hermes", {})`
- model:   `{}`
