package com.github.naveenand.quiettab

import com.google.gson.Gson
import com.google.gson.JsonObject
import com.intellij.codeInsight.inline.completion.InlineCompletionEvent
import com.intellij.codeInsight.inline.completion.InlineCompletionProvider
import com.intellij.codeInsight.inline.completion.InlineCompletionProviderID
import com.intellij.codeInsight.inline.completion.InlineCompletionRequest
import com.intellij.codeInsight.inline.completion.elements.InlineCompletionGrayTextElement
import com.intellij.codeInsight.inline.completion.suggestion.InlineCompletionSingleSuggestion
import com.intellij.codeInsight.inline.completion.suggestion.InlineCompletionSuggestion
import com.intellij.openapi.application.readAction
import com.intellij.openapi.diagnostic.thisLogger
import com.intellij.psi.PsiComment
import com.intellij.psi.util.PsiTreeUtil
import kotlinx.coroutines.delay
import kotlinx.coroutines.future.await
import java.net.URI
import java.net.http.HttpClient
import java.net.http.HttpRequest
import java.net.http.HttpResponse
import java.time.Duration
import kotlin.coroutines.cancellation.CancellationException

class QuietTabProvider : InlineCompletionProvider {
    override val id = InlineCompletionProviderID("QuietTab")

    private val http = HttpClient.newBuilder().connectTimeout(Duration.ofMillis(500)).build()
    private val gson = Gson()

    // ---- memory between keystrokes ----
    private val keystrokes = ArrayDeque<Long>()   // times of recent keystrokes (for typing speed)
    private val outcomes = ArrayDeque<Boolean>()  // last 20 results: true = accepted, false = rejected
    @Volatile private var lastShown: Shown? = null

    private data class Shown(val offset: Int, val text: String, val info: JsonObject)
    private data class Ctx(
        val prefix: String, val suffix: String, val cursor: Int,
        val accepted: Boolean?, val midWord: Boolean, val inComment: Boolean, val ext: String,
    )

    override fun isEnabled(event: InlineCompletionEvent): Boolean =
        event is InlineCompletionEvent.DocumentChange

    override suspend fun getSuggestion(request: InlineCompletionRequest): InlineCompletionSuggestion {
        val cps = recordKeystroke(System.currentTimeMillis())   // chars typed in the last second

        // 1. Read the code, and check: was the LAST suggestion accepted?
        val ctx = readAction {
            val text = request.document.charsSequence
            val cursor = request.endOffset
            val accepted = lastShown?.let { s ->
                val end = s.offset + s.text.length
                end <= text.length && text.subSequence(s.offset, end).toString() == s.text
            }
            val lineEnd = text.indexOf('\n', cursor).let { if (it == -1) text.length else it }
            val restOfLine = text.subSequence(cursor, lineEnd)
            val element = request.file.findElementAt(maxOf(0, cursor - 1))
            Ctx(
                prefix = text.subSequence(maxOf(0, cursor - 1500), cursor).toString(),
                suffix = text.subSequence(cursor, minOf(text.length, cursor + 500)).toString(),
                cursor = cursor,
                accepted = accepted,
                midWord = restOfLine.any { it.isLetterOrDigit() || it == '_' },
                inComment = PsiTreeUtil.getParentOfType(element, PsiComment::class.java, false) != null,
                ext = request.file.virtualFile?.extension ?: "",
            )
        }

        // 2. Log the previous suggestion's result (once)
        ctx.accepted?.let { acc ->
            lastShown?.let { log(it.info.deepCopy().apply { addProperty("event", if (acc) "accepted" else "rejected") }) }
            lastShown = null
            synchronized(outcomes) { outcomes.addLast(acc); if (outcomes.size > 20) outcomes.removeFirst() }
        }

        // 3. Adaptive wait. Typing again cancels this call (= debounce + cancel stale)
        val waitMs = currentDelay()
        delay(waitMs)

        val base = JsonObject().apply {
            addProperty("ext", ctx.ext); addProperty("cps", cps); addProperty("delay_ms", waitMs)
        }

        // 4. Gate 0: skip obviously bad moments without calling the model
        val skip = when {
            ctx.midWord -> "code_after"
            ctx.inComment -> "in_comment"
            else -> null
        }
        if (skip != null) {
            log(base.apply { addProperty("event", "skipped"); addProperty("reason", skip) })
            return empty()
        }
        
        // 5. Ask the model server
        val res = fetch(ctx.prefix, ctx.suffix) ?: return empty()
        val text = res.get("text")?.asString.orEmpty()
        if (text.isBlank()) {
            log(base.apply { addProperty("event", "empty") })
            return empty()
        }

        // 6. Show it, and remember it so the next keystroke can tell if it was accepted
        val info = base.apply {
            for (key in listOf("latency_ms", "avg_logprob", "min_logprob", "single_line")) res.get(key)?.let { add(key, it) }
            addProperty("text", text)
            addProperty("text_len", text.length)
        }
        log(info.deepCopy().apply { addProperty("event", "shown") })
        lastShown = Shown(ctx.cursor, text, info)
        return InlineCompletionSingleSuggestion.build { emit(InlineCompletionGrayTextElement(text)) }
    }

    // ---- helpers ----
    private fun empty() = InlineCompletionSingleSuggestion.build { }

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

    private suspend fun fetch(prefix: String, suffix: String): JsonObject? {
        val body = JsonObject().apply { addProperty("prefix", prefix); addProperty("suffix", suffix) }
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
        http.sendAsync(post("$BASE/log", event, 1000), HttpResponse.BodyHandlers.discarding())  // fire and forget
    }

    private fun post(url: String, body: JsonObject, timeoutMs: Long): HttpRequest =
        HttpRequest.newBuilder(URI.create(url))
            .timeout(Duration.ofMillis(timeoutMs))
            .header("Content-Type", "application/json")
            .POST(HttpRequest.BodyPublishers.ofString(gson.toJson(body)))
            .build()

    companion object {
        const val BASE = "http://localhost:8000"
    }
}