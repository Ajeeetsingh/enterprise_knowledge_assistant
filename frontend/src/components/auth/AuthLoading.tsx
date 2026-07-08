import Spinner from '@/components/ui/Spinner'

export interface AuthLoadingProps {
  message?: string
}

export default function AuthLoading({ message = 'Loading…' }: AuthLoadingProps) {
  return (
    <div
      role="status"
      aria-live="polite"
      aria-busy="true"
      className="flex min-h-screen flex-col items-center justify-center gap-4 bg-neutral-50 dark:bg-neutral-950"
    >
      <Spinner size="lg" label={message} />
      <p className="text-sm text-neutral-600 dark:text-neutral-400">{message}</p>
    </div>
  )
}
