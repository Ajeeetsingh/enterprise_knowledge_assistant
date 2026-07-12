import {
  createContext,
  useCallback,
  useContext,
  useMemo,
  useState,
  type ReactNode,
} from 'react'

import type { Conversation } from '@/features/chat/types'

export interface MobileChatPanelState {
  conversations: Conversation[]
  selectedId: string | null
  isLoading: boolean
  isCreating: boolean
  onSelect: (conversationId: string) => void
  onCreate: () => void
}

interface LayoutContextValue {
  isChatRoute: boolean
  setChatRouteActive: (active: boolean) => void
  conversationDrawerOpen: boolean
  openConversationDrawer: () => void
  closeConversationDrawer: () => void
  mobileShellOpen: boolean
  openMobileShell: () => void
  closeMobileShell: () => void
  mobileChatPanel: MobileChatPanelState | null
  setMobileChatPanel: (panel: MobileChatPanelState | null) => void
}

const LayoutContext = createContext<LayoutContextValue | null>(null)

export function LayoutProvider({ children }: { children: ReactNode }) {
  const [isChatRoute, setChatRouteActive] = useState(false)
  const [conversationDrawerOpen, setConversationDrawerOpen] = useState(false)
  const [mobileShellOpen, setMobileShellOpen] = useState(false)
  const [mobileChatPanel, setMobileChatPanel] = useState<MobileChatPanelState | null>(null)

  const openConversationDrawer = useCallback(() => {
    setConversationDrawerOpen(true)
  }, [])

  const closeConversationDrawer = useCallback(() => {
    setConversationDrawerOpen(false)
  }, [])

  const openMobileShell = useCallback(() => {
    setMobileShellOpen(true)
  }, [])

  const closeMobileShell = useCallback(() => {
    setMobileShellOpen(false)
  }, [])

  const value = useMemo(
    () => ({
      isChatRoute,
      setChatRouteActive,
      conversationDrawerOpen,
      openConversationDrawer,
      closeConversationDrawer,
      mobileShellOpen,
      openMobileShell,
      closeMobileShell,
      mobileChatPanel,
      setMobileChatPanel,
    }),
    [
      isChatRoute,
      conversationDrawerOpen,
      openConversationDrawer,
      closeConversationDrawer,
      mobileShellOpen,
      openMobileShell,
      closeMobileShell,
      mobileChatPanel,
    ],
  )

  return <LayoutContext.Provider value={value}>{children}</LayoutContext.Provider>
}

export function useLayoutContext(): LayoutContextValue {
  const context = useContext(LayoutContext)
  if (!context) {
    throw new Error('useLayoutContext must be used within a LayoutProvider')
  }
  return context
}
