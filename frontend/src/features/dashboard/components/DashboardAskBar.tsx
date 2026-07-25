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
          'dashboard-ask-bar',
          'flex items-end gap-3 rounded-[var(--radius-lg)]',
          'bg-surface-raised px-4 py-3.5',
          'transition-[border-color,box-shadow] duration-200',
        )}
      >
        <input
          id="dashboard-ask"
          type="text"
          value={value}
          onChange={(event) => setValue(event.target.value)}
          placeholder="Ask anything about your organisation's knowledge…"
          className={cn(
            'dashboard-ask-bar__input',
            'min-w-0 flex-1 border-none bg-transparent shadow-none',
            'text-[15px] text-foreground outline-none',
            'focus:outline-none focus:ring-0',
            'placeholder:text-subtle',
          )}
          autoComplete="off"
        />
        <kbd className="dashboard-ask-bar__kbd hidden sm:inline-flex">⌘K</kbd>
        <button
          type="submit"
          disabled={!canSend}
          aria-label="Ask question"
          className={cn(
            'dashboard-ask-bar__send',
            !canSend && 'cursor-not-allowed',
          )}
        >
          <ArrowUpIcon className="size-4" />
        </button>
      </div>
    </form>
  )
}
