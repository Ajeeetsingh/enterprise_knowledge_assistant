import { useEffect } from 'react'

import { useToast } from '@/contexts/ToastContext'
import { registerUnauthorizedHandler } from '@/services/api'

/** Shows a toast when the API client clears the session after auth failure. */
export default function SessionExpiredListener() {
  const { showError } = useToast()

  useEffect(() => {
    return registerUnauthorizedHandler(() => {
      showError('Session expired. Please sign in again.')
    })
  }, [showError])

  return null
}
