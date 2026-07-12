import { useCallback, useEffect, useRef, useState } from 'react'
import { Outlet, useLocation } from 'react-router-dom'

import { PageContainer, Sidebar, TopNavbar } from '@/components/layout'
import AnimatedOutlet from '@/components/layout/AnimatedOutlet'
import MobileShellDrawer from '@/components/layout/MobileShellDrawer'
import ResizeHandle from '@/components/layout/ResizeHandle'
import { LayoutProvider } from '@/contexts/LayoutContext'
import { useMinWidthMediaQuery } from '@/hooks/useMinWidthMediaQuery'
import {
  DESKTOP_MIN,
  LAYOUT_BREAKPOINTS,
  LAYOUT_STORAGE_KEYS,
  SIDEBAR_LAYOUT,
  WIDE_DESKTOP_MIN,
  clamp,
  getResponsiveSidebarMax,
  readStoredNumber,
  shouldUseIconSidebar,
  writeStoredBoolean,
  writeStoredNumber,
} from '@/utils/layoutStorage'

export default function AppLayout() {
  const location = useLocation()
  const isChatRoute = location.pathname === '/chat'
  const isDocumentViewerRoute = /^\/documents\/[^/]+$/.test(location.pathname)
  const isFullHeightRoute = isChatRoute || isDocumentViewerRoute
  const isDesktopNav = useMinWidthMediaQuery(DESKTOP_MIN)
  const isWideDesktop = useMinWidthMediaQuery(WIDE_DESKTOP_MIN)

  const [sidebarCollapsed, setSidebarCollapsed] = useState(() => {
    const stored = localStorage.getItem(LAYOUT_STORAGE_KEYS.sidebarCollapsed)
    if (stored === 'true') return true
    if (stored === 'false') return false
    if (typeof window !== 'undefined') {
      return shouldUseIconSidebar(window.innerWidth)
    }
    return false
  })
  const [sidebarWidth, setSidebarWidth] = useState(() =>
    readStoredNumber(LAYOUT_STORAGE_KEYS.sidebarWidth, SIDEBAR_LAYOUT.default),
  )

  const resizeStartX = useRef(0)
  const resizeStartWidth = useRef(sidebarWidth)

  const effectiveSidebarWidth = sidebarCollapsed ? SIDEBAR_LAYOUT.collapsed : sidebarWidth

  const clampSidebarWidth = useCallback((width: number) => {
    const maxWidth = getResponsiveSidebarMax(window.innerWidth)
    return clamp(width, SIDEBAR_LAYOUT.min, maxWidth)
  }, [])

  const persistSidebarWidth = useCallback((width: number) => {
    writeStoredNumber(LAYOUT_STORAGE_KEYS.sidebarWidth, width)
  }, [])

  const persistSidebarCollapsed = useCallback((collapsed: boolean) => {
    writeStoredBoolean(LAYOUT_STORAGE_KEYS.sidebarCollapsed, collapsed)
  }, [])

  const toggleSidebar = useCallback(() => {
    setSidebarCollapsed((prev) => {
      const next = !prev
      persistSidebarCollapsed(next)
      return next
    })
  }, [persistSidebarCollapsed])

  const handleSidebarResizeStart = useCallback(
    (clientX: number) => {
      resizeStartX.current = clientX
      resizeStartWidth.current = sidebarWidth
    },
    [sidebarWidth],
  )

  const handleSidebarResize = useCallback(
    (clientX: number) => {
      if (sidebarCollapsed) return
      const delta = clientX - resizeStartX.current
      setSidebarWidth(clampSidebarWidth(resizeStartWidth.current + delta))
    },
    [clampSidebarWidth, sidebarCollapsed],
  )

  const handleSidebarResizeEnd = useCallback(() => {
    if (sidebarCollapsed) return
    setSidebarWidth((current) => {
      const clamped = clampSidebarWidth(current)
      persistSidebarWidth(clamped)
      return clamped
    })
  }, [clampSidebarWidth, persistSidebarWidth, sidebarCollapsed])

  useEffect(() => {
    const handleViewportChange = () => {
      const width = window.innerWidth

      setSidebarWidth((current) => {
        const clamped = clampSidebarWidth(current)
        if (clamped !== current) {
          persistSidebarWidth(clamped)
        }
        return clamped
      })

      if (width >= LAYOUT_BREAKPOINTS.mobile && width < WIDE_DESKTOP_MIN) {
        setSidebarCollapsed((prev) => {
          if (prev) return prev
          persistSidebarCollapsed(true)
          return true
        })
      }
    }

    handleViewportChange()
    window.addEventListener('resize', handleViewportChange)
    return () => window.removeEventListener('resize', handleViewportChange)
  }, [clampSidebarWidth, persistSidebarCollapsed, persistSidebarWidth])

  useEffect(() => {
    const mediaQuery = window.matchMedia(
      `(min-width: ${LAYOUT_BREAKPOINTS.mobile}px) and (max-width: ${WIDE_DESKTOP_MIN - 1}px)`,
    )
    const handleChange = (event: MediaQueryListEvent) => {
      if (event.matches) {
        setSidebarCollapsed(true)
        persistSidebarCollapsed(true)
      }
    }
    mediaQuery.addEventListener('change', handleChange)
    return () => mediaQuery.removeEventListener('change', handleChange)
  }, [persistSidebarCollapsed])

  return (
    <LayoutProvider>
      <div className="flex h-screen overflow-hidden bg-canvas">
        <Sidebar
          collapsed={sidebarCollapsed}
          mobileOpen={false}
          width={effectiveSidebarWidth}
          onCloseMobile={() => undefined}
        />

        {isDesktopNav && !sidebarCollapsed && isWideDesktop && (
          <ResizeHandle
            aria-label="Resize navigation sidebar"
            onResizeStart={handleSidebarResizeStart}
            onResize={handleSidebarResize}
            onResizeEnd={handleSidebarResizeEnd}
          />
        )}

        <div className="flex min-w-0 flex-1 flex-col">
          <TopNavbar
            sidebarCollapsed={sidebarCollapsed}
            onToggleSidebar={toggleSidebar}
          />

          <main
            className={
              isFullHeightRoute
                ? 'flex min-h-0 flex-1 flex-col overflow-hidden'
                : 'flex-1 overflow-y-auto scrollbar-thin'
            }
          >
            {isFullHeightRoute ? (
              <AnimatedOutlet className="flex min-h-0 flex-1 flex-col">
                <Outlet context={{ sidebarWidth: effectiveSidebarWidth, sidebarCollapsed }} />
              </AnimatedOutlet>
            ) : (
              <AnimatedOutlet>
                <PageContainer>
                  <Outlet />
                </PageContainer>
              </AnimatedOutlet>
            )}
          </main>
        </div>
      </div>

      <MobileShellDrawer />
    </LayoutProvider>
  )
}
