import EmptyState from '@/components/ui/EmptyState'
import { cn } from '@/utils/cn'

import { GUEST_SUGGESTED_QUESTIONS } from '../constants'

export interface GuestEmptyStateProps {
  onSelectSuggestion: (question: string) => void
  disabled?: boolean
}

export default function GuestEmptyState({
  onSelectSuggestion,
  disabled = false,
}: GuestEmptyStateProps) {
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
      title="Explore Knowra"
      description="Try a product question below. Guest sessions do not access organisational documents."
      className="max-w-md px-4 py-10 sm:px-6"
      action={
        <div className="w-full max-w-sm text-left">
          <p className="mb-2 text-xs font-medium uppercase tracking-wide text-neutral-500 dark:text-neutral-400">
            Suggested questions
          </p>
          <ul className="space-y-2">
            {GUEST_SUGGESTED_QUESTIONS.map((prompt) => (
              <li key={prompt}>
                <button
                  type="button"
                  disabled={disabled}
                  onClick={() => onSelectSuggestion(prompt)}
                  className={cn(
                    'interactive-row w-full rounded-md border border-neutral-200 bg-white px-3 py-2 text-left text-sm text-neutral-600 transition-colors duration-150',
                    'hover:border-accent/40 hover:text-foreground',
                    'dark:border-neutral-700 dark:bg-neutral-900 dark:text-neutral-300',
                    'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent',
                    disabled && 'cursor-not-allowed opacity-60',
                  )}
                >
                  {prompt}
                </button>
              </li>
            ))}
          </ul>
        </div>
      }
    />
  )
}
