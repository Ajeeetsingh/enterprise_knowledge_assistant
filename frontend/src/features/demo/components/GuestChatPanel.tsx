import { useCallback, useEffect, useMemo, useState } from 'react'

import MessageComposer from '@/features/chat/components/MessageComposer'
import { resolveErrorMessage } from '@/services/errorHandler'

import {
  GUEST_API_HISTORY_MAX_MESSAGES,
  GUEST_CONVERSATION_ID,
  GUEST_QUESTION_LIMIT,
} from '../constants'
import { askGuestQuestion } from '../services/demoApi'
import {
  loadGuestSession,
  saveGuestSession,
} from '../storage/guestSessionStorage'
import { createGuestMessage, type GuestMessage, type GuestSessionState } from '../types'
import GuestEmptyState from './GuestEmptyState'
import GuestLimitBanner from './GuestLimitBanner'
import GuestMessageList from './GuestMessageList'

function buildHistoryPayload(messages: GuestMessage[]) {
  return messages.slice(-GUEST_API_HISTORY_MAX_MESSAGES).map((message) => ({
    role: message.role === 'assistant' ? ('assistant' as const) : ('user' as const),
    content: message.content,
    answer_kind: message.answerKind ?? null,
  }))
}

/**
 * Guest chat panel — sessionStorage-backed state + public /demo/ask API.
 * Never calls authenticated conversation or /chat/ask endpoints.
 */
export default function GuestChatPanel() {
  const [session, setSession] = useState<GuestSessionState>(() => loadGuestSession())
  const [draft, setDraft] = useState('')
  const [isSending, setIsSending] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const limitReached = session.successfulQuestionCount >= GUEST_QUESTION_LIMIT
  const messages = session.messages

  useEffect(() => {
    saveGuestSession(session)
  }, [session])

  const remaining = useMemo(
    () => Math.max(0, GUEST_QUESTION_LIMIT - session.successfulQuestionCount),
    [session.successfulQuestionCount],
  )

  const submitQuestion = useCallback(
    async (question: string, historyMessages?: GuestMessage[]) => {
      const trimmed = question.trim()
      if (!trimmed || isSending) return

      const baseMessages = historyMessages ?? session.messages
      const questionCount = session.successfulQuestionCount
      if (questionCount >= GUEST_QUESTION_LIMIT) {
        return
      }

      setError(null)
      setIsSending(true)

      const userMessage = createGuestMessage('user', trimmed)
      const historyForApi = buildHistoryPayload(baseMessages)
      setSession((prev) => ({
        ...prev,
        messages: [...baseMessages, userMessage],
        updatedAt: new Date().toISOString(),
      }))

      try {
        const response = await askGuestQuestion({
          question: trimmed,
          history: historyForApi,
        })
        const assistantMessage = createGuestMessage('assistant', response.answer, {
          requiresAuth: response.requires_auth,
          answerKind: response.answer_kind,
        })
        setSession((prev) => ({
          ...prev,
          messages: [...baseMessages, userMessage, assistantMessage],
          successfulQuestionCount: questionCount + 1,
          updatedAt: new Date().toISOString(),
        }))
      } catch (err) {
        // Failed requests do not consume the question limit.
        setError(resolveErrorMessage(err, 'Something went wrong. Please try again.'))
      } finally {
        setIsSending(false)
      }
    },
    [isSending, session.messages, session.successfulQuestionCount],
  )

  function handleSend() {
    const question = draft
    setDraft('')
    void submitQuestion(question)
  }

  function handleSelectSuggestion(question: string) {
    void submitQuestion(question)
  }

  function handleRetry() {
    if (isSending || limitReached) return
    const lastUser = [...messages].reverse().find((message) => message.role === 'user')
    if (!lastUser) return
    const withoutOrphan =
      messages[messages.length - 1]?.role === 'user' ? messages.slice(0, -1) : messages
    setError(null)
    void submitQuestion(lastUser.content, withoutOrphan)
  }

  return (
    <div className="guest-chat-panel flex h-full min-h-0 min-w-0 flex-1 flex-col bg-surface">
      <header className="guest-chat-panel__header">
        <div className="guest-chat-panel__title-row">
          <h1 className="guest-chat-panel__title">Guest chat</h1>
          <span className="guest-chat-panel__live-dot" aria-hidden />
          <span className="sr-only">Live assistant session</span>
        </div>
        <p className="guest-chat-panel__badge">
          Temporary session ·{' '}
          <span className="guest-chat-panel__count">
            {remaining} of {GUEST_QUESTION_LIMIT}
          </span>{' '}
          questions remaining
        </p>
      </header>

      <div className="flex min-h-0 flex-1 flex-col">
        {messages.length === 0 ? (
          <div className="flex min-h-0 flex-1 items-center justify-center overflow-y-auto">
            <GuestEmptyState
              onSelectSuggestion={handleSelectSuggestion}
              disabled={isSending || limitReached}
            />
          </div>
        ) : (
          <GuestMessageList conversationId={GUEST_CONVERSATION_ID} messages={messages} />
        )}
      </div>

      {limitReached && <GuestLimitBanner />}

      <div className="guest-chat-panel__composer shrink-0 px-4 pb-4 sm:px-6">
        {error && (
          <div className="mb-3 flex flex-wrap items-center gap-3" role="alert">
            <p className="text-sm text-error-500">{error}</p>
            <button
              type="button"
              onClick={handleRetry}
              className="text-sm font-medium text-accent hover:underline"
            >
              Retry
            </button>
          </div>
        )}
        <MessageComposer
          value={draft}
          onChange={setDraft}
          onSend={handleSend}
          isSending={isSending}
          disabled={isSending || limitReached}
          error={null}
        />
      </div>
    </div>
  )
}
