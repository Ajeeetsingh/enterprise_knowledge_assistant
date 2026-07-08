import { useEffect, useId, useRef, useState } from 'react'

import Button from '@/components/ui/Button'
import { cn } from '@/utils/cn'

export interface ConversationMenuProps {
  onRename: () => void
  onDelete: () => void
}

export default function ConversationMenu({ onRename, onDelete }: ConversationMenuProps) {
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
        variant="ghost"
        size="sm"
        aria-haspopup="menu"
        aria-expanded={open}
        aria-controls={menuId}
        aria-label="Conversation actions"
        className="px-2"
        onClick={(event) => {
          event.stopPropagation()
          setOpen((prev) => !prev)
        }}
      >
        ···
      </Button>

      {open && (
        <div
          id={menuId}
          role="menu"
          className={cn(
            'absolute right-0 top-full z-20 mt-1 min-w-[9rem] rounded-md border border-neutral-200 bg-white py-1 shadow-lg',
            'dark:border-neutral-700 dark:bg-neutral-900',
          )}
        >
          <button
            type="button"
            role="menuitem"
            className="block w-full px-3 py-2 text-left text-sm text-neutral-700 hover:bg-neutral-100 focus-visible:bg-neutral-100 focus-visible:outline-none dark:text-neutral-200 dark:hover:bg-neutral-800"
            onClick={(event) => {
              event.stopPropagation()
              setOpen(false)
              onRename()
            }}
          >
            Rename
          </button>
          <button
            type="button"
            role="menuitem"
            className="block w-full px-3 py-2 text-left text-sm text-error-700 hover:bg-error-50 focus-visible:bg-error-50 focus-visible:outline-none dark:text-error-400 dark:hover:bg-error-700/10"
            onClick={(event) => {
              event.stopPropagation()
              setOpen(false)
              onDelete()
            }}
          >
            Delete
          </button>
        </div>
      )}
    </div>
  )
}
