import { type KeyboardEvent, useCallback, useId, useLayoutEffect, useRef } from 'react'

import { ArrowUpIcon } from '@/components/layout/NavIcons'
import Spinner from '@/components/ui/Spinner'

export interface MessageComposerProps {
  value: string
  onChange: (value: string) => void
  onSend: () => void
  disabled?: boolean
  isSending?: boolean
  error?: string | null
}

const MAX_LINES = 7
const LINE_HEIGHT_PX = 24
const MAX_TEXTAREA_HEIGHT_PX = LINE_HEIGHT_PX * MAX_LINES

export default function MessageComposer({
  value,
  onChange,
  onSend,
  disabled = false,
  isSending = false,
  error = null,
}: MessageComposerProps) {
  const textareaRef = useRef<HTMLTextAreaElement>(null)
  const hintId = useId()
  const isDisabled = disabled || isSending
  const canSend = !isDisabled && value.trim().length > 0

  const resizeTextarea = useCallback(() => {
    const element = textareaRef.current
    if (!element) return

    element.style.height = 'auto'
    element.style.height = `${Math.min(element.scrollHeight, MAX_TEXTAREA_HEIGHT_PX)}px`
  }, [])

  useLayoutEffect(() => {
    resizeTextarea()
  }, [value, resizeTextarea])

  function handleChange(nextValue: string) {
    onChange(nextValue)
    resizeTextarea()
  }

  function handleKeyDown(event: KeyboardEvent<HTMLTextAreaElement>) {
    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault()
      if (canSend) {
        onSend()
      }
    }
  }

  function handleSend() {
    if (canSend) {
      onSend()
      textareaRef.current?.focus()
    }
  }

  return (
    <div className="chat-composer">
      <div className="chat-input-fade" aria-hidden />

      {error && (
        <p role="alert" className="mb-3 text-sm text-error-500">
          {error}
        </p>
      )}

      <div className="chat-input-bar">
        <label htmlFor="chat-message" className="sr-only">
          Message
        </label>
        <textarea
          ref={textareaRef}
          id="chat-message"
          rows={1}
          value={value}
          disabled={isDisabled}
          aria-describedby={hintId}
          placeholder="Ask a question about your organisation's knowledge…"
          className="chat-input-field scrollbar-thin"
          style={{
            maxHeight: MAX_TEXTAREA_HEIGHT_PX,
            lineHeight: `${LINE_HEIGHT_PX}px`,
          }}
          onChange={(event) => handleChange(event.target.value)}
          onKeyDown={handleKeyDown}
        />

        <button
          type="button"
          className="chat-send-button"
          disabled={!canSend}
          aria-label="Send message"
          onClick={handleSend}
        >
          {isSending ? (
            <Spinner size="sm" label="Sending message" />
          ) : (
            <ArrowUpIcon />
          )}
        </button>
      </div>

      <p id={hintId} className="mt-2 px-1 text-[11px] text-subtle">
        Press Enter to send, Shift+Enter for a new line.
      </p>
    </div>
  )
}
