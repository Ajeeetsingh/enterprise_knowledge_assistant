import { useEffect, useRef } from 'react'
import { createPortal } from 'react-dom'

import Button from '@/components/ui/Button'
import { useMinWidthMediaQuery } from '@/hooks/useMinWidthMediaQuery'
import type { Citation } from '@/features/chat/types'
import { DESKTOP_MIN } from '@/utils/layoutStorage'
import { cn } from '@/utils/cn'

import AnswerDetailsContent, { type AnswerMetadata } from './AnswerDetailsContent'

export interface AnswerDetailsPanelProps {
  panelId: string
  isOpen: boolean
  onClose: () => void
  metadata: AnswerMetadata
  onOpenSource: (citation: Citation) => void
  isOpeningSource?: boolean
}

export default function AnswerDetailsPanel({
  panelId,
  isOpen,
  onClose,
  metadata,
  onOpenSource,
  isOpeningSource = false,
}: AnswerDetailsPanelProps) {
  const isDesktop = useMinWidthMediaQuery(DESKTOP_MIN)
  const closeButtonRef = useRef<HTMLButtonElement>(null)
  const hasOpenedRef = useRef(false)

  if (isOpen) {
    hasOpenedRef.current = true
  }

  useEffect(() => {
    if (!isOpen || isDesktop) return

    closeButtonRef.current?.focus()

    function handleKeyDown(event: KeyboardEvent) {
      if (event.key === 'Escape') onClose()
    }

    document.addEventListener('keydown', handleKeyDown)
    return () => document.removeEventListener('keydown', handleKeyDown)
  }, [isDesktop, isOpen, onClose])

  useEffect(() => {
    if (!isOpen || isDesktop) return
    const previousOverflow = document.body.style.overflow
    document.body.style.overflow = 'hidden'
    return () => {
      document.body.style.overflow = previousOverflow
    }
  }, [isDesktop, isOpen])

  if (isDesktop) {
    if (!hasOpenedRef.current) return null

    return (
      <div
        id={panelId}
        className={cn(
          'grid transition-[grid-template-rows] duration-200 ease-out',
          isOpen ? 'grid-rows-[1fr]' : 'grid-rows-[0fr]',
        )}
        aria-hidden={!isOpen}
      >
        <div className="overflow-hidden">
          <div
            className={cn(
              'mt-2 rounded-lg border border-neutral-200 bg-neutral-50/80 p-4',
              'transition-opacity duration-200 ease-out',
              'dark:border-neutral-700 dark:bg-neutral-800/40',
              isOpen ? 'visible opacity-100' : 'invisible opacity-0',
            )}
            inert={!isOpen ? true : undefined}
          >
            <AnswerDetailsContent
              metadata={metadata}
              onOpenSource={onOpenSource}
              isOpeningSource={isOpeningSource}
            />
          </div>
        </div>
      </div>
    )
  }

  if (!isOpen) return null

  const mobileSheet = (
    <>
      <button
        type="button"
        aria-label="Close answer details"
        className="fixed inset-0 z-50 bg-black/40 transition-opacity duration-200"
        onClick={onClose}
      />

      <div
        id={panelId}
        role="dialog"
        aria-modal="true"
        aria-label="Answer details"
        className={cn(
          'fixed inset-x-0 bottom-0 z-50 flex max-h-[85dvh] flex-col',
          'rounded-t-xl border border-neutral-200 bg-white shadow-xl',
          'transition-transform duration-200 ease-out',
          'dark:border-neutral-700 dark:bg-neutral-900',
          'translate-y-0',
        )}
      >
        <div className="flex shrink-0 justify-center py-3" aria-hidden>
          <div className="h-1 w-10 rounded-full bg-neutral-300 dark:bg-neutral-600" />
        </div>

        <div className="flex shrink-0 items-center justify-between border-b border-neutral-200 px-4 pb-3 dark:border-neutral-700">
          <h3 className="text-sm font-semibold text-neutral-900 dark:text-neutral-50">
            Sources
          </h3>
          <Button
            ref={closeButtonRef}
            type="button"
            variant="ghost"
            size="sm"
            aria-label="Close answer details"
            onClick={onClose}
          >
            Close
          </Button>
        </div>

        <div className="min-h-0 flex-1 overflow-y-auto px-4 py-4">
          <AnswerDetailsContent
            metadata={metadata}
            onOpenSource={onOpenSource}
            isOpeningSource={isOpeningSource}
          />
        </div>
      </div>
    </>
  )

  return createPortal(mobileSheet, document.body)
}
