package com.github.naveenand.quiettab

import com.intellij.codeInsight.inline.completion.InlineCompletionEvent
import com.intellij.codeInsight.inline.completion.InlineCompletionProvider
import com.intellij.codeInsight.inline.completion.InlineCompletionProviderID
import com.intellij.codeInsight.inline.completion.InlineCompletionRequest
import com.intellij.codeInsight.inline.completion.elements.InlineCompletionGrayTextElement
import com.intellij.codeInsight.inline.completion.suggestion.InlineCompletionSingleSuggestion
import com.intellij.codeInsight.inline.completion.suggestion.InlineCompletionSuggestion

class QuietTabProvider : InlineCompletionProvider {
    override val id = InlineCompletionProviderID("QuietTab")

    // Trigger on typing
    override fun isEnabled(event: InlineCompletionEvent): Boolean =
        event is InlineCompletionEvent.DocumentChange

    // Always suggest the same text for now (Step 2 replaces this with the model)
    override suspend fun getSuggestion(request: InlineCompletionRequest): InlineCompletionSuggestion =
        InlineCompletionSingleSuggestion.build {
            emit(InlineCompletionGrayTextElement("return a + b"))
        }
}