import { type FormEvent, useState } from 'react'
import { useNavigate } from 'react-router-dom'

import { ArrowUpIcon } from '@/components/layout/NavIcons'
import { cn } from '@/utils/cn'

/**
 * Dashboard ask bar — visually matches the chat composer input bar.
 * Submitting navigates to /chat with the question as initial state.
 */
export default function DashboardAskBar() {
  const navigate = useNavigate()
  const [value, setValue] = useState('')

  function handleSubmit(event?: FormEvent) {
    event?.preventDefault()
    const question = value.trim()
    if (!question) return
    navigate('/chat', { state: { initialQuestion: question } })
  }

  const canSend = value.trim().length > 0

  return (
    <form onSubmit={handleSubmit} className="w-full">
      <label htmlFor="dashboard-ask" className="sr-only">
        Ask anything
      </label>
      <div
        className={cn(
          'flex items-end gap-3 rounded-[var(--radius-lg)] border border-border-default',
          'bg-surface-raised px-4 py-3.5 shadow-elevation-sm',
          'transition-[border-color,box-shadow] duration-200',
          'focus-within:border-accent focus-within:shadow-[0_0_0_3px_var(--accent-muted)]',
        )}
      >
        <input
          id="dashboard-ask"
          type="text"
          value={value}
          onChange={(event) => setValue(event.target.value)}
          placeholder="Ask anything about your organisation's knowledge…"
          className={cn(
            'min-w-0 flex-1 bg-transparent text-[15px] text-foreground outline-none',
            'placeholder:text-subtle',
          )}
          autoComplete="off"
        />
        <button
          type="submit"
          disabled={!canSend}
          aria-label="Ask question"
          className={cn(
            'chat-send-button',
            !canSend && 'cursor-not-allowed',
          )}
        >
          <ArrowUpIcon className="size-4" />
        </button>
      </div>
    </form>
  )
}
