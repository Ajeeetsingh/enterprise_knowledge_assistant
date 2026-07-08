import { useCallback, useEffect, useState } from 'react'

import EmptyState from '@/components/ui/EmptyState'
import { useToast } from '@/contexts/ToastContext'
import { getApiErrorMessage } from '@/services/errorHandler'
import type { ApiError } from '@/types'

import { useAskQuestion } from '../hooks/useAskQuestion'
import { useConversationMessages } from '../hooks/useConversationMessages'
import { normalizeMessageCitations } from '../types'
import type { ActiveStream } from '../types/streaming'
import MessageComposer from './MessageComposer'
import MessageList from './MessageList'

export interface ChatAreaProps {
  conversationId: string | null
}

function resolveErrorMessage(error: unknown): string {
  if (error && typeof error === 'object' && 'message' in error) {
    return String((error as ApiError).message)
  }
  return 'Something went wrong. Please try again.'
}

export default function ChatArea({ conversationId }: ChatAreaProps) {
  const [draft, setDraft] = useState('')
  const [sendError, setSendError] = useState<string | null>(null)
  const [activeStream, setActiveStream] = useState<ActiveStream | null>(null)
  const { showError } = useToast()

  const {
    data: messages = [],
    isLoading,
    isError,
    error: messagesError,
  } = useConversationMessages(conversationId)

  const askQuestion = useAskQuestion()

  useEffect(() => {
    setActiveStream(null)
  }, [conversationId])

  const handleStreamComplete = useCallback(() => {
    setActiveStream(null)
  }, [])

  if (!conversationId) {
    return (
      <section className="flex flex-1 items-center justify-center bg-neutral-50 dark:bg-neutral-950">
        <EmptyState
          title="Select a conversation"
          description="Choose an existing conversation or create a new one to start asking questions."
        />
      </section>
    )
  }

  async function handleSend() {
    const question = draft.trim()
    if (!question || !conversationId) return

    setSendError(null)
    setActiveStream(null)

    try {
      const result = await askQuestion.mutateAsync({ conversation_id: conversationId, question })
      setDraft('')
      setActiveStream({
        conversationId,
        content: result.answer,
        citations: normalizeMessageCitations(result.citations),
        confidence_score: result.confidence_score,
      })
    } catch (error) {
      setSendError(getApiErrorMessage(error))
      showError(getApiErrorMessage(error))
    }
  }

  return (
    <section className="flex min-w-0 flex-1 flex-col bg-neutral-50 dark:bg-neutral-950">
      {isError && (
        <p role="alert" className="border-b border-error-500/20 bg-error-50 px-4 py-3 text-sm text-error-700 dark:bg-error-700/10 dark:text-error-400">
          {resolveErrorMessage(messagesError)}
        </p>
      )}

      {!isError && messages.length === 0 && !isLoading && !activeStream ? (
        <div className="flex flex-1 items-center justify-center px-4">
          <EmptyState
            title="No messages yet"
            description="Ask your first question about policies, documents, or procedures."
          />
        </div>
      ) : (
        <MessageList
          messages={messages}
          isLoading={isLoading}
          activeStream={activeStream}
          onStreamComplete={handleStreamComplete}
        />
      )}

      <MessageComposer
        value={draft}
        onChange={setDraft}
        onSend={() => void handleSend()}
        disabled={!conversationId}
        isSending={askQuestion.isPending}
        error={sendError}
      />
    </section>
  )
}
