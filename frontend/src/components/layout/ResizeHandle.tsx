import { useCallback, useEffect, useRef, useState } from 'react'

import { cn } from '@/utils/cn'

export interface ResizeHandleProps {
  onResize: (clientX: number) => void
  onResizeStart?: (clientX: number) => void
  onResizeEnd?: () => void
  className?: string
  'aria-label'?: string
}

export default function ResizeHandle({
  onResize,
  onResizeStart,
  onResizeEnd,
  className,
  'aria-label': ariaLabel = 'Resize panel',
}: ResizeHandleProps) {
  const [isDragging, setIsDragging] = useState(false)
  const frameRef = useRef<number | null>(null)
  const latestClientX = useRef(0)

  const stopDragging = useCallback(() => {
    setIsDragging(false)
    onResizeEnd?.()
  }, [onResizeEnd])

  const handlePointerDown = useCallback(
    (event: React.PointerEvent<HTMLDivElement>) => {
      event.preventDefault()
      event.currentTarget.setPointerCapture(event.pointerId)
      latestClientX.current = event.clientX
      setIsDragging(true)
      onResizeStart?.(event.clientX)
    },
    [onResizeStart],
  )

  useEffect(() => {
    if (!isDragging) return

    const handlePointerMove = (event: PointerEvent) => {
      latestClientX.current = event.clientX
      if (frameRef.current !== null) return
      frameRef.current = window.requestAnimationFrame(() => {
        frameRef.current = null
        onResize(latestClientX.current)
      })
    }

    const handlePointerUp = () => {
      if (frameRef.current !== null) {
        window.cancelAnimationFrame(frameRef.current)
        frameRef.current = null
      }
      stopDragging()
    }

    window.addEventListener('pointermove', handlePointerMove)
    window.addEventListener('pointerup', handlePointerUp)
    document.body.style.cursor = 'col-resize'
    document.body.style.userSelect = 'none'

    return () => {
      window.removeEventListener('pointermove', handlePointerMove)
      window.removeEventListener('pointerup', handlePointerUp)
      document.body.style.cursor = ''
      document.body.style.userSelect = ''
      if (frameRef.current !== null) {
        window.cancelAnimationFrame(frameRef.current)
        frameRef.current = null
      }
    }
  }, [isDragging, onResize, stopDragging])

  return (
    <div
      role="separator"
      aria-orientation="vertical"
      aria-label={ariaLabel}
      tabIndex={0}
      onPointerDown={handlePointerDown}
      onKeyDown={(event) => {
        if (event.key === 'ArrowLeft' || event.key === 'ArrowRight') {
          event.preventDefault()
        }
      }}
      className={cn(
        'group relative z-10 w-2 shrink-0 touch-none px-0.5',
        'cursor-col-resize',
        'transition-colors duration-200',
        isDragging && 'bg-primary-500/10 dark:bg-primary-400/10',
        className,
      )}
    >
      <div
        aria-hidden
        className={cn(
          'absolute inset-y-3 left-1/2 flex -translate-x-1/2 flex-col items-center justify-center gap-1 rounded-full px-0.5',
          'transition-colors duration-200',
          'group-hover:bg-neutral-200/80 dark:group-hover:bg-neutral-700/80',
          isDragging && 'bg-primary-100 dark:bg-primary-900/40',
        )}
      >
        <span className="block h-1 w-1 rounded-full bg-neutral-400 group-hover:bg-neutral-500 dark:bg-neutral-500 dark:group-hover:bg-neutral-300" />
        <span className="block h-1 w-1 rounded-full bg-neutral-400 group-hover:bg-neutral-500 dark:bg-neutral-500 dark:group-hover:bg-neutral-300" />
        <span className="block h-1 w-1 rounded-full bg-neutral-400 group-hover:bg-neutral-500 dark:bg-neutral-500 dark:group-hover:bg-neutral-300" />
      </div>
      <div
        aria-hidden
        className={cn(
          'absolute inset-y-0 left-1/2 w-px -translate-x-1/2',
          'bg-neutral-200 transition-colors duration-200 dark:bg-neutral-700',
          'group-hover:bg-primary-400 dark:group-hover:bg-primary-500',
          isDragging && 'bg-primary-500 dark:bg-primary-400',
        )}
      />
    </div>
  )
}
