import { useEffect, useId, useRef, useState } from 'react'

import Button from '@/components/ui/Button'
import { EXPORT_FORMATS, type ExportFormat } from '@/features/chat/export'
import { cn } from '@/utils/cn'

export interface ExportMenuProps {
  onSelectFormat: (format: ExportFormat) => void
  disabled?: boolean
}

function DownloadIcon() {
  return (
    <svg
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.75"
      className="size-4"
      aria-hidden="true"
    >
      <path strokeLinecap="round" strokeLinejoin="round" d="M12 3v12m0 0-4-4m4 4 4-4M5 19h14" />
    </svg>
  )
}

function ChevronDownIcon() {
  return (
    <svg
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      className="size-3.5"
      aria-hidden="true"
    >
      <path strokeLinecap="round" strokeLinejoin="round" d="m6 9 6 6 6-6" />
    </svg>
  )
}

/** "Export" button in the chat header — opens a dropdown of the four export formats. */
export default function ExportMenu({ onSelectFormat, disabled = false }: ExportMenuProps) {
  const menuId = useId()
  const containerRef = useRef<HTMLDivElement>(null)
  const [open, setOpen] = useState(false)

  useEffect(() => {
    if (!open) return

    function handlePointerDown(event: MouseEvent) {
      if (!containerRef.current?.contains(event.target as Node)) {
        setOpen(false)
      }
    }

    function handleKeyDown(event: KeyboardEvent) {
      if (event.key === 'Escape') setOpen(false)
    }

    document.addEventListener('mousedown', handlePointerDown)
    document.addEventListener('keydown', handleKeyDown)
    return () => {
      document.removeEventListener('mousedown', handlePointerDown)
      document.removeEventListener('keydown', handleKeyDown)
    }
  }, [open])

  return (
    <div ref={containerRef} className="relative shrink-0">
      <Button
        type="button"
        variant="secondary"
        size="sm"
        aria-haspopup="menu"
        aria-expanded={open}
        aria-controls={menuId}
        disabled={disabled}
        onClick={() => setOpen((prev) => !prev)}
      >
        <DownloadIcon />
        Export
        <ChevronDownIcon />
      </Button>

      {open && (
        <div
          id={menuId}
          role="menu"
          aria-label="Export conversation as"
          className={cn(
            'absolute right-0 top-full z-20 mt-1.5 min-w-[15rem] rounded-md border border-neutral-200 bg-white py-1.5 shadow-lg',
            'dark:border-neutral-700 dark:bg-neutral-900',
          )}
        >
          {EXPORT_FORMATS.map((format) => (
            <button
              key={format.id}
              type="button"
              role="menuitem"
              className="flex w-full flex-col items-start gap-0.5 px-3 py-2 text-left hover:bg-neutral-100 focus-visible:bg-neutral-100 focus-visible:outline-none dark:hover:bg-neutral-800"
              onClick={() => {
                setOpen(false)
                onSelectFormat(format.id)
              }}
            >
              <span className="text-sm font-medium text-neutral-800 dark:text-neutral-100">
                {format.label}
              </span>
              <span className="text-xs text-neutral-500 dark:text-neutral-400">
                {format.description}
              </span>
            </button>
          ))}
        </div>
      )}
    </div>
  )
}
