import { useCallback, useEffect, useRef, useState, type ReactNode } from 'react'

import ResizeHandle from '@/components/layout/ResizeHandle'
import { useLayoutContext } from '@/contexts/LayoutContext'
import { useMinWidthMediaQuery } from '@/hooks/useMinWidthMediaQuery'
import {
  CHAT_AREA_MIN_WIDTH,
  CONVERSATION_PANEL_LAYOUT,
  DESKTOP_MIN,
  LAYOUT_STORAGE_KEYS,
  clamp,
  getResponsiveConversationMax,
  readStoredNumber,
  writeStoredNumber,
} from '@/utils/layoutStorage'
import { cn } from '@/utils/cn'

export interface ChatLayoutProps {
  sidebarWidth: number
  sidebarCollapsed: boolean
  conversationList: ReactNode
  chatArea: ReactNode
}

export default function ChatLayout({
  sidebarWidth,
  sidebarCollapsed,
  conversationList,
  chatArea,
}: ChatLayoutProps) {
  const { conversationDrawerOpen, closeConversationDrawer } = useLayoutContext()
  const isSplitView = useMinWidthMediaQuery(DESKTOP_MIN)
  const [panelWidth, setPanelWidth] = useState(() =>
    readStoredNumber(
      LAYOUT_STORAGE_KEYS.conversationPanelWidth,
      CONVERSATION_PANEL_LAYOUT.default,
    ),
  )
  const resizeStartX = useRef(0)
  const resizeStartWidth = useRef(panelWidth)

  const clampPanelWidth = useCallback(
    (width: number) => {
      const maxWidth = getResponsiveConversationMax(
        window.innerWidth,
        sidebarWidth,
        sidebarCollapsed,
      )
      return clamp(width, CONVERSATION_PANEL_LAYOUT.min, maxWidth)
    },
    [sidebarCollapsed, sidebarWidth],
  )

  const persistPanelWidth = useCallback((width: number) => {
    writeStoredNumber(LAYOUT_STORAGE_KEYS.conversationPanelWidth, width)
  }, [])

  const handleResizeStart = useCallback(
    (clientX: number) => {
      resizeStartX.current = clientX
      resizeStartWidth.current = panelWidth
    },
    [panelWidth],
  )

  const handleResize = useCallback(
    (clientX: number) => {
      const delta = clientX - resizeStartX.current
      setPanelWidth(clampPanelWidth(resizeStartWidth.current + delta))
    },
    [clampPanelWidth],
  )

  const handleResizeEnd = useCallback(() => {
    setPanelWidth((current) => {
      const clamped = clampPanelWidth(current)
      persistPanelWidth(clamped)
      return clamped
    })
  }, [clampPanelWidth, persistPanelWidth])

  useEffect(() => {
    const handleViewportChange = () => {
      if (window.innerWidth < DESKTOP_MIN) return
      setPanelWidth((current) => {
        const clamped = clampPanelWidth(current)
        if (clamped !== current) {
          persistPanelWidth(clamped)
        }
        return clamped
      })
    }

    handleViewportChange()
    window.addEventListener('resize', handleViewportChange)
    return () => window.removeEventListener('resize', handleViewportChange)
  }, [clampPanelWidth, persistPanelWidth, sidebarCollapsed, sidebarWidth])

  useEffect(() => {
    if (!conversationDrawerOpen || isSplitView) return
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') closeConversationDrawer()
    }
    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [closeConversationDrawer, conversationDrawerOpen, isSplitView])

  useEffect(() => {
    if (isSplitView) closeConversationDrawer()
  }, [closeConversationDrawer, isSplitView])

  return (
    <div className="flex h-full min-h-0 flex-1 overflow-hidden bg-canvas">
      {isSplitView && (
        <>
          <div
            className={cn(
              'flex h-full min-h-0 shrink-0 flex-col overflow-hidden',
              'border-r border-neutral-200/80 bg-white dark:border-neutral-700/80 dark:bg-neutral-900',
            )}
            style={{
              width: panelWidth,
              minWidth: CONVERSATION_PANEL_LAYOUT.min,
              maxWidth: CONVERSATION_PANEL_LAYOUT.max,
            }}
          >
            {conversationList}
          </div>

          <ResizeHandle
            aria-label="Resize conversation panel"
            onResizeStart={handleResizeStart}
            onResize={handleResize}
            onResizeEnd={handleResizeEnd}
          />
        </>
      )}

      {!isSplitView && (
        <>
          {conversationDrawerOpen && (
            <button
              type="button"
              aria-label="Close conversations panel"
              className="fixed inset-0 z-40 bg-black/50 transition-opacity duration-200"
              onClick={closeConversationDrawer}
            />
          )}

          <div
            className={cn(
              'fixed inset-y-0 right-0 z-50 flex w-[min(88vw,20rem)] flex-col overflow-hidden',
              'border-l border-neutral-200 bg-white shadow-xl',
              'transition-transform duration-200 ease-out dark:border-neutral-700 dark:bg-neutral-900',
              conversationDrawerOpen ? 'translate-x-0' : 'pointer-events-none translate-x-full',
            )}
          >
            {conversationList}
          </div>
        </>
      )}

      <div
        className="flex min-w-0 flex-1 flex-col overflow-hidden"
        style={{ minWidth: isSplitView ? CHAT_AREA_MIN_WIDTH : undefined }}
      >
        {chatArea}
      </div>
    </div>
  )
}
