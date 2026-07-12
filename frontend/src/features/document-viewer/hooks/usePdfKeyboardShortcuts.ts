import { useEffect } from 'react'

interface PdfKeyboardShortcutHandlers {
  onNextPage: () => void
  onPreviousPage: () => void
  onZoomIn: () => void
  onZoomOut: () => void
  onFitWidth: () => void
  onFocusSearch?: () => void
  enabled?: boolean
}

export function usePdfKeyboardShortcuts({
  onNextPage,
  onPreviousPage,
  onZoomIn,
  onZoomOut,
  onFitWidth,
  onFocusSearch,
  enabled = true,
}: PdfKeyboardShortcutHandlers) {
  useEffect(() => {
    if (!enabled) return

    function handleKeyDown(event: KeyboardEvent) {
      const target = event.target
      if (
        target instanceof HTMLInputElement ||
        target instanceof HTMLTextAreaElement ||
        target instanceof HTMLSelectElement
      ) {
        return
      }

      switch (event.key) {
        case 'ArrowDown':
        case 'PageDown':
          event.preventDefault()
          onNextPage()
          break
        case 'ArrowUp':
        case 'PageUp':
          event.preventDefault()
          onPreviousPage()
          break
        case '+':
        case '=':
          if (event.ctrlKey || event.metaKey) {
            event.preventDefault()
            onZoomIn()
          }
          break
        case '-':
          if (event.ctrlKey || event.metaKey) {
            event.preventDefault()
            onZoomOut()
          }
          break
        case '0':
          if (event.ctrlKey || event.metaKey) {
            event.preventDefault()
            onFitWidth()
          }
          break
        case 'f':
          if (event.ctrlKey || event.metaKey) {
            event.preventDefault()
            onFocusSearch?.()
          }
          break
        default:
          break
      }
    }

    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [enabled, onFitWidth, onFocusSearch, onNextPage, onPreviousPage, onZoomIn, onZoomOut])
}
