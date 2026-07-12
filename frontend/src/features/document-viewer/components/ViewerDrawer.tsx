import { useEffect, type ReactNode } from 'react'

import { cn } from '@/utils/cn'

import { CloseIcon } from './ViewerIcons'

export interface ViewerDrawerProps {
  isOpen: boolean
  onClose: () => void
  title: string
  children: ReactNode
  side?: 'left' | 'right' | 'bottom'
  /** When true the drawer overlays content with a backdrop (mobile/tablet). */
  overlay?: boolean
  className?: string
}

export default function ViewerDrawer({
  isOpen,
  onClose,
  title,
  children,
  side = 'right',
  overlay = true,
  className,
}: ViewerDrawerProps) {
  useEffect(() => {
    if (!isOpen || !overlay) return
    function handleKey(event: KeyboardEvent) {
      if (event.key === 'Escape') onClose()
    }
    document.addEventListener('keydown', handleKey)
    return () => document.removeEventListener('keydown', handleKey)
  }, [isOpen, onClose, overlay])

  return (
    <>
      {overlay && (
        <button
          type="button"
          aria-label={`Close ${title}`}
          className={cn(
            'viewer-drawer-backdrop',
            isOpen ? 'viewer-drawer-backdrop--open' : 'viewer-drawer-backdrop--closed',
          )}
          onClick={onClose}
        />
      )}

      <aside
        role="dialog"
        aria-label={title}
        aria-hidden={!isOpen}
        className={cn(
          'viewer-drawer',
          `viewer-drawer--${side}`,
          overlay ? 'viewer-drawer--overlay' : 'viewer-drawer--inline',
          isOpen ? 'viewer-drawer--open' : 'viewer-drawer--closed',
          className,
        )}
      >
        <div className="viewer-drawer-head">
          <h2 className="viewer-drawer-title">{title}</h2>
          <button
            type="button"
            aria-label={`Close ${title}`}
            className="viewer-tb-btn viewer-tb-btn--sm"
            onClick={onClose}
          >
            <CloseIcon width={16} height={16} />
          </button>
        </div>
        <div className="viewer-drawer-body scrollbar-thin">{children}</div>
      </aside>
    </>
  )
}
