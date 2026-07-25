import Button from '@/components/ui/Button'
import { cn } from '@/utils/cn'

export interface GuestContinuePromptProps {
  isImporting: boolean
  error: string | null
  onContinue: () => void
  onStartFresh: () => void
  onRetry?: () => void
}

/**
 * Lightweight post-auth choice — does not import until the user continues.
 */
export default function GuestContinuePrompt({
  isImporting,
  error,
  onContinue,
  onStartFresh,
  onRetry,
}: GuestContinuePromptProps) {
  return (
    <div
      className={cn(
        'border-b border-border-subtle bg-surface-raised px-4 py-3 sm:px-6',
      )}
      role="region"
      aria-label="Continue guest conversation"
    >
      <p className="text-sm font-semibold text-foreground">Continue your guest conversation?</p>
      <p className="mt-1 text-sm text-muted">
        You have a temporary conversation from your demo session. You can continue it in your
        workspace or start fresh.
      </p>
      {error && (
        <div className="mt-2 flex flex-wrap items-center gap-2" role="alert">
          <p className="text-sm text-error-500">{error}</p>
          {onRetry && (
            <button
              type="button"
              className="text-sm font-medium text-accent hover:underline"
              onClick={onRetry}
              disabled={isImporting}
            >
              Retry
            </button>
          )}
        </div>
      )}
      <div className="mt-3 flex flex-wrap gap-2">
        <Button
          type="button"
          size="sm"
          onClick={onContinue}
          isLoading={isImporting}
          disabled={isImporting}
        >
          Continue conversation
        </Button>
        <Button
          type="button"
          size="sm"
          variant="secondary"
          onClick={onStartFresh}
          disabled={isImporting}
        >
          Start fresh
        </Button>
      </div>
    </div>
  )
}
