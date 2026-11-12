package com.github.naveenand.quiettab
import com.google.gson.Gson
import com.google.gson.JsonArray
import com.google.gson.JsonObject
import com.intellij.codeInsight.inline.completion.InlineCompletion
import com.intellij.codeInsight.inline.completion.InlineCompletionEvent
import com.intellij.codeInsight.inline.completion.InlineCompletionEventAdapter
import com.intellij.codeInsight.inline.completion.InlineCompletionEventType
import com.intellij.codeInsight.inline.completion.InlineCompletionProvider
import com.intellij.codeInsight.inline.completion.InlineCompletionProviderID
import com.intellij.codeInsight.inline.completion.InlineCompletionRequest
import com.intellij.codeInsight.inline.completion.elements.InlineCompletionGrayTextElement
import com.intellij.codeInsight.inline.completion.suggestion.InlineCompletionSingleSuggestion
import com.intellij.codeInsight.inline.completion.suggestion.InlineCompletionSuggestion
import com.intellij.openapi.application.readAction
import com.intellij.openapi.diagnostic.thisLogger
import com.intellij.openapi.editor.Editor
import com.intellij.openapi.project.IndexNotReadyException
import com.intellij.openapi.roots.ProjectFileIndex
import com.intellij.psi.PsiComment
import com.intellij.psi.PsiElement
import com.intellij.psi.PsiErrorElement
import com.intellij.psi.PsiFile
import com.intellij.psi.PsiFileFactory
import com.intellij.psi.PsiNameIdentifierOwner
import com.intellij.psi.util.PsiTreeUtil
import kotlinx.coroutines.delay
import kotlinx.coroutines.future.await
import java.net.URI
import java.net.http.HttpClient
import java.net.http.HttpRequest
import java.net.http.HttpResponse
import java.time.Duration
import java.util.Collections
import java.util.WeakHashMap
import kotlin.coroutines.cancellation.CancellationException

class QuietTabProvider : InlineCompletionProvider {
    override val id = InlineCompletionProviderID("QuietTab")

    // HTTP/1.1: stops uvicorn's "Unsupported upgrade request" warnings
    private val http = HttpClient.newBuilder()
        .version(HttpClient.Version.HTTP_1_1)
        .connectTimeout(Duration.ofMillis(500))
        .build()
    private val gson = Gson()

    // ---- memory between keystrokes ----
    private val keystrokes = ArrayDeque<Long>()   // times of recent keystrokes (typing speed)
    private val outcomes = ArrayDeque<Boolean>()  // last 20 results: true = accepted
    @Volatile private var lastShown: Shown? = null
    @Volatile private var lastGated: Shown? = null   // last suggestion the gate hid
    @Volatile private var shownAt = 0L               // when the current gray text appeared
    @Volatile private var partialChars = 0           // chars taken word-by-word (Ctrl+Right)
    private val watched = Collections.synchronizedSet(Collections.newSetFromMap(WeakHashMap<Editor, Boolean>()))

    // Fix 8: the IDE tells us exactly what happened to the gray text (Tab, typed it, Esc, moved away...)
    private val outcomeListener = object : InlineCompletionEventAdapter {
        override fun onChange(event: InlineCompletionEventType.Change) {
            // lengthChange < 0 = gray text got shorter; count it only for word-by-word accepts
            if (lastShown != null && event.event is InlineCompletionEvent.PartialAccept) partialChars -= event.lengthChange
        }

        override fun onHide(event: InlineCompletionEventType.Hide) {
            val s = lastShown ?: return
            lastShown = null
            val finish = event.finishType.name
            val outcome = when (finish) {
                "SELECTED" -> "accepted"            // Tab
                "TYPED" -> "typed_through"          // typed the whole suggestion by hand
                else -> if (partialChars > 0) "partial" else "rejected"
            }
            log(s.info.deepCopy().apply {
                addProperty("event", outcome)
                addProperty("finish", finish)      // ESCAPE_PRESSED, INVALIDATED, CARET_CHANGED, ...
                addProperty("partial_chars", partialChars)
                addProperty("shown_ms", System.currentTimeMillis() - shownAt)
            })
            synchronized(outcomes) { outcomes.addLast(outcome != "rejected"); if (outcomes.size > 20) outcomes.removeFirst() }
            partialChars = 0
        }
    }

