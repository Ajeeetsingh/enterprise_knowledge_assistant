import { Link } from 'react-router-dom'

import { Button, Card } from '@/components/ui'

export interface ErrorFallbackProps {
  title?: string
  message?: string
  onReload?: () => void
}

export default function ErrorFallback({
  title = 'Something went wrong',
  message = 'An unexpected error occurred while rendering this page. Please try again or return home.',
  onReload,
}: ErrorFallbackProps) {
  function handleReload() {
    if (onReload) {
      onReload()
      return
    }
    window.location.reload()
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-neutral-50 px-4 dark:bg-neutral-950">
      <Card className="max-w-lg text-center">
        <h1 className="text-2xl font-bold text-neutral-900 dark:text-neutral-50">{title}</h1>
        <p className="mt-3 text-sm text-neutral-600 dark:text-neutral-400">{message}</p>
        <div className="mt-6 flex flex-wrap justify-center gap-3">
          <Button onClick={handleReload}>Reload</Button>
          <Link to="/">
            <Button variant="secondary">Go Home</Button>
          </Link>
        </div>
      </Card>
    </div>
  )
}
