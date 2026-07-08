import {
  createContext,
  useCallback,
  useContext,
  useMemo,
  useState,
  type ReactNode,
} from 'react'

import ToastContainer, { type ToastItem } from '@/components/ui/ToastContainer'
import type { ToastVariant } from '@/components/ui/Toast'

const DEFAULT_TOAST_DURATION_MS = 5_000

interface ToastContextValue {
  showSuccess: (message: string) => void
  showError: (message: string) => void
  showWarning: (message: string) => void
  showInfo: (message: string) => void
  dismiss: (id: string) => void
}

const ToastContext = createContext<ToastContextValue | null>(null)

function createToastId(): string {
  return crypto.randomUUID()
}

export function ToastProvider({ children }: { children: ReactNode }) {
  const [toasts, setToasts] = useState<ToastItem[]>([])

  const dismiss = useCallback((id: string) => {
    setToasts((current) => current.filter((toast) => toast.id !== id))
  }, [])

  const showToast = useCallback(
    (variant: ToastVariant, message: string, duration = DEFAULT_TOAST_DURATION_MS) => {
      const id = createToastId()
      setToasts((current) => [...current, { id, variant, message }])

      if (duration > 0) {
        window.setTimeout(() => {
          dismiss(id)
        }, duration)
      }
    },
    [dismiss],
  )

  const showSuccess = useCallback(
    (message: string) => showToast('success', message),
    [showToast],
  )
  const showError = useCallback(
    (message: string) => showToast('error', message),
    [showToast],
  )
  const showWarning = useCallback(
    (message: string) => showToast('warning', message),
    [showToast],
  )
  const showInfo = useCallback(
    (message: string) => showToast('info', message),
    [showToast],
  )

  const value = useMemo<ToastContextValue>(
    () => ({
      showSuccess,
      showError,
      showWarning,
      showInfo,
      dismiss,
    }),
    [showSuccess, showError, showWarning, showInfo, dismiss],
  )

  return (
    <ToastContext.Provider value={value}>
      {children}
      <ToastContainer toasts={toasts} onDismiss={dismiss} />
    </ToastContext.Provider>
  )
}

export function useToast(): ToastContextValue {
  const context = useContext(ToastContext)
  if (!context) {
    throw new Error('useToast must be used inside <ToastProvider>')
  }
  return context
}