    private data class Shown(val offset: Int, val text: String, val info: JsonObject)
    private data class Snippet(val filename: String, val text: String)
    private data class Ctx(
        val prefix: String, val suffix: String, val cursor: Int,
        val codeAfter: Boolean, val inComment: Boolean, val ext: String,
        val throughGated: Boolean,
    )

    override fun isEnabled(event: InlineCompletionEvent): Boolean =
        event is InlineCompletionEvent.DocumentChange

    override suspend fun getSuggestion(request: InlineCompletionRequest): InlineCompletionSuggestion {
        if (isSensitive(request.file.virtualFile?.name.orEmpty())) return empty()   // never send or log secrets
        if (watched.add(request.editor)) InlineCompletion.getHandlerOrNull(request.editor)?.addEventListener(outcomeListener)
        val cps = recordKeystroke(System.currentTimeMillis())

        // 1. Read the code around the cursor
        val ctx = readAction {
            val text = request.document.charsSequence
            val cursor = request.endOffset
            val lineEnd = text.indexOf('\n', cursor).let { if (it == -1) text.length else it }
            val restOfLine = text.subSequence(cursor, lineEnd)
            val element = request.file.findElementAt(maxOf(0, cursor - 1))
            // is the user typing exactly what the gate just hid?
            val throughGated = lastGated?.let { g ->
                val typed = cursor - g.offset
                typed in 1 until g.text.length &&
                        text.subSequence(g.offset, cursor).toString() == g.text.substring(0, typed)
            } ?: false
            Ctx(
                prefix = text.subSequence(maxOf(0, cursor - PREFIX_CHARS), cursor).toString(),
                suffix = text.subSequence(cursor, minOf(text.length, cursor + SUFFIX_CHARS)).toString(),
                cursor = cursor,
                // real code later on this line (not just ) ] } ; " or spaces) -> don't push text into it
                codeAfter = restOfLine.any { it.isLetterOrDigit() || it == '_' },
                inComment = PsiTreeUtil.getParentOfType(element, PsiComment::class.java, false) != null,
                ext = request.file.virtualFile?.extension ?: "",
                throughGated = throughGated,
            )
        }

        // 2. (accept/reject is now logged by outcomeListener, from the IDE's own events)
        // 2b. Typing through a suggestion the gate already hid -> it would stay hidden; skip the model call
        if (ctx.throughGated) {
            log(JsonObject().apply { addProperty("ext", ctx.ext); addProperty("event", "skipped"); addProperty("reason", "typing_through_gated") })
            return empty()
        }
        lastGated = null

        // 3. Adaptive wait. Typing again cancels this call (= debounce + cancel stale)
        val waitMs = currentDelay()
        delay(waitMs)

        val base = JsonObject().apply {
            addProperty("ext", ctx.ext); addProperty("cps", cps); addProperty("delay_ms", waitMs)
        }

        // 4. Gate 0: skip obviously bad moments without calling the model
        val skip = when {
            ctx.codeAfter -> "code_after"
            ctx.inComment -> "in_comment"
            else -> null
        }
        if (skip != null) {
            log(base.apply { addProperty("event", "skipped"); addProperty("reason", skip) })
            return empty()
        }

        // 5. Cheat sheet = imports + signatures of things you just used
        val extra = readAction { collectContext(request.file, request.document.charsSequence, ctx.cursor) }
        base.addProperty("n_extra", extra.size)
        base.addProperty("extra_chars", extra.sumOf { it.text.length })

        // 6. Ask the model server
        val res = fetch(ctx.prefix, ctx.suffix, extra) ?: return empty()
        val text = res.get("text")?.asString.orEmpty()
        if (text.isBlank()) {
            log(base.apply { addProperty("event", "empty") })
            return empty()
        }
        // 6b. Gate 1 (Phase 7): the server's confidence gate says "stay quiet"
        if (res.get("show")?.asBoolean == false) {
            log(base.apply {
                addProperty("event", "gated")
                res.get("p_good")?.let { add("p_good", it) }
                res.get("avg_logprob")?.let { add("avg_logprob", it) }
                addProperty("text", text)
            })
            lastGated = Shown(ctx.cursor, text, base)
            return empty()
        }

        // 7. Gate 2: drop the suggestion if it adds syntax errors
        val addsErrors = readAction {
            val doc = request.document.charsSequence
            if (doc.length > 200_000 || ctx.cursor > doc.length) false
            else countErrors(request.file, StringBuilder(doc).insert(ctx.cursor, text)) > countErrors(request.file, doc)
        }
        if (addsErrors) {
            log(base.apply { addProperty("event", "dropped_syntax"); addProperty("text", text) })
            return empty()
        }

        // 8. Show it, and remember it so outcomeListener can log what happened to it
        val info = base.apply {
            for (key in listOf("latency_ms", "avg_logprob", "min_logprob", "single_line", "raw_text", "p_good")) res.get(key)?.let { add(key, it) }
            addProperty("text", text)
            addProperty("text_len", text.length)
        }
        log(info.deepCopy().apply { addProperty("event", "shown") })
        shownAt = System.currentTimeMillis(); partialChars = 0
        lastShown = Shown(ctx.cursor, text, info)
        return InlineCompletionSingleSuggestion.build { emit(InlineCompletionGrayTextElement(text)) }
    }

