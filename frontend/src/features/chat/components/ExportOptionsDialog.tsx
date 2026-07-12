import { useEffect, useId, useRef } from 'react'

import Button from '@/components/ui/Button'
import Card from '@/components/ui/Card'
import { getExportFormatMeta, type ExportFormat, type ExportOptions } from '@/features/chat/export'
import { cn } from '@/utils/cn'

export interface ExportOptionsDialogProps {
  isOpen: boolean
  format: ExportFormat | null
  options: ExportOptions
  isExporting: boolean
  error: string | null
  onToggleOption: (key: keyof ExportOptions) => void
  onClose: () => void
  onConfirm: () => void
}

const TOGGLES: Array<{ key: keyof ExportOptions; label: string; description: string }> = [
  { key: 'includeSources', label: 'Include Sources', description: 'Cited documents and excerpts for each answer' },
  {
    key: 'includeConfidence',
    label: 'Include Confidence',
    description: 'Answer and per-source confidence scores',
  },
  { key: 'includeTimestamps', label: 'Include Timestamps', description: 'When the conversation and each message occurred' },
  {
    key: 'includeDocumentNames',
    label: 'Include Document Names',
    description: 'Summary list of every document referenced',
  },
]

export default function ExportOptionsDialog({
  isOpen,
  format,
  options,
  isExporting,
  error,
  onToggleOption,
  onClose,
  onConfirm,
}: ExportOptionsDialogProps) {
  const titleId = useId()
  const dialogRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (!isOpen) return
    function handleKeyDown(event: KeyboardEvent) {
      if (event.key === 'Escape' && !isExporting) onClose()
    }
    document.addEventListener('keydown', handleKeyDown)
    return () => document.removeEventListener('keydown', handleKeyDown)
  }, [isOpen, isExporting, onClose])

  useEffect(() => {
    if (isOpen) {
      dialogRef.current?.querySelector<HTMLButtonElement>('button[data-autofocus]')?.focus()
    }
  }, [isOpen])

  if (!isOpen || !format) return null

  const formatMeta = getExportFormatMeta(format)
  const isJson = format === 'json'

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-neutral-950/50 p-4"
      role="presentation"
      onClick={() => !isExporting && onClose()}
    >
      <Card
        className="w-full max-w-md"
        role="dialog"
        aria-modal="true"
        aria-labelledby={titleId}
        onClick={(event) => event.stopPropagation()}
      >
        <div ref={dialogRef} className="flex flex-col gap-5">
          <div>
            <h2 id={titleId} className="text-lg font-semibold text-neutral-900 dark:text-neutral-50">
              Export as {formatMeta.label}
            </h2>
            <p className="mt-1 text-sm text-neutral-500 dark:text-neutral-400">
              Choose what to include. These preferences are remembered for next time.
            </p>
          </div>

          <div className="flex flex-col gap-3">
            {TOGGLES.map((toggle) => (
              <label
                key={toggle.key}
                className={cn(
                  'flex cursor-pointer items-start gap-3 rounded-md border border-neutral-200 p-3',
                  'dark:border-neutral-700',
                  isJson && 'opacity-60',
                )}
              >
                <input
                  type="checkbox"
                  className="mt-0.5 size-4 shrink-0 rounded border-neutral-300 accent-accent dark:border-neutral-600"
                  checked={options[toggle.key]}
                  onChange={() => onToggleOption(toggle.key)}
                />
                <span className="flex flex-col">
                  <span className="text-sm font-medium text-neutral-800 dark:text-neutral-100">
                    {toggle.label}
                  </span>
                  <span className="text-xs text-neutral-500 dark:text-neutral-400">
                    {toggle.description}
                  </span>
                </span>
              </label>
            ))}
          </div>

          {isJson && (
            <p className="rounded-md bg-neutral-100 px-3 py-2 text-xs text-neutral-600 dark:bg-neutral-800 dark:text-neutral-300">
              JSON exports always preserve the full conversation structure and metadata, regardless
              of these toggles.
            </p>
          )}

          {error && (
            <p role="alert" className="text-sm text-error-500 dark:text-error-400">
              {error}
            </p>
          )}

          <div className="flex justify-end gap-2">
            <Button
              type="button"
              variant="secondary"
              data-autofocus
              disabled={isExporting}
              onClick={onClose}
            >
              Cancel
            </Button>
            <Button type="button" isLoading={isExporting} onClick={onConfirm}>
              Download {formatMeta.extension.toUpperCase()}
            </Button>
          </div>
        </div>
      </Card>
    </div>
  )
}
