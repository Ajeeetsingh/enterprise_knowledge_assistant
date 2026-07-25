import { cn } from '@/utils/cn'

import GuestAuthLink from './GuestAuthLink'

export default function GuestChatSidebar() {
  return (
    <aside
      className="guest-chat-sidebar flex h-full min-h-0 w-full flex-col"
      aria-label="Guest conversation"
    >
      <div className="guest-chat-sidebar__header space-y-2 px-4 py-4">
        <p className="guest-chat-sidebar__eyebrow">Guest session</p>
        <p className="guest-chat-sidebar__title">Explore Knowra before signing in.</p>
        <p className="guest-chat-sidebar__subtext">
          Messages stay in this browser tab only and are not saved to your organisation.
        </p>
      </div>

      <div className="flex-1" />

      <div className="guest-chat-sidebar__footer px-4 py-3">
        <GuestAuthLink
          className={cn(
            'block w-full rounded-xl px-3 py-2.5 text-center text-sm font-semibold text-[#4F46E5]',
            'transition-colors hover:bg-[rgba(99,102,241,0.08)] hover:text-[#4338CA]',
            'focus-visible:outline-none focus-visible:shadow-[0_0_0_3px_rgba(99,102,241,0.2)]',
          )}
        >
          Sign in
        </GuestAuthLink>
      </div>
    </aside>
  )
}