    // ---- context (Step 5) ----

    private fun collectContext(file: PsiFile, text: CharSequence, cursor: Int): List<Snippet> = try {
        val winStart = maxOf(0, cursor - PREFIX_CHARS)
        val winEnd = minOf(text.length, cursor + SUFFIX_CHARS)
        val out = LinkedHashMap<String, Snippet>()

        // a) imports at the top of the file, if they're not already inside the window
        if (winStart > 0) {
            val imports = text.lineSequence().take(150)
                .filter { it.startsWith("import ") || it.startsWith("from ") || it.startsWith("package ") }
                .joinToString("\n")
            if (imports.isNotBlank()) out["imports"] = Snippet(file.name, imports)
        }

        // b) names used in the last ~400 chars -> where are they defined? keep the signature
        val index = ProjectFileIndex.getInstance(file.project)
        var offset = maxOf(winStart, cursor - 400)
        while (offset < cursor && out.size < 6) {
            val leaf = file.findElementAt(offset) ?: break
            offset = maxOf(leaf.textRange.endOffset, offset + 1)
            val target = (leaf.parent?.reference ?: leaf.reference)?.resolve() ?: continue
            val vf = target.containingFile?.virtualFile ?: continue
            if (!index.isInContent(vf)) continue                                          // only YOUR code
            val start = target.textRange?.startOffset ?: continue
            if (target.containingFile == file && start in winStart until winEnd) continue // already visible
            out.putIfAbsent("${vf.path}:$start", Snippet(vf.name, signatureOf(target)))
        }
        out.values.toList()
    } catch (e: IndexNotReadyException) {
        emptyList()   // IDE is still indexing: just send no cheat sheet this time
    }

    // A function -> its header line. A class -> its header + its members' header lines.
    private fun signatureOf(el: PsiElement): String {
        val header = headerOf(el)
        if (!CLASS_LIKE.containsMatchIn(header)) return header
        val members = PsiTreeUtil.findChildrenOfType(el, PsiNameIdentifierOwner::class.java)
            .filter { PsiTreeUtil.getParentOfType(it, PsiNameIdentifierOwner::class.java, true) == el }
            .take(15)
            .joinToString("\n") { "    " + headerOf(it) }
        return "$header\n$members".take(1000)
    }

