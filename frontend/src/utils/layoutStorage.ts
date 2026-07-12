export const LAYOUT_STORAGE_KEYS = {
  sidebarWidth: 'eka-sidebar-width',
  sidebarCollapsed: 'eka-sidebar-collapsed',
  conversationPanelWidth: 'eka-conversation-panel-width',
} as const

export const LAYOUT_BREAKPOINTS = {
  mobile: 768,
  desktop: 1024,
  wide: 1600,
} as const

export const SIDEBAR_LAYOUT = {
  default: 240,
  collapsed: 64,
  min: 180,
  max: 320,
} as const

export const CONVERSATION_PANEL_LAYOUT = {
  default: 350,
  min: 240,
  max: 480,
  tablet: 280,
  mobileDrawer: 320,
} as const

export const CHAT_AREA_MIN_WIDTH = 360
export const WIDE_DESKTOP_MIN = LAYOUT_BREAKPOINTS.wide
export const DESKTOP_MIN = LAYOUT_BREAKPOINTS.desktop

export function clamp(value: number, min: number, max: number): number {
  return Math.min(max, Math.max(min, value))
}

export function readStoredNumber(key: string, fallback: number): number {
  if (typeof window === 'undefined') return fallback
  const stored = localStorage.getItem(key)
  if (!stored) return fallback
  const parsed = Number(stored)
  return Number.isFinite(parsed) ? parsed : fallback
}

export function readStoredBoolean(key: string, fallback: boolean): boolean {
  if (typeof window === 'undefined') return fallback
  const stored = localStorage.getItem(key)
  if (stored === 'true') return true
  if (stored === 'false') return false
  return fallback
}

export function writeStoredNumber(key: string, value: number): void {
  localStorage.setItem(key, String(value))
}

export function writeStoredBoolean(key: string, value: boolean): void {
  localStorage.setItem(key, String(value))
}

export function shouldUseIconSidebar(viewportWidth: number): boolean {
  return viewportWidth >= LAYOUT_BREAKPOINTS.mobile && viewportWidth < WIDE_DESKTOP_MIN
}

export function getResponsiveSidebarMax(viewportWidth: number): number {
  if (viewportWidth >= WIDE_DESKTOP_MIN) return SIDEBAR_LAYOUT.max
  if (viewportWidth >= 1280) return 260
  if (viewportWidth >= DESKTOP_MIN) return 220
  return SIDEBAR_LAYOUT.collapsed
}

export function getResponsiveConversationMax(
  viewportWidth: number,
  sidebarWidth: number,
  sidebarCollapsed: boolean,
): number {
  const effectiveSidebar = sidebarCollapsed ? SIDEBAR_LAYOUT.collapsed : sidebarWidth
  const available = viewportWidth - effectiveSidebar - CHAT_AREA_MIN_WIDTH - 16
  return clamp(available, CONVERSATION_PANEL_LAYOUT.min, CONVERSATION_PANEL_LAYOUT.max)
}
