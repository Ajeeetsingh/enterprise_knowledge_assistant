import MessageList from '@/features/chat/components/MessageList'
import { cn } from '@/utils/cn'

import type { GuestMessage } from '../types'
import GuestAuthLink from './GuestAuthLink'

export interface GuestMessageListProps {
  conversationId: string
  messages: GuestMessage[]
}

/**
 * Guest message list that surfaces a Sign In action after auth-required answers.
 */
export default function GuestMessageList({
  conversationId,
  messages,
}: GuestMessageListProps) {
  const showSignIn = messages.some(
    (message) => message.role === 'assistant' && message.requiresAuth,
  )

  return (
    <div className="flex min-h-0 flex-1 flex-col">
      <MessageList
        conversationId={conversationId}
        messages={messages}
        isLoading={false}
      />
      {showSignIn && (
        <div className="shrink-0 border-t border-border-subtle px-4 py-2 sm:px-6">
          <GuestAuthLink
            className={cn(
              'inline-flex items-center rounded-md bg-accent px-3 py-1.5 text-sm font-medium text-white',
              'transition-colors hover:bg-accent-hover',
              'focus-visible:outline-none focus-visible:shadow-[0_0_0_3px_var(--accent-muted)]',
            )}
          >
            Sign In
          </GuestAuthLink>
          <span className="ml-2 text-xs text-muted">
            to ask about your organisation&apos;s documents
          </span>
        </div>
      )}
    </div>
  )
}
