import { type KeyboardEvent, useRef } from 'react'

import Button from '@/components/ui/Button'

export interface MessageComposerProps {
  value: string
  onChange: (value: string) => void
  onSend: () => void
  disabled?: boolean
  isSending?: boolean
  error?: string | null
}

export default function MessageComposer({
  value,
  onChange,
  onSend,
  disabled = false,
  isSending = false,
  error = null,
}: MessageComposerProps) {
  const textareaRef = useRef<HTMLTextAreaElement>(null)
  const isDisabled = disabled || isSending

  function handleKeyDown(event: KeyboardEvent<HTMLTextAreaElement>) {
    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault()
      if (!isDisabled && value.trim()) {
        onSend()
      }
    }
  }

  function handleSend() {
    if (!isDisabled && value.trim()) {
      onSend()
      textareaRef.current?.focus()
    }
  }

  return (
    <div className="border-t border-neutral-200 bg-white p-4 dark:border-neutral-700 dark:bg-neutral-900">
      {error && (
        <p role="alert" className="mb-3 text-sm text-error-500 dark:text-error-400">
          {error}
        </p>
      )}

      <div className="flex items-end gap-3">
        <label htmlFor="chat-message" className="sr-only">
          Message
        </label>
        <textarea
          ref={textareaRef}
          id="chat-message"
          rows={3}
          value={value}
          disabled={isDisabled}
          placeholder="Ask a question about your organisation's knowledge…"
          className="block w-full resize-none rounded-md border border-neutral-300 bg-white px-3 py-2 text-sm text-neutral-900 placeholder:text-neutral-400 focus:outline-none focus:ring-2 focus:ring-primary-500 disabled:cursor-not-allowed disabled:opacity-50 dark:border-neutral-600 dark:bg-neutral-800 dark:text-neutral-50"
          onChange={(event) => onChange(event.target.value)}
          onKeyDown={handleKeyDown}
        />

        <Button
          type="button"
          disabled={isDisabled || !value.trim()}
          isLoading={isSending}
          onClick={handleSend}
        >
          Send
        </Button>
      </div>

      <p className="mt-2 text-xs text-neutral-500 dark:text-neutral-400">
        Press Enter to send, Shift+Enter for a new line.
      </p>
    </div>
  )
}
