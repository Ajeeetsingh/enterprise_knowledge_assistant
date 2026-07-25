import { useCallback, useEffect, useRef, useState } from 'react'

import EmptyState from '@/components/ui/EmptyState'
import Skeleton from '@/components/ui/Skeleton'
import { useToast } from '@/contexts/ToastContext'
import { getApiErrorMessage, resolveErrorMessage } from '@/services/errorHandler'
import { cn } from '@/utils/cn'

import { useAskQuestion } from '../hooks/useAskQuestion'
import { useConversationMessages } from '../hooks/useConversationMessages'
import { useSuggestedQuestions } from '../hooks/useSuggestedQuestions'
import { normalizeMessageCitations } from '../types'
import type { ActiveStream } from '../types/streaming'
import ChatHeader from './ChatHeader'
import MessageComposer from './MessageComposer'
import MessageList from './MessageList'

export interface ChatAreaProps {
  conversationId: string | null
  /** One-shot question from dashboard deep-link; sent once messages are ready. */
  initialQuestion?: string | null
  onInitialQuestionConsumed?: () => void
}

// Shown only while suggestions are loading, or if the request fails —
// the real list is fetched dynamically via useSuggestedQuestions.
const FALLBACK_PROMPTS = [
  'What can this assistant help me with?',
  'How does document access work?',
  'How are answers sourced?',
  'What document formats are supported?',
]

interface ChatEmptyStateProps {
  onSelectSuggestion: (question: string) => void
}

function ChatEmptyState({ onSelectSuggestion }: ChatEmptyStateProps) {
  const { data, isLoading } = useSuggestedQuestions()
  const suggestions =
    data && data.items.length > 0 ? data.items.map((item) => item.text) : FALLBACK_PROMPTS

  return (
    <EmptyState
      icon={
        <svg
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="1.5"
          className="size-6"
          aria-hidden
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            d="M8 10h8M8 14h5M6 4h12a2 2 0 0 1 2 2v12l-3-2-3 2-3-2-3 2V6a2 2 0 0 1 2-2Z"
          />
        </svg>
      }
      title="Start the conversation"
      description="Ask questions about policies, procedures, financial reports, and other organisational knowledge."
      className="max-w-md px-4 py-10 sm:px-6"
      action={
        <div className="w-full max-w-sm text-left">
          <p className="mb-2 text-xs font-medium uppercase tracking-wide text-neutral-500 dark:text-neutral-400">
            Suggested questions
          </p>
          {isLoading ? (
            <div className="space-y-2" aria-hidden>
              {[0, 1, 2].map((index) => (
                <Skeleton key={index} className="h-10 w-full" />
              ))}
            </div>
          ) : (
            <ul className="space-y-2">
              {suggestions.map((prompt) => (
                <li key={prompt}>
                  <button
                    type="button"
                    onClick={() => onSelectSuggestion(prompt)}
                    className="interactive-row w-full rounded-md border border-neutral-200 bg-white px-3 py-2 text-left text-sm text-neutral-600 transition-colors duration-150 hover:border-accent/40 hover:text-foreground dark:border-neutral-700 dark:bg-neutral-900 dark:text-neutral-300"
                  >
                    {prompt}
                  </button>
                </li>
              ))}
            </ul>
          )}
        </div>
      }
    />
  )
}

export default function ChatArea({
  conversationId,
  initialQuestion = null,
  onInitialQuestionConsumed,
}: ChatAreaProps) {
  const [draft, setDraft] = useState('')
  const [sendError, setSendError] = useState<string | null>(null)
  const [activeStream, setActiveStream] = useState<ActiveStream | null>(null)
  const [isTransitioning, setIsTransitioning] = useState(false)
  const { showError } = useToast()

  const {
    data: messages = [],
    isLoading,
    isError,
    error: messagesError,
  } = useConversationMessages(conversationId)

  const askQuestion = useAskQuestion()
  const initialQuestionConsumedRef = useRef(false)

  useEffect(() => {
    initialQuestionConsumedRef.current = false
  }, [conversationId, initialQuestion])

  useEffect(() => {
    setActiveStream(null)
    setIsTransitioning(true)
    const timer = window.setTimeout(() => setIsTransitioning(false), 180)
    return () => window.clearTimeout(timer)
  }, [conversationId])

  const handleStreamComplete = useCallback(() => {
    setActiveStream(null)
  }, [])

  const sendQuestion = useCallback(
    async (question: string) => {
      const trimmed = question.trim()
      if (!trimmed || !conversationId) return

      setSendError(null)
      setActiveStream(null)

      try {
        const result = await askQuestion.mutateAsync({
          conversation_id: conversationId,
          question: trimmed,
        })
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
    },
    [askQuestion, conversationId, showError],
  )

  // Consume a dashboard deep-linked question once the conversation is empty/ready.
  useEffect(() => {
    const question = initialQuestion?.trim()
    if (
      !question ||
      !conversationId ||
      isLoading ||
      isError ||
      askQuestion.isPending ||
      initialQuestionConsumedRef.current
    ) {
      return
    }
    if (messages.length > 0 || activeStream) {
      initialQuestionConsumedRef.current = true
      onInitialQuestionConsumed?.()
      return
    }

    initialQuestionConsumedRef.current = true
    onInitialQuestionConsumed?.()
    void sendQuestion(question)
  }, [
    initialQuestion,
    conversationId,
    isLoading,
    isError,
    messages.length,
    activeStream,
    askQuestion.isPending,
    sendQuestion,
    onInitialQuestionConsumed,
  ])

  if (!conversationId) {
    return (
      <section className="flex h-full min-h-0 flex-1 items-center justify-center bg-neutral-100 dark:bg-neutral-950">
        <EmptyState
          icon={
            <svg
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="1.5"
              className="size-6"
              aria-hidden
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="M7 8h10M7 12h6m-3 8l-3-2-3 2-3-2-3 2V6a2 2 0 0 1 2-2h10a2 2 0 0 1 2 2v12l-3-2-3 2-3-2-3 2Z"
              />
            </svg>
          }
          title="Select a conversation"
          description="Choose an existing conversation from the panel, or create a new one to begin."
          className="px-4 py-10 sm:px-6"
        />
      </section>
    )
  }

  function handleSend() {
    return sendQuestion(draft)
  }

  function handleSelectSuggestion(question: string) {
    return sendQuestion(question)
  }

  const showEmptyState =
    !isError && messages.length === 0 && !isLoading && !activeStream && !isTransitioning && !initialQuestion

  return (
    <section className="flex h-full min-h-0 min-w-0 flex-1 flex-col bg-surface">
      <ChatHeader conversationId={conversationId} messages={messages} />

      {isError && (
        <p
          role="alert"
          className="shrink-0 border-b border-error-500/20 bg-error-50 px-4 py-3 text-sm text-error-700 dark:bg-error-700/10 dark:text-error-400 sm:px-6"
        >
          {resolveErrorMessage(messagesError, 'Something went wrong. Please try again.')}
        </p>
      )}

      <div
        key={conversationId}
        className={cn(
          'flex min-h-0 flex-1 flex-col',
          !isTransitioning && 'animate-fade-in',
        )}
      >
        {showEmptyState ? (
          <div className="flex min-h-0 flex-1 items-center justify-center">
            <ChatEmptyState onSelectSuggestion={(question) => void handleSelectSuggestion(question)} />
          </div>
        ) : (
          <MessageList
            conversationId={conversationId}
            messages={messages}
            isLoading={isLoading}
            activeStream={activeStream}
            onStreamComplete={handleStreamComplete}
          />
        )}
      </div>

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
