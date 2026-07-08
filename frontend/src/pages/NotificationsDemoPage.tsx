import Button from '@/components/ui/Button'
import Card from '@/components/ui/Card'
import { useToast } from '@/contexts/ToastContext'

export default function NotificationsDemoPage() {
  const { showSuccess, showError, showWarning, showInfo } = useToast()

  return (
    <div className="flex flex-col gap-6">
      <div>
        <h1 className="text-2xl font-bold text-neutral-900 dark:text-neutral-50">
          Notifications Demo
        </h1>
        <p className="mt-1 text-sm text-neutral-500 dark:text-neutral-400">
          Trigger toast notifications to verify the Phase 8.7 notification system.
        </p>
      </div>

      <Card title="Toast variants">
        <div className="flex flex-wrap gap-3">
          <Button onClick={() => showSuccess('Operation completed successfully.')}>
            Success
          </Button>
          <Button variant="danger" onClick={() => showError('Something went wrong.')}>
            Error
          </Button>
          <Button variant="secondary" onClick={() => showWarning('Please review your input.')}>
            Warning
          </Button>
          <Button variant="secondary" onClick={() => showInfo('Here is some helpful information.')}>
            Info
          </Button>
        </div>
      </Card>
    </div>
  )
}
