import { NavLink } from 'react-router-dom'

import Button from '@/components/ui/Button'
import { PlusIcon } from '@/components/layout/NavIcons'
import { useAuth } from '@/contexts/AuthContext'
import { useLayoutContext } from '@/contexts/LayoutContext'
import { conversationDisplayTitle } from '@/features/chat/types'
import { canAccessNavItem } from '@/types/permissions'
import { cn } from '@/utils/cn'

import { NAV_GROUPS } from './Sidebar'
import SidebarFooter from './SidebarFooter'
import { NAV_ICON_BY_PATH, NavIcon } from './NavIcons'

export default function MobileShellDrawer() {
  const { user } = useAuth()
  const {
    isChatRoute,
    mobileShellOpen,
    closeMobileShell,
    mobileChatPanel,
    closeConversationDrawer,
  } = useLayoutContext()

  const visibleGroups = NAV_GROUPS.map((group) => ({
    group,
    items: group.items.filter((item) => canAccessNavItem(user, item.roles)),
  })).filter((entry) => entry.items.length > 0)

  if (!mobileShellOpen) return null

  function handleSelectConversation(conversationId: string) {
    mobileChatPanel?.onSelect(conversationId)
    closeMobileShell()
    closeConversationDrawer()
  }

  return (
    <>
      <button
        type="button"
        aria-label="Close menu"
        className="fixed inset-0 z-50 bg-black/50 transition-opacity duration-200 md:hidden"
        onClick={closeMobileShell}
      />

      <aside
        className={cn(
          'fixed inset-y-0 left-0 z-50 flex w-[min(88vw,20rem)] flex-col bg-sidebar',
          'border-r border-border-subtle shadow-elevation-md',
          'transition-transform duration-200 ease-out',
          mobileShellOpen ? 'translate-x-0' : '-translate-x-full',
        )}
        aria-label="Application menu"
      >
        <div className="flex h-14 shrink-0 items-center justify-between border-b border-border-subtle px-4">
          <span className="font-display text-sm font-semibold text-accent">Knowledge Assistant</span>
          <Button
            variant="ghost"
            size="sm"
            className="text-muted hover:bg-overlay hover:text-foreground"
            aria-label="Close menu"
            onClick={closeMobileShell}
          >
            Close
          </Button>
        </div>

        <nav className="scrollbar-thin overflow-y-auto p-3">
          {visibleGroups.map((entry, index) => (
            <div
              key={entry.group.id}
              className={cn(index > 0 && 'mt-6 border-t border-border-subtle pt-6')}
            >
              <p className="mb-2 px-2 text-[11px] font-medium uppercase tracking-[0.06em] text-subtle">
                {entry.group.label}
              </p>
              <ul className="flex flex-col gap-1">
                {entry.items.map((item) => (
                  <li key={item.path}>
                    <NavLink
                      to={item.path}
                      onClick={closeMobileShell}
                      className={({ isActive }) =>
                        cn(
                          'flex items-center gap-3 rounded-md px-3 py-2.5 text-sm font-medium transition-all duration-200 ease-out',
                          'focus-visible:outline-none focus-visible:shadow-[0_0_0_3px_var(--accent-muted)]',
                          isActive
                            ? 'bg-accent-muted text-accent [&_svg]:text-accent'
                            : 'text-muted hover:bg-overlay [&_svg]:text-muted',
                        )
                      }
                    >
                      <NavIcon name={NAV_ICON_BY_PATH[item.path] ?? 'dashboard'} />
                      {item.label}
                    </NavLink>
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </nav>

        {isChatRoute && mobileChatPanel && (
          <div className="scrollbar-thin flex min-h-0 flex-1 flex-col border-t border-border-subtle">
            <div className="flex items-center justify-between gap-2 px-4 py-3">
              <p className="text-[11px] font-medium uppercase tracking-[0.06em] text-subtle">
                Conversations
              </p>
              <button
                type="button"
                className="new-conversation-button px-3 py-1.5 text-xs"
                disabled={mobileChatPanel.isCreating}
                onClick={() => {
                  mobileChatPanel.onCreate()
                  closeMobileShell()
                }}
              >
                <PlusIcon />
                <span>New</span>
              </button>
            </div>
            <ul className="flex-1 overflow-y-auto px-2 pb-4">
              {mobileChatPanel.isLoading ? (
                <li className="px-3 py-4 text-sm text-muted">Loading…</li>
              ) : mobileChatPanel.conversations.length === 0 ? (
                <li className="px-3 py-4 text-sm text-muted">No conversations yet.</li>
              ) : (
                mobileChatPanel.conversations.map((conversation) => {
                  const isSelected = conversation.id === mobileChatPanel.selectedId
                  return (
                    <li
                      key={conversation.id}
                      className={cn(
                        isSelected && 'border-l-[3px] border-l-accent',
                        !isSelected && 'border-l-[3px] border-l-transparent',
                      )}
                    >
                      <button
                        type="button"
                        onClick={() => handleSelectConversation(conversation.id)}
                        className={cn(
                          'interactive-row w-full rounded-md px-3 py-2.5 text-left',
                          isSelected ? 'text-accent' : 'text-muted hover:text-foreground',
                        )}
                      >
                        <p className="truncate text-sm font-medium">
                          {conversationDisplayTitle(conversation)}
                        </p>
                      </button>
                    </li>
                  )
                })
              )}
            </ul>
          </div>
        )}

        <SidebarFooter />
      </aside>
    </>
  )
}