    // Text up to where the body starts: "{" (Java/Kotlin) or ":" + newline (Python).
    // Doc comments (/** ... */ and # lines) are removed first so they don't eat the 300-char budget.
    private fun headerOf(el: PsiElement): String {
        val t = el.text
            .replace(Regex("/\\*.*?\\*/", RegexOption.DOT_MATCHES_ALL), "")
            .lineSequence().filterNot { it.trim().startsWith("//") || it.trim().startsWith("#") }
            .joinToString("\n")
        val cut = listOf(t.indexOf('{'), t.indexOf(":\n")).filter { it >= 0 }.minOrNull()
        val h = if (cut != null) t.substring(0, cut + 1) else t.lineSequence().first()
        return h.replace(Regex("\\s+"), " ").trim().take(300)
    }

    // ---- helpers ----
    private fun empty() = InlineCompletionSingleSuggestion.build { }

    // Parse a copy of the file with IntelliJ's own parser and count syntax errors
    private fun countErrors(file: PsiFile, text: CharSequence): Int {
        val copy = PsiFileFactory.getInstance(file.project).createFileFromText(file.name, file.language, text)
        return PsiTreeUtil.findChildrenOfType(copy, PsiErrorElement::class.java).size
    }

    private fun recordKeystroke(now: Long): Int = synchronized(keystrokes) {
        keystrokes.addLast(now)
        while (keystrokes.isNotEmpty() && now - keystrokes.first() > 1000) keystrokes.removeFirst()
        keystrokes.size
    }

    // 150 ms until we have 5 results; then 100 ms (accept everything) ... 500 ms (reject everything)
    private fun currentDelay(): Long = synchronized(outcomes) {
        if (outcomes.size < 5) 150L
        else (100 + (1 - outcomes.count { it }.toDouble() / outcomes.size) * 400).toLong()
    }

    private suspend fun fetch(prefix: String, suffix: String, extra: List<Snippet>): JsonObject? {
        val body = JsonObject().apply {
            addProperty("prefix", prefix)
            addProperty("suffix", suffix)
            add("extra", JsonArray().apply {
                extra.forEach { s -> add(JsonObject().apply { addProperty("filename", s.filename); addProperty("text", s.text) }) }
            })
        }
        return try {
            val res = http.sendAsync(post("$BASE/complete", body, 1000), HttpResponse.BodyHandlers.ofString()).await()
            if (res.statusCode() != 200) null else gson.fromJson(res.body(), JsonObject::class.java)
        } catch (e: CancellationException) {
            throw e
        } catch (e: Exception) {
            thisLogger().warn("QuietTab: server call failed: ${e.message}")
            null
        }
    }

    private fun log(event: JsonObject) {
        event.addProperty("ts", System.currentTimeMillis())
        http.sendAsync(post("$BASE/log", event, 1000), HttpResponse.BodyHandlers.discarding())
    }

    private fun post(url: String, body: JsonObject, timeoutMs: Long): HttpRequest =
        HttpRequest.newBuilder(URI.create(url))
            .timeout(Duration.ofMillis(timeoutMs))
            .header("Content-Type", "application/json")
            .POST(HttpRequest.BodyPublishers.ofString(gson.toJson(body)))
            .build()

    companion object {
        const val BASE = "http://localhost:8000"
        const val PREFIX_CHARS = 1500
        const val SUFFIX_CHARS = 500
        private val CLASS_LIKE = Regex("\\b(class|interface|enum|object|record)\\b")
        private val SECRET_NAMES = Regex("""(?i)^\.env(\..*)?$|\.(pem|key|p12|pfx|jks|keystore)$|secret|credential|id_rsa""")
        fun isSensitive(name: String) = SECRET_NAMES.containsMatchIn(name)
    }
}