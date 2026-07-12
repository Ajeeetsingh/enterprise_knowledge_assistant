import { useState } from 'react'

import { useTheme } from '@/contexts/ThemeContext'
import { useToast } from '@/contexts/ToastContext'
import { exportConversation, useExportPreferences, type ExportFormat } from '@/features/chat/export'

import { useConversations } from '../hooks/useConversations'
import { conversationDisplayTitle, type Message } from '../types'
import ExportMenu from './ExportMenu'
import ExportOptionsDialog from './ExportOptionsDialog'

export interface ChatHeaderProps {
  conversationId: string
  messages: Message[]
}

function resolveExportErrorMessage(error: unknown): string {
  if (error instanceof Error && error.message) return error.message
  return 'Unable to export the conversation. Please try again.'
}

/** Thin bar above the message list: conversation title + Export. */
export default function ChatHeader({ conversationId, messages }: ChatHeaderProps) {
  const { data } = useConversations()
  const { theme } = useTheme()
  const { showSuccess, showError } = useToast()
  const { options, toggleOption } = useExportPreferences()

  const [pendingFormat, setPendingFormat] = useState<ExportFormat | null>(null)
  const [isExporting, setIsExporting] = useState(false)
  const [exportError, setExportError] = useState<string | null>(null)

  const conversation = data?.items.find((item) => item.id === conversationId) ?? null
  if (!conversation) return null

  const title = conversationDisplayTitle(conversation)
  const hasMessages = messages.length > 0

  function handleSelectFormat(format: ExportFormat) {
    setExportError(null)
    setPendingFormat(format)
  }

  function closeDialog() {
    if (isExporting) return
    setPendingFormat(null)
    setExportError(null)
  }

  async function handleConfirmExport() {
    if (!pendingFormat || !conversation) return
    setIsExporting(true)
    setExportError(null)

    try {
      // Yield a frame first so the loading spinner actually paints before
      // synchronous generation work (PDF layout in particular) blocks the
      // main thread on long conversations.
      await new Promise<void>((resolve) => requestAnimationFrame(() => resolve()))
      const result = exportConversation({
        conversation,
        messages,
        format: pendingFormat,
        options,
        theme,
      })
      showSuccess(`Downloaded ${result.filename}`)
      setPendingFormat(null)
    } catch (error) {
      const message = resolveExportErrorMessage(error)
      setExportError(message)
      showError(message)
    } finally {
      setIsExporting(false)
    }
  }

  return (
    <header className="flex shrink-0 items-center justify-between gap-3 border-b border-neutral-200/80 bg-surface px-4 py-2.5 dark:border-neutral-700/80 sm:px-6">
      <h2 className="min-w-0 truncate text-sm font-semibold text-neutral-800 dark:text-neutral-100">
        {title}
      </h2>

      <ExportMenu onSelectFormat={handleSelectFormat} disabled={!hasMessages} />

      <ExportOptionsDialog
        isOpen={pendingFormat !== null}
        format={pendingFormat}
        options={options}
        isExporting={isExporting}
        error={exportError}
        onToggleOption={toggleOption}
        onClose={closeDialog}
        onConfirm={() => void handleConfirmExport()}
      />
    </header>
  )
}
