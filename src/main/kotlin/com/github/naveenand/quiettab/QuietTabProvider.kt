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

    private val http = HttpClient.newBuilder()
        .connectTimeout(Duration.ofMillis(500))
        .build()
    private val gson = Gson()

    // Ask for a suggestion whenever the user types
    override fun isEnabled(event: InlineCompletionEvent): Boolean =
        event is InlineCompletionEvent.DocumentChange

    override suspend fun getSuggestion(request: InlineCompletionRequest): InlineCompletionSuggestion {
        // 1. Wait 150 ms. If the user types again, IntelliJ cancels this call (= debounce + cancel stale)
        delay(150)

        // 2. Read the code around the cursor: 1500 chars before, 500 after
        val (prefix, suffix) = readAction {
            val text = request.document.charsSequence
            val cursor = request.endOffset
            val start = maxOf(0, cursor - 1500)
            val end = minOf(text.length, cursor + 500)
            text.subSequence(start, cursor).toString() to text.subSequence(cursor, end).toString()
        }

        // 3. Ask our FastAPI server
        val suggestion = fetch(prefix, suffix)

        // 4. Show it in gray, or show nothing
        return InlineCompletionSingleSuggestion.build {
            if (!suggestion.isNullOrBlank()) emit(InlineCompletionGrayTextElement(suggestion))
        }
    }

    private suspend fun fetch(prefix: String, suffix: String): String? {
        val body = JsonObject().apply {
            addProperty("prefix", prefix)
            addProperty("suffix", suffix)
        }
        val req = HttpRequest.newBuilder(URI.create(SERVER_URL))
            .timeout(Duration.ofSeconds(1))
            .header("Content-Type", "application/json")
            .POST(HttpRequest.BodyPublishers.ofString(gson.toJson(body)))
            .build()
        return try {
            val res = http.sendAsync(req, HttpResponse.BodyHandlers.ofString()).await()
            if (res.statusCode() != 200) return null
            gson.fromJson(res.body(), JsonObject::class.java).get("text")?.asString
        } catch (e: CancellationException) {
            throw e   // user typed again: let IntelliJ cancel us
        } catch (e: Exception) {
            thisLogger().warn("QuietTab: server call failed: ${e.message}")
            null      // server down or slow: just show nothing
        }
    }

    companion object {
        const val SERVER_URL = "http://localhost:8000/complete"
    }
}