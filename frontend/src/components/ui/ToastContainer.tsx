import Toast, { type ToastVariant } from './Toast'

export interface ToastItem {
  id: string
  variant: ToastVariant
  message: string
}

export interface ToastContainerProps {
  toasts: ToastItem[]
  onDismiss: (id: string) => void
}

export default function ToastContainer({ toasts, onDismiss }: ToastContainerProps) {
  if (toasts.length === 0) return null

  return (
    <div
      aria-label="Notifications"
      className="pointer-events-none fixed z-[100] flex w-full flex-col gap-2 px-4 top-4 left-1/2 -translate-x-1/2 sm:left-auto sm:translate-x-0 sm:right-4 sm:max-w-sm sm:px-0"
    >
      {toasts.map((toast) => (
        <div key={toast.id} className="pointer-events-auto">
          <Toast
            id={toast.id}
            variant={toast.variant}
            message={toast.message}
            onDismiss={onDismiss}
          />
        </div>
      ))}
    </div>
  )
}
